# config/config.py
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]     # dbs/
DATA_DIR = ROOT / "data"
OUTPUTS_DIR = DATA_DIR / "outputs"

# member 1 processed file now copied here
PAPERS_CSV = DATA_DIR / "papers_clean.csv"

# minimum required columns for first validation
REQUIRED_COLUMNS = ["paper_id", "title", "abstract"]
