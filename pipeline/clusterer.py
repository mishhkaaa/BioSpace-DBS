# pipeline/clusterer.py
"""
Microstep 6:
Clustering for all embeddings using KMeans.
"""

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans

def load_embeddings(npy_path, meta_path):
    """
    Load embeddings.npy and embeddings_meta.csv
    """
    embeddings = np.load(npy_path)
    meta = pd.read_csv(meta_path)
    return embeddings, meta


def run_kmeans(embeddings, n_clusters=5):
    """
    Apply KMeans clustering.
    """
    print(f"[Clusterer] Running KMeans with n_clusters={n_clusters}")
    kmeans = KMeans(n_clusters=n_clusters, random_state=42)
    labels = kmeans.fit_predict(embeddings)
    return labels


def generate_clusters(embeddings_path, meta_path, n_clusters=5):
    """
    Full clustering pipeline:
    - load embeddings
    - run clustering
    - produce dataframe: paper_id, cluster_id
    """
    embeddings, meta = load_embeddings(embeddings_path, meta_path)
    labels = run_kmeans(embeddings, n_clusters=n_clusters)

    meta["cluster_id"] = labels
    return meta[["paper_id", "cluster_id"]]
