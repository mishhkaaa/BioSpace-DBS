# pipeline/utils.py
import pandas as pd
from pathlib import Path

def load_and_validate_data(csv_path, required_columns):
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")
    
    df = pd.read_csv(csv_path)
    
    missing = [c for c in required_columns if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns in CSV: {missing}")
    
    df = df.dropna(subset=["paper_id", "abstract"])
    df = df.reset_index(drop=True)
    return df
