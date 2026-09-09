"""Create normalized RemoteCLIP embeddings for satellite-image tiles on CPU."""

from pathlib import Path

import numpy as np
import torch
from PIL import Image

from semantic_search.model import load_remoteclip


import re

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SENTINEL2_TILES_DIRECTORY = PROJECT_ROOT / "data" / "tiles" / "sentinel2"
LEGACY_TILES_DIRECTORY = PROJECT_ROOT / "data" / "tiles"
TILES_DIRECTORY = SENTINEL2_TILES_DIRECTORY


def tile_sort_key(path: Path) -> tuple[int, str]:
    """Sort key extracting trailing numerical tile index for natural ordering (e.g. tile_1 before tile_2 before tile_10)."""
    match = re.search(r"_(\d+)$", path.stem) or re.search(r"(\d+)$", path.stem)
    if match:
        return (int(match.group(1)), path.name.lower())
    return (float("inf"), path.name.lower())


def find_one_satellite_tile(tiles_dir: Path | str | None = None) -> Path:
    """Return one TIFF tile, or explain how to provide the required input."""
    tiles = find_satellite_tiles(tiles_dir=tiles_dir)
    if not tiles:
        raise FileNotFoundError(
            "No satellite tile was found. Place .tif or .tiff satellite "
            f"tiles inside: {TILES_DIRECTORY}"
        )
    return tiles[0]


def find_satellite_tiles(tiles_dir: Path | str | None = None) -> list[Path]:
    """Return all Sentinel-2 RGB tiles recursively in deterministic order.

    The function automatically discovers tiles inside date-wise subfolders,
    for example:

        data/tiles/sentinel2/
            2025-06-07/
                sentinel2_tile_1.tif
                ...
            2026-01-18/
                sentinel2_tile_1.tif
                ...
            2026-06-27/
                sentinel2_tile_1.tif
                ...

    Future date folders are picked up automatically without code changes.

    Only generated RGB tile files matching ``sentinel2_tile_*.tif`` are
    included. Full composite files and legacy test tiles are excluded.
    """
    target_dir = (
        Path(tiles_dir)
        if tiles_dir is not None
        else TILES_DIRECTORY
    )

    if not target_dir.is_dir():
        if LEGACY_TILES_DIRECTORY.is_dir():
            target_dir = LEGACY_TILES_DIRECTORY
        else:
            return []

    # Recursively find only final RGB Sentinel-2 tiles.
    candidate_tiles = target_dir.rglob("sentinel2_tile_*.tif")

    tiles: list[Path] = []

    for path in candidate_tiles:
        if not path.is_file():
            continue

        # Safety exclusions.
        if path.name.lower() == "test_tile.tiff":
            continue

        if path.name.lower().endswith("_full.tif"):
            continue

        if path.name.lower().endswith("_full.tiff"):
            continue

        tiles.append(path)

    # Remove accidental duplicates while preserving deterministic ordering.
    unique_tiles = list(dict.fromkeys(tiles))

    def sort_key(path: Path) -> tuple[str, int, str]:
        """Sort by date-folder/path, then numerical tile index."""
        parent_name = path.parent.name.lower()

        match = re.search(r"sentinel2_tile_(\d+)$", path.stem.lower())

        if match:
            tile_number = int(match.group(1))
        else:
            tile_number = float("inf")

        return (
            parent_name,
            tile_number,
            path.as_posix().lower(),
        )

    return sorted(unique_tiles, key=sort_key)


def image_to_embedding(
    image_path: str | Path, model=None, preprocess=None
) -> np.ndarray:
    """Convert one satellite-image tile into a normalized float32 vector."""
    path = Path(image_path)
    if not path.is_file():
        raise FileNotFoundError(f"Satellite image was not found: {path}")

    if model is None and preprocess is None:
        model, _, preprocess = load_remoteclip(device="cpu")
    elif model is None or preprocess is None:
        raise ValueError("Provide both model and preprocess, or neither.")

    try:
        with Image.open(path) as image:
            rgb_image = image.convert("RGB")
            image_tensor = preprocess(rgb_image).unsqueeze(0)
    except Exception:
        # Fallback to rasterio for multi-band, uint16, or specialized GeoTIFF rasters
        import rasterio
        from semantic_search.sentinel2 import normalize_uint16_to_uint8

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

            norm_bands = []
            for b in raw_bands:
                if b.dtype != np.uint8:
                    norm_bands.append(normalize_uint16_to_uint8(b))
                else:
                    norm_bands.append(b)

            rgb_array = np.stack(norm_bands, axis=-1)
            pil_img = Image.fromarray(rgb_array)
            image_tensor = preprocess(pil_img).unsqueeze(0)

    with torch.no_grad():
        features = model.encode_image(image_tensor)
        normalized_features = torch.nn.functional.normalize(features, p=2, dim=-1)

    embedding = normalized_features.squeeze(0).cpu().numpy().astype(np.float32)
    print(f"Image: {path}")
    print(f"Embedding shape: {embedding.shape}")
    print(f"Embedding dtype: {embedding.dtype}")
    print(f"Embedding norm: {np.linalg.norm(embedding):.6f}")
    return embedding



def generate_tile_embeddings(
    tiles_dir: Path | str | None = None,
    model=None,
    preprocess=None,
) -> tuple[np.ndarray, list[Path]]:
    """Generate one normalized float32 embedding for every satellite tile."""
    image_paths = find_satellite_tiles(tiles_dir=tiles_dir)
    if not image_paths:
        target_dir = Path(tiles_dir) if tiles_dir is not None else TILES_DIRECTORY
        raise FileNotFoundError(
            "No satellite tiles were found. Place .tif or .tiff satellite tiles "
            f"inside: {target_dir}"
        )

    if model is None or preprocess is None:
        loaded_model, _, loaded_preprocess = load_remoteclip(device="cpu")
        if model is None:
            model = loaded_model
        if preprocess is None:
            preprocess = loaded_preprocess

    embeddings: list[np.ndarray] = []
    embedding_dimension: int | None = None

    for number, image_path in enumerate(image_paths, start=1):
        print(f"Processing tile {number}/{len(image_paths)}: {image_path.name}")
        embedding = image_to_embedding(image_path, model=model, preprocess=preprocess)

        if embedding_dimension is None:
            embedding_dimension = embedding.shape[0]
        elif embedding.shape[0] != embedding_dimension:
            raise ValueError("RemoteCLIP returned inconsistent embedding dimensions.")

        embeddings.append(embedding)

    return np.stack(embeddings).astype(np.float32, copy=False), image_paths
