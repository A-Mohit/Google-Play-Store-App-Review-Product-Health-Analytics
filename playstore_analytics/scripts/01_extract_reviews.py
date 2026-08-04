"""
Stage 1 — EXTRACTION
=====================
Pulls Google Play Store review data for a target app.

This script uses the `google-play-scraper` library to pull real reviews.
It requires normal internet access to `play.google.com`; if live scraping
is unavailable, the script stops with a clear error instead of fabricating data.

Output: data/raw_reviews.csv
"""

import csv
from pathlib import Path

APPS = [
    {"app_id": "com.spotify.music", "app_name": "Spotify"},
    {"app_id": "com.google.android.apps.youtube.music", "app_name": "YouTube Music"},
    {"app_id": "com.jio.media.jiobeats", "app_name": "JioSaavn"},
    {"app_id": "com.soundcloud.android", "app_name": "SoundCloud"},
    {"app_id": "com.amazon.mp3", "app_name": "Amazon Music"},
]
OUT_PATH = Path(__file__).resolve().parents[1] / "data" / "raw_reviews.csv"

def try_live_extraction(app_id, app_name, n_reviews=2000):
    try:
        from google_play_scraper import Sort, reviews

        result, _ = reviews(
            app_id,
            lang="en",
            country="us",
            sort=Sort.NEWEST,
            count=n_reviews,
        )
        if not result:
            return None
        rows = []
        for r in result:
            rows.append({
                "app_id": app_id,
                "app_name": app_name,
                "review_id": r.get("reviewId"),
                "user_name": r.get("userName"),
                "rating": r.get("score"),
                "review_text": r.get("content"),
                "thumbs_up": r.get("thumbsUpCount"),
                "app_version": r.get("reviewCreatedVersion"),
                "review_date": r.get("at"),
                "reply_text": r.get("replyContent"),
            })
        return rows
    except Exception as e:
        print(f"[extract] Live scrape unavailable ({e.__class__.__name__}: {e}).")
        return None

def main():
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    all_rows = []

    for app in APPS:
        app_id, app_name = app["app_id"], app["app_name"]
        rows = try_live_extraction(app_id, app_name, n_reviews=20000)
        if rows is None:
            raise RuntimeError(
                f"Live extraction failed for {app_name} ({app_id}). "
                "Run this script on a machine with internet access."
            )
        all_rows.extend(rows)
        print(f"[extract] source=live | rows={len(rows)} | app={app_name} ({app_id})")

    fieldnames = ["app_id", "app_name", "review_id", "user_name", "rating",
                  "review_text", "thumbs_up", "app_version", "review_date", "reply_text"]
    with open(OUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"[extract] total rows={len(all_rows)} | apps={len(APPS)}")
    print(f"[extract] wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
