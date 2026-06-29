# PlaceMux · Task 12 · 2-Minute Demo Script

## Setup (before demo)
```bash
cd placemux_task12
pip install -r requirements.txt
python create_database.py
python generate_offer_events.py
python metrics.py
python data_quality_checks.py
python export_reports.py
streamlit run dashboard.py
```

---

## DEMO (2 minutes)

### 0:00 — Context (15 sec)
> "This is Task 12 of PlaceMux Phase 2.
> My job: measure Time-to-Hire and prove every signed offer is tamper-evident.
> Everything you're about to see is backed by real queries on real data — not slides."

---

### 0:15 — KPI Overview page (30 sec)
Open **📊 KPI Overview**.

> "Here are our top-line numbers — all live from SQLite.
> Average Time-to-Hire is **[X] hours**.
> [X]% of candidates signed — anything below 80% triggers a recruiter review.
> The funnel shows we lose the most candidates between Offer Generated and Offer Signed —
> that's the stage worth optimising first."

Point to the weekly trend chart:
> "This shows us whether hiring velocity is improving week over week."

---

### 0:45 — Trust Layer / E-Sign page (45 sec)
Open **🔐 Trust Layer / E-Sign**.

> "Every offer generates a SHA-256 hash over the canonical payload —
> candidate ID, job title, salary, issue date.
> That hash is stored in the database at signing time."

Select a **tampered** candidate from the dropdown (look for one with `verification_status = tampered`):

> "Watch what happens when I select this candidate —
> the stored hash was computed before the salary was quietly changed.
> The re-computed hash doesn't match. That's a tamper detected.
> Action: freeze the offer immediately, escalate to Legal."

Select a **verified** candidate:
> "For a clean offer, the hashes match perfectly. Authentic and untampered."

---

### 1:30 — Data Quality page (20 sec)
Open **🔍 Data Quality**.

> "Before trusting any dashboard number, we verify the pipe.
> Null check: all required fields are populated.
> Timestamps: all in correct chronological order — no event before its predecessor.
> Freshness: data is [X] hours old — within our 48-hour SLA."

---

### 1:50 — Decision (10 sec)
> "Bottom line:
> Average Time-to-Hire is **[X] hours** — [below/above] our 168-hour target.
> We have **[N] tampered offers** — [zero is good / escalation required].
> The pipeline is fresh. Every number on this dashboard has a source I can point to."

---

## Key Decision Thresholds to Mention

| Metric | Threshold | Action |
|--------|-----------|--------|
| Avg TTH | > 168 h | Recruiter SLA audit |
| Signed % | < 80 % | Offer-stage drop-off investigation |
| Verified % | < 100 % | Legal escalation |
| Tampered count | > 0 | Freeze offer, forensic audit |
| Data freshness | > 48 h | Pipeline alert |
