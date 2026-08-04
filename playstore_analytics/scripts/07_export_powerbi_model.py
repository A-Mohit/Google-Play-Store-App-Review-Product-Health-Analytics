"""Stage 6 — Export Power BI model CSVs.
=========================================
Copies the latest star-schema tables from data/app_reviews.db into
exports/powerbi_data_model/ so Power BI can be refreshed with the newest
results without manual file editing.
"""

from pathlib import Path
import sqlite3

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "app_reviews.db"
OUT_DIR = ROOT / "exports" / "powerbi_data_model"

TABLES = [
    "fact_reviews",
    "dim_app",
    "dim_app_version",
    "dim_date",
    "dim_issue_category",
]


def main():
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Missing database: {DB_PATH}. Run scripts/03_load_to_sql.py first."
        )

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    try:
        for table in TABLES:
            df = pd.read_sql_query(f"SELECT * FROM {table}", conn)
            out_path = OUT_DIR / f"{table}.csv"
            df.to_csv(out_path, index=False)
            print(f"[powerbi] wrote {out_path} ({len(df)} rows)")
    finally:
        conn.close()


if __name__ == "__main__":
    main()