import json
from pathlib import Path
import numpy as np
import pytest

from semantic_search.embeddings import (
    PROJECT_ROOT,
    find_satellite_tiles,
    generate_tile_embeddings,
    image_to_embedding,
)
from semantic_search.model import load_remoteclip


def test_multiple_embeddings() -> None:
    """Confirm available tiles produce normalized float32 vectors."""
    tiles = find_satellite_tiles()
    assert len(tiles) == 90, f"Expected 90 Sentinel-2 tiles, found {len(tiles)}"

    model, _, preprocess = load_remoteclip(device="cpu")
    sample_tiles = tiles[:4]
    embeddings = [image_to_embedding(t, model=model, preprocess=preprocess) for t in sample_tiles]
    embeddings_matrix = np.stack(embeddings)

    assert len(embeddings_matrix) == len(sample_tiles)
    assert embeddings_matrix.dtype == np.float32
    assert not np.all(embeddings_matrix == 0)
    assert np.allclose(np.linalg.norm(embeddings_matrix, axis=1), 1.0, atol=1e-5)
    assert embeddings_matrix.shape[1] == 512


def test_saved_embeddings_and_paths_contract() -> None:
    """Validate saved image_embeddings.npy and image_paths.json for shape, norm, and alignment."""
    emb_path = PROJECT_ROOT / "data" / "embeddings" / "image_embeddings.npy"
    paths_path = PROJECT_ROOT / "data" / "embeddings" / "image_paths.json"

    assert emb_path.is_file(), f"Embeddings file missing at {emb_path}"
    assert paths_path.is_file(), f"Image paths file missing at {paths_path}"

    embeddings = np.load(emb_path)
    paths = json.loads(paths_path.read_text(encoding="utf-8"))

    # 1. Exactly 90 tiles
    assert len(paths) == 90
    assert embeddings.shape == (90, 512)
    assert embeddings.dtype == np.float32

    # 2. All embeddings finite & non-zero
    assert np.all(np.isfinite(embeddings))
    assert not np.any(np.all(embeddings == 0, axis=1))

    # 3. Unit norm
    norms = np.linalg.norm(embeddings, axis=1)
    assert np.allclose(norms, 1.0, atol=1e-4)

    # 4. Correct tile naming and alignment
    for idx, p in enumerate(paths, start=1):
        tile_num = ((idx - 1) % 30) + 1
        expected_name = f"sentinel2_tile_{tile_num}.tif"
        assert p.endswith(expected_name), f"Tile {idx} path mismatch: expected {expected_name}, got {p}"
        full_tile_path = PROJECT_ROOT / p
        assert full_tile_path.is_file(), f"Tile file referenced in paths does not exist: {full_tile_path}"


if __name__ == "__main__":
    test_multiple_embeddings()
    test_saved_embeddings_and_paths_contract()
    print("All satellite-tile embeddings passed validation.")
