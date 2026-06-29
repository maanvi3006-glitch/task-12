"""
export_reports.py
─────────────────
Exports:
  • reports/metrics_summary.csv   – one-row KPI snapshot
  • reports/dashboard_export.png  – static chart grid (matplotlib)
  • data/metric_dictionary.csv    – full metric dictionary
  • data/time_to_hire_export.csv  – per-candidate detail
"""

import logging
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import pandas as pd

from analytics_queries import (
    get_dept_breakdown,
    get_funnel_data,
    get_kpi_summary,
    get_time_to_hire_data,
    get_weekly_trend,
)
from metrics import export_metric_dictionary, export_time_to_hire_csv

logging.basicConfig(level=logging.INFO, format="%(levelname)s │ %(message)s")
log = logging.getLogger(__name__)

REPORTS_DIR = pathlib.Path(__file__).parent / "reports"
REPORTS_DIR.mkdir(exist_ok=True)


# ── KPI summary CSV ───────────────────────────────────────────────────────────

def export_metrics_summary() -> pathlib.Path:
    kpis = get_kpi_summary()
    df   = pd.DataFrame([kpis])
    out  = REPORTS_DIR / "metrics_summary.csv"
    df.to_csv(out, index=False)
    log.info("Metrics summary → %s", out)
    return out


# ── Static dashboard PNG ──────────────────────────────────────────────────────

def export_dashboard_png() -> pathlib.Path:
    kpis     = get_kpi_summary()
    tth_df   = get_time_to_hire_data()
    funnel   = get_funnel_data()
    weekly   = get_weekly_trend()
    dept     = get_dept_breakdown()

    signed = tth_df[tth_df["offer_signed_time"].notna()].copy()

    fig = plt.figure(figsize=(18, 12), facecolor="#0f1117")
    fig.suptitle(
        "PlaceMux — Task 12 · Time-to-Hire Dashboard",
        fontsize=16, fontweight="bold", color="white", y=0.98,
    )

    gs = gridspec.GridSpec(3, 3, figure=fig, hspace=0.45, wspace=0.35)

    ACCENT = "#00C2FF"
    BG     = "#1a1d2e"
    TEXT   = "white"
    WARN   = "#FF4B4B"
    GREEN  = "#00D084"

    def _ax(row, col, colspan=1, rowspan=1):
        ax = fig.add_subplot(gs[row:row+rowspan, col:col+colspan])
        ax.set_facecolor(BG)
        for spine in ax.spines.values():
            spine.set_edgecolor("#2a2d3e")
        ax.tick_params(colors=TEXT, labelsize=8)
        ax.xaxis.label.set_color(TEXT)
        ax.yaxis.label.set_color(TEXT)
        ax.title.set_color(TEXT)
        return ax

    # ── Row 0: KPI cards (text only) ──
    kpi_labels = [
        ("Avg TTH", f"{kpis['avg_tth_hours']} h"),
        ("Median TTH", f"{kpis['median_tth_hours']} h"),
        ("Fastest", f"{kpis['fastest_hrs']} h"),
        ("Slowest", f"{kpis['slowest_hrs']} h"),
        ("Signed %", f"{kpis['signed_pct']} %"),
        ("Verified %", f"{kpis['verified_pct']} %"),
    ]
    # Squeeze KPI cards into top strip
    kpi_ax = fig.add_subplot(gs[0, :])
    kpi_ax.set_facecolor("#0f1117")
    kpi_ax.axis("off")
    for i, (label, val) in enumerate(kpi_labels):
        x = 0.08 + i * 0.16
        kpi_ax.text(x, 0.75, val, transform=kpi_ax.transAxes,
                    fontsize=18, fontweight="bold", color=ACCENT, ha="center")
        kpi_ax.text(x, 0.25, label, transform=kpi_ax.transAxes,
                    fontsize=9, color="#aaaaaa", ha="center")

    # ── Row 1 left: TTH distribution ──
    ax1 = _ax(1, 0)
    ax1.hist(signed["time_to_hire_hours"], bins=20, color=ACCENT, edgecolor="#0f1117", alpha=0.85)
    ax1.axvline(kpis["avg_tth_hours"], color=WARN, linewidth=1.5, linestyle="--", label="Mean")
    ax1.axvline(kpis["median_tth_hours"], color=GREEN, linewidth=1.5, linestyle="--", label="Median")
    ax1.legend(fontsize=7, facecolor=BG, labelcolor=TEXT)
    ax1.set_title("TTH Distribution (hours)", fontsize=10)
    ax1.set_xlabel("Hours", fontsize=8)
    ax1.set_ylabel("Candidates", fontsize=8)

    # ── Row 1 mid: Funnel ──
    ax2 = _ax(1, 1)
    colors = [ACCENT, "#4DC3FF", "#7DD5FF", "#AADEFF", "#CCE9FF", GREEN]
    bars = ax2.barh(funnel["stage"], funnel["count"], color=colors)
    ax2.invert_yaxis()
    ax2.set_title("Hiring Funnel", fontsize=10)
    ax2.set_xlabel("Count", fontsize=8)
    for bar, val in zip(bars, funnel["count"]):
        ax2.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2,
                 str(int(val)), va="center", color=TEXT, fontsize=8)

    # ── Row 1 right: Dept breakdown ──
    ax3 = _ax(1, 2)
    ax3.barh(dept["department"], dept["avg_tth_hours"], color="#7B61FF", alpha=0.85)
    ax3.set_title("Avg TTH by Department (h)", fontsize=10)
    ax3.set_xlabel("Hours", fontsize=8)
    ax3.invert_yaxis()

    # ── Row 2 left+mid: Weekly trend ──
    ax4 = _ax(2, 0, colspan=2)
    w = weekly.dropna(subset=["avg_tth_hours"])
    ax4.plot(w["week"], w["avg_tth_hours"], color=ACCENT, marker="o", linewidth=2, markersize=5)
    ax4.fill_between(w["week"], w["avg_tth_hours"], alpha=0.15, color=ACCENT)
    ax4.set_title("Weekly Avg Time-to-Hire (hours)", fontsize=10)
    ax4.set_xlabel("Week", fontsize=8)
    ax4.set_ylabel("Avg TTH (h)", fontsize=8)
    plt.setp(ax4.xaxis.get_majorticklabels(), rotation=35, ha="right", fontsize=7)

    # ── Row 2 right: Verification status pie ──
    ax5 = _ax(2, 2)
    from data_quality_checks import check_tamper_summary
    ts = check_tamper_summary()
    pie_colors = {
        "verified":  GREEN,
        "not_signed": "#AAAAAA",
        "tampered":  WARN,
        "pending":   "#FFD166",
    }
    c_list = [pie_colors.get(s, ACCENT) for s in ts["verification_status"]]
    wedges, texts, autotexts = ax5.pie(
        ts["count"], labels=ts["verification_status"],
        autopct="%1.0f%%", colors=c_list, startangle=90,
        textprops={"color": TEXT, "fontsize": 8},
    )
    for at in autotexts:
        at.set_color("#0f1117")
        at.set_fontsize(7)
    ax5.set_title("Verification Status", fontsize=10)

    out = REPORTS_DIR / "dashboard_export.png"
    plt.savefig(out, dpi=150, bbox_inches="tight", facecolor="#0f1117")
    plt.close()
    log.info("Dashboard PNG → %s", out)
    return out


# ── Main ──────────────────────────────────────────────────────────────────────

def run():
    export_metrics_summary()
    export_metric_dictionary()
    export_time_to_hire_csv()
    export_dashboard_png()
    log.info("✓ All reports exported.")


if __name__ == "__main__":
    run()
