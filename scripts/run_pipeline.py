"""Generate mock data, load MySQL, and export CSVs for Tableau.

Usage:
    python scripts/run_pipeline.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.pipeline import run

if __name__ == "__main__":
    run()
