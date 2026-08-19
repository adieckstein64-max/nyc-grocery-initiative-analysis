"""Shared chart styling: validated categorical palette + chrome tokens.

Palette is the dataviz-skill reference instance (light mode). Colors are
assigned by fixed slot order and reused consistently for the same entity
across charts (e.g. a scenario keeps its color in every chart it appears in).
"""

import matplotlib.pyplot as plt
import seaborn as sns

CATEGORICAL = {
    "blue": "#2a78d6",
    "orange": "#eb6834",
    "aqua": "#1baf7a",
    "yellow": "#eda100",
    "magenta": "#e87ba4",
    "green": "#008300",
    "violet": "#4a3aa7",
    "red": "#e34948",
}

CHROME = {
    "surface": "#fcfcfb",
    "primary_ink": "#0b0b0b",
    "secondary_ink": "#52514e",
    "muted_ink": "#898781",
    "gridline": "#e1e0d9",
    "baseline": "#c3c2b7",
}

STATUS = {
    "good": "#0ca30c",
    "warning": "#fab219",
    "serious": "#ec835a",
    "critical": "#d03b3b",
}

# The 4 executive decision mechanisms, in recommendation order, with a fixed
# color mapping reused across every decision chart: saturated highlight for
# the two recommended mechanisms, neutral gray / critical red for the two
# flagged ones. This mapping is the visual spine of the whole Step-3 story —
# a mechanism's color never changes between charts.
MECHANISM_ORDER = [
    "NYC Grocery Tax Credit",
    "Targeted Digital Voucher",
    "Physical Stores",
    "Universal Digital Voucher",
]

MECHANISM_COLORS = {
    "NYC Grocery Tax Credit": CATEGORICAL["blue"],       # recommended — standout blue
    "Targeted Digital Voucher": CATEGORICAL["aqua"],     # recommended — standout teal
    "Physical Stores": CHROME["muted_ink"],              # flagged — muted gray
    "Universal Digital Voucher": STATUS["serious"],      # flagged — warning orange
}


def set_style() -> None:
    sns.set_theme(style="white")
    plt.rcParams.update({
        "figure.facecolor": CHROME["surface"],
        "axes.facecolor": CHROME["surface"],
        "savefig.facecolor": CHROME["surface"],
        "font.family": "sans-serif",
        "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"],
        "text.color": CHROME["primary_ink"],
        "axes.edgecolor": CHROME["baseline"],
        "axes.labelcolor": CHROME["secondary_ink"],
        "axes.titlecolor": CHROME["primary_ink"],
        "xtick.color": CHROME["muted_ink"],
        "ytick.color": CHROME["muted_ink"],
        "grid.color": CHROME["gridline"],
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.spines.left": False,
        "axes.grid": True,
        "axes.grid.axis": "y",
        "grid.linewidth": 0.8,
        "font.size": 11,
        "axes.titlesize": 13,
        "axes.titleweight": "bold",
    })
