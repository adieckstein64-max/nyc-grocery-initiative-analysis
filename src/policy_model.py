"""Policy-scenario definitions and the core coverage/cost/ROI simulation.

Encodes the two hypotheses driving this project:

1. Scale & means-testing: a physical store's reach is capped by its walkable
   service radius (`store_locations.population_within_radius`), regardless of
   how the eligibility policy is designed. Tax credits / digital vouchers have
   no such spatial cap — they reach citywide from day one.
2. Universal vs. means-tested: opening a benefit to everyone avoids
   means-testing friction/stigma (higher participation) but dilutes public
   ROI, because dollars flow to non-target households too ("leakage").
   Means-testing improves targeting but adds administrative overhead and a
   stigma/friction dropout among the very households it's meant to reach.

`households_reached` / `coverage_pct` / `roi_estimate` are always measured
against a single, consistent target population across every scenario: the
borough's low-income households (`population_demographics.pct_households_low_income`).
That's what makes the scenarios comparable — a universal design isn't
penalized for existing, but it *is* penalized in total_program_cost for
serving everyone, and in roi_estimate for how much of that cost reaches the
target population.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.cost_model import total_annual_cost

AVG_HOUSEHOLD_SIZE = 2.6
ASSUMED_ANNUAL_GROCERY_SPEND = 6_500.0  # per low-income household, "food at home"

SCENARIOS = [
    {
        "scenario_name": "Physical Stores - Universal Access",
        "scenario_type": "physical_store",
        "eligibility_model": "universal",
        "eligibility_threshold_pct_ami": None,
        "description": "5 city-run pilot stores, discounted pricing open to all NYC residents regardless of income.",
    },
    {
        "scenario_name": "Physical Stores - Means-Tested",
        "scenario_type": "physical_store",
        "eligibility_model": "means_tested",
        "eligibility_threshold_pct_ami": 200.0,
        "description": "Same 5 stores, but discounted pricing requires proof-of-income verification at checkout for households under 200% AMI.",
    },
    {
        "scenario_name": "NYC Grocery Tax Credit",
        "scenario_type": "tax_credit",
        "eligibility_model": "means_tested",
        "eligibility_threshold_pct_ami": 200.0,
        "description": "Refundable city tax credit for grocery spending, delivered via existing income-tax filing for households under 200% AMI.",
    },
    {
        "scenario_name": "Universal Digital Grocery Voucher",
        "scenario_type": "digital_voucher",
        "eligibility_model": "universal",
        "eligibility_threshold_pct_ami": None,
        "description": "Citywide digital voucher/debit card mailed to every household, redeemable at any grocery retailer.",
    },
    {
        "scenario_name": "Targeted Digital Grocery Voucher",
        "scenario_type": "digital_voucher",
        "eligibility_model": "means_tested",
        "eligibility_threshold_pct_ami": 200.0,
        "description": "Digital voucher issued only to households enrolled via SNAP/benefits-screening data match, under 200% AMI.",
    },
]

# Internal simulation parameters, keyed by scenario_name (not persisted verbatim —
# admin/verification costs feed means_testing_overhead; the rest feed scenario_outputs).
SCENARIO_PARAMS = {
    "Physical Stores - Universal Access": {
        "participation_rate": 0.90,
        "admin_staff_cost_annual": 150_000.0,       # per store — basic customer service, no verification
        "verification_system_cost_annual": 0.0,
        "estimated_stigma_dropout_pct": 3.0,
        "estimated_leakage_pct": 55.0,               # share of shoppers who are not low-income
        "avg_processing_time_days": 0.0,
        "benefit_source": "price_basket",
    },
    "Physical Stores - Means-Tested": {
        "participation_rate": 0.65,
        "admin_staff_cost_annual": 480_000.0,        # per store — checkout verification staffing
        "verification_system_cost_annual": 650_000.0,  # per store — income-verification POS system
        "estimated_stigma_dropout_pct": 30.0,
        "estimated_leakage_pct": 8.0,
        "avg_processing_time_days": 12.0,
        "benefit_source": "price_basket",
    },
    "NYC Grocery Tax Credit": {
        "participation_rate": 0.85,
        "admin_staff_cost_annual": 120_000.0,        # citywide total — piggybacks on Dept. of Finance tax infra
        "verification_system_cost_annual": 80_000.0,   # citywide total
        "estimated_stigma_dropout_pct": 2.0,
        "estimated_leakage_pct": 6.0,
        "avg_processing_time_days": 1.0,
        "benefit_source": "flat",
        "benefit_value_annual": 1_200.0,
    },
    "Universal Digital Grocery Voucher": {
        "participation_rate": 0.88,
        "admin_staff_cost_annual": 200_000.0,        # citywide total
        "verification_system_cost_annual": 300_000.0,  # citywide total — card/app platform
        "estimated_stigma_dropout_pct": 4.0,
        "estimated_leakage_pct": 55.0,
        "avg_processing_time_days": 0.0,
        "benefit_source": "flat",
        "benefit_value_annual": 1_200.0,
    },
    "Targeted Digital Grocery Voucher": {
        "participation_rate": 0.80,
        "admin_staff_cost_annual": 220_000.0,        # citywide total
        "verification_system_cost_annual": 400_000.0,  # citywide total — SNAP/benefits data-match screening
        "estimated_stigma_dropout_pct": 10.0,
        "estimated_leakage_pct": 5.0,
        "avg_processing_time_days": 5.0,
        "benefit_source": "flat",
        "benefit_value_annual": 1_200.0,
    },
}


def build_subsidy_scenarios_df() -> pd.DataFrame:
    return pd.DataFrame(SCENARIOS)


def build_means_testing_overhead_df(scenarios: pd.DataFrame) -> pd.DataFrame:
    """scenarios must have scenario_id + scenario_name (post-DB-insert)."""
    rows = []
    for _, s in scenarios.iterrows():
        p = SCENARIO_PARAMS[s["scenario_name"]]
        rows.append({
            "scenario_id": s["scenario_id"],
            "admin_staff_cost_annual": p["admin_staff_cost_annual"],
            "verification_system_cost_annual": p["verification_system_cost_annual"],
            "estimated_stigma_dropout_pct": p["estimated_stigma_dropout_pct"],
            "estimated_leakage_pct": p["estimated_leakage_pct"],
            "avg_processing_time_days": p["avg_processing_time_days"],
        })
    return pd.DataFrame(rows)


def _physical_benefit_value(avg_discount_pct: float) -> float:
    return avg_discount_pct * ASSUMED_ANNUAL_GROCERY_SPEND


def build_scenario_outputs_df(
    scenarios: pd.DataFrame,       # scenario_id, scenario_name, scenario_type, eligibility_model
    boroughs: pd.DataFrame,        # borough_id, borough_name, total_population
    demographics: pd.DataFrame,    # borough_name, year, total_households, pct_households_low_income
    store_locations: pd.DataFrame,  # borough_name, store_id, population_within_radius
    store_costs: pd.DataFrame,     # store_id, cost_scenario, ...
    avg_discount_pct: float,
) -> pd.DataFrame:
    borough_by_name = boroughs.set_index("borough_name")
    store_by_borough = store_locations.set_index("borough_name")
    realistic_costs = store_costs[store_costs["cost_scenario"] == "realistic"].set_index("store_id")
    physical_benefit_value = _physical_benefit_value(avg_discount_pct)

    rows = []
    for _, scenario in scenarios.iterrows():
        params = SCENARIO_PARAMS[scenario["scenario_name"]]
        is_physical = scenario["scenario_type"] == "physical_store"
        is_universal = scenario["eligibility_model"] == "universal"

        # Allocate citywide (non-physical) admin/verification cost proportionally
        # to each borough's share of citywide eligible households, so summing
        # across boroughs in Tableau reproduces the true citywide total.
        year_elig_totals = (
            demographics.assign(eligible=lambda d: d["total_households"] * d["pct_households_low_income"] / 100)
            .groupby("year")["eligible"].sum()
        )

        for _, demo in demographics.iterrows():
            borough_name = demo["borough_name"]
            year = demo["year"]
            borough_row = borough_by_name.loc[borough_name]
            eligible_households = demo["total_households"] * demo["pct_households_low_income"] / 100

            participation = params["participation_rate"] * (1 - params["estimated_stigma_dropout_pct"] / 100)

            if is_physical:
                store = store_by_borough.loc[borough_name]
                cost_row = realistic_costs.loc[store["store_id"]]
                households_within_radius = store["population_within_radius"] / AVG_HOUSEHOLD_SIZE

                if is_universal:
                    recipients_total = households_within_radius * participation
                    households_reached = recipients_total * (demo["pct_households_low_income"] / 100)
                else:
                    eligible_within_radius = households_within_radius * (demo["pct_households_low_income"] / 100)
                    households_reached = eligible_within_radius * participation

                total_program_cost = (
                    total_annual_cost(cost_row)
                    + params["admin_staff_cost_annual"]
                    + params["verification_system_cost_annual"]
                )
                benefit_value_per_household = physical_benefit_value

            else:
                borough_share = eligible_households / year_elig_totals.loc[year]
                allocated_overhead = (
                    params["admin_staff_cost_annual"] + params["verification_system_cost_annual"]
                ) * borough_share

                if is_universal:
                    recipients_total = demo["total_households"] * participation
                    households_reached = recipients_total * (demo["pct_households_low_income"] / 100)
                else:
                    recipients_total = eligible_households * participation
                    households_reached = recipients_total

                benefit_value_per_household = params["benefit_value_annual"]
                total_program_cost = benefit_value_per_household * recipients_total + allocated_overhead

            households_reached = min(households_reached, eligible_households)
            coverage_pct = min(households_reached / eligible_households * 100, 100.0) if eligible_households else 0.0
            roi_estimate = (
                (households_reached * benefit_value_per_household) / total_program_cost
                if total_program_cost else None
            )

            rows.append({
                "scenario_id": scenario["scenario_id"],
                "borough_id": borough_row["borough_id"],
                "year": year,
                "eligible_households": int(round(eligible_households)),
                "households_reached": int(round(households_reached)),
                "total_program_cost": round(total_program_cost, 2),
                "admin_overhead_cost": round(
                    params["admin_staff_cost_annual"] + params["verification_system_cost_annual"]
                    if is_physical else allocated_overhead,
                    2,
                ),
                "cost_per_household_reached": round(total_program_cost / households_reached, 2) if households_reached else None,
                "coverage_pct": round(coverage_pct, 2),
                "coverage_gap_pct": round(100 - coverage_pct, 2),
                "roi_estimate": round(roi_estimate, 4) if roi_estimate is not None else None,
            })

    return pd.DataFrame(rows)
