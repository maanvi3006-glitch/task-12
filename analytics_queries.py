"""
analytics_queries.py
────────────────────
All SQL-backed analytics queries for the PlaceMux hiring pipeline.
Returns pandas DataFrames for downstream use in metrics.py and dashboard.py.
"""

import pathlib
import sqlite3
import pandas as pd

from create_database import get_connection

SQL_DIR = pathlib.Path(__file__).parent / "sql"


def _conn() -> sqlite3.Connection:
    return get_connection()


def get_time_to_hire_data() -> pd.DataFrame:
    sql = (SQL_DIR / "time_to_hire.sql").read_text()
    first_select = sql.split("-- ── Aggregate")[0].strip()
    conn = _conn()
    df = pd.read_sql_query(first_select, conn, parse_dates=[
        "application_time", "shortlist_time", "interview_time",
        "offer_generated_time", "offer_signed_time",
    ])
    conn.close()
    return df


def get_kpi_summary() -> dict:
    conn = _conn()
    df = pd.read_sql_query(
        """
        SELECT
            COUNT(*)                                                        AS total,
            COUNT(CASE WHEN offer_signed_time IS NOT NULL THEN 1 END)       AS signed,
            COUNT(CASE WHEN verification_status = 'verified' THEN 1 END)    AS verified,
            COUNT(CASE WHEN tamper_detected = 1 THEN 1 END)                 AS tampered
        FROM hiring_events
        """,
        conn,
    )
    conn.close()

    tth_df = get_time_to_hire_data()
    signed = tth_df[tth_df["offer_signed_time"].notna()].copy()

    return {
        "total_candidates": int(df["total"].iloc[0]),
        "signed_count":     int(df["signed"].iloc[0]),
        "verified_count":   int(df["verified"].iloc[0]),
        "tampered_count":   int(df["tampered"].iloc[0]),
        "signed_pct":       round(df["signed"].iloc[0] / df["total"].iloc[0] * 100, 1),
        "verified_pct":     round(df["verified"].iloc[0] / df["total"].iloc[0] * 100, 1),
        "avg_tth_hours":    round(signed["time_to_hire_hours"].mean(), 1),
        "median_tth_hours": round(signed["time_to_hire_hours"].median(), 1),
        "fastest_hrs":      round(signed["time_to_hire_hours"].min(), 1),
        "slowest_hrs":      round(signed["time_to_hire_hours"].max(), 1),
    }


def get_funnel_data() -> pd.DataFrame:
    conn = _conn()
    df = pd.read_sql_query(
        """
        SELECT
            COUNT(*)                                                            AS applied,
            COUNT(CASE WHEN shortlist_time       IS NOT NULL THEN 1 END)        AS shortlisted,
            COUNT(CASE WHEN interview_time       IS NOT NULL THEN 1 END)        AS interviewed,
            COUNT(CASE WHEN offer_generated_time IS NOT NULL THEN 1 END)        AS offer_generated,
            COUNT(CASE WHEN offer_signed_time    IS NOT NULL THEN 1 END)        AS offer_signed,
            COUNT(CASE WHEN verification_status  = 'verified' THEN 1 END)       AS offer_verified
        FROM hiring_events
        """,
        conn,
    )
    conn.close()
    stages = ["Applied", "Shortlisted", "Interviewed", "Offer Generated", "Offer Signed", "Offer Verified"]
    values = df.iloc[0].tolist()
    return pd.DataFrame({"stage": stages, "count": values})


def get_weekly_trend() -> pd.DataFrame:
    conn = _conn()
    df = pd.read_sql_query(
        """
        SELECT
            strftime('%Y-W%W', application_time) AS week,
            COUNT(*)                              AS applications,
            COUNT(offer_signed_time)              AS offers_signed,
            ROUND(AVG(
                CASE WHEN offer_signed_time IS NOT NULL
                THEN (JULIANDAY(offer_signed_time) - JULIANDAY(application_time)) * 24
                END
            ), 1) AS avg_tth_hours
        FROM hiring_events
        GROUP BY week
        ORDER BY week
        """,
        conn,
    )
    conn.close()
    return df


def get_dept_breakdown() -> pd.DataFrame:
    conn = _conn()
    df = pd.read_sql_query(
        """
        SELECT
            c.department,
            COUNT(*)                    AS total,
            COUNT(he.offer_signed_time) AS signed,
            ROUND(AVG(
                CASE WHEN he.offer_signed_time IS NOT NULL
                THEN (JULIANDAY(he.offer_signed_time) - JULIANDAY(he.application_time)) * 24
                END
            ), 1) AS avg_tth_hours
        FROM hiring_events he
        JOIN candidates c ON he.candidate_id = c.candidate_id
        GROUP BY c.department
        ORDER BY avg_tth_hours
        """,
        conn,
    )
    conn.close()
    return df


def get_verification_log() -> pd.DataFrame:
    conn = _conn()
    df = pd.read_sql_query(
        "SELECT * FROM verification_log ORDER BY verified_at DESC LIMIT 50",
        conn,
    )
    conn.close()
    return df


def get_data_freshness() -> dict:
    conn = _conn()
    df = pd.read_sql_query(
        """
        SELECT
            MAX(application_time) AS latest_event,
            ROUND((JULIANDAY('now') - JULIANDAY(MAX(application_time))) * 24, 1)
              AS hours_since
        FROM hiring_events
        """,
        conn,
    )
    conn.close()
    latest = df["latest_event"].iloc[0]
    hours  = df["hours_since"].iloc[0]
    hours  = float(hours) if hours is not None else 9999.0
    return {
        "latest_event": latest,
        "hours_since":  hours,
        "status":       "FRESH" if hours < 48 else "STALE",
    }
