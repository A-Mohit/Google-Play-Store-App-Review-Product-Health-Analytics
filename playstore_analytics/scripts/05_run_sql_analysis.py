"""
Stage 4 — RUN SQL ANALYSIS
============================
Executes each named query block in sql/04_analysis_queries.sql against
app_reviews.db, prints a preview of each result, and writes each result
set to exports/sql_results/<name>.csv for use in Excel validation and the
Power BI data model.
"""

import re
import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "app_reviews.db"
SQL_PATH = ROOT / "sql" / "04_analysis_queries.sql"
OUT_DIR = ROOT / "exports" / "sql_results"


def split_queries(sql_text: str):
    """Split the .sql file into (label, query) pairs on dashed '-- ---' rule lines.
    Header blocks (containing 'Qn.') and their SQL body appear as consecutive
    parts once split on the dashed rule lines."""
    parts = re.split(r"\n-- -{20,}\n", sql_text)
    queries = []
    for i, part in enumerate(parts):
        m = re.search(r"--\s*(Q\d)\.\s*(.*)", part)
        if not m or i + 1 >= len(parts):
            continue
        qnum, rest_of_label = m.group(1), m.group(2)
        body = parts[i + 1].strip().rstrip(";").strip()
        queries.append((f"{qnum}. {rest_of_label}", body))
    return queries


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    sql_text = SQL_PATH.read_text()

    queries = split_queries(sql_text)
    print(f"[sql] found {len(queries)} labeled query blocks\n")

    for label, query in queries:
        # strip trailing inline comment lines from label for filename
        short = re.match(r"(Q\d)\.\s*(.*)", label).group(2)
        slug = re.sub(r"[^a-z0-9]+", "_", short.lower()).strip("_")[:60]
        try:
            df = pd.read_sql_query(query, conn)
        except Exception as e:
            print(f"[sql] ERROR running {label}: {e}\n")
            continue
        out_path = OUT_DIR / f"{label.split('.')[0].lower()}_{slug}.csv"
        df.to_csv(out_path, index=False)
        print(f"[sql] {label}")
        print(f"       -> {len(df)} rows -> {out_path.name}")
        print(df.head(5).to_string(index=False))
        print()

    conn.close()


if __name__ == "__main__":
    main()
