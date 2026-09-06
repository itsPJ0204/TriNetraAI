"""Store locally generated satellite-tile embeddings in Qdrant."""

import json
from pathlib import Path

import numpy as np
from qdrant_client import QdrantClient, models
import rasterio


PROJECT_ROOT = Path(__file__).resolve().parents[1]
QDRANT_URL = "http://localhost:6333"
COLLECTION_NAME = "satellite_tiles"
EMBEDDINGS_PATH = PROJECT_ROOT / "data" / "embeddings" / "image_embeddings.npy"
import threading

IMAGE_PATHS_PATH = PROJECT_ROOT / "data" / "embeddings" / "image_paths.json"
DEFAULT_SCENE_DATE = "2025-03-29"

_CLIENT_CACHE_LOCK = threading.Lock()
_CLIENT_CACHE: dict[str, QdrantClient] = {}


def clear_client_cache() -> None:
    """Clear cached Qdrant client instances (useful for testing)."""
    with _CLIENT_CACHE_LOCK:
        _CLIENT_CACHE.clear()


def get_qdrant_client(url: str = QDRANT_URL, reload: bool = False) -> QdrantClient:
    """Connect to the local Qdrant server, verify it responds, and safely reuse client."""
    with _CLIENT_CACHE_LOCK:
        if not reload and url in _CLIENT_CACHE:
            return _CLIENT_CACHE[url]

        client = QdrantClient(url=url)
        client.get_collections()
        _CLIENT_CACHE[url] = client
        return client


def extract_geospatial_metadata(image_path: str | Path) -> dict:
    """Read CRS, bounding box, and pixel dimensions directly from a GeoTIFF using rasterio."""
    path = PROJECT_ROOT / image_path if not Path(image_path).is_absolute() else Path(image_path)
    if not path.is_file():
        raise FileNotFoundError(f"Tile image file not found: {path}")

    with rasterio.open(path) as src:
        crs_str = str(src.crs) if src.crs else "EPSG:4326"
        bounds = {
            "left": float(src.bounds.left),
            "bottom": float(src.bounds.bottom),
            "right": float(src.bounds.right),
            "top": float(src.bounds.top),
        }
        width = int(src.width)
        height = int(src.height)

    return {
        "crs": crs_str,
        "bounds": bounds,
        "width": width,
        "height": height,
    }


def load_embeddings_and_paths() -> tuple[np.ndarray, list[str]]:
    """Load the Phase 4 matrix and its matching ordered image paths."""
    if not EMBEDDINGS_PATH.is_file() or not IMAGE_PATHS_PATH.is_file():
        raise FileNotFoundError(
            "Embedding files are missing. Run: python -m scripts.generate_embeddings"
        )

    embeddings = np.load(EMBEDDINGS_PATH).astype(np.float32, copy=False)
    image_paths = json.loads(IMAGE_PATHS_PATH.read_text(encoding="utf-8"))

    if embeddings.ndim != 2:
        raise ValueError("image_embeddings.npy must contain a two-dimensional matrix.")
    if len(embeddings) != len(image_paths):
        raise ValueError("The number of embeddings does not match the number of image paths.")
    return embeddings, image_paths


def create_collection_if_needed(client: QdrantClient, vector_dimension: int) -> None:
    """Create the cosine-similarity collection, or validate its dimension."""
    if not client.collection_exists(COLLECTION_NAME):
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=models.VectorParams(
                size=vector_dimension,
                distance=models.Distance.COSINE,
            ),
        )
        return

    collection = client.get_collection(COLLECTION_NAME)
    configured_dimension = collection.config.params.vectors.size
    if configured_dimension != vector_dimension:
        raise ValueError(
            f"Collection dimension is {configured_dimension}, but embeddings use "
            f"dimension {vector_dimension}."
        )


def upload_embeddings(
    client: QdrantClient,
    embeddings: np.ndarray,
    image_paths: list[str],
    date: str = DEFAULT_SCENE_DATE,
) -> None:
    """Upsert vectors with stable IDs and geospatial metadata, preserving embeddings[i] -> paths[i]."""
    for point_id, (embedding, image_path) in enumerate(zip(embeddings, image_paths)):
        print(f"Uploading vector {point_id + 1}/{len(embeddings)}: {image_path}")
        geo_meta = extract_geospatial_metadata(image_path)
        payload = {
            "image_path": image_path,
            "tile_name": Path(image_path).name,
            "crs": geo_meta["crs"],
            "bounds": geo_meta["bounds"],
            "width": geo_meta["width"],
            "height": geo_meta["height"],
            "date": date,
        }
        client.upsert(
            collection_name=COLLECTION_NAME,
            points=[
                models.PointStruct(
                    id=point_id,
                    vector=embedding.tolist(),
                    payload=payload,
                )
            ],
            wait=True,
        )


def remove_stale_points(client: QdrantClient, image_paths: list[str]) -> int:
    """Remove points whose image paths are absent from the current manifest."""
    current_paths = set(image_paths)
    stale_point_ids: list[int] = []
    offset = None

    while True:
        points, next_offset = client.scroll(
            collection_name=COLLECTION_NAME,
            limit=100,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        stale_point_ids.extend(
            point.id
            for point in points
            if point.payload.get("image_path") not in current_paths
        )
        if next_offset is None:
            break
        offset = next_offset

    if stale_point_ids:
        client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=models.PointIdsList(points=stale_point_ids),
            wait=True,
        )
    return len(stale_point_ids)
