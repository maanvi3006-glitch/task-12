-- PlaceMux · Task 12 · Schema
-- Hiring pipeline events + e-sign tamper-evidence layer

CREATE TABLE IF NOT EXISTS candidates (
    candidate_id    TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    email           TEXT NOT NULL,
    job_id          TEXT NOT NULL,
    job_title       TEXT NOT NULL,
    department      TEXT NOT NULL,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS hiring_events (
    event_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id          TEXT NOT NULL,
    job_id                TEXT NOT NULL,
    application_time      TIMESTAMP,
    shortlist_time        TIMESTAMP,
    interview_time        TIMESTAMP,
    offer_generated_time  TIMESTAMP,
    offer_signed_time     TIMESTAMP,
    offer_hash            TEXT,
    offer_payload         TEXT,
    verification_status   TEXT CHECK(verification_status IN ('pending','verified','tampered','not_signed')),
    tamper_detected       INTEGER DEFAULT 0,
    created_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (candidate_id) REFERENCES candidates(candidate_id)
);

CREATE TABLE IF NOT EXISTS verification_log (
    log_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id    TEXT NOT NULL,
    job_id          TEXT NOT NULL,
    verified_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expected_hash   TEXT,
    actual_hash     TEXT,
    result          TEXT CHECK(result IN ('PASS','FAIL')),
    notes           TEXT
);

CREATE TABLE IF NOT EXISTS metric_snapshots (
    snapshot_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_time   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    avg_tth_hours   REAL,
    median_tth_hours REAL,
    fastest_hrs     REAL,
    slowest_hrs     REAL,
    signed_pct      REAL,
    verified_pct    REAL,
    total_candidates INTEGER
);
