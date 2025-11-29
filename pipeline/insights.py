# pipeline/insights.py
"""
Microstep 9:
Generate basic scientific insights from clusters,
keywords, and cluster summaries.
"""

import pandas as pd
import json
from pathlib import Path

def find_top_keywords(df_keywords, top_n=5):
    """
    Returns top keywords per cluster.
    """
    result = {}

    for cid, group in df_keywords.groupby("cluster_id"):
        ranked = group.sort_values("score").head(top_n)  # YAKE: lower score = better
        result[cid] = list(ranked["keyword"])
    
    return result


def identify_knowledge_gaps(cluster_summaries):
    """
    Heuristic-based simple gap detector:
    searches for common scientific gap indicators.
    """
    gaps = []

    gap_terms = [
        "unknown", "unclear", "lack", "limited", "future work",
        "further studies", "not understood", "requires validation"
    ]

    for _, row in cluster_summaries.iterrows():
        text = row["cluster_summary"].lower()
        for term in gap_terms:
            if term in text:
                gaps.append({
                    "cluster_id": row["cluster_id"],
                    "gap_term": term,
                    "sentence": text
                })
    
    return gaps


def generate_insights(df_keywords, df_cluster_summaries):
    top_keywords = find_top_keywords(df_keywords)
    gaps = identify_knowledge_gaps(df_cluster_summaries)

    insights = {
        "top_keywords_per_cluster": top_keywords,
        "knowledge_gaps": gaps,
        "num_clusters": len(top_keywords)
    }

    return insights


def save_insights(insights, output_path):
    output_path = Path(output_path)
    with open(output_path, "w") as f:
        json.dump(insights, f, indent=4)
