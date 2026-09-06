"""Phase 3 verification for one satellite-image RemoteCLIP embedding."""

import numpy as np

from semantic_search.embeddings import find_one_satellite_tile, image_to_embedding


def test_image_embedding() -> None:
    """Create and validate a normalized embedding for one local TIFF tile."""
    tile_path = find_one_satellite_tile()
    embedding = image_to_embedding(tile_path)

    assert embedding is not None
    assert embedding.dtype == np.float32
    assert not np.all(embedding == 0)
    assert np.isclose(np.linalg.norm(embedding), 1.0, atol=1e-5)


if __name__ == "__main__":
    try:
        test_image_embedding()
    except FileNotFoundError as error:
        raise SystemExit(f"ERROR: {error}") from error
    print("One satellite-image embedding was created successfully.")
