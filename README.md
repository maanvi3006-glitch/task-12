# PlaceMux — Task 12 · E-Sign Integration & Tamper-Evidence
**Data Analyst · Phase 2 · Week 4**

> **Primary KPI:** Time-to-Hire (hours from `application_submitted` → `offer_signed`)
> **Trust Layer:** SHA-256 offer hashing with live tamper detection

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Initialise database
python create_database.py

# 3. Generate 120 synthetic hiring events (with tamper simulation)
python generate_offer_events.py

# 4. Compute and persist KPIs
python metrics.py

# 5. Run data quality + hash verification
python data_quality_checks.py

# 6. Export reports (CSV + PNG)
python export_reports.py

# 7. Launch live dashboard
streamlit run dashboard.py
```

---

## Project Structure

```
placemux_task12/
├── create_database.py          DB init + schema
├── generate_offer_events.py    Synthetic data + SHA-256 hashing
├── analytics_queries.py        SQL-backed analytics → DataFrames
├── metrics.py                  KPI compute, snapshots, metric dict
├── data_quality_checks.py      Null / dup / freshness / tamper checks
├── dashboard.py                Streamlit 5-page live dashboard
├── export_reports.py           CSV + static PNG export
├── requirements.txt
├── README.md
├── database/
│   └── placemux.db             SQLite (WAL mode)
├── data/
│   ├── offer_events.csv
│   ├── metric_dictionary.csv
│   └── time_to_hire_export.csv
├── sql/
│   ├── create_tables.sql
│   ├── time_to_hire.sql
│   └── validation.sql
├── reports/
│   ├── dashboard_export.png
│   └── metrics_summary.csv
└── docs/
    ├── architecture.md
    └── demo_script.md
```

---

## KPIs Tracked

| Metric | Definition | Decision |
|--------|-----------|----------|
| Avg Time-to-Hire | Mean hours: applied → signed | > 168 h → SLA review |
| Median Time-to-Hire | Median (outlier-robust) | Divergence from mean → investigate tail |
| Signed Offer % | Signed / Total | < 80 % → drop-off investigation |
| Verification % | Verified / Total | < 100 % → legal escalation |
| Tampered Count | Offers with hash mismatch | Any > 0 → freeze + audit |
| Fastest / Slowest | Min / Max TTH | Benchmarks for SLA setting |

---

## Trust Layer

Each offer gets a **SHA-256 hash** over its canonical JSON payload:
```json
{
  "candidate_id": "...",
  "job_id": "...",
  "job_title": "...",
  "salary_inr": 1200000,
  "offer_date": "2025-06-01T10:00:00",
  "issuer": "PlaceMux-HR"
}
```

At verification, the hash is **recomputed live** and compared with the stored value.
Any mismatch → `tamper_detected = 1` → logged in `verification_log`.

---

## Dashboard Pages

| Page | Content |
|------|---------|
| 📊 KPI Overview | Cards, funnel, weekly trend, dept breakdown |
| ⏱ TTH Deep Dive | Distribution, stage box plots, scatter, raw table |
| 🔐 Trust Layer | Tamper status, live hash verifier, verification log |
| 🔍 Data Quality | Null, duplicate, timestamp, freshness, hash checks |
| 📖 Metric Dictionary | Source → formula → decision for every number |

---

## Scoring Alignment (Task 12 · 100 pts)

| Criterion | How this project satisfies it |
|-----------|-------------------------------|
| Core deliverable — TTH built & demoable (50) | `analytics_queries.py` + live dashboard page |
| Real-data quality & correctness (20) | 120 synthetic rows, DQ checks, freshness SLA |
| Live verification & evidence (15) | Streamlit live hash verifier, real numbers |
| Dependency, failure & edge-case handling (15) | Unsigned offers, tampered offers, null handling |
"# task-12" 
