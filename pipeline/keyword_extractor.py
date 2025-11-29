# pipeline/keyword_extractor.py
"""
Microstep 7:
Extract keywords from each paper summary, link to clusters,
and save cluster_keywords.csv.
"""

import pandas as pd
import yake

# YAKE configuration (can tune later)
kw_extractor = yake.KeywordExtractor(
    lan="en",
    n=1,            # unigrams
    dedupLim=0.9,
    top=10
)

def extract_keywords_from_text(text):
    """
    Extracts keywords from one summary.
    Returns list of (keyword, score).
    """
    try:
        return kw_extractor.extract_keywords(text)
    except:
        return []


def build_cluster_keywords(summaries_df, clusters_df):
    """
    Combine summaries.csv + clusters.csv
    For each summary:
        extract keywords
        attach cluster_id
    """
    merged = summaries_df.merge(clusters_df, on="paper_id", how="inner")

    rows = []

    for _, row in merged.iterrows():
        summary = row["summary"]
        paper_id = row["paper_id"]
        cluster_id = row["cluster_id"]

        # get top 10 keywords for this summary
        kw_list = extract_keywords_from_text(summary)

        for kw, score in kw_list:
            rows.append({
                "paper_id": paper_id,
                "cluster_id": cluster_id,
                "keyword": kw,
                "score": score
            })

    df_keywords = pd.DataFrame(rows)
    return df_keywords


from pipeline.summarizer import summarize_text

def generate_cluster_summaries(summaries_df, clusters_df):
    """
    For each cluster_id:
        gather all summaries in that cluster
        merge into a single blob
        run summarizer
        save cluster-level summary
    """
    merged = summaries_df.merge(clusters_df, on="paper_id", how="inner")

    cluster_ids = sorted(merged["cluster_id"].unique())
    rows = []

    for cid in cluster_ids:
        df_cluster = merged[merged["cluster_id"] == cid]

        # Combine summaries (limit text length if needed)
        big_text = " ".join(df_cluster["summary"].tolist())[:5000]

        try:
            cluster_summary = summarize_text(big_text, max_len=180)
        except:
            cluster_summary = "Summary generation failed."

        rows.append({
            "cluster_id": cid,
            "cluster_summary": cluster_summary
        })

    return pd.DataFrame(rows)
