"""
metrics.py
──────────
Computes and persists metric snapshots.
Produces the metric dictionary (what each number means + the decision it drives).
Every metric traces: EVENT → METRIC → DECISION.
"""

import logging
import pathlib

import pandas as pd

from analytics_queries import get_kpi_summary, get_time_to_hire_data
from create_database import get_connection

logging.basicConfig(level=logging.INFO, format="%(levelname)s │ %(message)s")
log = logging.getLogger(__name__)

DATA_DIR = pathlib.Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)


# ── Metric dictionary ─────────────────────────────────────────────────────────

METRIC_DICTIONARY = [
    {
        "metric_name": "Time-to-Hire (avg)",
        "definition":  "Average hours from application_submitted to offer_signed across all signed candidates.",
        "source_table":"hiring_events",
        "source_columns":"application_time, offer_signed_time",
        "formula":     "AVG((JULIANDAY(offer_signed_time) - JULIANDAY(application_time)) * 24)",
        "event_chain": "application_submitted → shortlisted → interview_completed → offer_generated → offer_signed",
        "decision":    "If avg TTH > 168 h (7 days), trigger recruiter SLA review and pipeline audit.",
        "owner":       "Data Analyst",
        "unit":        "hours",
        "refresh":     "real-time on query",
    },
    {
        "metric_name": "Time-to-Hire (median)",
        "definition":  "Median hours from application to signed offer — less sensitive to outliers than mean.",
        "source_table":"hiring_events",
        "source_columns":"application_time, offer_signed_time",
        "formula":     "MEDIAN((JULIANDAY(offer_signed_time) - JULIANDAY(application_time)) * 24)",
        "event_chain": "application_submitted → offer_signed",
        "decision":    "Use alongside avg; divergence signals long-tail bottlenecks worth investigating.",
        "owner":       "Data Analyst",
        "unit":        "hours",
        "refresh":     "real-time on query",
    },
    {
        "metric_name": "Signed Offer %",
        "definition":  "Percentage of candidates who reached offer_signed vs total who applied.",
        "source_table":"hiring_events",
        "source_columns":"offer_signed_time",
        "formula":     "COUNT(offer_signed_time) / COUNT(*) * 100",
        "event_chain": "application_submitted → offer_signed",
        "decision":    "Drop below 80 % → investigate offer-stage drop-off; check competing offers.",
        "owner":       "Recruiting Ops",
        "unit":        "%",
        "refresh":     "real-time on query",
    },
    {
        "metric_name": "Verification Success %",
        "definition":  "Percentage of offers whose SHA-256 hash matches the stored payload (tamper-free).",
        "source_table":"hiring_events",
        "source_columns":"verification_status, offer_hash, offer_payload",
        "formula":     "COUNT(CASE WHEN verification_status='verified') / COUNT(*) * 100",
        "event_chain": "offer_generated → hash_stored → offer_signed → hash_verified",
        "decision":    "Any value < 100 % triggers immediate legal & compliance escalation.",
        "owner":       "Compliance / Legal",
        "unit":        "%",
        "refresh":     "real-time on query",
    },
    {
        "metric_name": "Tampered Offers Detected",
        "definition":  "Count of offers where re-computed SHA-256 does not match the stored hash.",
        "source_table":"hiring_events + verification_log",
        "source_columns":"tamper_detected, offer_hash, offer_payload",
        "formula":     "COUNT(CASE WHEN tamper_detected=1)",
        "event_chain": "offer_signed → verify_hash → FAIL → tamper_detected=1",
        "decision":    "Any count > 0 → freeze offer; notify legal; launch forensic audit.",
        "owner":       "Compliance / Legal",
        "unit":        "count",
        "refresh":     "real-time on query",
    },
    {
        "metric_name": "Fastest Hire",
        "definition":  "Minimum Time-to-Hire in hours across all signed candidates.",
        "source_table":"hiring_events",
        "source_columns":"application_time, offer_signed_time",
        "formula":     "MIN((JULIANDAY(offer_signed_time) - JULIANDAY(application_time)) * 24)",
        "event_chain": "application_submitted → offer_signed",
        "decision":    "Benchmark for recruiter best-practice; use to set SLA targets.",
        "owner":       "Data Analyst",
        "unit":        "hours",
        "refresh":     "real-time on query",
    },
    {
        "metric_name": "Slowest Hire",
        "definition":  "Maximum Time-to-Hire in hours — signals worst-case pipeline stalls.",
        "source_table":"hiring_events",
        "source_columns":"application_time, offer_signed_time",
        "formula":     "MAX((JULIANDAY(offer_signed_time) - JULIANDAY(application_time)) * 24)",
        "event_chain": "application_submitted → offer_signed",
        "decision":    "Outlier investigation trigger; if > 30 days, review interview scheduling SLA.",
        "owner":       "Data Analyst",
        "unit":        "hours",
        "refresh":     "real-time on query",
    },
]


# ── Snapshot persistence ──────────────────────────────────────────────────────

def persist_snapshot(kpis: dict) -> None:
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO metric_snapshots
          (avg_tth_hours, median_tth_hours, fastest_hrs, slowest_hrs,
           signed_pct, verified_pct, total_candidates)
        VALUES (?,?,?,?,?,?,?)
        """,
        (
            kpis["avg_tth_hours"],
            kpis["median_tth_hours"],
            kpis["fastest_hrs"],
            kpis["slowest_hrs"],
            kpis["signed_pct"],
            kpis["verified_pct"],
            kpis["total_candidates"],
        ),
    )
    conn.commit()
    conn.close()
    log.info("Metric snapshot persisted ✓")


# ── Exports ───────────────────────────────────────────────────────────────────

def export_metric_dictionary() -> pathlib.Path:
    out = DATA_DIR / "metric_dictionary.csv"
    pd.DataFrame(METRIC_DICTIONARY).to_csv(out, index=False)
    log.info("Metric dictionary exported → %s", out)
    return out


def export_time_to_hire_csv() -> pathlib.Path:
    df  = get_time_to_hire_data()
    out = DATA_DIR / "time_to_hire_export.csv"
    df.to_csv(out, index=False)
    log.info("Time-to-hire export → %s  (%d rows)", out, len(df))
    return out


# ── Main ──────────────────────────────────────────────────────────────────────

def run():
    kpis = get_kpi_summary()
    log.info("─" * 50)
    log.info("KPI SUMMARY")
    log.info("─" * 50)
    for k, v in kpis.items():
        log.info("  %-25s %s", k, v)
    log.info("─" * 50)

    persist_snapshot(kpis)
    export_metric_dictionary()
    export_time_to_hire_csv()


if __name__ == "__main__":
    run()
