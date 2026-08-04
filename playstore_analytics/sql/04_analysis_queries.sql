-- =====================================================================
-- Google Play Store Music Apps Analytics — SQL Analysis
-- Database: app_reviews.db (SQLite)
-- Apps: Spotify, YouTube Music, JioSaavn, SoundCloud, Amazon Music
-- =====================================================================

-- ---------------------------------------------------------------------
-- Q1. Overall app performance ranking
-- ---------------------------------------------------------------------
SELECT
    a.app_name,
    COUNT(*) AS review_count,
    ROUND(AVG(f.rating), 2) AS avg_rating,
    ROUND(AVG(f.sentiment_score), 3) AS avg_sentiment,
    ROUND(100.0 * SUM(CASE WHEN f.sentiment_label = 'positive' THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_positive,
    ROUND(100.0 * SUM(CASE WHEN f.sentiment_label = 'negative' THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_negative,
    ROUND(100.0 * SUM(CASE WHEN f.has_developer_reply = 1 THEN 1 ELSE 0 END) / COUNT(*), 1) AS developer_reply_rate
FROM fact_reviews f
JOIN dim_app a ON f.app_key = a.app_key
GROUP BY a.app_key, a.app_name
ORDER BY avg_rating DESC, avg_sentiment DESC;


-- ---------------------------------------------------------------------
-- Q2. App-version health and change versus previous version within app
-- ---------------------------------------------------------------------
WITH version_stats AS (
    SELECT
        a.app_name,
        v.app_version,
        v.version_release_date,
        COUNT(*) AS review_count,
        ROUND(AVG(f.rating), 2) AS avg_rating,
        ROUND(AVG(f.sentiment_score), 3) AS avg_sentiment
    FROM fact_reviews f
    JOIN dim_app a ON f.app_key = a.app_key
    JOIN dim_app_version v ON f.version_key = v.version_key
    GROUP BY a.app_key, a.app_name, v.version_key, v.app_version, v.version_release_date
)
SELECT
    app_name,
    app_version,
    version_release_date,
    review_count,
    avg_rating,
    avg_sentiment,
    ROUND(avg_rating - LAG(avg_rating) OVER (
        PARTITION BY app_name ORDER BY version_release_date
    ), 2) AS rating_change_vs_prev,
    ROUND(avg_sentiment - LAG(avg_sentiment) OVER (
        PARTITION BY app_name ORDER BY version_release_date
    ), 3) AS sentiment_change_vs_prev
FROM version_stats
ORDER BY app_name, version_release_date;


-- ---------------------------------------------------------------------
-- Q3. Issue-category frequency and share by app
-- ---------------------------------------------------------------------
WITH issue_counts AS (
    SELECT
        a.app_name,
        i.issue_category,
        COUNT(*) AS issue_review_count
    FROM fact_reviews f
    JOIN dim_app a ON f.app_key = a.app_key
    JOIN dim_issue_category i ON f.issue_key = i.issue_key
    GROUP BY a.app_key, a.app_name, i.issue_category
),
app_totals AS (
    SELECT
        a.app_name,
        COUNT(*) AS total_reviews
    FROM fact_reviews f
    JOIN dim_app a ON f.app_key = a.app_key
    GROUP BY a.app_key, a.app_name
)
SELECT
    ic.app_name,
    ic.issue_category,
    ic.issue_review_count,
    at.total_reviews,
    ROUND(100.0 * ic.issue_review_count / at.total_reviews, 1) AS pct_of_app_reviews
FROM issue_counts ic
JOIN app_totals at ON ic.app_name = at.app_name
WHERE ic.issue_category != 'none'
ORDER BY ic.app_name, issue_review_count DESC;


-- ---------------------------------------------------------------------
-- Q4. Monthly rating trend by app with 3-month rolling average
-- ---------------------------------------------------------------------
WITH monthly AS (
    SELECT
        a.app_name,
        d.month_name,
        MIN(d.date) AS month_start,
        COUNT(*) AS review_count,
        ROUND(AVG(f.rating), 2) AS avg_rating,
        ROUND(AVG(f.sentiment_score), 3) AS avg_sentiment
    FROM fact_reviews f
    JOIN dim_app a ON f.app_key = a.app_key
    JOIN dim_date d ON f.date_key = d.date_key
    GROUP BY a.app_key, a.app_name, d.month_name
)
SELECT
    app_name,
    month_name,
    review_count,
    avg_rating,
    avg_sentiment,
    ROUND(AVG(avg_rating) OVER (
        PARTITION BY app_name
        ORDER BY month_start
        ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    ), 2) AS rolling_3mo_avg_rating
FROM monthly
ORDER BY app_name, month_start;


-- ---------------------------------------------------------------------
-- Q5. Pre-vs-post 14-day release impact for each app/version
-- ---------------------------------------------------------------------
WITH release_windows AS (
    SELECT
        a.app_name,
        v.version_key,
        v.app_version,
        v.version_release_date,
        f.rating,
        f.sentiment_score,
        CASE
            WHEN f.review_date < v.version_release_date
                 AND f.review_date >= DATE(v.version_release_date, '-14 days')
                THEN 'pre_release_14d'
            WHEN f.review_date >= v.version_release_date
                 AND f.review_date < DATE(v.version_release_date, '+14 days')
                THEN 'post_release_14d'
            ELSE NULL
        END AS window_label
    FROM dim_app_version v
    JOIN dim_app a ON v.app_id = a.app_id
    JOIN fact_reviews f ON f.app_key = a.app_key
),
agg AS (
    SELECT
        app_name,
        version_key,
        app_version,
        version_release_date,
        window_label,
        COUNT(*) AS review_count,
        ROUND(AVG(rating), 2) AS avg_rating,
        ROUND(AVG(sentiment_score), 3) AS avg_sentiment
    FROM release_windows
    WHERE window_label IS NOT NULL
    GROUP BY app_name, version_key, app_version, version_release_date, window_label
)
SELECT
    pre.app_name,
    pre.app_version,
    pre.version_release_date,
    pre.review_count AS pre_review_count,
    pre.avg_rating AS pre_avg_rating,
    pre.avg_sentiment AS pre_avg_sentiment,
    post.review_count AS post_review_count,
    post.avg_rating AS post_avg_rating,
    post.avg_sentiment AS post_avg_sentiment,
    ROUND(post.avg_rating - pre.avg_rating, 2) AS rating_delta,
    ROUND(post.avg_sentiment - pre.avg_sentiment, 3) AS sentiment_delta
FROM agg pre
JOIN agg post
    ON pre.version_key = post.version_key
    AND pre.window_label = 'pre_release_14d'
    AND post.window_label = 'post_release_14d'
ORDER BY sentiment_delta ASC;


-- ---------------------------------------------------------------------
-- Q6. Top 5 most-liked negative reviews per app
-- ---------------------------------------------------------------------
WITH ranked AS (
    SELECT
        a.app_name,
        f.review_text,
        f.rating,
        f.thumbs_up,
        i.issue_category,
        f.review_date,
        RANK() OVER (
            PARTITION BY a.app_key
            ORDER BY f.thumbs_up DESC
        ) AS thumbs_up_rank
    FROM fact_reviews f
    JOIN dim_app a ON f.app_key = a.app_key
    JOIN dim_issue_category i ON f.issue_key = i.issue_key
    WHERE f.rating <= 2
)
SELECT
    app_name,
    review_text,
    rating,
    thumbs_up,
    issue_category,
    review_date
FROM ranked
WHERE thumbs_up_rank <= 5
ORDER BY app_name, thumbs_up_rank, thumbs_up DESC;


-- ---------------------------------------------------------------------
-- Q7. Developer response rate and review health by app
-- ---------------------------------------------------------------------
SELECT
    a.app_name,
    f.has_developer_reply,
    COUNT(*) AS review_count,
    ROUND(AVG(f.rating), 2) AS avg_rating,
    ROUND(AVG(f.sentiment_score), 3) AS avg_sentiment
FROM fact_reviews f
JOIN dim_app a ON f.app_key = a.app_key
GROUP BY a.app_key, a.app_name, f.has_developer_reply
ORDER BY a.app_name, f.has_developer_reply DESC;


-- ---------------------------------------------------------------------
-- Q8. Worst app/version combinations by rating and negative-review rate
-- ---------------------------------------------------------------------
SELECT
    a.app_name,
    v.app_version,
    v.version_release_date,
    COUNT(*) AS review_count,
    ROUND(AVG(f.rating), 2) AS avg_rating,
    ROUND(AVG(f.sentiment_score), 3) AS avg_sentiment,
    ROUND(100.0 * SUM(CASE WHEN f.sentiment_label = 'negative' THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_negative,
    SUM(CASE WHEN i.issue_category != 'none' THEN 1 ELSE 0 END) AS issue_review_count
FROM fact_reviews f
JOIN dim_app a ON f.app_key = a.app_key
JOIN dim_app_version v ON f.version_key = v.version_key
JOIN dim_issue_category i ON f.issue_key = i.issue_key
GROUP BY a.app_key, a.app_name, v.version_key, v.app_version, v.version_release_date
HAVING COUNT(*) >= 10
ORDER BY avg_rating ASC, pct_negative DESC
LIMIT 20;
