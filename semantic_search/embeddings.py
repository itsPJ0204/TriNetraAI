"""Create normalized RemoteCLIP embeddings for satellite-image tiles on CPU."""

from pathlib import Path

import numpy as np
import torch
from PIL import Image

from semantic_search.model import load_remoteclip


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TILES_DIRECTORY = PROJECT_ROOT / "data" / "tiles"


def find_one_satellite_tile() -> Path:
    """Return one TIFF tile, or explain how to provide the required input."""
    tiles = find_satellite_tiles()
    if not tiles:
        raise FileNotFoundError(
            "No satellite tile was found. Place one .tif or .tiff satellite "
            f"tile inside: {TILES_DIRECTORY}"
        )
    return tiles[0]


def find_satellite_tiles() -> list[Path]:
    """Return all TIFF tiles in a stable alphabetical order, supporting nested subdirectories and CSV registry."""
    if not TILES_DIRECTORY.is_dir():
        return []

    # Check tiles_metadata.csv from Person 1 if available
    csv_file = PROJECT_ROOT / "data" / "tiles_metadata.csv"
    if csv_file.is_file():
        import csv
        with csv_file.open("r", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            paths = [Path(row["filepath"]) for row in reader if "filepath" in row and Path(row["filepath"]).is_file()]
            if paths:
                return sorted(paths, key=lambda p: p.name.lower())

    # Recursive scan to discover tiles in data/tiles/<scene_name>/
    return sorted(
        (
            path
            for path in TILES_DIRECTORY.rglob("*")
            if (
                path.is_file()
                and path.suffix.lower() in {".tif", ".tiff"}
                and path.name.lower() != "test_tile.tiff"
            )
        ),
        key=lambda path: path.name.lower(),
    )


def image_to_embedding(
    image_path: str | Path, model=None, preprocess=None
) -> np.ndarray:
    """Convert one satellite-image tile into a normalized float32 vector with 16-bit percentile normalization."""
    path = Path(image_path)
    if not path.is_file():
        raise FileNotFoundError(f"Satellite image was not found: {path}")

    if model is None and preprocess is None:
        model, _, preprocess = load_remoteclip(device="cpu")
    elif model is None or preprocess is None:
        raise ValueError("Provide both model and preprocess, or neither.")

    # Multi-band / 16-bit GeoTIFF robust reader
    try:
        import rasterio
        with rasterio.open(path) as src:
            if src.count >= 3:
                arr = src.read([1, 2, 3]).astype(np.float32)
                arr = np.transpose(arr, (1, 2, 0))
            else:
                arr = src.read(1).astype(np.float32)
                arr = np.stack([arr, arr, arr], axis=-1)

            p2, p98 = np.percentile(arr[arr > 0] if np.any(arr > 0) else arr, (2, 98))
            if p98 > p2:
                arr = np.clip((arr - p2) / (p98 - p2 + 1e-5) * 255.0, 0, 255).astype(np.uint8)
            else:
                arr = np.clip(arr / 10000.0 * 255.0, 0, 255).astype(np.uint8)
            rgb_image = Image.fromarray(arr, mode="RGB")
    except Exception:
        with Image.open(path) as image:
            rgb_image = image.convert("RGB")

    image_tensor = preprocess(rgb_image).unsqueeze(0)

    with torch.no_grad():
        features = model.encode_image(image_tensor)
        normalized_features = torch.nn.functional.normalize(features, p=2, dim=-1)

    embedding = normalized_features.squeeze(0).cpu().numpy().astype(np.float32)
    print(f"Image: {path}")
    print(f"Embedding shape: {embedding.shape}")
    print(f"Embedding dtype: {embedding.dtype}")
    print(f"Embedding norm: {np.linalg.norm(embedding):.6f}")
    return embedding


def generate_tile_embeddings() -> tuple[np.ndarray, list[Path]]:
    """Generate one normalized float32 embedding for every satellite tile."""
    image_paths = find_satellite_tiles()
    if not image_paths:
        raise FileNotFoundError(
            "No satellite tiles were found. Place .tif or .tiff satellite tiles "
            f"inside: {TILES_DIRECTORY}"
        )

    model, _, preprocess = load_remoteclip(device="cpu")
    embeddings: list[np.ndarray] = []
    embedding_dimension: int | None = None

    for number, image_path in enumerate(image_paths, start=1):
        print(f"Processing tile {number}/{len(image_paths)}: {image_path}")
        embedding = image_to_embedding(image_path, model=model, preprocess=preprocess)

        if embedding_dimension is None:
            embedding_dimension = embedding.shape[0]
        elif embedding.shape[0] != embedding_dimension:
            raise ValueError("RemoteCLIP returned inconsistent embedding dimensions.")

        embeddings.append(embedding)

    return np.stack(embeddings).astype(np.float32, copy=False), image_paths
