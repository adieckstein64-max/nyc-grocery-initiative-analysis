"""Generates a standalone Tableau workbook (.twb) with the 4 decision charts
already built — open it in Tableau Desktop and the charts are there, no
manual rebuilding required.

All derived values (color groupings, inline labels, chart-2's 3 cost tiers)
are pre-baked into the CSVs by decision_charts.export_tableau_extras(), so
every worksheet here is a plain drag-and-drop of existing columns onto
rows/cols/color/size/label — no calculated fields, no dual axes, no Gantt
marks. That keeps the hand-authored XML to the most standard, well-documented
shelf patterns Tableau has, to maximize the odds this opens cleanly with no
manual repair.

This file was authored without the ability to open Tableau and verify it —
if a shelf comes in empty or a color doesn't apply, the data and datasource
connections are still correct; re-dragging that one field takes seconds.

Run via `python scripts/build_tableau_workbook.py`.
"""

from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

DATA_DIR = Path(__file__).resolve().parent.parent / "exports_for_tableau"
OUT_PATH = Path(__file__).resolve().parent.parent / "NYC_Grocery_Initiative_Dashboard.twb"

MECHANISM_COLORS = {
    "NYC Grocery Tax Credit": "#2a78d6",
    "Targeted Digital Voucher": "#1baf7a",
    "Physical Stores": "#898781",
    "Universal Digital Voucher": "#ec835a",
}

TIER_COLORS = {
    "Planned CapEx (official $12M figure)": "#2a78d6",
    "Realistic CapEx (modeled)": "#eb6834",
    "Realistic CapEx + Year-1 hidden subsidy": "#d03b3b",
}

TIMELINE_COLORS = {**MECHANISM_COLORS, "Build & launch phase": "#e1e0d9"}

FLAG_COLORS = {"Meets guardrails": "#1baf7a", "Below reach guardrail": "#d03b3b"}


def _col(name: str, caption: str, datatype: str, role: str, dtype_type: str,
        default_agg: str | None = None) -> str:
    agg = f" default-aggregation='{default_agg}'" if default_agg else ""
    return (f"    <column caption='{caption}' datatype='{datatype}'{agg} "
            f"name='[{name}]' role='{role}' type='{dtype_type}' />")


def _datasource(ds_name: str, filename: str, columns: list[str]) -> str:
    cols = "\n".join(columns)
    directory = str(DATA_DIR)
    return f"""  <datasource caption='{ds_name}' inline='true' name='textscan.{ds_name}' version='18.1'>
    <connection class='textscan' directory='{directory}' filename='{filename}' password='' server=''>
      <relation name='{filename}' table='[{ds_name}#csv]' type='table' />
    </connection>
    <aliases enabled='yes' />
{cols}
  </datasource>"""


def _color_map(field: str, colors: dict[str, str]) -> str:
    entries = "\n".join(
        f"            <map to='{hexval}'>\n              <bucket>{escape(label)}</bucket>\n            </map>"
        for label, hexval in colors.items()
    )
    return f"""        <encoding attr='color' field='[{field}]' palette='automatic' type='palette'>
{entries}
        </encoding>"""


def _worksheet_bar(name: str, ds: str, rows_field: str, cols_field: str, cols_agg: str,
                   color_field: str, color_map: dict[str, str], label_field: str,
                   sort_desc_by: str | None = None) -> str:
    sort = ""
    if sort_desc_by:
        sort = f"\n        <sort class='tableau' direction='DESC' field='[{ds}].[{sort_desc_by}]' />"
    return f"""  <worksheet name='{name}'>
    <table>
      <view>
        <datasources>
          <datasource caption='{ds}' name='textscan.{ds}' />
        </datasources>
        <datasource-dependencies datasource='textscan.{ds}' />
      </view>
      <style />
      <panes>
        <pane selection-relaxation-option='selection-relaxation-allow'>
          <view>
            <breakdown value='auto' />
          </view>
          <mark class='Bar' />
          <encodings>
{_color_map(color_field, color_map)}
            <text column='[textscan.{ds}].[{label_field}]' />
          </encodings>
        </pane>
      </panes>
      <rows>[textscan.{ds}].[none:{rows_field}:nk]</rows>
      <cols>[textscan.{ds}].[{cols_agg}:{cols_field}:qk]</cols>{sort}
    </table>
  </worksheet>"""


def _worksheet_stacked_bar(name: str, ds: str, rows_field: str, stack_field: str,
                           value_field: str, color_map: dict[str, str], label_field: str) -> str:
    return f"""  <worksheet name='{name}'>
    <table>
      <view>
        <datasources>
          <datasource caption='{ds}' name='textscan.{ds}' />
        </datasources>
        <datasource-dependencies datasource='textscan.{ds}' />
      </view>
      <style />
      <panes>
        <pane selection-relaxation-option='selection-relaxation-allow'>
          <view>
            <breakdown value='auto' />
          </view>
          <mark class='Bar' />
          <encodings>
{_color_map(stack_field, color_map)}
            <text column='[textscan.{ds}].[{label_field}]' />
          </encodings>
        </pane>
      </panes>
      <rows>[textscan.{ds}].[none:{rows_field}:nk]</rows>
      <cols>[textscan.{ds}].[sum:{value_field}:qk]</cols>
    </table>
  </worksheet>"""


def _worksheet_grouped_bar(name: str, ds: str, cols_dim: str, cols_dim2: str, rows_field: str,
                           color_field: str, color_map: dict[str, str], label_field: str) -> str:
    return f"""  <worksheet name='{name}'>
    <table>
      <view>
        <datasources>
          <datasource caption='{ds}' name='textscan.{ds}' />
        </datasources>
        <datasource-dependencies datasource='textscan.{ds}' />
      </view>
      <style />
      <panes>
        <pane selection-relaxation-option='selection-relaxation-allow'>
          <view>
            <breakdown value='auto' />
          </view>
          <mark class='Bar' />
          <encodings>
{_color_map(color_field, color_map)}
            <text column='[textscan.{ds}].[{label_field}]' />
          </encodings>
        </pane>
      </panes>
      <rows>[textscan.{ds}].[sum:{rows_field}:qk]</rows>
      <cols>[textscan.{ds}].[none:{cols_dim}:nk]/[textscan.{ds}].[none:{cols_dim2}:nk]</cols>
    </table>
  </worksheet>"""


def _worksheet_scatter(name: str, ds: str, x_field: str, y_field: str, color_field: str,
                       color_map: dict[str, str], size_field: str, label_field: str) -> str:
    return f"""  <worksheet name='{name}'>
    <table>
      <view>
        <datasources>
          <datasource caption='{ds}' name='textscan.{ds}' />
        </datasources>
        <datasource-dependencies datasource='textscan.{ds}' />
      </view>
      <style />
      <panes>
        <pane selection-relaxation-option='selection-relaxation-allow'>
          <view>
            <breakdown value='auto' />
          </view>
          <mark class='Circle' />
          <encodings>
{_color_map(color_field, color_map)}
            <size column='[textscan.{ds}].[sum:{size_field}:qk]' />
            <text column='[textscan.{ds}].[{label_field}]' />
          </encodings>
        </pane>
      </panes>
      <rows>[textscan.{ds}].[avg:{y_field}:qk]</rows>
      <cols>[textscan.{ds}].[avg:{x_field}:qk]</cols>
    </table>
  </worksheet>"""


def build_workbook() -> str:
    mech_cols = [
        _col("mechanism", "Mechanism", "string", "dimension", "nominal"),
        _col("eligible_households", "Eligible Households", "real", "measure", "quantitative", "Sum"),
        _col("households_reached", "Households Reached", "real", "measure", "quantitative", "Sum"),
        _col("total_program_cost", "Total Program Cost", "real", "measure", "quantitative", "Sum"),
        _col("coverage_pct", "Coverage Pct", "real", "measure", "quantitative", "Avg"),
        _col("cost_per_hh_reached", "Cost Per Hh Reached", "real", "measure", "quantitative", "Avg"),
        _col("roi_estimate", "Roi Estimate", "real", "measure", "quantitative", "Avg"),
        _col("roi_label", "Roi Label", "string", "dimension", "nominal"),
        _col("flag_status", "Flag Status", "string", "dimension", "nominal"),
    ]
    tier_cols = [
        _col("borough_name", "Borough Name", "string", "dimension", "nominal"),
        _col("tier", "Tier", "string", "dimension", "nominal"),
        _col("tier_order", "Tier Order", "integer", "dimension", "ordinal"),
        _col("value_millions", "Value Millions", "real", "measure", "quantitative", "Sum"),
    ]
    timeline_cols = [
        _col("mechanism", "Mechanism", "string", "dimension", "nominal"),
        _col("phase", "Phase", "string", "dimension", "nominal"),
        _col("phase_order", "Phase Order", "integer", "dimension", "ordinal"),
        _col("start_month", "Start Month", "real", "measure", "quantitative", "Sum"),
        _col("end_month", "End Month", "real", "measure", "quantitative", "Sum"),
        _col("duration_months", "Duration Months", "real", "measure", "quantitative", "Sum"),
        _col("milestone_month", "Milestone Month", "real", "measure", "quantitative", "Avg"),
        _col("milestone_coverage_pct", "Milestone Coverage Pct", "real", "measure", "quantitative", "Avg"),
        _col("capped", "Capped", "boolean", "dimension", "nominal"),
        _col("color_key", "Color Key", "string", "dimension", "nominal"),
        _col("milestone_label", "Milestone Label", "string", "dimension", "nominal"),
    ]

    datasources = "\n".join([
        _datasource("mechanism_summary", "mechanism_summary.csv", mech_cols),
        _datasource("capex_tiers", "capex_tiers.csv", tier_cols),
        _datasource("rollout_timeline", "rollout_timeline.csv", timeline_cols),
    ])

    ws1 = _worksheet_scatter(
        "1 Reach vs Cost Frontier", "mechanism_summary",
        x_field="coverage_pct", y_field="cost_per_hh_reached",
        color_field="mechanism", color_map=MECHANISM_COLORS,
        size_field="total_program_cost", label_field="mechanism",
    )
    ws2 = _worksheet_grouped_bar(
        "2 Promise vs Real Bill", "capex_tiers",
        cols_dim="borough_name", cols_dim2="tier", rows_field="value_millions",
        color_field="tier", color_map=TIER_COLORS, label_field="value_millions",
    )
    ws3 = _worksheet_bar(
        "3 ROI Guardrailed", "mechanism_summary",
        rows_field="mechanism", cols_field="roi_estimate", cols_agg="avg",
        color_field="flag_status", color_map=FLAG_COLORS, label_field="roi_label",
        sort_desc_by=None,
    )
    ws4 = _worksheet_stacked_bar(
        "4 Time to Impact", "rollout_timeline",
        rows_field="mechanism", stack_field="color_key",
        value_field="duration_months", color_map=TIMELINE_COLORS,
        label_field="milestone_label",
    )
    worksheets = "\n".join([ws1, ws2, ws3, ws4])

    dashboard = """  <dashboard name='Executive Decision Summary'>
    <style />
    <size maxheight='1600' maxwidth='2000' minheight='1600' minwidth='2000' />
    <zones>
      <zone h='100000' id='1' type-v2='layout-basic' w='100000' x='0' y='0'>
        <zone h='6000' id='2' param='vert' type-v2='text' w='100000' x='0' y='0'>
          <formatted-text>
            <run bold='true' fontsize='18'>NYC Public Grocery Store Initiative — Executive Decision Summary</run>
          </formatted-text>
        </zone>
        <zone h='47000' id='3' type-v2='layout-flow' w='50000' x='0' y='6000'>
          <zone h='47000' id='4' name='1 Reach vs Cost Frontier' type-v2='layout-basic' w='50000' x='0' y='6000' />
        </zone>
        <zone h='47000' id='5' type-v2='layout-flow' w='50000' x='50000' y='6000'>
          <zone h='47000' id='6' name='2 Promise vs Real Bill' type-v2='layout-basic' w='50000' x='50000' y='6000' />
        </zone>
        <zone h='47000' id='7' type-v2='layout-flow' w='50000' x='0' y='53000'>
          <zone h='47000' id='8' name='3 ROI Guardrailed' type-v2='layout-basic' w='50000' x='0' y='53000' />
        </zone>
        <zone h='47000' id='9' type-v2='layout-flow' w='50000' x='50000' y='53000'>
          <zone h='47000' id='10' name='4 Time to Impact' type-v2='layout-basic' w='50000' x='50000' y='53000' />
        </zone>
      </zone>
    </zones>
  </dashboard>"""

    return f"""<?xml version='1.0' encoding='utf-8' ?>

<workbook source-build='2026.1.0' source-platform='mac' version='18.1' xmlns:user='http://www.tableausoftware.com/xml/user'>
  <preferences>
    <preference name='ui.encoding.shelf.height' value='24' />
  </preferences>
{datasources}
  <worksheets>
{worksheets}
  </worksheets>
  <dashboards>
{dashboard}
  </dashboards>
  <windows source-height='42'>
    <window class='worksheet' name='1 Reach vs Cost Frontier'>
      <cards>
        <edge name='left'>
          <strip size='160'>
            <card type='pages' />
            <card type='filters' />
            <card type='marks' />
          </strip>
        </edge>
        <edge name='top'>
          <strip size='2147483647'>
            <card type='columns' />
          </strip>
          <strip size='2147483647'>
            <card type='rows' />
          </strip>
        </edge>
      </cards>
    </window>
    <window class='dashboard' name='Executive Decision Summary'>
      <cards>
        <edge name='left'>
          <strip size='160'>
            <card type='pages' />
            <card type='filters' />
            <card type='legends' />
          </strip>
        </edge>
      </cards>
    </window>
  </windows>
</workbook>
"""


def write_workbook() -> Path:
    xml = build_workbook()
    OUT_PATH.write_text(xml)
    return OUT_PATH


if __name__ == "__main__":
    path = write_workbook()
    print(f"Wrote {path}")
