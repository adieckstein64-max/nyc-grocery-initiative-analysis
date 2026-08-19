"""Build NYC_Grocery_Initiative_Dashboard.twb from the exports_for_tableau/ CSVs.

Usage:
    python scripts/build_tableau_workbook.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.tableau_workbook import write_workbook

if __name__ == "__main__":
    path = write_workbook()
    print(f"Wrote {path}")
