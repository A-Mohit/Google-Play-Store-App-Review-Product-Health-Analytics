> **Note on data source:** this is for your reference only.
> This is what I did to explain the data and extract insights.
> You can make your own dashboard with the data.
> This is only for educational purposes, and using github copilot
> during the development was helpful.

# Power BI — Product Health Dashboard Build Guide

Power BI Desktop can't be run inside this environment, so instead of a fake/undeliverable
`.pbix`, this is the exact data model, relationships, and DAX needed to build the real
dashboard in ~15 minutes. The five CSVs in `powerbi_data_model/` are the fully-prepared
star schema — import them as-is.

## 1. Import & relationships

Get Data → Text/CSV → import all five files from `powerbi_data_model/`:

| Table | Role | Rows |
|---|---|---|
| `fact_reviews` | Fact table | 10,000 |
| `dim_app` | Dimension | 5 |
| `dim_app_version` | Dimension | 389 |
| `dim_date` | Dimension | 55 |
| `dim_issue_category` | Dimension | 6 |

In **Model view**, create these relationships (all 1-to-many, single direction, from dim → fact):

- `dim_app[app_key]` → `fact_reviews[app_key]`
- `dim_app_version[version_key]` → `fact_reviews[version_key]`
- `dim_issue_category[issue_key]` → `fact_reviews[issue_key]`
- `dim_date[date_key]` → `fact_reviews[date_key]`

Mark `dim_date` as a **Date table** (Table tools → Mark as date table → `date` column).

## 2. DAX measures

Create a new Measures table (Model view → Enter Data → empty table named `_Measures`), then add:

```dax
Total Reviews = COUNTROWS(fact_reviews)

Avg Rating = AVERAGE(fact_reviews[rating])

Avg Sentiment = AVERAGE(fact_reviews[sentiment_score])

% Negative Reviews =
DIVIDE(
    CALCULATE(COUNTROWS(fact_reviews), fact_reviews[sentiment_label] = "negative"),
    [Total Reviews]
)

% Positive Reviews =
DIVIDE(
    CALCULATE(COUNTROWS(fact_reviews), fact_reviews[sentiment_label] = "positive"),
    [Total Reviews]
)

Prev Version Avg Rating =
CALCULATE(
    [Avg Rating],
    FILTER(
        ALL(dim_app_version),
        dim_app_version[version_release_date] =
            CALCULATE(MAX(dim_app_version[version_release_date]),
                FILTER(ALL(dim_app_version),
                    dim_app_version[version_release_date] < MIN(dim_app_version[version_release_date])))
    )
)

Rating Change vs Prev Version = [Avg Rating] - [Prev Version Avg Rating]

Post-Release Avg Rating (14d) =
CALCULATE([Avg Rating], fact_reviews[is_post_release_window] = 1)

Developer Reply Rate =
DIVIDE(
    CALCULATE(COUNTROWS(fact_reviews), fact_reviews[has_developer_reply] = 1),
    [Total Reviews]
)

Rolling 3-Month Avg Rating =
AVERAGEX(
    DATESINPERIOD(dim_date[date], MAX(dim_date[date]), -3, MONTH),
    CALCULATE([Avg Rating])
)
```

## 3. Dashboard pages & visuals

**Best dashboard layout for results**
Use three pages rather than a wide, corporate-style report. This keeps the analysis readable and makes the strongest signals easier to spot.

**Page 1 — App Overview**
- KPI cards: `Total Reviews`, `Avg Rating`, `Avg Sentiment`, `% Negative Reviews`
- Line chart: `Avg Rating` and `Rolling 3-Month Avg Rating` by `dim_date[month_name]`, split by `dim_app[app_name]`
- Stacked bar: review count by `sentiment_label`, by month, with `dim_app[app_name]` in the legend
- Slicer: `dim_app[app_name]`

**Page 2 — Version and Issue Analysis**
- Clustered bar: `Avg Rating` and `Avg Sentiment` by `dim_app_version[app_version]`
- Matrix: `app_name` (rows) × `issue_category` (columns), values = review count, with conditional formatting
- Waterfall or bar chart: `Rating Change vs Prev Version`
- Donut chart: review share by `issue_category`

**Page 3 — Release Impact**
- Table/matrix: pre vs. post 14-day window per app/version (`is_post_release_window` as the slicer field, or replicate the SQL pre/post logic as a calculated table)
- Table: top complaints where `rating <= 2`, sorted by `thumbs_up` descending
- Slicers: `dim_app[app_name]`, `app_version`, `issue_category`, `sentiment_label`, date range

If you want one "best" page for quick results, make Page 1 the default landing page. It gives the fastest read on app health, trend direction, and which app needs attention.

## 4. Suggested filters/slicers (all pages)
`dim_app[app_name]`, `app_version`, `issue_category`, `sentiment_label`, date range (`dim_date[date]`)

## 5. Known signal in this dataset (what the dashboard should surface)
- **v4.3.0** (Apr 1, 2025): payment-failure complaints spike, rating drops ~0.7 pts
- **v4.5.0** (Jun 23, 2025): crash + login complaints spike, rating drops ~1.3 pts (partially
  recovered by hotfix v4.5.1)
- **v4.8.0** (Nov 12, 2025): UI redesign backlash, rating drops ~0.9 pts, mixed sentiment
- Reviews with a developer reply skew heavily negative (avg rating 1.92 vs. 4.08) — replies
  are reactive/support-driven, not proactive engagement
