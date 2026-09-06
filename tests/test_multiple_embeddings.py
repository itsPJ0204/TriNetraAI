"""Phase 4 verification for embeddings from all local satellite tiles."""

import numpy as np

from semantic_search.embeddings import find_satellite_tiles, generate_tile_embeddings


def test_multiple_embeddings() -> None:
    """Confirm every available tile produces one normalized float32 vector."""
    tiles = find_satellite_tiles()
    assert tiles, "Place at least one .tif or .tiff tile inside data/tiles/."
    assert len(tiles) == 4, "Expected tile_1.tif through tile_4.tif only."

    embeddings, image_paths = generate_tile_embeddings()

    assert len(embeddings) == len(image_paths)
    assert len(embeddings) == len(tiles)
    assert embeddings.dtype == np.float32
    assert not np.all(embeddings == 0)
    assert np.allclose(np.linalg.norm(embeddings, axis=1), 1.0, atol=1e-5)
    assert len({embedding.shape[0] for embedding in embeddings}) == 1


if __name__ == "__main__":
    test_multiple_embeddings()
    print("All satellite-tile embeddings passed validation.")
