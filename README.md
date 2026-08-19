# NYC Public Grocery Store Initiative — Analytics & Business Modeling

End-to-end analysis of the proposed NYC public grocery store program, benchmarked against
alternative purchasing-power interventions (tax credits / digital vouchers).

## Business questions

1. **Scale & means-testing**: 5 physical stores cover a tiny radius of the city. Restricting
   access to low-income residents requires means-testing (friction, stigma, admin overhead);
   opening to all erodes ROI by subsidizing households that don't need it.
2. **Market intervention trade-off**: how do direct purchasing-power interventions (tax
   credits, vouchers) compare to physical retail on scalability, time-to-market, coverage,
   and cost per household reached?

## Stack

- **Python** (Pandas, NumPy, SQLAlchemy, Matplotlib/Seaborn) — simulation, pipeline, modeling
- **MySQL** — relational store for demographics, costs, pricing, eligibility, scenario outputs
- **Tableau** — executive dashboard, fed by `exports_for_tableau/`

## Product & business strategy

North Star metric, guardrails, trade-off matrix, and phased rollout recommendation are
summarized in the project conversation; the headline finding: **direct purchasing-power
mechanisms (tax credit, targeted voucher) clear both a Net Social ROI guardrail (≥0.50)
and a coverage guardrail (≥60% of eligible households) — physical stores and universal
vouchers each fail one.** See `exports/charts/` for the 4 executive decision charts.

## Project structure

```
nyc-grocery-initiative-analysis/
├── data/
│   ├── raw/                # source/mock input data (gitignored)
│   └── processed/          # cleaned intermediate data (gitignored)
├── exports_for_tableau/    # flat CSVs feeding the Tableau workbook (gitignored)
├── exports/charts/         # 4 executive decision charts (PNG, dpi=300)
├── NYC_Grocery_Initiative_Dashboard.twb  # Tableau workbook — the 4 charts + dashboard, pre-built
├── notebooks/              # exploratory analysis
├── scripts/                # one-off / entrypoint scripts
│   ├── setup_database.py           # creates DB + runs schema.sql
│   ├── run_pipeline.py             # generates mock data, loads MySQL, exports CSVs
│   ├── generate_decision_charts.py # builds the 4 executive decision charts (PNG)
│   └── build_tableau_workbook.py   # builds NYC_Grocery_Initiative_Dashboard.twb
├── sql/
│   └── schema.sql          # MySQL DDL for all tables
├── src/
│   ├── config.py            # env-based settings
│   ├── db.py                 # SQLAlchemy engine/session helpers
│   ├── data_generation.py    # borough/demographic/price-basket baseline data
│   ├── cost_model.py         # CapEx/OpEx simulation (planned vs. realistic + hidden subsidies)
│   ├── policy_model.py       # subsidy scenarios, means-testing friction, scenario_outputs simulation
│   ├── pipeline.py           # orchestrates generation -> MySQL load -> Tableau CSV export
│   ├── style.py              # validated chart palette + mechanism color mapping
│   ├── decision_charts.py    # the 4 executive decision charts + Tableau CSV exports
│   └── tableau_workbook.py   # generates NYC_Grocery_Initiative_Dashboard.twb
├── .env.example
├── requirements.txt
└── README.md
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in your MySQL credentials
python scripts/setup_database.py
python scripts/run_pipeline.py
python scripts/generate_decision_charts.py
python scripts/build_tableau_workbook.py
```

Then open `NYC_Grocery_Initiative_Dashboard.twb` in Tableau Desktop — it connects to the CSVs
in `exports_for_tableau/` by absolute path, so keep the repo at its current location (or
re-run `build_tableau_workbook.py` after moving it, which regenerates the paths). If any shelf
comes in empty, the datasource connection is still correct — re-dragging that one field takes
seconds; this workbook was authored without a way to open Tableau and verify it end-to-end.

## Status

- [x] Project scaffold + MySQL schema
- [x] Mock data generation (demographics, CapEx/OpEx, price baskets)
- [x] Cost & CapEx simulation module
- [x] Means-testing & friction analysis module
- [x] Alternative policy modeling (tax credit / voucher)
- [x] Pipeline export to Tableau
- [x] Executive decision charts (Matplotlib/Seaborn)
- [x] Tableau dashboard (`NYC_Grocery_Initiative_Dashboard.twb`)
