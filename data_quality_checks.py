"""
data_quality_checks.py
──────────────────────
Runs all data-quality checks against hiring_events and logs results.
Checks:
  1. Null completeness per column
  2. Duplicate candidate_id detection
  3. Timestamp ordering sanity
  4. Data freshness (hours since last event)
  5. Tamper-evidence summary
  6. Offer-hash re-verification (live SHA-256 recompute)
"""

import hashlib
import json
import logging
import pathlib

import pandas as pd

from create_database import get_connection

logging.basicConfig(level=logging.INFO, format="%(levelname)s │ %(message)s")
log = logging.getLogger(__name__)

SQL_DIR = pathlib.Path(__file__).parent / "sql"


# ── Individual checks ─────────────────────────────────────────────────────────

def check_nulls() -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query(
        """
        SELECT
            SUM(CASE WHEN application_time     IS NULL THEN 1 ELSE 0 END) AS null_application_time,
            SUM(CASE WHEN shortlist_time        IS NULL THEN 1 ELSE 0 END) AS null_shortlist_time,
            SUM(CASE WHEN interview_time        IS NULL THEN 1 ELSE 0 END) AS null_interview_time,
            SUM(CASE WHEN offer_generated_time  IS NULL THEN 1 ELSE 0 END) AS null_offer_generated,
            SUM(CASE WHEN offer_signed_time     IS NULL THEN 1 ELSE 0 END) AS null_offer_signed,
            SUM(CASE WHEN offer_hash            IS NULL THEN 1 ELSE 0 END) AS null_offer_hash
        FROM hiring_events
        """,
        conn,
    )
    conn.close()
    result = df.T.rename(columns={0: "null_count"})
    result["status"] = result["null_count"].apply(
        lambda x: "⚠ WARNING" if x > 0 else "✓ OK"
    )
    return result


def check_duplicates() -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query(
        """
        SELECT candidate_id, COUNT(*) AS cnt
        FROM hiring_events
        GROUP BY candidate_id
        HAVING cnt > 1
        """,
        conn,
    )
    conn.close()
    return df


def check_timestamp_ordering() -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query(
        """
        SELECT candidate_id,
               application_time, shortlist_time, interview_time,
               offer_generated_time, offer_signed_time
        FROM hiring_events
        WHERE shortlist_time < application_time
           OR interview_time < shortlist_time
           OR offer_generated_time < interview_time
           OR (offer_signed_time IS NOT NULL AND offer_signed_time < offer_generated_time)
        """,
        conn,
    )
    conn.close()
    return df


def check_freshness() -> dict:
    conn = get_connection()
    row = conn.execute(
        """
        SELECT
            MAX(application_time) AS latest_event,
            ROUND((JULIANDAY('now') - JULIANDAY(MAX(application_time))) * 24, 1) AS hours_since
        FROM hiring_events
        """
    ).fetchone()
    conn.close()
    hours = row["hours_since"] or 9999
    return {
        "latest_event":  row["latest_event"],
        "hours_since":   hours,
        "status":        "FRESH ✓" if hours < 48 else "STALE ⚠",
        "threshold_hrs": 48,
    }


def check_tamper_summary() -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query(
        """
        SELECT
            verification_status,
            COUNT(*) AS count,
            ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) AS pct
        FROM hiring_events
        GROUP BY verification_status
        ORDER BY count DESC
        """,
        conn,
    )
    conn.close()
    return df


def verify_offer_hashes() -> pd.DataFrame:
    """
    Re-computes SHA-256 for every signed offer and compares with stored hash.
    Writes results to verification_log.
    Returns a DataFrame of all verification results.
    """
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT candidate_id, job_id, offer_hash, offer_payload
        FROM hiring_events
        WHERE offer_signed_time IS NOT NULL
          AND offer_hash IS NOT NULL
        """
    ).fetchall()

    results = []
    for row in rows:
        payload = json.loads(row["offer_payload"])
        canonical = json.dumps(payload, sort_keys=True, default=str)
        recomputed = hashlib.sha256(canonical.encode()).hexdigest()
        passed = recomputed == row["offer_hash"]
        result_str = "PASS" if passed else "FAIL"

        conn.execute(
            """
            INSERT INTO verification_log
              (candidate_id, job_id, expected_hash, actual_hash, result, notes)
            VALUES (?,?,?,?,?,?)
            """,
            (
                row["candidate_id"],
                row["job_id"],
                row["offer_hash"],
                recomputed,
                result_str,
                "Hash match" if passed else "TAMPER DETECTED — payload mutated post-sign",
            ),
        )
        results.append({
            "candidate_id":  row["candidate_id"],
            "job_id":        row["job_id"],
            "expected_hash": row["offer_hash"][:16] + "…",
            "actual_hash":   recomputed[:16] + "…",
            "result":        result_str,
        })

    conn.commit()
    conn.close()
    return pd.DataFrame(results)


# ── Full report ───────────────────────────────────────────────────────────────

def run_all_checks(verbose: bool = True) -> dict:
    results = {}

    # 1. Nulls
    null_df = check_nulls()
    results["nulls"] = null_df
    if verbose:
        log.info("\n── Null Check ──\n%s", null_df.to_string())

    # 2. Duplicates
    dup_df = check_duplicates()
    results["duplicates"] = dup_df
    if verbose:
        if dup_df.empty:
            log.info("── Duplicate Check ── ✓ No duplicates found")
        else:
            log.warning("── Duplicate Check ── ⚠ %d duplicate candidate_ids!", len(dup_df))

    # 3. Timestamp ordering
    ts_df = check_timestamp_ordering()
    results["timestamp_ordering"] = ts_df
    if verbose:
        if ts_df.empty:
            log.info("── Timestamp Ordering ── ✓ All timestamps in correct order")
        else:
            log.warning("── Timestamp Ordering ── ⚠ %d out-of-order rows!", len(ts_df))

    # 4. Freshness
    fresh = check_freshness()
    results["freshness"] = fresh
    if verbose:
        log.info("── Data Freshness ── %s  (latest event: %s, %.1f h ago)",
                 fresh["status"], fresh["latest_event"], fresh["hours_since"])

    # 5. Tamper summary
    tamper_df = check_tamper_summary()
    results["tamper_summary"] = tamper_df
    if verbose:
        log.info("\n── Verification Status Summary ──\n%s", tamper_df.to_string(index=False))

    # 6. Live hash verification
    hash_df = verify_offer_hashes()
    results["hash_verification"] = hash_df
    fails = hash_df[hash_df["result"] == "FAIL"] if not hash_df.empty else pd.DataFrame()
    if verbose:
        log.info("── Hash Verification ── %d checked │ %d PASS │ %d FAIL",
                 len(hash_df),
                 len(hash_df[hash_df["result"] == "PASS"]) if not hash_df.empty else 0,
                 len(fails))
        if not fails.empty:
            log.warning("TAMPERED OFFERS DETECTED:\n%s", fails.to_string(index=False))

    return results


if __name__ == "__main__":
    run_all_checks()
