"""
generate_offer_events.py
────────────────────────
Generates realistic synthetic hiring-pipeline events with e-sign tamper-evidence.

Each offer gets a SHA-256 hash over its canonical payload (candidate_id + job_id +
offer_generated_time + salary). A small fraction of rows are intentionally
'tampered' to demonstrate detection.
"""

import hashlib
import json
import logging
import pathlib
import random
import sqlite3
import uuid
from datetime import datetime, timedelta

import pandas as pd
from faker import Faker

from create_database import create_database, get_connection

logging.basicConfig(level=logging.INFO, format="%(levelname)s │ %(message)s")
log = logging.getLogger(__name__)

fake = Faker("en_IN")
random.seed(42)
Faker.seed(42)

DATA_DIR = pathlib.Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

DEPARTMENTS = ["Engineering", "Product", "Design", "Data", "Marketing", "Operations"]
JOB_TITLES = {
    "Engineering": ["Backend Engineer", "Frontend Engineer", "DevOps Engineer", "Mobile Engineer"],
    "Product":     ["Product Manager", "Associate PM", "Senior PM"],
    "Design":      ["UI Designer", "UX Researcher", "Product Designer"],
    "Data":        ["Data Analyst", "Data Scientist", "Analytics Engineer"],
    "Marketing":   ["Growth Marketer", "Content Strategist", "SEO Specialist"],
    "Operations":  ["Operations Manager", "HR Generalist", "Recruiter"],
}
SALARY_RANGE = {
    "Engineering": (900_000, 3_000_000),
    "Product":     (800_000, 2_500_000),
    "Design":      (700_000, 1_800_000),
    "Data":        (800_000, 2_200_000),
    "Marketing":   (600_000, 1_500_000),
    "Operations":  (500_000, 1_200_000),
}

N_CANDIDATES = 120
TAMPER_RATE   = 0.07   # 7 % of signed offers get payload-tampered to demo detection
UNSIGNED_RATE = 0.10   # 10 % never sign


# ── Helpers ──────────────────────────────────────────────────────────────────

def _jitter(base: datetime, min_hrs: float, max_hrs: float) -> datetime:
    delta_hrs = random.uniform(min_hrs, max_hrs)
    return base + timedelta(hours=delta_hrs)


def _hash_payload(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


# ── Generator ────────────────────────────────────────────────────────────────

def generate_candidates(n: int = N_CANDIDATES) -> list[dict]:
    rows = []
    for _ in range(n):
        dept = random.choice(DEPARTMENTS)
        title = random.choice(JOB_TITLES[dept])
        rows.append({
            "candidate_id": str(uuid.uuid4()),
            "name":         fake.name(),
            "email":        fake.email(),
            "job_id":       f"JOB-{random.randint(1000, 1099):04d}",
            "job_title":    title,
            "department":   dept,
        })
    return rows


def generate_events(candidates: list[dict]) -> list[dict]:
    events = []
    base_start = datetime.now() - timedelta(days=60)

    for c in candidates:
        dept = c["department"]
        salary = random.randint(*SALARY_RANGE[dept])

        # Stagger applications over 60 days
        app_time = _jitter(base_start, 0, 60 * 24)
        sl_time  = _jitter(app_time, 12, 96)          # shortlist:   0.5–4 days
        iv_time  = _jitter(sl_time,  24, 120)          # interview:   1–5 days
        og_time  = _jitter(iv_time,  4,  48)           # offer gen:   4–48 h
        os_time  = _jitter(og_time,  1,  72)           # offer sign:  1–72 h

        unsigned = random.random() < UNSIGNED_RATE
        tampered = (not unsigned) and (random.random() < TAMPER_RATE)

        # Build canonical offer payload for hashing
        payload = {
            "candidate_id":  c["candidate_id"],
            "job_id":        c["job_id"],
            "job_title":     c["job_title"],
            "salary_inr":    salary,
            "offer_date":    og_time.isoformat(),
            "issuer":        "PlaceMux-HR",
        }
        offer_hash = _hash_payload(payload)

        if unsigned:
            verification_status = "not_signed"
            os_time_val = None
            offer_hash_val = None
            tamper_flag = 0
        elif tampered:
            # Simulate an offer where the salary was quietly changed after signing
            verification_status = "tampered"
            tamper_flag = 1
            # hash stored in DB still reflects original, but payload has been mutated
            offer_hash_val = offer_hash
            payload["salary_inr"] = salary + random.randint(50_000, 200_000)  # post-sign mutation
            os_time_val = os_time.isoformat()
        else:
            verification_status = "verified"
            tamper_flag = 0
            offer_hash_val = offer_hash
            os_time_val = os_time.isoformat()

        events.append({
            "candidate_id":          c["candidate_id"],
            "job_id":                c["job_id"],
            "application_time":      app_time.isoformat(),
            "shortlist_time":        sl_time.isoformat(),
            "interview_time":        iv_time.isoformat(),
            "offer_generated_time":  og_time.isoformat(),
            "offer_signed_time":     os_time_val,
            "offer_hash":            offer_hash_val,
            "offer_payload":         json.dumps(payload),
            "verification_status":   verification_status,
            "tamper_detected":       tamper_flag,
        })
    return events


# ── Database insert ───────────────────────────────────────────────────────────

def _insert_candidates(conn: sqlite3.Connection, rows: list[dict]) -> None:
    conn.executemany(
        """INSERT OR IGNORE INTO candidates
           (candidate_id, name, email, job_id, job_title, department)
           VALUES (:candidate_id,:name,:email,:job_id,:job_title,:department)""",
        rows,
    )
    conn.commit()
    log.info("Inserted %d candidates", len(rows))


def _insert_events(conn: sqlite3.Connection, events: list[dict]) -> None:
    conn.executemany(
        """INSERT INTO hiring_events
           (candidate_id, job_id,
            application_time, shortlist_time, interview_time,
            offer_generated_time, offer_signed_time,
            offer_hash, offer_payload, verification_status, tamper_detected)
           VALUES
           (:candidate_id,:job_id,
            :application_time,:shortlist_time,:interview_time,
            :offer_generated_time,:offer_signed_time,
            :offer_hash,:offer_payload,:verification_status,:tamper_detected)""",
        events,
    )
    conn.commit()
    log.info("Inserted %d hiring events", len(events))


# ── CSV export ────────────────────────────────────────────────────────────────

def _export_csv(candidates: list[dict], events: list[dict]) -> None:
    cdf = pd.DataFrame(candidates)
    edf = pd.DataFrame(events)
    merged = edf.merge(cdf[["candidate_id", "name", "email", "job_title", "department"]],
                       on="candidate_id")
    out = DATA_DIR / "offer_events.csv"
    merged.to_csv(out, index=False)
    log.info("Exported offer_events.csv → %s", out)


# ── Main ──────────────────────────────────────────────────────────────────────

def run():
    create_database()
    conn = get_connection()

    # Wipe previous synthetic data for idempotent re-runs
    conn.execute("DELETE FROM verification_log")
    conn.execute("DELETE FROM metric_snapshots")
    conn.execute("DELETE FROM hiring_events")
    conn.execute("DELETE FROM candidates")
    conn.commit()

    candidates = generate_candidates()
    events     = generate_events(candidates)

    _insert_candidates(conn, candidates)
    _insert_events(conn, events)
    _export_csv(candidates, events)

    conn.close()
    log.info("✓ Data generation complete — %d candidates seeded.", len(candidates))


if __name__ == "__main__":
    run()
