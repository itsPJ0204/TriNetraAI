"""
run_clustering.py — Job B Runner: Discovery & Similarity Clustering
====================================================================
Runs the full clustering pipeline on the Year 3 (2026) composite and outputs:

    cluster_outputs/
    |-- cluster_map.png          <- spatial map coloured by cluster ID
    |-- tile_embeddings.npy      <- (N_tiles, 50) embedding matrix
    |-- tile_metadata.json       <- tile IDs, row/col positions, valid_frac
    |-- similar_tiles.json       <- demo: find_similar results for sample tiles

Usage:
    python run_clustering.py

Requirements:
    - sih_dataset/year_3/default.tif must be a 5-band TIF (run download.py first)
    - pip install tifffile numpy scikit-learn matplotlib scipy
"""

import json
import os
import numpy as np

from clustering import (
    build_and_cluster,
    find_similar,
    visualise_clusters,
)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(BASE_DIR, "sih_dataset")
OUTPUT_DIR  = os.path.join(BASE_DIR, "cluster_outputs")

# We cluster the most recent (2026) year by default — fewest atmospheric issues
TIF_PATH = os.path.join(DATASET_DIR, "year_3", "default.tif")

TILE_SIZE       = 32   # 512/32 = 16x16 grid = 256 tiles before cloud exclusion
N_PCA_DIMS      = 50   # embedding dimensionality
N_CLUSTERS      = 8    # K-Means clusters (tunable; 8 is a sensible default for urban AOI)
MIN_VALID_FRAC  = 0.3  # skip tiles with < 30% valid (cloud-free) pixels

# Tiles to demo find_similar on — we'll pick the first, middle, and last valid tiles
DEMO_TOP_K = 5


def run_clustering():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("=" * 60)
    print("  Sentinel-2 Discovery & Clustering Pipeline (Job B)")
    print("=" * 60)

    if not os.path.exists(TIF_PATH):
        print(f"\n[ERROR] {TIF_PATH} not found.")
        print("  -> Run download.py first to fetch the 5-band composite.")
        return

    # -----------------------------------------------------------------------
    # 1. Tile + Embed + Cluster
    # -----------------------------------------------------------------------
    result = build_and_cluster(
        tif_path=TIF_PATH,
        tile_size=TILE_SIZE,
        n_components=N_PCA_DIMS,
        n_clusters=N_CLUSTERS,
        min_valid_frac=MIN_VALID_FRAC,
        scl_band_index=4,
    )
    tiles      = result["tiles"]
    embeddings = result["embeddings"]
    labels     = result["labels"]
    img_shape  = result["img_shape"]

    print(f"\n  Total valid tiles : {len(tiles)}")
    print(f"  Embedding shape   : {embeddings.shape}")

    # -----------------------------------------------------------------------
    # 2. Save artefacts
    # -----------------------------------------------------------------------

    # 2a. Embedding matrix
    emb_path = os.path.join(OUTPUT_DIR, "tile_embeddings.npy")
    np.save(emb_path, embeddings)
    print(f"\n  Saved embeddings  : {emb_path}")

    # 2b. Tile metadata (without the large patch arrays — keep JSON small)
    metadata = [
        {
            "id":          t["id"],
            "row":         t["row"],
            "col":         t["col"],
            "valid_frac":  t["valid_frac"],
            "cluster":     int(labels[i]),
        }
        for i, t in enumerate(tiles)
    ]
    meta_path = os.path.join(OUTPUT_DIR, "tile_metadata.json")
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"  Saved metadata    : {meta_path}")

    # 2c. Cluster map visualisation
    map_path = os.path.join(OUTPUT_DIR, "cluster_map.png")
    visualise_clusters(
        labels=labels,
        tiles=tiles,
        img_shape=img_shape,
        tile_size=TILE_SIZE,
        save_path=map_path,
    )

    # -----------------------------------------------------------------------
    # 3. Demo: find_similar() on a few representative tiles
    # -----------------------------------------------------------------------
    print("\n--- find_similar() Demo ---")

    # Pick demo tiles: first, middle-ish, and last valid tile
    demo_ids = []
    if len(tiles) > 0:
        demo_ids.append(tiles[0]["id"])
    if len(tiles) > 2:
        demo_ids.append(tiles[len(tiles) // 2]["id"])
    if len(tiles) > 1:
        demo_ids.append(tiles[-1]["id"])

    similar_results = {}
    for tid in demo_ids:
        similar = find_similar(
            tile_id=tid,
            tiles=tiles,
            embeddings=embeddings,
            labels=labels,
            top_k=DEMO_TOP_K,
        )
        similar_results[tid] = similar

    # Save results
    sim_path = os.path.join(OUTPUT_DIR, "similar_tiles.json")
    with open(sim_path, "w") as f:
        json.dump(similar_results, f, indent=2)
    print(f"\n  Saved similar_tiles.json: {sim_path}")

    # -----------------------------------------------------------------------
    # 4. Cluster distribution summary
    # -----------------------------------------------------------------------
    print("\n--- Cluster Distribution ---")
    from collections import Counter
    dist = Counter(int(l) for l in labels)
    print(f"  {'Cluster':<10}  {'Tiles':>6}  {'Pct':>6}")
    print(f"  {'-'*10}  {'-'*6}  {'-'*6}")
    for k in sorted(dist.keys()):
        pct = dist[k] / len(labels) * 100
        print(f"  {k:<10}  {dist[k]:>6}  {pct:>5.1f}%")

    print(f"\n  All outputs in: {OUTPUT_DIR}")
    print("\nClustering complete!")


if __name__ == "__main__":
    run_clustering()
