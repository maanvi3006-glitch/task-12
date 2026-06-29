"""
dashboard.py
────────────
PlaceMux · Task 12 · Decision-Grade Streamlit Dashboard
Run:  streamlit run dashboard.py
"""

import hashlib
import json
import pathlib
import sqlite3

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from analytics_queries import (
    get_data_freshness,
    get_dept_breakdown,
    get_funnel_data,
    get_kpi_summary,
    get_time_to_hire_data,
    get_verification_log,
    get_weekly_trend,
)
from data_quality_checks import (
    check_nulls,
    check_tamper_summary,
    run_all_checks,
    verify_offer_hashes,
)
from create_database import get_connection

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="PlaceMux · Task 12 · Time-to-Hire",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Theme / CSS ───────────────────────────────────────────────────────────────

st.markdown("""
<style>
    [data-testid="stAppViewContainer"] { background: #0f1117; }
    [data-testid="stSidebar"]          { background: #1a1d2e; }
    .metric-card {
        background: #1a1d2e;
        border: 1px solid #2a2d3e;
        border-radius: 10px;
        padding: 18px 22px;
        text-align: center;
        margin-bottom: 6px;
    }
    .metric-card .value { font-size: 2rem; font-weight: 700; color: #00C2FF; }
    .metric-card .label { font-size: 0.78rem; color: #aaaaaa; margin-top: 4px; }
    .metric-card .decision { font-size: 0.7rem; color: #FFD166; margin-top: 6px; }
    .status-ok   { color: #00D084; font-weight: 600; }
    .status-warn { color: #FF4B4B; font-weight: 600; }
    .section-header {
        font-size: 1.1rem; font-weight: 700; color: #00C2FF;
        border-left: 3px solid #00C2FF; padding-left: 10px;
        margin: 18px 0 10px 0;
    }
    .trust-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    .badge-ok   { background: #00D08422; color: #00D084; border: 1px solid #00D084; }
    .badge-warn { background: #FF4B4B22; color: #FF4B4B; border: 1px solid #FF4B4B; }
</style>
""", unsafe_allow_html=True)

PLOTLY_LAYOUT = dict(
    paper_bgcolor="#0f1117",
    plot_bgcolor="#1a1d2e",
    font_color="white",
    font_size=12,
    margin=dict(t=40, b=30, l=40, r=20),
)

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.image("https://via.placeholder.com/200x50/0f1117/00C2FF?text=PlaceMux", width=180)
    st.markdown("### Task 12 · E-Sign & TTH")

    fresh = get_data_freshness()
    freshness_color = "status-ok" if fresh["status"] == "FRESH" else "status-warn"
    st.markdown(
        f"**Data freshness:** <span class='{freshness_color}'>{fresh['status']}</span><br>"
        f"<small>Last event: {fresh['latest_event']}<br>{fresh['hours_since']} h ago</small>",
        unsafe_allow_html=True,
    )
    st.divider()

    st.markdown("**Navigation**")
    page = st.radio(
        "",
        ["📊 KPI Overview", "⏱ Time-to-Hire Deep Dive",
         "🔐 Trust Layer / E-Sign", "🔍 Data Quality",
         "📖 Metric Dictionary"],
        label_visibility="collapsed",
    )
    st.divider()
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

# ── Cached data loaders ───────────────────────────────────────────────────────

@st.cache_data(ttl=60)
def load_kpis():          return get_kpi_summary()
@st.cache_data(ttl=60)
def load_tth():           return get_time_to_hire_data()
@st.cache_data(ttl=60)
def load_funnel():        return get_funnel_data()
@st.cache_data(ttl=60)
def load_weekly():        return get_weekly_trend()
@st.cache_data(ttl=60)
def load_dept():          return get_dept_breakdown()
@st.cache_data(ttl=60)
def load_tamper():        return check_tamper_summary()
@st.cache_data(ttl=60)
def load_vlog():          return get_verification_log()


# ─────────────────────────────────────────────────────────────────────────────
#  PAGE 1 · KPI OVERVIEW
# ─────────────────────────────────────────────────────────────────────────────

if page == "📊 KPI Overview":
    st.title("📊 PlaceMux — Hiring Analytics · KPI Overview")
    st.caption("Task 12 · E-Sign Integration & Tamper-Evidence · Phase 2 · Week 4")

    kpis = load_kpis()

    # ── KPI Cards row ──
    c1, c2, c3, c4, c5, c6 = st.columns(6)

    def kpi_card(col, value, label, decision, unit=""):
        col.markdown(f"""
        <div class="metric-card">
            <div class="value">{value}{unit}</div>
            <div class="label">{label}</div>
            <div class="decision">→ {decision}</div>
        </div>""", unsafe_allow_html=True)

    kpi_card(c1, kpis["avg_tth_hours"], "Avg Time-to-Hire", "SLA target < 168 h", " h")
    kpi_card(c2, kpis["median_tth_hours"], "Median TTH", "Outlier benchmark", " h")
    kpi_card(c3, kpis["fastest_hrs"], "Fastest Hire", "Best-practice target", " h")
    kpi_card(c4, kpis["slowest_hrs"], "Slowest Hire", "Outlier investigation", " h")
    kpi_card(c5, kpis["signed_pct"], "Signed Offer %", "Alert if < 80 %", " %")
    kpi_card(c6, kpis["verified_pct"], "Verified %", "< 100 % → legal flag", " %")

    st.markdown('<div class="section-header">Hiring Funnel</div>', unsafe_allow_html=True)
    funnel = load_funnel()
    fig_funnel = go.Figure(go.Funnel(
        y=funnel["stage"],
        x=funnel["count"],
        textinfo="value+percent initial",
        marker=dict(color=["#00C2FF","#20C8FF","#40CEFF","#60D4FF","#80DAFF","#00D084"]),
    ))
    fig_funnel.update_layout(title="Candidate Pipeline Funnel", **PLOTLY_LAYOUT)
    st.plotly_chart(fig_funnel, use_container_width=True)

    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown('<div class="section-header">Weekly Trend — Applications & Avg TTH</div>',
                    unsafe_allow_html=True)
        weekly = load_weekly()
        fig_w = go.Figure()
        fig_w.add_trace(go.Bar(
            x=weekly["week"], y=weekly["applications"],
            name="Applications", marker_color="#2a2d5e", yaxis="y"
        ))
        fig_w.add_trace(go.Scatter(
            x=weekly["week"], y=weekly["avg_tth_hours"],
            name="Avg TTH (h)", line=dict(color="#00C2FF", width=2),
            mode="lines+markers", yaxis="y2"
        ))
        fig_w.update_layout(
            yaxis=dict(title="Applications", color="white"),
            yaxis2=dict(title="Avg TTH (h)", overlaying="y", side="right", color="#00C2FF"),
            legend=dict(bgcolor="#1a1d2e"),
            **PLOTLY_LAYOUT,
        )
        st.plotly_chart(fig_w, use_container_width=True)

    with col_right:
        st.markdown('<div class="section-header">Avg TTH by Department</div>',
                    unsafe_allow_html=True)
        dept = load_dept()
        fig_d = px.bar(
            dept.sort_values("avg_tth_hours"),
            x="avg_tth_hours", y="department",
            orientation="h", color="avg_tth_hours",
            color_continuous_scale=["#00D084", "#00C2FF", "#FF4B4B"],
            labels={"avg_tth_hours": "Avg TTH (h)", "department": ""},
        )
        fig_d.update_layout(**PLOTLY_LAYOUT)
        st.plotly_chart(fig_d, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
#  PAGE 2 · TIME-TO-HIRE DEEP DIVE
# ─────────────────────────────────────────────────────────────────────────────

elif page == "⏱ Time-to-Hire Deep Dive":
    st.title("⏱ Time-to-Hire — Deep Dive")

    tth = load_tth()
    signed = tth[tth["offer_signed_time"].notna()].copy()

    # Distribution
    st.markdown('<div class="section-header">TTH Distribution</div>', unsafe_allow_html=True)
    fig_hist = px.histogram(
        signed, x="time_to_hire_hours", nbins=25,
        color_discrete_sequence=["#00C2FF"],
        labels={"time_to_hire_hours": "Hours to Hire"},
    )
    kpis = load_kpis()
    fig_hist.add_vline(x=kpis["avg_tth_hours"],    line_color="#FF4B4B", line_dash="dash",
                       annotation_text="Mean", annotation_font_color="#FF4B4B")
    fig_hist.add_vline(x=kpis["median_tth_hours"], line_color="#00D084", line_dash="dash",
                       annotation_text="Median", annotation_font_color="#00D084")
    fig_hist.update_layout(title="Time-to-Hire Distribution (signed offers only)", **PLOTLY_LAYOUT)
    st.plotly_chart(fig_hist, use_container_width=True)

    # Stage duration breakdown (box plots)
    st.markdown('<div class="section-header">Stage Duration Breakdown</div>', unsafe_allow_html=True)
    stage_cols = ["hours_to_shortlist", "hours_to_interview", "hours_to_offer", "hours_to_sign"]
    stage_labels = ["→ Shortlist", "→ Interview", "→ Offer", "→ Sign"]
    stage_df = signed[stage_cols].dropna()
    fig_box = go.Figure()
    colors = ["#00C2FF", "#7B61FF", "#FFD166", "#00D084"]
    for col, label, color in zip(stage_cols, stage_labels, colors):
        fig_box.add_trace(go.Box(
            y=stage_df[col], name=label,
            marker_color=color, line_color=color,
            boxmean=True,
        ))
    fig_box.update_layout(title="Hours per Pipeline Stage", **PLOTLY_LAYOUT)
    st.plotly_chart(fig_box, use_container_width=True)

    # Scatter: offer_signed vs application (TTH bubble)
    st.markdown('<div class="section-header">Individual Candidate TTH Scatter</div>',
                unsafe_allow_html=True)
    fig_sc = px.scatter(
        signed, x="application_time", y="time_to_hire_hours",
        color="department", hover_data=["name", "job_title", "verification_status"],
        color_discrete_sequence=px.colors.qualitative.Bold,
        labels={"time_to_hire_hours": "Time to Hire (h)", "application_time": "Applied"},
    )
    fig_sc.update_layout(**PLOTLY_LAYOUT)
    st.plotly_chart(fig_sc, use_container_width=True)

    # Raw data table
    st.markdown('<div class="section-header">Raw Pipeline Data</div>', unsafe_allow_html=True)
    display_cols = ["candidate_id","name","department","job_title",
                    "application_time","offer_signed_time",
                    "time_to_hire_hours","verification_status"]
    st.dataframe(
        tth[display_cols].sort_values("time_to_hire_hours"),
        use_container_width=True, height=350,
    )


# ─────────────────────────────────────────────────────────────────────────────
#  PAGE 3 · TRUST LAYER / E-SIGN
# ─────────────────────────────────────────────────────────────────────────────

elif page == "🔐 Trust Layer / E-Sign":
    st.title("🔐 Trust Layer — E-Sign & Tamper Evidence")
    st.caption("Every signed offer is SHA-256 hashed. Re-computing and comparing detects post-sign tampering.")

    tamper = load_tamper()

    # Status badge row
    col1, col2, col3 = st.columns(3)
    kpis = load_kpis()
    tampered_cnt = kpis["tampered_count"]
    with col1:
        badge = "badge-warn" if tampered_cnt > 0 else "badge-ok"
        label = f"⚠ {tampered_cnt} TAMPERED" if tampered_cnt > 0 else "✓ No Tampering"
        st.markdown(f'<span class="trust-badge {badge}">{label}</span>', unsafe_allow_html=True)
        st.metric("Tampered Offers", tampered_cnt, delta=None)
    with col2:
        st.metric("Verified (hash match)", kpis["verified_count"])
    with col3:
        st.metric("Unsigned (no hash)", kpis["total_candidates"] - kpis["signed_count"])

    # Pie chart
    st.markdown('<div class="section-header">Verification Status Breakdown</div>',
                unsafe_allow_html=True)
    fig_pie = px.pie(
        tamper, values="count", names="verification_status",
        color="verification_status",
        color_discrete_map={
            "verified":  "#00D084",
            "tampered":  "#FF4B4B",
            "not_signed":"#AAAAAA",
            "pending":   "#FFD166",
        },
        hole=0.45,
    )
    fig_pie.update_layout(title="Offer Verification Status", **PLOTLY_LAYOUT)
    st.plotly_chart(fig_pie, use_container_width=True)

    # Live hash verifier
    st.markdown('<div class="section-header">🔎 Live Offer Hash Verifier</div>',
                unsafe_allow_html=True)
    st.markdown("Select a candidate to re-compute their offer hash and check tamper-evidence in real-time.")

    conn = get_connection()
    rows = conn.execute(
        """
        SELECT he.candidate_id, c.name, he.offer_hash, he.offer_payload, he.verification_status
        FROM hiring_events he
        JOIN candidates c ON he.candidate_id = c.candidate_id
        WHERE he.offer_signed_time IS NOT NULL AND he.offer_hash IS NOT NULL
        ORDER BY c.name
        """
    ).fetchall()
    conn.close()

    options = {f"{r['name']} ({r['candidate_id'][:8]}…)": r for r in rows}
    selected = st.selectbox("Choose a signed candidate", list(options.keys()))

    if selected:
        r = options[selected]
        payload = json.loads(r["offer_payload"])

        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("**Stored offer payload**")
            st.json(payload)

        with col_b:
            stored_hash = r["offer_hash"]
            recomputed  = hashlib.sha256(
                json.dumps(payload, sort_keys=True, default=str).encode()
            ).hexdigest()
            match = stored_hash == recomputed

            st.markdown("**Stored hash (from DB)**")
            st.code(stored_hash, language="text")
            st.markdown("**Re-computed hash (live)**")
            st.code(recomputed, language="text")

            if match:
                st.success("✅ HASH MATCH — Offer is authentic and untampered.")
            else:
                st.error("🚨 HASH MISMATCH — Offer payload has been TAMPERED post-signing!")
                st.warning("Action: Freeze offer, notify Legal & Compliance immediately.")

    # Verification log
    st.markdown('<div class="section-header">Recent Verification Log</div>',
                unsafe_allow_html=True)
    vlog = load_vlog()
    if vlog.empty:
        st.info("No verification events logged yet. Run data_quality_checks.py first.")
    else:
        def highlight_fail(row):
            if row.get("result") == "FAIL":
                return ["background-color: #FF4B4B22"] * len(row)
            return [""] * len(row)
        st.dataframe(
            vlog.style.apply(highlight_fail, axis=1),
            use_container_width=True, height=300,
        )


# ─────────────────────────────────────────────────────────────────────────────
#  PAGE 4 · DATA QUALITY
# ─────────────────────────────────────────────────────────────────────────────

elif page == "🔍 Data Quality":
    st.title("🔍 Data Quality Checks")

    with st.spinner("Running all quality checks…"):
        results = run_all_checks(verbose=False)

    # Freshness
    fresh = get_data_freshness()
    fcol = "status-ok" if fresh["status"] == "FRESH" else "status-warn"
    st.markdown(
        f"**Pipeline freshness:** <span class='{fcol}'>{fresh['status']}</span> "
        f"— last event {fresh['hours_since']} h ago (threshold: 48 h)",
        unsafe_allow_html=True,
    )
    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="section-header">Null Completeness</div>',
                    unsafe_allow_html=True)
        null_df = results["nulls"].reset_index()
        null_df.columns = ["Column", "Null Count", "Status"]
        st.dataframe(null_df, use_container_width=True, hide_index=True)

    with col2:
        st.markdown('<div class="section-header">Timestamp Ordering</div>',
                    unsafe_allow_html=True)
        ts_df = results["timestamp_ordering"]
        if ts_df.empty:
            st.success("✓ All timestamps in correct chronological order.")
        else:
            st.error(f"⚠ {len(ts_df)} out-of-order rows detected!")
            st.dataframe(ts_df, use_container_width=True)

    st.markdown('<div class="section-header">Duplicate Check</div>', unsafe_allow_html=True)
    dup_df = results["duplicates"]
    if dup_df.empty:
        st.success("✓ No duplicate candidate IDs found.")
    else:
        st.error(f"⚠ {len(dup_df)} duplicate candidate records!")
        st.dataframe(dup_df, use_container_width=True)

    st.markdown('<div class="section-header">Hash Verification Results</div>',
                unsafe_allow_html=True)
    hv = results["hash_verification"]
    if hv.empty:
        st.info("No signed offers to verify.")
    else:
        pass_count = len(hv[hv["result"] == "PASS"])
        fail_count = len(hv[hv["result"] == "FAIL"])
        c1, c2 = st.columns(2)
        c1.metric("PASS (authentic)", pass_count)
        c2.metric("FAIL (tampered)", fail_count, delta=None)

        def highlight(row):
            return ["background-color:#FF4B4B22" if row["result"]=="FAIL" else ""] * len(row)
        st.dataframe(hv.style.apply(highlight, axis=1), use_container_width=True, height=300)


# ─────────────────────────────────────────────────────────────────────────────
#  PAGE 5 · METRIC DICTIONARY
# ─────────────────────────────────────────────────────────────────────────────

elif page == "📖 Metric Dictionary":
    st.title("📖 Metric Dictionary")
    st.caption("Every number on this dashboard is defined here: source → formula → decision.")

    data_path = pathlib.Path(__file__).parent / "data" / "metric_dictionary.csv"
    if data_path.exists():
        df = pd.read_csv(data_path)
        for _, row in df.iterrows():
            with st.expander(f"**{row['metric_name']}** — {row['unit']}"):
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f"**Definition:** {row['definition']}")
                    st.markdown(f"**Formula:** `{row['formula']}`")
                    st.markdown(f"**Event chain:** `{row['event_chain']}`")
                with c2:
                    st.markdown(f"**Source table:** `{row['source_table']}`")
                    st.markdown(f"**Source columns:** `{row['source_columns']}`")
                    st.info(f"🎯 **Decision trigger:** {row['decision']}")
                    st.markdown(f"**Owner:** {row['owner']} │ **Refresh:** {row['refresh']}")
    else:
        st.warning("Run `python metrics.py` to generate the metric dictionary first.")
