"""
Stage 3 — LOAD INTO SQL
=========================
Loads reviews_cleaned.csv into a SQLite database (app_reviews.db) using a
lightweight star schema:

  fact_reviews        one row per review
  dim_app_version     one row per app version, with release date
  dim_date            one row per calendar date present in the data
  dim_issue_category  lookup table of issue categories

SQLite is used so the whole database ships as a single portable file
(app_reviews.db) that can be opened with any SQL client, or queried directly
with the .sql analysis script. The schema/queries are standard ANSI SQL and
port directly to Postgres/MySQL/SQL Server if needed.
"""

import sqlite3
from pathlib import Path

import pandas as pd

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "reviews_cleaned.csv"
DB_PATH = Path(__file__).resolve().parents[1] / "data" / "app_reviews.db"


def main():
    df = pd.read_csv(DATA_PATH, parse_dates=["review_date", "version_release_date"])

    if DB_PATH.exists():
        DB_PATH.unlink()
    conn = sqlite3.connect(DB_PATH)

    # ---------------- dim_app ----------------
    dim_app = df[["app_id", "app_name"]].drop_duplicates().sort_values("app_name").reset_index(drop=True)
    dim_app.insert(0, "app_key", range(1, len(dim_app) + 1))
    dim_app.to_sql("dim_app", conn, index=False, if_exists="replace")

    # ---------------- dim_app_version ----------------
    dim_version = (
        df[["app_id", "app_version", "version_release_date"]]
        .drop_duplicates()
        .sort_values("version_release_date")
        .reset_index(drop=True)
    )
    dim_version.insert(0, "version_key", range(1, len(dim_version) + 1))
    dim_version.to_sql("dim_app_version", conn, index=False, if_exists="replace")

    # ---------------- dim_date ----------------
    dim_date = pd.DataFrame({"date": pd.to_datetime(df["review_date"].dt.date.unique())})
    dim_date = dim_date.sort_values("date").reset_index(drop=True)
    dim_date["date_key"] = dim_date["date"].dt.strftime("%Y%m%d").astype(int)
    dim_date["year"] = dim_date["date"].dt.year
    dim_date["month"] = dim_date["date"].dt.month
    dim_date["month_name"] = dim_date["date"].dt.strftime("%b %Y")
    dim_date["quarter"] = "Q" + dim_date["date"].dt.quarter.astype(str) + " " + dim_date["date"].dt.year.astype(str)
    dim_date["week_start"] = (dim_date["date"] - pd.to_timedelta(dim_date["date"].dt.weekday, unit="D"))
    dim_date.to_sql("dim_date", conn, index=False, if_exists="replace")

    # ---------------- dim_issue_category ----------------
    dim_issue = pd.DataFrame({
        "issue_category": ["crash", "login", "payment", "ui", "performance", "none"],
        "issue_description": [
            "App crashes, freezes, or force closes",
            "Login, authentication, OTP, or session issues",
            "Payment, transfer, or transaction failures",
            "UI/redesign/navigation complaints",
            "Speed, lag, loading, or battery complaints",
            "No specific product issue mentioned",
        ],
    })
    dim_issue.insert(0, "issue_key", range(1, len(dim_issue) + 1))
    dim_issue.to_sql("dim_issue_category", conn, index=False, if_exists="replace")

    # ---------------- fact_reviews ----------------
    fact = df.merge(dim_app[["app_id", "app_key"]], on="app_id", how="left")
    fact = fact.merge(dim_version[["app_id", "app_version", "version_key"]], on=["app_id", "app_version"], how="left")
    fact = fact.merge(dim_issue[["issue_category", "issue_key"]], on="issue_category", how="left")
    fact["date_key"] = fact["review_date"].dt.strftime("%Y%m%d").astype(int)

    fact_cols = [
        "review_id", "user_name", "rating", "review_text", "review_length",
        "word_count", "sentiment_score", "sentiment_label", "thumbs_up",
        "has_developer_reply", "is_post_release_window",
        "days_since_version_release", "app_key", "version_key", "issue_key", "date_key",
        "review_date",
    ]
    fact = fact[fact_cols]
    fact.to_sql("fact_reviews", conn, index=False, if_exists="replace")

    # helpful indexes for the analysis queries
    cur = conn.cursor()
    cur.execute("CREATE INDEX idx_fact_app ON fact_reviews(app_key)")
    cur.execute("CREATE INDEX idx_fact_version ON fact_reviews(version_key)")
    cur.execute("CREATE INDEX idx_fact_issue ON fact_reviews(issue_key)")
    cur.execute("CREATE INDEX idx_fact_date ON fact_reviews(date_key)")
    conn.commit()

    print("[load] tables written:")
    for t in ["dim_app", "dim_app_version", "dim_date", "dim_issue_category", "fact_reviews"]:
        cnt = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"        {t:<20} {cnt} rows")

    conn.close()
    print(f"[load] wrote {DB_PATH}")


if __name__ == "__main__":
    main()
