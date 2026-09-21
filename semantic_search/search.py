"""Semantic text search with optional geographic filtering over Qdrant satellite-tile vectors."""

from pathlib import Path
from typing import Any
import numbers

import numpy as np
from qdrant_client import models
import torch

from semantic_search.model import load_remoteclip
from semantic_search.schemas import SearchResult
from semantic_search.vector_store import COLLECTION_NAME, get_qdrant_client


def validate_bbox(bbox: dict[str, Any] | tuple[float, float, float, float] | list[float]) -> dict[str, float]:
    """Validate bounding-box dictionary or tuple/list and return sanitized float coordinates."""
    if isinstance(bbox, (tuple, list)) and len(bbox) == 4:
        bbox = {"left": bbox[0], "bottom": bbox[1], "right": bbox[2], "top": bbox[3]}
    elif not isinstance(bbox, dict):
        raise ValueError("Bounding box must be a dictionary with 'left', 'bottom', 'right', and 'top' keys or a 4-element sequence.")

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
    """Convert one non-empty natural-language query into a normalized vector using RemoteCLIP prompt ensembling."""
    normalized = normalize_query(query)

    if use_cache:
        with _QUERY_CACHE_LOCK:
            if normalized in _QUERY_EMBEDDING_CACHE:
                return _QUERY_EMBEDDING_CACHE[normalized].copy()

    try:
        model, tokenizer, _ = load_remoteclip(device="cpu")
    except Exception as error:
        raise RuntimeError("Could not load the RemoteCLIP model for text search.") from error

    prompts = [
        f"satellite imagery of {normalized}",
        f"aerial view of {normalized}",
        f"a satellite photo showing {normalized}",
        normalized,
    ]
    text_tokens = tokenizer(prompts)
    with torch.inference_mode():
        features = model.encode_text(text_tokens)
        normalized_features = torch.nn.functional.normalize(features, p=2, dim=-1)
        mean_feature = normalized_features.mean(dim=0, keepdim=True)
        final_embedding = torch.nn.functional.normalize(mean_feature, p=2, dim=-1)

    embedding = final_embedding.squeeze(0).cpu().numpy().astype(np.float32)

    if use_cache:
        with _QUERY_CACHE_LOCK:
            if len(_QUERY_EMBEDDING_CACHE) >= MAX_QUERY_CACHE_SIZE:
                # Evict oldest entry (FIFO)
                oldest_key = next(iter(_QUERY_EMBEDDING_CACHE))
                _QUERY_EMBEDDING_CACHE.pop(oldest_key, None)
            _QUERY_EMBEDDING_CACHE[normalized] = embedding.copy()

    return embedding


SENTINEL1_COLLECTION_NAME = "sentinel1_tiles"


def execute_vector_search(
    query_vector: np.ndarray,
    top_k: int = 5,
    bbox: dict[str, Any] | None = None,
    geographic_bbox: dict[str, Any] | None = None,
    sensor: str = "sentinel2",
) -> list[SearchResult]:
    """
    Internal execution helper: query Qdrant with a 512-dim vector and optional bounding-box filter.
    Supports routing to 'satellite_tiles' (Sentinel-2), 'sentinel1_tiles' (Sentinel-1), or 'all' (both).
    """
    if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k <= 0:
        raise ValueError("top_k must be a positive integer.")

    filter_box = bbox if bbox is not None else geographic_bbox
    query_filter = build_geographic_filter(filter_box) if filter_box is not None else None

    sensor_choice = (sensor or "sentinel2").lower().strip()
    if sensor_choice in {"sentinel1", "s1"}:
        target_collections = [SENTINEL1_COLLECTION_NAME]
    elif sensor_choice in {"all", "both", "multi"}:
        target_collections = [COLLECTION_NAME, SENTINEL1_COLLECTION_NAME]
    else:
        target_collections = [COLLECTION_NAME]

    raw_results: list[SearchResult] = []

    try:
        client = get_qdrant_client()
        for col_name in target_collections:
            if not client.collection_exists(col_name):
                # If specifically requested a collection that doesn't exist, handle appropriately
                if len(target_collections) == 1 and col_name == COLLECTION_NAME:
                    raise RuntimeError(
                        "The satellite_tiles collection does not exist. "
                        "Run: python -m scripts.index_embeddings"
                    )
                continue

            indexed_count = client.count(col_name, exact=True).count
            if indexed_count == 0:
                continue

            fetch_limit = min(max(top_k * 10, 60), indexed_count)
            response = client.query_points(
                collection_name=col_name,
                query=query_vector.tolist(),
                query_filter=query_filter,
                limit=fetch_limit,
                with_payload=True,
                with_vectors=False,
            )

            col_sensor = "sentinel1" if col_name == SENTINEL1_COLLECTION_NAME else "sentinel2"
            for point in response.points:
                payload = point.payload or {}
                tile_name = str(payload.get("tile_name", ""))
                image_path = str(payload.get("image_path", ""))

                # Filter out full scene mosaics / composites - search results should only contain 256x256 tiles
                lower_ident = f"{tile_name} {image_path}".lower()
                if any(k in lower_ident for k in ("_full", "rgb_full", "sar_full", "full_scene", "full_composite", "composite", "mosaic")):
                    continue

                width = int(payload.get("width", 0))
                height = int(payload.get("height", 0))

                raw_bounds = payload.get("bounds", {})
                bounds = {
                    "left": float(raw_bounds.get("left", 0.0)),
                    "bottom": float(raw_bounds.get("bottom", 0.0)),
                    "right": float(raw_bounds.get("right", 0.0)),
                    "top": float(raw_bounds.get("top", 0.0)),
                }
                tile_date = str(payload.get("date", ""))
                point_sensor = str(payload.get("sensor") or col_sensor)
                tile_id = str(payload.get("tile_id") or f"{point_sensor}:{tile_date}:{image_path}")
                raw_results.append(
                    SearchResult(
                        tile_name=tile_name,
                        image_path=image_path,
                        score=float(point.score),
                        crs=str(payload.get("crs", "")),
                        bounds=bounds,
                        width=width,
                        height=height,
                        date=tile_date,
                        tile_id=tile_id,
                        sensor=point_sensor,
                    )
                )
    except RuntimeError:
        raise
    except Exception as error:
        raise ConnectionError(
            "Could not connect to Qdrant at http://localhost:6333."
        ) from error

    # Penalize narrow slivers (< 32px) so full tiles outrank border cuts
    def rank_score(res: SearchResult) -> float:
        is_sliver = (0 < res.width < 32) or (0 < res.height < 32)
        return res.score - (0.05 if is_sliver else 0.0)

    # Sort primarily by effective score descending
    raw_results.sort(key=lambda r: (-rank_score(r), -r.score, r.date or "", r.tile_name))

    # Spatial diversification: prioritize distinct geographic tiles across time, then backfill
    distinct_results: list[SearchResult] = []
    seen_spatial_keys: set[str] = set()
    remaining_results: list[SearchResult] = []

    for res in raw_results:
        spatial_key = f"{res.sensor}:{res.tile_name}"
        if spatial_key not in seen_spatial_keys:
            seen_spatial_keys.add(spatial_key)
            distinct_results.append(res)
        else:
            remaining_results.append(res)

    combined_results = distinct_results + remaining_results
    return combined_results[:top_k]



def image_input_to_embedding(
    image: Any,
    model: Any = None,
    preprocess: Any = None,
) -> np.ndarray:
    """
    Convert a PIL.Image, file path, or Path object into a normalized 512-dim RemoteCLIP embedding.

    Args:
        image: PIL.Image.Image instance or valid file path (str | Path).
        model: Optional preloaded RemoteCLIP model.
        preprocess: Optional preloaded RemoteCLIP transform.

    Returns:
        1D float32 NumPy array of shape (512,) normalized to unit length.

    Raises:
        ValueError: If image is None or cannot be read.
        TypeError: If image is not a PIL Image, str, or Path.
        FileNotFoundError: If image file path does not exist on disk.
    """
    from PIL import Image

    if image is None:
        raise ValueError("Image input cannot be None.")

    if isinstance(image, Image.Image):
        pil_image = image.convert("RGB")
    elif isinstance(image, (str, Path)):
        path = Path(image)
        if not path.is_file():
            raise FileNotFoundError(f"Image file not found: {path}")
        try:
            with Image.open(path) as img:
                pil_image = img.convert("RGB")
        except Exception:
            # Fallback for multi-band / uint16 GeoTIFFs using rasterio
            import rasterio
            from semantic_search.sentinel2 import normalize_uint16_to_uint8

            try:
                with rasterio.open(path) as src:
                    count = src.count
                    if count >= 3:
                        raw_bands = [src.read(i) for i in range(1, 4)]
                    elif count == 1:
                        b1 = src.read(1)
                        raw_bands = [b1, b1, b1]
                    else:
                        b1 = src.read(1)
                        raw_bands = [b1, src.read(2), b1]

                    norm_bands = [
                        normalize_uint16_to_uint8(b) if b.dtype != np.uint8 else b
                        for b in raw_bands
                    ]
                    rgb_array = np.stack(norm_bands, axis=-1)
                    pil_image = Image.fromarray(rgb_array)
            except Exception as err:
                raise ValueError(f"Could not open image file: {path} ({err})") from err
    else:
        raise TypeError(
            f"Invalid image type: expected PIL.Image.Image, str, or Path, got {type(image).__name__}."
        )

    if model is None or preprocess is None:
        model, _, preprocess = load_remoteclip(device="cpu")

    tensor = preprocess(pil_image).unsqueeze(0)
    with torch.inference_mode():
        features = model.encode_image(tensor)
        normalized = torch.nn.functional.normalize(features, p=2, dim=-1)

    embedding = normalized.squeeze(0).cpu().numpy().astype(np.float32)
    return embedding


def fuse_embeddings(
    image_embedding: np.ndarray,
    text_embedding: np.ndarray,
    alpha: float = 0.5,
    fusion_strategy: str = "weighted_sum",
    image_weight: float | None = None,
    text_weight: float | None = None,
) -> np.ndarray:
    """
    Fuse image and text embeddings into a single normalized 512-dim query vector.

    Args:
        image_embedding: 512-dim float32 normalized image embedding vector.
        text_embedding: 512-dim float32 normalized text embedding vector.
        alpha: Weight assigned to image in weighted sum [0.0, 1.0]. Default 0.5.
        fusion_strategy: Strategy for multimodal combination:
            - 'weighted_sum': alpha * image + (1 - alpha) * text (or explicit weights).
            - 'average': equal 50/50 weighting.
            - 'image_only': image vector only.
            - 'text_only': text vector only.
        image_weight: Explicit image weight (overrides alpha if specified).
        text_weight: Explicit text weight (overrides alpha if specified).

    Returns:
        Normalized 512-dim float32 vector.
    """
    strategy = fusion_strategy.lower().strip()
    if strategy in {"image_only", "image"}:
        return image_embedding.astype(np.float32)

    if strategy in {"text_only", "text"}:
        return text_embedding.astype(np.float32)

    if strategy in {"average", "mean"}:
        w_img, w_txt = 0.5, 0.5
    elif strategy == "weighted_sum":
        if image_weight is not None or text_weight is not None:
            w_img = float(image_weight if image_weight is not None else (1.0 - (text_weight or 0.0)))
            w_txt = float(text_weight if text_weight is not None else (1.0 - (image_weight or 0.0)))
            if w_img < 0.0 or w_txt < 0.0:
                raise ValueError(
                    f"Weights must be non-negative, got image_weight={w_img}, text_weight={w_txt}"
                )
            total = w_img + w_txt
            if total <= 0.0:
                raise ValueError("Sum of image_weight and text_weight must be strictly positive.")
            w_img /= total
            w_txt /= total
        else:
            if not isinstance(alpha, (int, float)) or isinstance(alpha, bool) or not (0.0 <= alpha <= 1.0):
                raise ValueError(f"alpha must be a real number between 0.0 and 1.0, got {alpha}")
            w_img = float(alpha)
            w_txt = 1.0 - w_img
    else:
        raise ValueError(
            f"Unsupported fusion_strategy '{fusion_strategy}'. "
            "Supported strategies: 'weighted_sum', 'average', 'image_only', 'text_only'."
        )

    fused = (w_img * image_embedding) + (w_txt * text_embedding)
    norm = float(np.linalg.norm(fused))
    if norm > 1e-12:
        fused = fused / norm
    else:
        fused = image_embedding.copy()

    return fused.astype(np.float32)


def search(
    query: str,
    bbox: dict[str, Any] | None = None,
    top_k: int = 3,
    geographic_bbox: dict[str, Any] | None = None,
    sensor: str = "sentinel2",
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
        sensor: Satellite sensor to search: 'sentinel2' (default), 'sentinel1', or 'all'/'both'.

    Returns:
        List of SearchResult objects ranked by cosine similarity score.

    Raises:
        ValueError: If query is empty or invalid, top_k is non-positive or invalid, or bbox is invalid.
        RuntimeError: If collection does not exist or model cannot be loaded.
        ConnectionError: If connection to Qdrant fails.
    """
    normalized_query = normalize_query(query)

    # Support legacy positional top_k as 2nd parameter if passed
    if isinstance(bbox, int) and not isinstance(bbox, bool):
        top_k = bbox
        bbox = None

    sensor_choice = (sensor or "sentinel2").lower().strip()
    if sensor_choice in {"sentinel1", "s1"}:
        from semantic_search.sentinel1_model import extract_sentinel1_text_embedding
        text_embedding = extract_sentinel1_text_embedding(normalized_query)
    else:
        text_embedding = text_to_embedding(normalized_query)

    return execute_vector_search(
        query_vector=text_embedding,
        top_k=top_k,
        bbox=bbox,
        geographic_bbox=geographic_bbox,
        sensor=sensor,
    )


def search_by_image(
    image: Any,
    query: str | None = None,
    top_k: int = 5,
    bbox: dict[str, Any] | None = None,
    alpha: float = 0.5,
    fusion_strategy: str = "weighted_sum",
    geographic_bbox: dict[str, Any] | None = None,
    image_weight: float | None = None,
    text_weight: float | None = None,
    sensor: str = "sentinel2",
) -> list[SearchResult]:
    """
    Search satellite tiles by query image (image-to-image) or multimodal query (image + text).

    Args:
        image: Query image as a PIL.Image.Image or a valid file path (str/Path).
        query: Optional natural-language text description for multimodal fusion.
               If None, executes pure image-to-image search.
               If provided, fuses image and text embeddings into a joint query vector.
        top_k: Positive integer maximum number of ranked results to return (default 5).
        bbox: Optional geographic bounding box dict with 'left', 'bottom', 'right', 'top'.
        alpha: Weight assigned to image in weighted sum [0.0, 1.0]. Default 0.5.
        fusion_strategy: Strategy for multimodal combination ('weighted_sum', 'average', 'image_only', 'text_only').
        geographic_bbox: Alias for bbox for backwards compatibility.
        image_weight: Optional explicit image weight for multimodal fusion.
        text_weight: Optional explicit text weight for multimodal fusion.
        sensor: Satellite sensor to search: 'sentinel2' (default), 'sentinel1', or 'all'/'both'.

    Returns:
        List of SearchResult objects ranked by cosine similarity score.

    Raises:
        ValueError: If image is None or invalid, query is invalid/empty string, top_k <= 0, or bbox is invalid.
        TypeError: If image is of an unsupported type.
        FileNotFoundError: If image file path does not exist.
        RuntimeError: If collection does not exist or model cannot be loaded.
        ConnectionError: If connection to Qdrant fails.
    """
    sensor_choice = (sensor or "sentinel2").lower().strip()

    # 1. Encode image
    if sensor_choice in {"sentinel1", "s1"}:
        from semantic_search.sentinel1_model import (
            extract_sentinel1_image_embedding,
            extract_sentinel1_text_embedding,
        )
        image_embedding = extract_sentinel1_image_embedding(image)
        if query is not None:
            normalized_query = normalize_query(query)
            text_embedding = extract_sentinel1_text_embedding(normalized_query)
            query_vector = fuse_embeddings(
                image_embedding=image_embedding,
                text_embedding=text_embedding,
                alpha=alpha,
                fusion_strategy=fusion_strategy,
                image_weight=image_weight,
                text_weight=text_weight,
            )
        else:
            query_vector = image_embedding
    else:
        image_embedding = image_input_to_embedding(image)
        if query is not None:
            normalized_query = normalize_query(query)
            text_embedding = text_to_embedding(normalized_query)
            query_vector = fuse_embeddings(
                image_embedding=image_embedding,
                text_embedding=text_embedding,
                alpha=alpha,
                fusion_strategy=fusion_strategy,
                image_weight=image_weight,
                text_weight=text_weight,
            )
        else:
            query_vector = image_embedding

    # 2. Execute vector search with optional bbox
    return execute_vector_search(
        query_vector=query_vector,
        top_k=top_k,
        bbox=bbox,
        geographic_bbox=geographic_bbox,
        sensor=sensor,
    )
