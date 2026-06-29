# PlaceMux · Task 12 · Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    PlaceMux Analytics Pipeline                   │
│                    Task 12 · E-Sign & TTH                        │
└─────────────────────────────────────────────────────────────────┘

  [Hiring Events]          [E-Sign Layer]           [Analytics Layer]
  ┌──────────────┐         ┌─────────────┐          ┌──────────────┐
  │ Faker-based  │ ──────► │ SHA-256     │ ──────►  │ SQLite DB    │
  │ synthetic    │         │ offer hash  │          │ (WAL mode)   │
  │ generator    │         │ generation  │          └──────┬───────┘
  └──────────────┘         └─────────────┘                 │
                                                           │ SQL queries
                                                    ┌──────▼───────┐
                                                    │ Pandas DFs   │
                                                    │ + metrics.py │
                                                    └──────┬───────┘
                                                           │
                                              ┌────────────▼───────────┐
                                              │  Streamlit Dashboard   │
                                              │  5 pages · live data   │
                                              └────────────────────────┘
```

## Database Schema

```
candidates          hiring_events           verification_log
──────────          ─────────────           ────────────────
candidate_id PK     event_id PK             log_id PK
name                candidate_id FK         candidate_id
email               job_id                  job_id
job_id              application_time        verified_at
job_title           shortlist_time          expected_hash
department          interview_time          actual_hash
                    offer_generated_time    result (PASS/FAIL)
                    offer_signed_time       notes
                    offer_hash
                    offer_payload (JSON)
                    verification_status
                    tamper_detected

metric_snapshots
────────────────
snapshot_id PK
snapshot_time
avg_tth_hours
median_tth_hours
fastest_hrs / slowest_hrs
signed_pct / verified_pct
total_candidates
```

## Trust Layer — Tamper Evidence

```
At offer generation:
  payload = {candidate_id, job_id, job_title, salary, offer_date, issuer}
  offer_hash = SHA-256(JSON.canonical(payload))
  stored in hiring_events.offer_hash

At verification:
  recomputed = SHA-256(JSON.canonical(current_payload))
  if recomputed == stored_hash  →  PASS  →  verification_status = 'verified'
  else                          →  FAIL  →  verification_status = 'tampered'
                                            tamper_detected = 1
                                            legal escalation triggered
```

## Key Metric

```
Time-to-Hire (hours) = JULIANDAY(offer_signed_time) - JULIANDAY(application_time)) * 24
```

Decision threshold: **> 168 h** (7 days) → recruiter SLA review.

## File Map

| File | Purpose |
|------|---------|
| `create_database.py` | DB init + schema from DDL |
| `generate_offer_events.py` | Synthetic data + SHA-256 hashing |
| `analytics_queries.py` | All SQL-backed queries → DataFrames |
| `metrics.py` | KPI compute, snapshot persist, metric dictionary |
| `data_quality_checks.py` | Null / dup / freshness / tamper checks |
| `dashboard.py` | Streamlit 5-page live dashboard |
| `export_reports.py` | CSV + static PNG export |
| `sql/create_tables.sql` | DDL |
| `sql/time_to_hire.sql` | Core TTH query |
| `sql/validation.sql` | DQ queries |
