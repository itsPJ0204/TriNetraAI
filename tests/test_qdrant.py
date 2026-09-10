"""Phase 7 verification for the local satellite_tiles Qdrant collection with geospatial metadata."""

from semantic_search.vector_store import (
    COLLECTION_NAME,
    DEFAULT_SCENE_DATE,
    get_qdrant_client,
    load_embeddings_and_paths,
)


def test_qdrant_index() -> None:
    """Verify Qdrant contains the indexed embeddings and complete geospatial metadata payloads."""
    embeddings, image_paths = load_embeddings_and_paths()
    client = get_qdrant_client()

    assert client.collection_exists(COLLECTION_NAME)
    collection = client.get_collection(COLLECTION_NAME)
    assert collection.config.params.vectors.size == embeddings.shape[1]
    assert collection.config.params.vectors.size == 512
    assert client.count(COLLECTION_NAME, exact=True).count == len(embeddings)
    assert len(embeddings) == 90

    points, _ = client.scroll(
        collection_name=COLLECTION_NAME,
        limit=120,
        with_payload=True,
        with_vectors=False,
    )
    assert len(points) == 90
    assert {point.payload["image_path"] for point in points} == set(image_paths)
    assert {point.payload["tile_name"] for point in points} == {
        f"sentinel2_tile_{i}.tif" for i in range(1, 31)
    }
    assert all("image_path" in point.payload for point in points)
    assert all("tile_name" in point.payload for point in points)
    assert all("crs" in point.payload for point in points)
    assert all("bounds" in point.payload for point in points)
    assert all("width" in point.payload for point in points)
    assert all("height" in point.payload for point in points)
    assert all("date" in point.payload for point in points)
    assert all("provenance" in point.payload for point in points)
    assert all("r_band" in point.payload for point in points)
    assert all(point.payload["date"] in {"2025-06-07", "2026-01-18", "2026-06-27"} for point in points)
    assert all(isinstance(point.payload["crs"], str) and len(point.payload["crs"]) > 0 for point in points)
    assert all(isinstance(point.payload["width"], int) and point.payload["width"] > 0 for point in points)
    assert all(isinstance(point.payload["height"], int) and point.payload["height"] > 0 for point in points)
    assert all(
        isinstance(point.payload["bounds"], dict)
        and all(k in point.payload["bounds"] for k in ("left", "bottom", "right", "top"))
        and point.payload["bounds"]["left"] < point.payload["bounds"]["right"]
        and point.payload["bounds"]["bottom"] < point.payload["bounds"]["top"]
        for point in points
    )
    assert all(point.payload["tile_name"] != "test_tile.tiff" for point in points)


if __name__ == "__main__":
    test_qdrant_index()
    print("Qdrant collection passed validation.")

