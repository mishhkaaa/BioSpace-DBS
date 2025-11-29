# pipeline/embedder.py
"""
Microstep 5:
Batch embedding generation for all paper summaries.
"""

import numpy as np
import pandas as pd
from tqdm import tqdm
from sentence_transformers import SentenceTransformer

EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

print(f"[Embedder] Loading model: {EMBED_MODEL}")
embedder = SentenceTransformer(EMBED_MODEL)


def embed_text(text: str):
    """
    Single text embedding
    """
    return embedder.encode(text)


def embed_all(df, text_column="summary"):
    """
    Embeds ALL summaries in the dataframe.
    Returns:
        - numpy array of shape (N, D)
        - metadata dataframe (paper_id, row_index)
    """
    vectors = []
    meta_rows = []

    for idx, row in tqdm(df.iterrows(), total=len(df), desc="Embedding summaries"):
        summary = row[text_column]
        vector = embed_text(summary)
        vectors.append(vector)

        meta_rows.append({
            "paper_id": row["paper_id"],
            "row_index": idx
        })

    embeddings_array = np.vstack(vectors)
    embeddings_meta = pd.DataFrame(meta_rows)

    return embeddings_array, embeddings_meta
