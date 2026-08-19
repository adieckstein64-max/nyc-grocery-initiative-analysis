"""Baseline reference data + simulated distributions for the 5 NYC boroughs.

Population and land-area figures are anchored to widely-published Census/ACS
orders of magnitude and are accurate to roughly the nearest thousand/percent.
Household-income distributions, price baskets, and store-siting figures are
*simulated* (seeded RNG) to be directionally realistic for modeling purposes —
swap in exact ACS/DCP source data before using this for a real public
presentation.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

RNG_SEED = 42
YEARS = [2024, 2025, 2026]
AVG_HOUSEHOLD_SIZE = 2.6  # NYC citywide approx persons/household

# ---------------------------------------------------------------------------
# 1. Boroughs — anchor reference data
# ---------------------------------------------------------------------------
_BOROUGH_ANCHORS = {
    "Manhattan":     {"total_population": 1_694_251, "land_area_sq_miles": 22.83},
    "Brooklyn":      {"total_population": 2_736_074, "land_area_sq_miles": 69.38},
    "Queens":        {"total_population": 2_405_464, "land_area_sq_miles": 108.10},
    "Bronx":         {"total_population": 1_472_654, "land_area_sq_miles": 42.10},
    "Staten Island": {"total_population": 495_747,   "land_area_sq_miles": 58.37},
}

# 2024 baseline demographics per borough (approximate/illustrative).
_DEMO_ANCHORS = {
    "Manhattan":     {"total_households": 772_000, "median_household_income": 101_000, "poverty_rate_pct": 14.5, "snap_enrollment_pct": 13.0, "food_insecurity_rate_pct": 12.0, "pct_households_low_income": 28.0},
    "Brooklyn":      {"total_households": 1_000_000, "median_household_income": 70_000,  "poverty_rate_pct": 19.0, "snap_enrollment_pct": 24.0, "food_insecurity_rate_pct": 18.0, "pct_households_low_income": 38.0},
    "Queens":        {"total_households": 815_000,  "median_household_income": 77_000,  "poverty_rate_pct": 12.5, "snap_enrollment_pct": 17.0, "food_insecurity_rate_pct": 14.0, "pct_households_low_income": 30.0},
    "Bronx":         {"total_households": 500_000,  "median_household_income": 45_000,  "poverty_rate_pct": 27.0, "snap_enrollment_pct": 34.0, "food_insecurity_rate_pct": 24.0, "pct_households_low_income": 48.0},
    "Staten Island": {"total_households": 178_000,  "median_household_income": 89_000,  "poverty_rate_pct": 11.0, "snap_enrollment_pct": 10.0, "food_insecurity_rate_pct": 9.0,  "pct_households_low_income": 20.0},
}

# Income-bracket share of households per borough (approximate, sums to 100).
_INCOME_BRACKETS = [
    ("<$25,000", 0, 25_000),
    ("$25,000-$49,999", 25_000, 49_999),
    ("$50,000-$74,999", 50_000, 74_999),
    ("$75,000-$99,999", 75_000, 99_999),
    ("$100,000-$149,999", 100_000, 149_999),
    ("$150,000+", 150_000, None),
]

_INCOME_SHARE_ANCHORS = {
    "Manhattan":     [18, 12, 10, 10, 16, 34],
    "Brooklyn":      [22, 18, 15, 13, 17, 15],
    "Queens":        [16, 17, 16, 15, 20, 16],
    "Bronx":         [34, 24, 16, 10, 10, 6],
    "Staten Island": [10, 13, 15, 15, 24, 23],
}

_PRICE_BASKET = [
    # (item_name, category, unit, market_price, subsidized_discount_pct)
    ("Milk (1 gallon)", "Dairy", "gallon", 4.79, 0.18),
    ("Eggs (dozen, large)", "Dairy", "dozen", 5.49, 0.20),
    ("White Bread (loaf)", "Grains", "loaf", 4.29, 0.15),
    ("Brown Rice (1 lb)", "Grains", "lb", 2.49, 0.15),
    ("Rolled Oats (1 lb)", "Grains", "lb", 3.29, 0.15),
    ("Chicken Breast (1 lb)", "Protein", "lb", 5.99, 0.20),
    ("Ground Beef (1 lb)", "Protein", "lb", 6.99, 0.18),
    ("Canned Black Beans", "Protein", "each", 1.79, 0.15),
    ("Bananas (1 lb)", "Produce", "lb", 0.69, 0.10),
    ("Apples (1 lb)", "Produce", "lb", 2.19, 0.12),
    ("Carrots (1 lb)", "Produce", "lb", 1.49, 0.12),
    ("Spinach (bunch)", "Produce", "bunch", 2.99, 0.15),
    ("Onions (1 lb)", "Produce", "lb", 1.29, 0.10),
    ("Potatoes (5 lb bag)", "Produce", "bag", 5.99, 0.15),
    ("Orange Juice (64 oz)", "Beverages", "bottle", 5.49, 0.18),
    ("Cheddar Cheese (8 oz)", "Dairy", "each", 4.49, 0.18),
    ("Peanut Butter (16 oz)", "Pantry", "jar", 4.99, 0.15),
    ("Pasta (1 lb)", "Grains", "lb", 1.99, 0.12),
]


def boroughs_df() -> pd.DataFrame:
    rows = [{"borough_name": name, **vals} for name, vals in _BOROUGH_ANCHORS.items()]
    return pd.DataFrame(rows)


def population_demographics_df() -> pd.DataFrame:
    rng = np.random.default_rng(RNG_SEED)
    rows = []
    for name, base in _DEMO_ANCHORS.items():
        for i, year in enumerate(YEARS):
            drift = 1 + 0.025 * i  # ~2.5%/yr income drift
            noise = rng.normal(0, 0.4, size=1)[0]  # small pp noise on rates
            rows.append({
                "borough_name": name,
                "year": year,
                "total_households": int(base["total_households"] * (1 + 0.003 * i)),
                "median_household_income": round(base["median_household_income"] * drift, 2),
                "poverty_rate_pct": round(max(base["poverty_rate_pct"] + noise, 0), 2),
                "snap_enrollment_pct": round(max(base["snap_enrollment_pct"] + noise * 0.8, 0), 2),
                "food_insecurity_rate_pct": round(max(base["food_insecurity_rate_pct"] + noise * 0.6, 0), 2),
                "pct_households_low_income": round(max(base["pct_households_low_income"] + noise * 0.5, 0), 2),
            })
    return pd.DataFrame(rows)


def income_distribution_df() -> pd.DataFrame:
    rows = []
    demo = {r["borough_name"]: r for r in population_demographics_df().to_dict("records") if r["year"] == YEARS[0]}
    for name, shares in _INCOME_SHARE_ANCHORS.items():
        total_hh = demo[name]["total_households"]
        for (label, bmin, bmax), share_pct in zip(_INCOME_BRACKETS, shares):
            for year in YEARS:
                rows.append({
                    "borough_name": name,
                    "year": year,
                    "income_bracket_label": label,
                    "bracket_min": bmin,
                    "bracket_max": bmax,
                    "household_count": int(round(total_hh * share_pct / 100)),
                    "pct_of_total_households": share_pct,
                })
    return pd.DataFrame(rows)


def store_locations_df() -> pd.DataFrame:
    """One flagship proposed store per borough — the actual 5-store pilot scope."""
    rng = np.random.default_rng(RNG_SEED)
    rows = []
    for name in _BOROUGH_ANCHORS:
        radius = round(rng.uniform(1.0, 1.6), 2)
        # Population reachable within a walkable service radius — a small
        # fraction of the borough, which is the core scale limitation.
        reach_pct_of_borough = rng.uniform(0.025, 0.05)
        pop_in_radius = int(_BOROUGH_ANCHORS[name]["total_population"] * reach_pct_of_borough)
        rows.append({
            "borough_name": name,
            "store_name": f"NYC Public Grocery — {name} Pilot",
            "address": f"TBD, {name}, NY",
            "latitude": None,
            "longitude": None,
            "service_radius_miles": radius,
            "population_within_radius": pop_in_radius,
            "planned_open_date": "2027-01-01",
            "status": "planned",
        })
    return pd.DataFrame(rows)


def price_basket_items_df() -> pd.DataFrame:
    rows = []
    for name, category, unit, market_price, discount_pct in _PRICE_BASKET:
        subsidized_price = round(market_price * (1 - discount_pct), 2)
        rows.append({
            "item_name": name,
            "category": category,
            "unit": unit,
            "market_price": market_price,
            "subsidized_price": subsidized_price,
        })
    return pd.DataFrame(rows)


def avg_discount_pct() -> float:
    """Mean discount rate across the price basket — used to value in-store savings."""
    df = price_basket_items_df()
    return float(((df["market_price"] - df["subsidized_price"]) / df["market_price"]).mean())
