"""
Stage 2 — CLEAN, PREPROCESS & FEATURE-ENGINEER
=================================================
Reads data/raw_reviews.csv and produces data/reviews_cleaned.csv

Steps:
  1. Duplicate removal (exact + near-duplicate on review_id)
  2. Missing-value handling (drop unusable rows, impute where reasonable)
  3. Text preprocessing (trim/case-normalize, strip noise)
  4. Feature engineering:
       - review_length, word_count
       - sentiment_score / sentiment_label (VADER)
       - issue_category (rule-based topic tagging: crash / login / payment / ui / performance / none)
       - review_date parts (year, month, week, quarter)
       - days_since_version_release
       - has_developer_reply
"""

import re
from pathlib import Path

import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

RAW_PATH = Path(__file__).resolve().parents[1] / "data" / "raw_reviews.csv"
OUT_PATH = Path(__file__).resolve().parents[1] / "data" / "reviews_cleaned.csv"

# app version release dates (must match extraction stage)
VERSION_RELEASES = {
    "4.1.0": "2025-01-06", "4.2.0": "2025-02-17", "4.3.0": "2025-04-01",
    "4.4.0": "2025-05-12", "4.5.0": "2025-06-23", "4.5.1": "2025-07-07",
    "4.6.0": "2025-08-18", "4.7.0": "2025-10-01", "4.8.0": "2025-11-12",
    "4.9.0": "2025-12-22", "5.0.0": "2026-01-20",
}

ISSUE_KEYWORDS = {
    "crash": ["crash", "force clos", "freeze", "froze", "not responding"],
    "login": ["log in", "login", "log-in", "sign in", "otp", "password", "authentic",
              "face id", "fingerprint", "logged out"],
    "payment": ["payment", "transfer", "transaction", "charged", "refund", "deduct",
                "pay bill", "money"],
    "ui": ["interface", "redesign", "layout", "ui ", "navigat", "button", "design"],
    "performance": ["slow", "lag", "battery", "load", "loading", "performance"],
}

analyzer = SentimentIntensityAnalyzer()


def tag_issue_category(text: str) -> str:
    if not isinstance(text, str) or not text.strip():
        return "none"
    t = text.lower()
    for category, keywords in ISSUE_KEYWORDS.items():
        if any(kw in t for kw in keywords):
            return category
    return "none"


def sentiment_label(compound: float) -> str:
    if compound >= 0.05:
        return "positive"
    if compound <= -0.05:
        return "negative"
    return "neutral"


def main():
    df = pd.read_csv(RAW_PATH)
    n_start = len(df)

    # -------------------- 1. Duplicate removal --------------------
    df = df.drop_duplicates(subset=["app_id", "review_id", "user_name", "review_text", "review_date"])
    n_after_dedup = len(df)

    # -------------------- 2. Missing-value handling --------------------
    # drop rows with no review text at all -- unusable for NLP
    df = df.dropna(subset=["review_text"])
    # rating missing -> impute with the median rating for that issue category later;
    # for now, drop the small number of rows with no rating (can't validate KPI without it)
    df = df.dropna(subset=["rating"])
    df["rating"] = df["rating"].astype(int)

    # reply_text missing simply means "no developer reply" -- keep as flag, not a drop reason
    df["has_developer_reply"] = df["reply_text"].notna().astype(int)

    n_after_missing = len(df)

    # -------------------- 3. Text preprocessing --------------------
    def clean_text(t: str) -> str:
        t = t.strip()
        t = re.sub(r"\s+", " ", t)          # collapse whitespace
        return t

    df["review_text"] = df["review_text"].apply(clean_text)
    df["review_text_normalized"] = df["review_text"].str.lower()

    # -------------------- 4. Feature engineering --------------------
    df["review_date"] = pd.to_datetime(df["review_date"])
    df["review_year"] = df["review_date"].dt.year
    df["review_month"] = df["review_date"].dt.to_period("M").astype(str)
    df["review_week"] = df["review_date"].dt.to_period("W").astype(str)
    df["review_quarter"] = df["review_date"].dt.to_period("Q").astype(str)

    df["review_length"] = df["review_text"].str.len()
    df["word_count"] = df["review_text"].str.split().str.len()

    # sentiment via VADER (rule-based, works well on short review text)
    scores = df["review_text"].apply(analyzer.polarity_scores)
    df["sentiment_score"] = scores.apply(lambda s: s["compound"])
    df["sentiment_label"] = df["sentiment_score"].apply(sentiment_label)

    # rule-based issue/topic tagging
    df["issue_category"] = df["review_text_normalized"].apply(tag_issue_category)

    # For multi-app live data, exact release dates are not supplied by the review API.
    # Use the first observed review date for each app/version as a consistent proxy.
    observed_release = df.groupby(["app_id", "app_version"])["review_date"].transform("min").dt.normalize()
    df["version_release_date"] = observed_release
    df["days_since_version_release"] = (df["review_date"] - df["version_release_date"]).dt.days
    df["days_since_version_release"] = df["days_since_version_release"].clip(lower=0)

    # flag reviews posted within 14 days of a release -- "post-release window"
    df["is_post_release_window"] = (df["days_since_version_release"] <= 14).astype(int)

    df = df.drop(columns=["review_text_normalized"])
    df = df.sort_values("review_date").reset_index(drop=True)

    df.to_csv(OUT_PATH, index=False)

    print("[clean] rows in                :", n_start)
    print("[clean] after dedup             :", n_after_dedup, f"(-{n_start - n_after_dedup})")
    print("[clean] after missing-value drop:", n_after_missing, f"(-{n_after_dedup - n_after_missing})")
    print("[clean] final rows              :", len(df))
    print("[clean] issue_category counts   :\n", df["issue_category"].value_counts())
    print("[clean] sentiment_label counts  :\n", df["sentiment_label"].value_counts())
    print(f"[clean] wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
