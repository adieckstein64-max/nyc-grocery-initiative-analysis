"""Orchestrates mock-data generation, MySQL load, and Tableau CSV export.

Idempotent: truncates all project tables (FK checks suspended, so order
doesn't matter) before reloading, so this can be re-run safely as the
model evolves.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from sqlalchemy import text

from src import cost_model, data_generation, policy_model
from src.cost_model import total_annual_cost
from src.db import get_engine

EXPORT_DIR = Path(__file__).resolve().parent.parent / "exports_for_tableau"

TABLES_IN_LOAD_ORDER = [
    "boroughs",
    "population_demographics",
    "income_distribution",
    "store_locations",
    "price_basket_items",
    "store_costs",
    "subsidy_scenarios",
    "means_testing_overhead",
    "scenario_outputs",
]


def _truncate_all(engine) -> None:
    with engine.begin() as conn:
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        for table in TABLES_IN_LOAD_ORDER:
            conn.execute(text(f"TRUNCATE TABLE {table}"))
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))


def run(export_csv: bool = True) -> None:
    engine = get_engine()
    _truncate_all(engine)

    # 1. boroughs
    boroughs = data_generation.boroughs_df()
    boroughs.to_sql("boroughs", engine, if_exists="append", index=False)
    boroughs_with_id = pd.read_sql("SELECT borough_id, borough_name FROM boroughs", engine)

    # 2. population_demographics
    demo = data_generation.population_demographics_df()
    demo_with_id = demo.merge(boroughs_with_id, on="borough_name")
    demo_with_id.drop(columns=["borough_name"]).to_sql(
        "population_demographics", engine, if_exists="append", index=False
    )

    # 3. income_distribution
    income = data_generation.income_distribution_df()
    income_with_id = income.merge(boroughs_with_id, on="borough_name")
    income_with_id.drop(columns=["borough_name"]).to_sql(
        "income_distribution", engine, if_exists="append", index=False
    )

    # 4. store_locations
    stores = data_generation.store_locations_df()
    stores_with_borough_id = stores.merge(boroughs_with_id, on="borough_name")
    stores_with_borough_id.drop(columns=["borough_name"]).to_sql(
        "store_locations", engine, if_exists="append", index=False
    )
    stores_with_id = pd.read_sql(
        "SELECT store_id, borough_id, store_name, service_radius_miles, population_within_radius "
        "FROM store_locations",
        engine,
    ).merge(boroughs_with_id, on="borough_id")

    # 5. price_basket_items
    price_basket = data_generation.price_basket_items_df()
    price_basket.to_sql("price_basket_items", engine, if_exists="append", index=False)

    # 6. store_costs
    store_costs = cost_model.build_store_costs_df(stores_with_id)
    store_costs.to_sql("store_costs", engine, if_exists="append", index=False)

    # 7. subsidy_scenarios
    scenarios = policy_model.build_subsidy_scenarios_df()
    scenarios.to_sql("subsidy_scenarios", engine, if_exists="append", index=False)
    scenarios_with_id = pd.read_sql(
        "SELECT scenario_id, scenario_name, scenario_type, eligibility_model FROM subsidy_scenarios",
        engine,
    )

    # 8. means_testing_overhead
    overhead = policy_model.build_means_testing_overhead_df(scenarios_with_id)
    overhead.to_sql("means_testing_overhead", engine, if_exists="append", index=False)

    # 9. scenario_outputs — the core simulation
    avg_discount = data_generation.avg_discount_pct()
    outputs = policy_model.build_scenario_outputs_df(
        scenarios=scenarios_with_id,
        boroughs=boroughs_with_id,
        demographics=demo,
        store_locations=stores_with_id,
        store_costs=store_costs,
        avg_discount_pct=avg_discount,
    )
    outputs.to_sql("scenario_outputs", engine, if_exists="append", index=False)

    print(f"Loaded {len(boroughs)} boroughs, {len(demo)} demographic rows, "
          f"{len(income)} income-bracket rows, {len(stores)} stores, "
          f"{len(price_basket)} basket items, {len(store_costs)} cost rows, "
          f"{len(scenarios)} scenarios, {len(overhead)} overhead rows, "
          f"{len(outputs)} scenario_outputs rows.")

    if export_csv:
        _export_for_tableau(engine)


def _export_for_tableau(engine) -> None:
    EXPORT_DIR.mkdir(exist_ok=True)

    for table in TABLES_IN_LOAD_ORDER:
        df = pd.read_sql(f"SELECT * FROM {table}", engine)
        df.to_csv(EXPORT_DIR / f"{table}.csv", index=False)

    # Denormalized, Tableau-friendly wide tables.
    scenario_outputs_flat = pd.read_sql(
        """
        SELECT so.*, sc.scenario_name, sc.scenario_type, sc.eligibility_model,
               sc.eligibility_threshold_pct_ami, b.borough_name
        FROM scenario_outputs so
        JOIN subsidy_scenarios sc ON sc.scenario_id = so.scenario_id
        JOIN boroughs b ON b.borough_id = so.borough_id
        """,
        engine,
    )
    scenario_outputs_flat.to_csv(EXPORT_DIR / "scenario_outputs_flat.csv", index=False)

    store_costs_flat = pd.read_sql(
        """
        SELECT sc.*, sl.store_name, sl.service_radius_miles, sl.population_within_radius,
               b.borough_name
        FROM store_costs sc
        JOIN store_locations sl ON sl.store_id = sc.store_id
        JOIN boroughs b ON b.borough_id = sl.borough_id
        """,
        engine,
    )
    store_costs_flat["total_annual_cost"] = store_costs_flat.apply(total_annual_cost, axis=1)
    store_costs_flat.to_csv(EXPORT_DIR / "store_costs_flat.csv", index=False)

    print(f"Exported {len(TABLES_IN_LOAD_ORDER) + 2} CSVs to {EXPORT_DIR}")


if __name__ == "__main__":
    run()
