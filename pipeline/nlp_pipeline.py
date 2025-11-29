# pipeline/nlp_pipeline.py
"""
Microstep 9:
Generate insights.json using keywords and cluster summaries.
"""

import sys
from pathlib import Path

# Add parent directory to path so imports work
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import os
import pandas as pd
from config.config import OUTPUTS_DIR
from pipeline.insights import generate_insights, save_insights

def main():
    keywords_file = OUTPUTS_DIR / "cluster_keywords.csv"
    summaries_file = OUTPUTS_DIR / "cluster_summaries.csv"

    print("Loading cluster keywords and cluster summaries...")
    df_keywords = pd.read_csv(keywords_file)
    df_cluster_summaries = pd.read_csv(summaries_file)

    print("Generating insights...")
    insights = generate_insights(df_keywords, df_cluster_summaries)

    output_path = OUTPUTS_DIR / "insights.json"
    save_insights(insights, output_path)

    print(f"Insights saved → {output_path}")
    print(insights)

if __name__ == "__main__":
    main()
