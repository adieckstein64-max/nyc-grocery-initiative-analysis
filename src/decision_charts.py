"""4 executive decision charts for the NYC Public Grocery Store Initiative.

Each chart is built to stand alone as a slide: bold headline, a one-line
takeaway subtitle, direct inline data labels, and a fixed color mapping per
mechanism (src.style.MECHANISM_COLORS) that never changes across charts —
Tax Credit and Targeted Voucher are the two recommended (highlighted)
mechanisms; Physical Stores and Universal Voucher are flagged (neutral
gray / critical red).

Reads from the CSVs the pipeline already exports to exports_for_tableau/,
so this can run standalone without a MySQL connection as long as
`python scripts/run_pipeline.py` has been run at least once.

Run via `python scripts/generate_decision_charts.py`.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
from matplotlib.patches import Rectangle

from src.style import CATEGORICAL, CHROME, MECHANISM_COLORS, MECHANISM_ORDER, STATUS, set_style

DATA_DIR = Path(__file__).resolve().parent.parent / "exports_for_tableau"
OUT_DIR = Path(__file__).resolve().parent.parent / "exports" / "charts"
BASE_YEAR = 2024
DPI = 300

# scenario_outputs.scenario_name -> executive-facing mechanism label.
# "Physical Stores - Means-Tested" is deliberately excluded from the headline
# 4: it is strictly dominated by the universal-access variant on both reach
# and ROI (see README), so "Physical Stores" here means the better of the two.
SCENARIO_TO_MECHANISM = {
    "Physical Stores - Universal Access": "Physical Stores",
    "NYC Grocery Tax Credit": "NYC Grocery Tax Credit",
    "Universal Digital Grocery Voucher": "Universal Digital Voucher",
    "Targeted Digital Grocery Voucher": "Targeted Digital Voucher",
}

# Illustrative rollout timeline (months from program approval), grounded in
# the Operational Complexity & Time-to-Market assessment in the PM memo, not
# a formal implementation plan.
ROLLOUT_TIMELINE = {
    "NYC Grocery Tax Credit": {"launch_month": 6, "coverage_month": 9},
    "Universal Digital Voucher": {"launch_month": 6, "coverage_month": 9},
    "Targeted Digital Voucher": {"launch_month": 9, "coverage_month": 12},
    "Physical Stores": {"launch_month": 30, "coverage_month": 33, "capped": True},
}

ROI_GUARDRAIL = 0.50          # minimum acceptable Net Social ROI
COVERAGE_GUARDRAIL_PCT = 60.0  # minimum acceptable coverage of eligible households


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_mechanism_summary() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "scenario_outputs_flat.csv")
    df = df[(df["year"] == BASE_YEAR) & (df["scenario_name"].isin(SCENARIO_TO_MECHANISM))].copy()
    df["mechanism"] = df["scenario_name"].map(SCENARIO_TO_MECHANISM)

    def _agg(g: pd.DataFrame) -> pd.Series:
        reached = g["households_reached"].sum()
        eligible = g["eligible_households"].sum()
        cost = g["total_program_cost"].sum()
        return pd.Series({
            "eligible_households": eligible,
            "households_reached": reached,
            "total_program_cost": cost,
            "coverage_pct": reached / eligible * 100,
            "cost_per_hh_reached": cost / reached,
            # True aggregate ratio, not a weighted average of per-borough ROI:
            # roi_row = benefit_value_per_hh / cost_per_hh_row, and
            # benefit_value_per_hh is constant across boroughs for a given
            # mechanism (by construction in policy_model), so recover it from
            # any row and divide by the *aggregate* cost/hh. A reach-weighted
            # average of roi_row would understate the cost of boroughs with
            # poor per-row economics but low reach (e.g. Staten Island for
            # Physical Stores) — exactly the effect this metric needs to catch.
            "roi_estimate": (g["roi_estimate"] * g["cost_per_household_reached"]).mean() / (cost / reached),
        })

    summary = df.groupby("mechanism").apply(_agg).reset_index()
    summary["mechanism"] = pd.Categorical(summary["mechanism"], categories=MECHANISM_ORDER, ordered=True)
    return summary.sort_values("mechanism").reset_index(drop=True)


def load_store_cost_tiers() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "store_costs_flat.csv")
    df["total_capex"] = df["capex_construction"] + df["capex_equipment"]
    df["hidden_subsidy_annual"] = df["foregone_property_tax_annual"] + df["rent_subsidy_annual"]

    planned = df[df["cost_scenario"] == "planned"].set_index("borough_name")["total_capex"]
    realistic = df[df["cost_scenario"] == "realistic"].set_index("borough_name")["total_capex"]
    hidden = df[df["cost_scenario"] == "realistic"].set_index("borough_name")["hidden_subsidy_annual"]

    out = pd.DataFrame({
        "planned_capex": planned,
        "realistic_capex": realistic,
        "realistic_plus_hidden": realistic + hidden,
    })
    return out.sort_values("realistic_plus_hidden", ascending=False)


# ---------------------------------------------------------------------------
# Shared chart chrome
# ---------------------------------------------------------------------------

def _title_block(fig, ax, title: str, subtitle: str) -> None:
    fig.suptitle(title, x=0.03, y=0.99, ha="left", fontsize=16, fontweight="bold", color=CHROME["primary_ink"])
    ax.set_title(subtitle, loc="left", pad=16, fontsize=11.5, fontweight="normal", color=CHROME["secondary_ink"])


def _footnote(fig, text: str) -> None:
    fig.text(0.03, 0.01, text, fontsize=8.5, color=CHROME["muted_ink"], ha="left", va="bottom")


def _save(fig, name: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_DIR / name, dpi=DPI, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Chart 1 — The Reach-vs-Cost Frontier
# ---------------------------------------------------------------------------

def chart_1_reach_vs_cost_frontier(summary: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(12.5, 8.5))

    costs = summary["total_program_cost"].to_numpy()
    sizes = 500 + 4200 * np.sqrt(costs / costs.max())

    # Efficient-frontier shading: high coverage, low cost-per-household — a
    # single rectangle for the exact intersection, not two overlapping spans.
    ax.add_patch(Rectangle((COVERAGE_GUARDRAIL_PCT, 600), 100 - COVERAGE_GUARDRAIL_PCT, 1400,
                           facecolor=STATUS["good"], alpha=0.09, zorder=0, linewidth=0))
    ax.text(98, 2080, "EFFICIENT FRONTIER (high reach, low cost/hh)", ha="right", va="bottom",
            fontsize=8.5, fontweight="bold", color=STATUS["good"], zorder=1)

    by_mechanism = summary.set_index("mechanism")

    # Explicit per-point label placement — the 4 points cluster unevenly
    # (Tax Credit and Targeted Voucher sit almost on top of each other), so a
    # single generic offset rule collides; each gets a hand-placed anchor.
    LABEL_PLACEMENT = {
        "Physical Stores": dict(xytext_dx=11, xytext_dy=1.0, ha="left"),
        "Universal Digital Voucher": dict(xytext_dx=0, xytext_dy=1.22, ha="center"),
        "NYC Grocery Tax Credit": dict(xytext_dx=2, xytext_dy=1.55, ha="left"),
        "Targeted Digital Voucher": dict(xytext_dx=-2, xytext_dy=0.62, ha="right"),
    }

    for i, row in summary.iterrows():
        color = MECHANISM_COLORS[row["mechanism"]]
        ax.scatter(row["coverage_pct"], row["cost_per_hh_reached"], s=sizes[i], color=color,
                   alpha=0.88, edgecolor="white", linewidth=2, zorder=3)
        label = (f"{row['mechanism']}\n{row['coverage_pct']:.0f}% reach  ·  "
                 f"${row['cost_per_hh_reached']:,.0f}/hh")
        p = LABEL_PLACEMENT[row["mechanism"]]
        ax.annotate(label, (row["coverage_pct"], row["cost_per_hh_reached"]),
                    xytext=(row["coverage_pct"] + p["xytext_dx"], row["cost_per_hh_reached"] * p["xytext_dy"]),
                    ha=p["ha"], va="center", fontsize=9.5, fontweight="bold",
                    color=CHROME["primary_ink"], zorder=4, linespacing=1.4)

    # Callout: Tax Credit — the optimal-policy point. Anchored in the mostly
    # empty upper-middle of the plot, well clear of every other bubble/label.
    tc = by_mechanism.loc["NYC Grocery Tax Credit"]
    ax.annotate(
        r"$\mathbf{Optimal\ Policy:}$" "\nDirect purchasing power support via tax rails.\n"
        "Zero retail overhead, zero stigma, near-zero friction.",
        xy=(tc["coverage_pct"], tc["cost_per_hh_reached"]), xycoords="data",
        xytext=(30, 3200), textcoords="data", ha="left", va="center", fontsize=9.5,
        color=CHROME["primary_ink"], linespacing=1.5,
        bbox=dict(boxstyle="round,pad=0.55", facecolor="white",
                  edgecolor=MECHANISM_COLORS["NYC Grocery Tax Credit"], linewidth=1.6),
        arrowprops=dict(arrowstyle="-|>", color=MECHANISM_COLORS["NYC Grocery Tax Credit"],
                        lw=1.6, connectionstyle="arc3,rad=0.12"),
        zorder=5,
    )

    # Callout: Physical Stores — the market-distortion point.
    ps = by_mechanism.loc["Physical Stores"]
    ax.annotate(
        r"$\mathbf{Market\ Distortion:}$" "\nHeavy CapEx/OpEx. Retail means-testing at store\n"
        "entrances creates an impossible trade-off between\nmassive budget leakage and operational friction.",
        xy=(ps["coverage_pct"], ps["cost_per_hh_reached"]), xycoords="data",
        xytext=(20, 7200), textcoords="data", ha="left", va="center", fontsize=9.5,
        color=CHROME["primary_ink"], linespacing=1.5,
        bbox=dict(boxstyle="round,pad=0.55", facecolor="white",
                  edgecolor=MECHANISM_COLORS["Physical Stores"], linewidth=1.6),
        arrowprops=dict(arrowstyle="-|>", color=MECHANISM_COLORS["Physical Stores"],
                        lw=1.6, connectionstyle="arc3,rad=0.15"),
        zorder=5,
    )

    ax.set_yscale("log")
    ax.set_xlim(-2, 102)
    ax.set_ylim(600, 12000)
    ax.yaxis.set_major_locator(mticker.LogLocator(base=10, subs=(1, 2, 3, 5)))
    ax.yaxis.set_minor_locator(mticker.NullLocator())
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"${v:,.0f}"))
    ax.set_xlabel("Coverage of eligible low-income households (%)", color=CHROME["secondary_ink"], fontsize=10.5)
    ax.set_ylabel("Cost per household reached / year (log scale)", color=CHROME["secondary_ink"], fontsize=10.5)
    ax.grid(axis="both", color=CHROME["gridline"], linewidth=0.8)
    ax.tick_params(length=0)

    _title_block(fig, ax, "The Reach-vs-Cost Frontier: Purchasing Power vs. Shelf-Price Subsidies",
                 "Direct tax credits achieve ~1:1 efficiency via existing tax rails; physical store "
                 "subsidies collapse under fixed retail overhead and means-testing friction.")
    _footnote(fig, "Bubble size = total citywide program cost/year. Citywide totals, 2024. "
                    "\"Physical Stores\" = universal-access variant (strictly outperforms means-tested on reach and ROI).")
    _save(fig, "01_reach_vs_cost_frontier.png")


# ---------------------------------------------------------------------------
# Chart 2 — The $12M Promise vs. the Real Bill
# ---------------------------------------------------------------------------

def chart_2_promise_vs_real_bill(tiers: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(11.5, 7))
    boroughs = tiers.index.tolist()
    x = np.arange(len(boroughs))
    width = 0.27

    bars_planned = ax.bar(x - width, tiers["planned_capex"] / 1e6, width,
                          label="Planned CapEx (official $12M figure)", color=CATEGORICAL["blue"])
    bars_realistic = ax.bar(x, tiers["realistic_capex"] / 1e6, width,
                            label="Realistic CapEx (modeled)", color=CATEGORICAL["orange"])
    bars_total = ax.bar(x + width, tiers["realistic_plus_hidden"] / 1e6, width,
                        label="Realistic CapEx + Year-1 hidden subsidy", color=STATUS["critical"])

    for bars in (bars_planned, bars_realistic, bars_total):
        for bar in bars:
            ax.annotate(f"${bar.get_height():.0f}M", (bar.get_x() + bar.get_width() / 2, bar.get_height()),
                        ha="center", va="bottom", fontsize=8.5, color=CHROME["secondary_ink"],
                        xytext=(0, 3), textcoords="offset points")

    ax.set_xticks(x)
    ax.set_xticklabels(boroughs)
    ax.set_ylabel("$ millions", color=CHROME["secondary_ink"], fontsize=10.5)
    ax.grid(axis="y", color=CHROME["gridline"], linewidth=0.8)
    ax.tick_params(length=0)
    ax.legend(frameon=False, loc="upper right", fontsize=9.5)

    _title_block(fig, ax, "The $12M Promise vs. the Real Bill",
                 "Realistic construction cost runs ~2.3x the announced figure per store — municipal "
                 "retail initiatives mask ongoing balance-sheet subsidies the headline number never shows.")
    _footnote(fig, "Third bar = one-time realistic CapEx + first-year hidden operating subsidy "
                    "(foregone property tax + free/below-market rent); hidden subsidy recurs annually thereafter.")
    _save(fig, "02_promise_vs_real_bill.png")


# ---------------------------------------------------------------------------
# Chart 3 — Net Social ROI, Guardrailed
# ---------------------------------------------------------------------------

def chart_3_roi_guardrailed(summary: pd.DataFrame) -> None:
    df = summary.sort_values("roi_estimate", ascending=True).reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(11, 6.5))

    colors = [MECHANISM_COLORS[m] for m in df["mechanism"]]
    bars = ax.barh(df["mechanism"], df["roi_estimate"], color=colors, height=0.6, zorder=3)

    ax.axvline(ROI_GUARDRAIL, color=CHROME["secondary_ink"], linestyle="--", linewidth=1.5, zorder=2)
    ax.annotate("Minimum acceptable\nNet Social ROI", xy=(ROI_GUARDRAIL, len(df) - 0.35),
                xytext=(8, 0), textcoords="offset points", ha="left", va="top",
                fontsize=9, color=CHROME["secondary_ink"], fontweight="bold")

    for i, row in df.iterrows():
        flagged = row["coverage_pct"] < COVERAGE_GUARDRAIL_PCT
        note_color = STATUS["critical"] if flagged else CHROME["secondary_ink"]
        text = f"ROI {row['roi_estimate']:.2f}   |   {row['coverage_pct']:.0f}% reach"
        suffix = "  (below reach guardrail)" if flagged else ""
        ax.annotate(text + suffix, (row["roi_estimate"], i), xytext=(8, 0), textcoords="offset points",
                    ha="left", va="center", fontsize=10, fontweight="bold", color=note_color, zorder=4)

    ax.set_xlim(0, 1.5)
    ax.set_xlabel(r"Net Social ROI (\$ of targeted benefit delivered per \$1 spent)",
                 color=CHROME["secondary_ink"], fontsize=10.5)
    ax.grid(axis="x", color=CHROME["gridline"], linewidth=0.8)
    ax.tick_params(length=0)

    _title_block(fig, ax, "Net Social ROI, Guardrailed by Coverage",
                 "Only income-side mechanisms — Tax Credit and Targeted Voucher — cross both the ROI "
                 "and reach thresholds; Physical Stores' ROI is disqualified by its 4% reach.")
    _footnote(fig, f"Guardrail: mechanisms reaching below {COVERAGE_GUARDRAIL_PCT:.0f}% of eligible "
                    "households are flagged regardless of ROI.")
    _save(fig, "03_roi_guardrailed.png")


# ---------------------------------------------------------------------------
# Chart 4 — Time-to-First-Impact
# ---------------------------------------------------------------------------

def chart_4_time_to_impact(summary: pd.DataFrame) -> None:
    order = sorted(ROLLOUT_TIMELINE, key=lambda m: ROLLOUT_TIMELINE[m]["launch_month"])
    coverage_by_mechanism = summary.set_index("mechanism")["coverage_pct"]

    fig, ax = plt.subplots(figsize=(11.5, 6))
    bar_height = 0.42

    for i, mechanism in enumerate(order):
        t = ROLLOUT_TIMELINE[mechanism]
        color = MECHANISM_COLORS[mechanism]
        coverage = coverage_by_mechanism[mechanism]

        ax.barh(i, t["launch_month"], height=bar_height, color=CHROME["gridline"], zorder=2,
                label="Build & launch phase" if i == 0 else None)
        ax.barh(i, t["coverage_month"] - t["launch_month"], left=t["launch_month"],
                height=bar_height, color=color, alpha=0.9, zorder=3)
        ax.scatter(t["coverage_month"], i, marker="D", s=90, color=color,
                  edgecolor="white", linewidth=1.5, zorder=4)

        cap_note = "  (hard cap — cannot scale further)" if t.get("capped") else ""
        ax.annotate(f"Month {t['coverage_month']}: {coverage:.0f}% reach{cap_note}",
                    (t["coverage_month"], i), xytext=(10, 0), textcoords="offset points",
                    ha="left", va="center", fontsize=9.5, fontweight="bold",
                    color=STATUS["critical"] if t.get("capped") else CHROME["primary_ink"])

    ax.set_yticks(range(len(order)))
    ax.set_yticklabels(order)
    ax.invert_yaxis()
    ax.set_xlim(0, 42)
    ax.set_xlabel("Months from program approval", color=CHROME["secondary_ink"], fontsize=10.5)
    ax.grid(axis="x", color=CHROME["gridline"], linewidth=0.8)
    ax.tick_params(length=0)
    ax.legend(frameon=False, loc="lower right", fontsize=9.5)

    _title_block(fig, ax, "Time-to-First-Impact",
                 "Existing tax/benefit rails deliver immediate relief within one budget cycle vs. "
                 "24+ months of retail development lag before Physical Stores serve a single household.")
    _footnote(fig, "Illustrative rollout timeline based on modeled operational complexity "
                    "(legislative/build lead time, construction schedule) — not a formal implementation plan.")
    _save(fig, "04_time_to_impact.png")


# ---------------------------------------------------------------------------

def generate_all() -> None:
    set_style()
    summary = load_mechanism_summary()
    tiers = load_store_cost_tiers()

    chart_1_reach_vs_cost_frontier(summary)
    chart_2_promise_vs_real_bill(tiers)
    chart_3_roi_guardrailed(summary)
    chart_4_time_to_impact(summary)

    print(f"Wrote 4 decision charts to {OUT_DIR}")


if __name__ == "__main__":
    generate_all()
