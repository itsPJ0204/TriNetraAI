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
    """Return all TIFF tiles in a stable alphabetical order."""
    if not TILES_DIRECTORY.is_dir():
        return []

    return sorted(
        (
            path
            for path in TILES_DIRECTORY.iterdir()
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
    """Convert one satellite-image tile into a normalized float32 vector."""
    path = Path(image_path)
    if not path.is_file():
        raise FileNotFoundError(f"Satellite image was not found: {path}")

    if model is None and preprocess is None:
        model, _, preprocess = load_remoteclip(device="cpu")
    elif model is None or preprocess is None:
        raise ValueError("Provide both model and preprocess, or neither.")

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
