"""Generate the 4 executive decision charts from exports_for_tableau/ CSVs.

Usage:
    python scripts/generate_decision_charts.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.decision_charts import generate_all

if __name__ == "__main__":
    generate_all()
