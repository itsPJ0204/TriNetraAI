"""
clustering.py — Discovery & Similarity Clustering (Job B)
==========================================================
Takes a 5-band Sentinel-2 composite, splits it into 32x32 tiles,
builds patch embeddings via PCA, runs K-Means clustering, and exposes
a find_similar(tile_id) function that returns the most visually/
semantically similar tiles.

Note on embeddings
------------------
This module generates its own patch embeddings (flatten 4 spectral bands
-> PCA 50 dims) as a self-contained demo.  When the Semantic AI teammate
produces proper neural embeddings, swap in load_embeddings_from_file()
and the rest of the pipeline works identically — K-Means is sensor/model
agnostic.

Public interface
----------------
    tile_image(tif_path, tile_size=32, scl_band_index=4, min_valid_frac=0.3)
        -> list[dict]   each dict: {"id", "row", "col", "patch", "valid_frac"}

    build_embeddings(tiles, n_components=50)
        -> np.ndarray  shape (N_tiles, n_components)

    run_kmeans(embeddings, n_clusters=8, random_state=42)
        -> (labels: np.ndarray[int], kmeans: KMeans)

    find_similar(tile_id, tiles, embeddings, labels, top_k=5)
        -> list[str]   tile IDs of the most similar tiles

    visualise_clusters(labels, tiles, img_shape, tile_size, save_path)
        -> saves cluster_map.png

    build_and_cluster(tif_path, ...)
        -> convenience wrapper returning all artefacts at once
"""

import os
import json

import numpy as np

try:
    import matplotlib.pyplot as plt
    import matplotlib.colors as mcolors
except ImportError:
    plt = None
    mcolors = None

try:
    import tifffile
except ImportError:
    tifffile = None

try:
    from sklearn.preprocessing import normalize
    from sklearn.decomposition import PCA
    from sklearn.cluster import KMeans
except ImportError:
    def normalize(X, norm='l2', axis=1):
        norm_val = np.linalg.norm(X, axis=axis, keepdims=True)
        norm_val[norm_val == 0] = 1.0
        return X / norm_val

    class KMeans:
        def __init__(self, n_clusters=5, random_state=42, n_init=10):
            self.n_clusters = n_clusters
            self.random_state = random_state
            self.labels_ = None
            self.cluster_centers_ = None

        def fit(self, X):
            np.random.seed(self.random_state)
            idx = np.random.choice(len(X), size=min(self.n_clusters, len(X)), replace=False)
            centers = X[idx].copy()
            labels = np.zeros(len(X), dtype=int)
            for _ in range(30):
                dists = np.linalg.norm(X[:, np.newaxis] - centers, axis=2)
                new_labels = np.argmin(dists, axis=1)
                if np.array_equal(labels, new_labels):
                    break
                labels = new_labels
                for k in range(self.n_clusters):
                    members = X[labels == k]
                    if len(members) > 0:
                        centers[k] = np.mean(members, axis=0)
            self.labels_ = labels
            self.cluster_centers_ = centers
            return self

    PCA = None


# ---------------------------------------------------------------------------
# Step 1: Tile the composite image
# ---------------------------------------------------------------------------

def tile_image(tif_path, tile_size=32, scl_band_index=4, min_valid_frac=0.3):
    """
    Split a 5-band Sentinel-2 composite into non-overlapping square patches.

    Parameters
    ----------
    tif_path        : str   Path to 5-band default.tif [R,G,B,NIR,SCL]
    tile_size       : int   Pixel size of each square tile (default 32)
    scl_band_index  : int   Band index of SCL layer (default 4)
    min_valid_frac  : float Tiles with fewer valid pixels than this fraction
                            are excluded from clustering (mostly cloud/no-data)

    Returns
    -------
    tiles : list[dict]
        Each dict contains:
            "id"         : str   e.g. "tile_0042"
            "row"        : int   tile row index (top-left in tile grid)
            "col"        : int   tile col index
            "patch"      : np.ndarray  shape (tile_size, tile_size, 4)
                           spectral bands only — SCL excluded from patch data
            "valid_frac" : float  fraction of pixels not in BAD_SCL_CLASSES
    """
    from qa_mask import BAD_SCL_CLASSES

    if tifffile is not None:
        img = tifffile.imread(tif_path)  # (H, W, bands)
    else:
        import rasterio
        with rasterio.open(tif_path) as src:
            # (bands, H, W) -> (H, W, bands)
            img = np.transpose(src.read(), (1, 2, 0))

    H, W, C = img.shape

    # Spectral bands only (exclude SCL from embedding data)
    scl_idx = min(scl_band_index, C - 1)
    spectral = img[:, :, :scl_idx].astype(np.float32)  # (H, W, bands)
    scl = img[:, :, scl_idx].astype(np.uint16) if C > 1 else np.zeros((H, W), dtype=np.uint16)

    # Build per-pixel validity from SCL
    bad = np.zeros((H, W), dtype=bool)
    for cls in BAD_SCL_CLASSES:
        bad |= (scl == cls)
    valid = ~bad

    tiles = []
    n_rows = H // tile_size
    n_cols = W // tile_size
    tile_idx = 0

    for r in range(n_rows):
        for c in range(n_cols):
            r0, r1 = r * tile_size, (r + 1) * tile_size
            c0, c1 = c * tile_size, (c + 1) * tile_size

            patch_valid = valid[r0:r1, c0:c1]
            valid_frac  = float(patch_valid.sum()) / patch_valid.size

            if valid_frac < min_valid_frac:
                # Skip tiles that are mostly cloudy/no-data
                tile_idx += 1
                continue

            patch = spectral[r0:r1, c0:c1]  # (tile_size, tile_size, 4)

            tiles.append({
                "id":         f"tile_{tile_idx:04d}",
                "row":        r,
                "col":        c,
                "patch":      patch,
                "valid_frac": round(valid_frac, 4),
            })
            tile_idx += 1

    print(f"  Tiling: {n_rows}x{n_cols} grid -> {len(tiles)} valid tiles "
          f"(tile_size={tile_size}px, min_valid={min_valid_frac:.0%})")
    return tiles, (H, W)


# ---------------------------------------------------------------------------
# Step 2: Build patch embeddings
# ---------------------------------------------------------------------------

def build_embeddings(tiles, n_components=50):
    """
    Convert each tile's spectral patch into a compact embedding vector via PCA.

    Steps:
        1. Flatten each (tile_size, tile_size, 4) patch -> 1-D vector
        2. L2-normalise all vectors (removes scale bias)
        3. Reduce dimensionality with PCA to n_components dims

    Parameters
    ----------
    tiles        : list[dict]  output of tile_image()
    n_components : int         PCA output dims (default 50)

    Returns
    -------
    embeddings : np.ndarray  shape (N_tiles, n_components), float32
                 Rows are L2-normalised PCA embeddings, one per valid tile.
    """
    # Stack flat patches: (N, H_tile * W_tile * 4)
    flat = np.stack([t["patch"].reshape(-1) for t in tiles], axis=0)

    # L2 normalise rows before PCA (prevents bright/dark tiles from dominating)
    flat_normed = normalize(flat, norm="l2")

    # PCA: reduce to n_components (or fewer if not enough tiles)
    actual_components = min(n_components, flat_normed.shape[0] - 1, flat_normed.shape[1])
    pca = PCA(n_components=actual_components, random_state=42)
    embeddings = pca.fit_transform(flat_normed).astype(np.float32)

    explained = pca.explained_variance_ratio_.sum() * 100
    print(f"  PCA: {flat_normed.shape[1]}-D -> {actual_components}-D "
          f"({explained:.1f}% variance retained)")
    return embeddings


# ---------------------------------------------------------------------------
# Step 3: K-Means clustering
# ---------------------------------------------------------------------------

def run_kmeans(embeddings, n_clusters=8, random_state=42):
    """
    Cluster the tile embeddings with K-Means.

    Parameters
    ----------
    embeddings   : np.ndarray  (N_tiles, embed_dim)
    n_clusters   : int         number of clusters (default 8)
    random_state : int

    Returns
    -------
    labels : np.ndarray[int]  shape (N_tiles,)  cluster ID per tile
    kmeans : KMeans           fitted scikit-learn model (for distances etc.)
    """
    actual_k = min(n_clusters, len(embeddings))
    if actual_k < n_clusters:
        print(f"  [Note] Only {len(embeddings)} tiles — reducing n_clusters to {actual_k}")

    kmeans = KMeans(n_clusters=actual_k, n_init=10, random_state=random_state)
    labels = kmeans.fit_predict(embeddings)

    cluster_counts = np.bincount(labels)
    print(f"  K-Means: {actual_k} clusters, "
          f"sizes = {cluster_counts.tolist()}")
    return labels, kmeans


# ---------------------------------------------------------------------------
# Step 4: find_similar()
# ---------------------------------------------------------------------------

def find_similar(tile_id, tiles, embeddings, labels, top_k=5):
    """
    Given a tile ID, return the top_k most similar tile IDs.

    Strategy:
        1. Find the cluster the query tile belongs to.
        2. Retrieve all tiles in the same cluster (same land-cover type).
        3. Sort by L2 distance in embedding space to the query tile.
        4. Return the top_k closest neighbours (excluding the query tile itself).

    Parameters
    ----------
    tile_id    : str          e.g. "tile_0042"
    tiles      : list[dict]   from tile_image()
    embeddings : np.ndarray   (N_tiles, embed_dim) from build_embeddings()
    labels     : np.ndarray   (N_tiles,) from run_kmeans()
    top_k      : int          number of similar tiles to return (default 5)

    Returns
    -------
    similar_ids : list[str]   tile IDs sorted by similarity (most similar first)

    Raises
    ------
    ValueError if tile_id is not found in the tiles list.
    """
    # Build id -> index mapping
    id_to_idx = {t["id"]: i for i, t in enumerate(tiles)}

    if tile_id not in id_to_idx:
        available = [t["id"] for t in tiles[:5]]
        raise ValueError(
            f"tile_id '{tile_id}' not found. "
            f"Available example IDs: {available} ..."
        )

    query_idx = id_to_idx[tile_id]
    query_cluster = labels[query_idx]
    query_embedding = embeddings[query_idx]

    # Gather all tiles in the same cluster (excluding query itself)
    cluster_indices = [
        i for i, lbl in enumerate(labels)
        if lbl == query_cluster and i != query_idx
    ]

    if not cluster_indices:
        print(f"  [Note] '{tile_id}' is the only tile in cluster {query_cluster}. "
              f"Expanding search to all tiles.")
        cluster_indices = [i for i in range(len(tiles)) if i != query_idx]

    # Sort by L2 distance in embedding space
    cluster_embeddings = embeddings[cluster_indices]
    diffs = cluster_embeddings - query_embedding
    distances = np.linalg.norm(diffs, axis=1)
    sorted_order = np.argsort(distances)

    top_indices = [cluster_indices[i] for i in sorted_order[:top_k]]
    similar_ids = [tiles[i]["id"] for i in top_indices]

    print(f"  find_similar('{tile_id}') cluster={query_cluster} -> {similar_ids}")
    return similar_ids


# ---------------------------------------------------------------------------
# Step 5: Visualise cluster map
# ---------------------------------------------------------------------------

def visualise_clusters(labels, tiles, img_shape, tile_size, save_path):
    """
    Paint a spatial cluster map: each tile's pixels are coloured by cluster ID.
    Non-clustered (excluded) tiles are left black.

    Parameters
    ----------
    labels     : np.ndarray[int]  cluster label per tile (N_tiles,)
    tiles      : list[dict]        from tile_image()
    img_shape  : tuple             (H, W) of the original image
    tile_size  : int
    save_path  : str               where to save the PNG

    Returns
    -------
    cluster_map : np.ndarray  (H, W, 3) float RGB image
    """
    H, W = img_shape
    cluster_map = np.zeros((H, W, 3), dtype=np.float32)  # black background

    n_clusters = int(labels.max()) + 1
    # Use a qualitative colour palette — one colour per cluster
    cmap = plt.get_cmap("tab10", n_clusters)
    cluster_colours = [cmap(i)[:3] for i in range(n_clusters)]  # list of RGB tuples

    for tile_dict, label in zip(tiles, labels):
        r, c = tile_dict["row"], tile_dict["col"]
        r0, r1 = r * tile_size, (r + 1) * tile_size
        c0, c1 = c * tile_size, (c + 1) * tile_size
        cluster_map[r0:r1, c0:c1] = cluster_colours[label]

    fig, ax = plt.subplots(figsize=(8, 8))
    ax.imshow(cluster_map)
    ax.set_title(
        f"Tile Cluster Map ({n_clusters} clusters, {tile_size}x{tile_size}px tiles)",
        fontsize=12, fontweight="bold"
    )
    ax.axis("off")

    # Legend
    import matplotlib.patches as mpatches
    patches = [
        mpatches.Patch(color=cluster_colours[k], label=f"Cluster {k}")
        for k in range(n_clusters)
    ]
    ax.legend(handles=patches, loc="lower right", fontsize=8,
              framealpha=0.85, fancybox=True, ncol=2)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved cluster map : {save_path}")
    return cluster_map


# ---------------------------------------------------------------------------
# Convenience wrapper
# ---------------------------------------------------------------------------

def build_and_cluster(
    tif_path,
    tile_size=32,
    n_components=50,
    n_clusters=8,
    min_valid_frac=0.3,
    scl_band_index=4,
):
    """
    End-to-end convenience wrapper: tile -> embed -> cluster.

    Returns
    -------
    dict with keys:
        "tiles"      : list[dict]
        "embeddings" : np.ndarray  (N, n_components)
        "labels"     : np.ndarray  (N,)
        "kmeans"     : KMeans
        "img_shape"  : (H, W)
    """
    print(f"\n  [build_and_cluster] {os.path.basename(tif_path)}")
    tiles, img_shape = tile_image(
        tif_path, tile_size=tile_size,
        scl_band_index=scl_band_index,
        min_valid_frac=min_valid_frac,
    )
    embeddings = build_embeddings(tiles, n_components=n_components)
    labels, kmeans = run_kmeans(embeddings, n_clusters=n_clusters)
    return {
        "tiles":      tiles,
        "embeddings": embeddings,
        "labels":     labels,
        "kmeans":     kmeans,
        "img_shape":  img_shape,
    }
