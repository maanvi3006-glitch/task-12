-- ── Data Quality / Validation Queries ───────────────────────────────────────

-- 1. Null check per column
SELECT
    SUM(CASE WHEN application_time     IS NULL THEN 1 ELSE 0 END) AS null_application_time,
    SUM(CASE WHEN shortlist_time       IS NULL THEN 1 ELSE 0 END) AS null_shortlist_time,
    SUM(CASE WHEN interview_time       IS NULL THEN 1 ELSE 0 END) AS null_interview_time,
    SUM(CASE WHEN offer_generated_time IS NULL THEN 1 ELSE 0 END) AS null_offer_generated,
    SUM(CASE WHEN offer_signed_time    IS NULL THEN 1 ELSE 0 END) AS null_offer_signed,
    SUM(CASE WHEN offer_hash           IS NULL THEN 1 ELSE 0 END) AS null_offer_hash,
    SUM(CASE WHEN verification_status  IS NULL THEN 1 ELSE 0 END) AS null_verification_status
FROM hiring_events;

-- 2. Duplicate candidate_id check
SELECT candidate_id, COUNT(*) AS cnt
FROM hiring_events
GROUP BY candidate_id
HAVING cnt > 1;

-- 3. Timestamp ordering sanity (should return 0 rows)
SELECT candidate_id, application_time, shortlist_time
FROM hiring_events
WHERE shortlist_time < application_time
   OR interview_time < shortlist_time
   OR offer_generated_time < interview_time
   OR (offer_signed_time IS NOT NULL AND offer_signed_time < offer_generated_time);

-- 4. Freshness check – most recent event
SELECT MAX(application_time) AS latest_event,
       ROUND((JULIANDAY('now') - JULIANDAY(MAX(application_time))) * 24, 1) AS hours_since_last_event
FROM hiring_events;

-- 5. Tamper detection count
SELECT
    verification_status,
    COUNT(*) AS cnt,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) AS pct
FROM hiring_events
GROUP BY verification_status;
