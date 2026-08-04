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

## Key findings (from this run's data)

- **v4.3.0 (Apr 2025):** payment-failure complaints spiked to ~29% of that release's
  reviews; avg rating fell **3.94 → 3.31** (‑0.71) and sentiment fell ‑0.20 in the 14-day
  post-release window vs. pre-release.
- **v4.5.0 (Jun 2025):** crash + login complaints spiked (43 crash + 29 login mentions in
  150 reviews); avg rating fell to **2.64**, the worst of any version, with a ‑1.25
  rating delta in the pre/post-release comparison. Largely recovered by the 4.5.1 hotfix.
- **v4.8.0 (Nov 2025):** UI redesign backlash — rating fell ~0.9 pts post-release, driven
  by navigation/layout complaints rather than functional bugs.
- **Developer replies correlate with negative reviews**, not proactive engagement: reviews
  with a reply average **1.92★** vs. **4.08★** for reviews without one — replies are
  reactive support responses, not community-building.
- **Payment issues are the single largest recurring complaint category** overall (1,609
  of 5,910 reviews / ~27%), ahead of UI (788), crashes (243), login (225), and
  performance (162).

## Product recommendations

1. **Gate payment-flow changes behind stronger pre-release QA / staged rollout.** Payment
   is both the highest-volume and most release-sensitive issue category — the 4.3.0 spike
   shows a single release can move overall sentiment materially.
2. **Add crash/ANR monitoring alerts tied to release windows** so a login/crash regression
   like 4.5.0's is caught and hotfixed within days, not weeks — the 4.5.1 hotfix response
   was fast but the damage window still hurt v4.5.0's lifetime rating.
3. **Pilot major UI redesigns with a subset of users first.** The 4.8.0 backlash was about
   navigation, not stability — a phased/opt-in rollout would surface this before a full
   release.
4. **Turn developer replies proactive, not just reactive.** Since replies currently
   correlate almost entirely with damage control, a lightweight triage SLA (reply within
   48h to any 1-2★ review mentioning payment/crash/login) would catch regressions earlier
   and demonstrably improve response-driven sentiment recovery.

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
