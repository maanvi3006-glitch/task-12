-- ── Time-to-Hire Core Query ──────────────────────────────────────────────────
-- Time-to-Hire = offer_signed_time − application_time  (in hours)
-- Only candidates who have actually signed are counted in the KPI.
-- All stages are shown for funnel analysis.

SELECT
    he.candidate_id,
    c.name,
    c.job_title,
    c.department,
    he.job_id,

    -- Raw timestamps
    he.application_time,
    he.shortlist_time,
    he.interview_time,
    he.offer_generated_time,
    he.offer_signed_time,

    -- Stage durations (hours)
    ROUND(
        (JULIANDAY(he.shortlist_time) - JULIANDAY(he.application_time)) * 24, 2
    )  AS hours_to_shortlist,

    ROUND(
        (JULIANDAY(he.interview_time) - JULIANDAY(he.shortlist_time)) * 24, 2
    )  AS hours_to_interview,

    ROUND(
        (JULIANDAY(he.offer_generated_time) - JULIANDAY(he.interview_time)) * 24, 2
    )  AS hours_to_offer,

    ROUND(
        (JULIANDAY(he.offer_signed_time) - JULIANDAY(he.offer_generated_time)) * 24, 2
    )  AS hours_to_sign,

    -- ── Primary KPI ──
    ROUND(
        (JULIANDAY(he.offer_signed_time) - JULIANDAY(he.application_time)) * 24, 2
    )  AS time_to_hire_hours,

    -- Trust layer
    he.offer_hash,
    he.verification_status,
    he.tamper_detected

FROM hiring_events he
JOIN candidates c ON he.candidate_id = c.candidate_id
ORDER BY he.application_time;


-- ── Aggregate KPIs ───────────────────────────────────────────────────────────
-- Run separately to get the summary row.

-- SELECT
--     COUNT(*)                                                        AS total_candidates,
--     COUNT(CASE WHEN offer_signed_time IS NOT NULL THEN 1 END)       AS signed_count,
--     COUNT(CASE WHEN verification_status = 'verified' THEN 1 END)    AS verified_count,
--     ROUND(AVG(
--         (JULIANDAY(offer_signed_time) - JULIANDAY(application_time)) * 24
--     ), 2)  AS avg_time_to_hire_hours,
--     ROUND(
--         (JULIANDAY(offer_signed_time) - JULIANDAY(application_time)) * 24, 2
--     )  AS median_time_to_hire_hours      -- use pandas median on the result set
-- FROM hiring_events
-- WHERE offer_signed_time IS NOT NULL;
