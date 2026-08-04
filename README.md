# Google Play Store App Review & Product Health Analytics

End-to-end pipeline: **Google Play reviews → Python extraction → cleaning/NLP → SQL
database → SQL analysis → Excel validation → Power BI → product recommendations.**

This project is designed for a multi-app review dashboard. The data pipeline samples
several apps, and the Power BI dashboard is meant to compare them by app name rather
than focusing on a single app.

> **Note on data source:** this script now does a live pull via the `google-play-scraper`
> library only. It requires normal internet access to `play.google.com`; if scraping is
> unavailable, the script stops instead of fabricating replacement data.

## Pipeline stages

| # | Script | What it does |
|---|---|---|
| 1 | `scripts/01_extract_reviews.py` | Extracts/generates raw reviews → `data/raw_reviews.csv` |
| 2 | `scripts/02_clean_transform.py` | Pandas cleaning, dedup, missing-value handling, text preprocessing, VADER sentiment scoring, rule-based issue-topic tagging, date/feature engineering → `data/reviews_cleaned.csv` |
| 3 | `scripts/03_load_to_sql.py` | Loads cleaned data into a SQLite star schema (`fact_reviews` + 4 dimension tables) → `data/app_reviews.db` |
| 4 | `sql/04_analysis_queries.sql` | 6 analysis queries: JOINs, CTEs, window functions (`LAG`, `RANK`, rolling `AVG`) |
| 5 | `scripts/05_run_sql_analysis.py` | Runs every query in #4 and exports results → `exports/sql_results/*.csv` |
| 6 | `scripts/06_build_excel.py` | Builds `exports/Product_Health_Reviews.xlsx`: raw data + PivotTable-style `COUNTIF`/`COUNTIFS`/`AVERAGEIF`/`AVERAGEIFS` formulas (live, recalculating — not hardcoded numbers) validating every KPI |
| 7 | `scripts/07_export_powerbi_model.py` | Exports the latest SQLite star-schema tables into `exports/powerbi_data_model/*.csv` for Power BI |
| — | `exports/PowerBI_Dashboard_Guide.md` | Full DAX measures and dashboard-layout spec |

Run the whole thing end to end:
```bash
python3 scripts/01_extract_reviews.py
python3 scripts/02_clean_transform.py
python3 scripts/03_load_to_sql.py
python3 scripts/05_run_sql_analysis.py
python3 scripts/06_build_excel.py
python3 scripts/07_export_powerbi_model.py
```
(`sql/04_analysis_queries.sql` is read directly by step 5 — nothing to run separately.)

If you only want to refresh Power BI after data changes, rerun `03_load_to_sql.py`
and then `07_export_powerbi_model.py`.


## Repo structure
```
playstore_analytics/
├── README.md
├── data/
│   ├── raw_reviews.csv
│   ├── reviews_cleaned.csv
│   └── app_reviews.db
├── scripts/
│   ├── 01_extract_reviews.py
│   ├── 02_clean_transform.py
│   ├── 03_load_to_sql.py
│   ├── 05_run_sql_analysis.py
│   ├── 06_build_excel.py
│   └── 07_export_powerbi_model.py
├── sql/
│   └── 04_analysis_queries.sql
└── exports/
    ├── Product_Health_Reviews.xlsx
    ├── sql_results/*.csv
    ├── powerbi_data_model/{fact_reviews,dim_app,dim_app_version,dim_date,dim_issue_category}.csv
    └── PowerBI_Dashboard_Guide.md
```
