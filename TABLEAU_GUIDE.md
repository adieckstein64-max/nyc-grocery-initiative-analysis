# Tableau Build Guide — Executive Decision Dashboard

Reproduces the 4 `exports/charts/*.png` decision charts natively in Tableau Desktop, with
real interactivity (tooltips, filters) that a static PNG can't give you. Uses the
pre-aggregated CSVs in `exports_for_tableau/` so most sheets need **zero calculated
fields** — just drag-and-drop.

Run `python scripts/generate_decision_charts.py` first if these don't exist yet:
- `exports_for_tableau/mechanism_summary.csv` — one row per mechanism (feeds sheets 1 & 3)
- `exports_for_tableau/rollout_timeline.csv` — one row per mechanism × phase (feeds sheet 4)
- `exports_for_tableau/store_costs_flat.csv` — one row per store × cost scenario (feeds sheet 2)

**Fixed mechanism color mapping** — use this palette everywhere below (Data pane → right-click
field → Default Properties → Color, or per-sheet via the Color legend → Edit Colors):

| Mechanism | Hex |
|---|---|
| NYC Grocery Tax Credit | `#2A78D6` |
| Targeted Digital Voucher | `#1BAF7A` |
| Physical Stores | `#898781` |
| Universal Digital Voucher | `#EC835A` |

---

## Sheet 1 — The Reach-vs-Cost Frontier

**Data source:** `mechanism_summary.csv`

1. Columns: `AVG(coverage_pct)` (continuous).
2. Rows: `AVG(cost_per_hh_reached)` → right-click the axis → **Log scale**.
3. Marks type: **Circle**.
4. Drag `mechanism` to **Color** → Edit Colors → apply the palette above.
5. Drag `mechanism` to **Detail** and to **Label**.
6. Drag `total_program_cost` to **Size**.
7. Analytics pane → drag **Reference Line** onto the coverage axis → Constant → value `60`
   (the coverage guardrail).
8. Analytics pane → drag **Reference Band** onto the cost axis → From `Min` to `2000`
   (approximates the "efficient frontier" shading from the Python version).
9. Right-click the Tax Credit mark → **Annotate → Mark**, paste:
   > **Optimal Policy:** Direct purchasing power support via tax rails. Zero retail
   > overhead, zero stigma, near-zero friction.
10. Right-click the Physical Stores mark → **Annotate → Mark**, paste:
    > **Market Distortion:** Heavy CapEx/OpEx. Retail means-testing at store entrances
    > creates an impossible trade-off between massive budget leakage and operational friction.
11. Title: *"The Reach-vs-Cost Frontier: Purchasing Power vs. Shelf-Price Subsidies"*, with
    subtitle text object below it: *"Direct tax credits achieve ~1:1 efficiency via existing
    tax rails; physical store subsidies collapse under fixed retail overhead and
    means-testing friction."*

---

## Sheet 2 — The $12M Promise vs. the Real Bill

**Data source:** `store_costs_flat.csv`

Create 3 calculated fields:

```
Total CapEx ($M)
([capex_construction] + [capex_equipment]) / 1000000
```
```
Planned CapEx
IIF([cost_scenario] = "planned", [Total CapEx ($M)], NULL)
```
```
Realistic CapEx
IIF([cost_scenario] = "realistic", [Total CapEx ($M)], NULL)
```
```
Realistic + Hidden Subsidy
IIF([cost_scenario] = "realistic",
    [Total CapEx ($M)] + ([foregone_property_tax_annual] + [rent_subsidy_annual]) / 1000000,
    NULL)
```

1. Select all three (`Planned CapEx`, `Realistic CapEx`, `Realistic + Hidden Subsidy`) in the
   Data pane with Ctrl/Cmd-click, then drag them together onto **Rows** — Tableau auto-creates
   `Measure Names` / `Measure Values`.
2. Drag `borough_name` to **Columns**, then drag `Measure Names` to **Columns** too (after
   `borough_name`) to get the clustered/grouped bar layout.
3. Drag `Measure Names` to **Color** → Edit Colors: Planned=`#2A78D6`, Realistic=`#EB6834`,
   Realistic + Hidden Subsidy=`#D03B3B`.
4. Filter `Measure Names` to keep only those 3 fields (Tableau lists all numeric fields by
   default).
5. Drag `Measure Values` to **Label**, format as `$#,##0"M"`.
6. Title: *"The $12M Promise vs. the Real Bill"*, subtitle: *"Realistic construction cost
   runs ~2.3x the announced figure per store — municipal retail initiatives mask ongoing
   balance-sheet subsidies the headline number never shows."*

---

## Sheet 3 — Net Social ROI, Guardrailed

**Data source:** `mechanism_summary.csv`

Calculated field:

```
ROI Label
"ROI " + STR(ROUND(AVG([roi_estimate]), 2)) + "   |   " +
STR(ROUND(AVG([coverage_pct]), 0)) + "% reach" +
IIF(AVG([coverage_pct]) < 60, "  (below reach guardrail)", "")
```

1. Rows: `mechanism` — sort descending by `AVG(roi_estimate)` (click the sort icon on the
   ROI axis, or right-click the field → Sort).
2. Columns: `AVG(roi_estimate)`.
3. Marks type: **Bar** (horizontal).
4. Color: `mechanism` → same palette.
5. Label: `ROI Label`.
6. Analytics pane → **Reference Line** on the ROI axis → Constant → value `0.5`, label
   "Minimum acceptable Net Social ROI".
7. Title: *"Net Social ROI, Guardrailed by Coverage"*, subtitle: *"Only income-side
   mechanisms — Tax Credit and Targeted Voucher — cross both the ROI and reach thresholds;
   Physical Stores' ROI is disqualified by its 4% reach."*

---

## Sheet 4 — Time-to-First-Impact (Gantt)

**Data source:** `rollout_timeline.csv`

Calculated field (unifies the gray "build" segment with each mechanism's colored "ramp"
segment into one color field):

```
Bar Color Key
IF [phase] = "Build & launch" THEN "Build & launch phase" ELSE [mechanism] END
```

1. Marks type: **Gantt Bar**.
2. Rows: `mechanism` — manually reorder (drag in the Rows shelf) to launch-month order:
   Tax Credit, Universal Voucher, Targeted Voucher, Physical Stores.
3. Columns: `SUM(start_month)` (continuous).
4. Size: `SUM(duration_months)`.
5. Color: `Bar Color Key` → Edit Colors: "Build & launch phase" = `#E1E0D9` (gray), each
   mechanism = its palette color.
6. **Add the milestone markers** (dual axis): drag `SUM(milestone_month)` to **Columns** next
   to the existing field → right-click its axis → **Dual Axis** → right-click again →
   **Synchronize Axis**. Change that second marks card's type to **Shape** (diamond), color
   by `mechanism`.
7. On the diamond marks card, drag `milestone_coverage_pct` to **Label**; format the label
   text as *"Month <ATTR(milestone_month)>: <ATTR(milestone_coverage_pct)>% reach"* (use the
   Label editor's Insert menu to combine fields). For the `capped = True` row (Physical
   Stores), manually append " (hard cap — cannot scale further)" via a calculated label field
   or a mark annotation, and set that label's font color to `#D03B3B`.
8. Title: *"Time-to-First-Impact"*, subtitle: *"Existing tax/benefit rails deliver immediate
   relief within one budget cycle vs. 24+ months of retail development lag before Physical
   Stores serve a single household."*

---

## Dashboard assembly

1. New Dashboard → size **1600 × 1200** (or Automatic).
2. Drag all 4 sheets into a 2×2 grid (horizontal container on top for Sheets 1–2, another
   below for Sheets 3–4, stacked in a vertical container).
3. Add a title text object: *"NYC Public Grocery Store Initiative — Executive Decision
   Summary"*.
4. Add a footnote text object with the same data caveat as the Python charts: borough
   population/land area are real Census-order figures; income distributions, price basket,
   and cost estimates are seeded simulations calibrated to plausible NYC magnitudes, not
   sourced from live ACS/DCP data.
5. Optional cross-filtering: Sheets 1 & 3 share `mechanism_summary.csv`, so a `mechanism`
   filter from one applies to the other via **Apply to Worksheets → All Using This Data
   Source**. Sheets 2 & 4 use different data sources, so they won't cross-filter
   automatically — a `borough_name` / `mechanism` **Parameter** driving a calculated filter
   on each data source is the standard workaround if you want full cross-filtering.

## Alternative: live MySQL connection

Instead of the CSVs, you can connect Tableau directly to the `nyc_grocery_initiative`
database (More… → MySQL connector; requires the MySQL ODBC/Connector driver, which Tableau
prompts to install if missing). Credentials are in `.env` (`DB_USER=nyc_grocery_app`). A live
connection means the dashboard always reflects the latest `python scripts/run_pipeline.py`
run — the CSV route means re-exporting after each pipeline run. The same calculated-field
formulas above apply; you'd rebuild `mechanism_summary`'s aggregation logic as a Tableau LOD
expression per mechanism instead of reading it pre-computed (ask if you want those LOD
formulas — they mirror `src/decision_charts.py::load_mechanism_summary`).
