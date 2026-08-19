"""CapEx/OpEx simulation for the proposed physical stores.

Models the gap between the official planning estimate (~$12M construction
per store) and a realistic estimate (~$30M+) that accounts for NYC
construction-cost overruns, prevailing-wage/union labor, and procurement
delays — plus the *hidden* municipal subsidies that don't show up in a
headline CapEx number: foregone property tax and free/below-market rent on
city-owned real estate.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

RNG_SEED = 43

PLANNED_CAPEX_CONSTRUCTION = 12_000_000.0
PLANNED_CAPEX_EQUIPMENT = 1_500_000.0


def build_store_costs_df(store_locations: pd.DataFrame) -> pd.DataFrame:
    """store_locations must have a `store_id` column (post-DB-insert)."""
    rng = np.random.default_rng(RNG_SEED)
    rows = []

    for _, store in store_locations.iterrows():
        planned = {
            "store_id": store["store_id"],
            "cost_scenario": "planned",
            "capex_construction": PLANNED_CAPEX_CONSTRUCTION,
            "capex_equipment": PLANNED_CAPEX_EQUIPMENT,
            "opex_annual_labor": round(rng.uniform(4_200_000, 4_800_000), 2),
            "opex_annual_utilities": round(rng.uniform(380_000, 450_000), 2),
            "opex_annual_inventory_subsidy": round(rng.uniform(1_000_000, 1_400_000), 2),
            "foregone_property_tax_annual": round(rng.uniform(350_000, 500_000), 2),
            "rent_subsidy_annual": round(rng.uniform(1_400_000, 2_000_000), 2),
            "notes": "Official city planning estimate",
        }
        realistic = {
            "store_id": store["store_id"],
            "cost_scenario": "realistic",
            "capex_construction": round(rng.uniform(28_000_000, 34_000_000), 2),
            "capex_equipment": round(rng.uniform(2_200_000, 2_800_000), 2),
            "opex_annual_labor": round(planned["opex_annual_labor"] * rng.uniform(1.15, 1.30), 2),
            "opex_annual_utilities": round(planned["opex_annual_utilities"] * rng.uniform(1.10, 1.25), 2),
            "opex_annual_inventory_subsidy": round(planned["opex_annual_inventory_subsidy"] * rng.uniform(1.10, 1.30), 2),
            "foregone_property_tax_annual": round(planned["foregone_property_tax_annual"] * rng.uniform(1.05, 1.20), 2),
            "rent_subsidy_annual": round(planned["rent_subsidy_annual"] * rng.uniform(1.05, 1.20), 2),
            "notes": "Modeled realistic cost incl. construction overruns, prevailing-wage labor, procurement delays",
        }
        rows.extend([planned, realistic])

    return pd.DataFrame(rows)


def total_annual_cost(cost_row: pd.Series, capex_amortization_years: int = 20) -> float:
    """Amortized CapEx + annual OpEx + hidden subsidies for one store-year."""
    amortized_capex = (cost_row["capex_construction"] + cost_row["capex_equipment"]) / capex_amortization_years
    opex = (
        cost_row["opex_annual_labor"]
        + cost_row["opex_annual_utilities"]
        + cost_row["opex_annual_inventory_subsidy"]
    )
    hidden_subsidy = cost_row["foregone_property_tax_annual"] + cost_row["rent_subsidy_annual"]
    return amortized_capex + opex + hidden_subsidy
