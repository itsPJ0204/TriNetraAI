"""Semantic text search with optional geographic filtering over Qdrant satellite-tile vectors."""

from typing import Any
import numbers

import numpy as np
from qdrant_client import models
import torch

from semantic_search.model import load_remoteclip
from semantic_search.schemas import SearchResult
from semantic_search.vector_store import COLLECTION_NAME, get_qdrant_client


def validate_bbox(bbox: dict[str, Any]) -> dict[str, float]:
    """Validate bounding-box dictionary and return sanitized float coordinates."""
    if not isinstance(bbox, dict):
        raise ValueError("Bounding box must be a dictionary with 'left', 'bottom', 'right', and 'top' keys.")

    required_keys = ("left", "bottom", "right", "top")
    for key in required_keys:
        if key not in bbox:
            raise ValueError(f"Bounding box missing required coordinate key: '{key}'.")
        val = bbox[key]
        if isinstance(val, bool) or not isinstance(val, (int, float, numbers.Real)):
            raise ValueError(f"Coordinate '{key}' must be a real number, got {type(val).__name__}.")

    left = float(bbox["left"])
    bottom = float(bbox["bottom"])
    right = float(bbox["right"])
    top = float(bbox["top"])

    if left >= right:
        raise ValueError(
            f"Invalid bounding box: 'left' ({left}) must be strictly less than 'right' ({right})."
        )
    if bottom >= top:
        raise ValueError(
            f"Invalid bounding box: 'bottom' ({bottom}) must be strictly less than 'top' ({top})."
        )

    return {"left": left, "bottom": bottom, "right": right, "top": top}


def build_geographic_filter(bbox: dict[str, Any]) -> models.Filter:
    """Construct a Qdrant payload filter for 2D bounding-box intersection."""
    valid_bbox = validate_bbox(bbox)
    return models.Filter(
        must=[
            models.FieldCondition(
                key="bounds.left",
                range=models.Range(lte=valid_bbox["right"]),
            ),
            models.FieldCondition(
                key="bounds.right",
                range=models.Range(gte=valid_bbox["left"]),
            ),
            models.FieldCondition(
                key="bounds.bottom",
                range=models.Range(lte=valid_bbox["top"]),
            ),
            models.FieldCondition(
                key="bounds.top",
                range=models.Range(gte=valid_bbox["bottom"]),
            ),
        ]
    )


def normalize_query(query: Any) -> str:
    """
    Deterministically normalize a search query string.

    Performs:
    - Type verification (must be str)
    - Stripping leading and trailing whitespace
    - Normalizing consecutive whitespace (spaces, tabs, newlines) into a single space

    Args:
        query: Input query object.

    Returns:
        Sanitized, non-empty query string.

    Raises:
        ValueError: If query is not a string, or is empty / whitespace-only.
    """
    if not isinstance(query, str) or isinstance(query, bool):
        raise ValueError("Search query must be a non-empty string.")

    # Collapse any multi-character whitespace sequence to a single space
    cleaned = " ".join(query.strip().split())
    if not cleaned:
        raise ValueError("Search query must be a non-empty string.")

    return cleaned


import threading

_QUERY_CACHE_LOCK = threading.Lock()
_QUERY_EMBEDDING_CACHE: dict[str, np.ndarray] = {}
MAX_QUERY_CACHE_SIZE = 128


def clear_query_cache() -> None:
    """Clear in-memory cached query embeddings (useful for testing)."""
    with _QUERY_CACHE_LOCK:
        _QUERY_EMBEDDING_CACHE.clear()


def get_query_cache_size() -> int:
    """Return the current number of cached query embeddings."""
    with _QUERY_CACHE_LOCK:
        return len(_QUERY_EMBEDDING_CACHE)


def text_to_embedding(query: str, use_cache: bool = True) -> np.ndarray:
    """Convert one non-empty natural-language query into a normalized vector."""
    normalized = normalize_query(query)

    if use_cache:
        with _QUERY_CACHE_LOCK:
            if normalized in _QUERY_EMBEDDING_CACHE:
                return _QUERY_EMBEDDING_CACHE[normalized].copy()

    try:
        model, tokenizer, _ = load_remoteclip(device="cpu")
    except Exception as error:
        raise RuntimeError("Could not load the RemoteCLIP model for text search.") from error

    text_tokens = tokenizer([normalized])
    with torch.inference_mode():
        features = model.encode_text(text_tokens)
        normalized_features = torch.nn.functional.normalize(features, p=2, dim=-1)

    embedding = normalized_features.squeeze(0).cpu().numpy().astype(np.float32)

    if use_cache:
        with _QUERY_CACHE_LOCK:
            if len(_QUERY_EMBEDDING_CACHE) >= MAX_QUERY_CACHE_SIZE:
                # Evict oldest entry (FIFO)
                oldest_key = next(iter(_QUERY_EMBEDDING_CACHE))
                _QUERY_EMBEDDING_CACHE.pop(oldest_key, None)
            _QUERY_EMBEDDING_CACHE[normalized] = embedding.copy()

    return embedding


def search(
    query: str,
    bbox: dict[str, Any] | None = None,
    top_k: int = 3,
    geographic_bbox: dict[str, Any] | None = None,
) -> list[SearchResult]:
    """
    Public Semantic AI search interface.

    Executes natural-language semantic search with optional 2D geographic bounding-box filtering
    over indexed satellite tiles.

    Args:
        query: Non-empty search query string (e.g., 'river', 'urban area').
        bbox: Optional geographic bounding box dict with 'left', 'bottom', 'right', 'top'.
        top_k: Positive integer maximum number of ranked results to return (default 3).
        geographic_bbox: Alias for bbox for backwards compatibility.

    Returns:
        List of SearchResult objects ranked by cosine similarity score.

    Raises:
        ValueError: If query is empty or invalid, top_k is non-positive or invalid, or bbox is invalid.
        RuntimeError: If collection does not exist or RemoteCLIP cannot be loaded.
        ConnectionError: If connection to Qdrant fails.
    """
    normalized_query = normalize_query(query)

    # Support legacy positional top_k as 2nd parameter if passed
    if isinstance(bbox, int) and not isinstance(bbox, bool):
        top_k = bbox
        bbox = None

    if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k <= 0:
        raise ValueError("top_k must be a positive integer.")

    filter_box = bbox if bbox is not None else geographic_bbox
    query_filter = build_geographic_filter(filter_box) if filter_box is not None else None

    text_embedding = text_to_embedding(normalized_query)

    try:
        client = get_qdrant_client()
        if not client.collection_exists(COLLECTION_NAME):
            raise RuntimeError(
                "The satellite_tiles collection does not exist. "
                "Run: python -m scripts.index_embeddings"
            )

        indexed_count = client.count(COLLECTION_NAME, exact=True).count
        if indexed_count == 0:
            return []

        response = client.query_points(
            collection_name=COLLECTION_NAME,
            query=text_embedding.tolist(),
            query_filter=query_filter,
            limit=min(top_k, indexed_count),
            with_payload=True,
            with_vectors=False,
        )
    except RuntimeError:
        raise
    except Exception as error:
        raise ConnectionError(
            "Could not connect to Qdrant at http://localhost:6333."
        ) from error

    results: list[SearchResult] = []
    for point in response.points:
        payload = point.payload or {}
        raw_bounds = payload.get("bounds", {})
        bounds = {
            "left": float(raw_bounds.get("left", 0.0)),
            "bottom": float(raw_bounds.get("bottom", 0.0)),
            "right": float(raw_bounds.get("right", 0.0)),
            "top": float(raw_bounds.get("top", 0.0)),
        }
        results.append(
            SearchResult(
                tile_name=str(payload.get("tile_name", "")),
                image_path=str(payload.get("image_path", "")),
                score=float(point.score),
                crs=str(payload.get("crs", "")),
                bounds=bounds,
                width=int(payload.get("width", 0)),
                height=int(payload.get("height", 0)),
                date=str(payload.get("date", "")),
            )
        )
    return results

