"""Create normalized RemoteCLIP embeddings for satellite-image tiles on CPU."""

import csv
import re
from pathlib import Path

import numpy as np
import torch
from PIL import Image

from semantic_search.model import load_remoteclip


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SENTINEL2_TILES_DIRECTORY = PROJECT_ROOT / "data" / "tiles" / "sentinel2"
LEGACY_TILES_DIRECTORY = PROJECT_ROOT / "data" / "tiles"
TILES_DIRECTORY = SENTINEL2_TILES_DIRECTORY


def tile_sort_key(path: Path) -> tuple[int, str]:
    """Sort key extracting trailing numerical tile index for natural ordering."""
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
    """Return all Sentinel-2 / optical tiles recursively in deterministic order.
    
    Supports:
      1. Registered tiles in data/tiles_metadata.csv (Person 1 registry)
      2. Multi-date subfolders (data/tiles/sentinel2/<date>/)
      3. Scene-partitioned folders (data/tiles/<scene_name>/)
      4. Legacy flat tile folders
    """
    # 1. Check tiles_metadata.csv if present
    csv_file = PROJECT_ROOT / "data" / "tiles_metadata.csv"
    if csv_file.is_file() and tiles_dir is None:
        try:
            with csv_file.open("r", encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                paths = [Path(row["filepath"]) for row in reader if "filepath" in row and Path(row["filepath"]).is_file()]
                if paths:
                    return sorted(paths, key=lambda p: p.name.lower())
        except Exception:
            pass

    search_dirs: list[Path] = []
    if tiles_dir is not None:
        search_dirs.append(Path(tiles_dir))
    else:
        # Check standard locations in priority order
        if SENTINEL2_TILES_DIRECTORY.is_dir():
            search_dirs.append(SENTINEL2_TILES_DIRECTORY)
        else:
            search_dirs.extend([
                LEGACY_TILES_DIRECTORY,
                PROJECT_ROOT / "sample_pairs",
                PROJECT_ROOT / "patches",
            ])

    candidate_tiles: list[Path] = []
    for sdir in search_dirs:
        if sdir.is_dir():
            found = [
                p for p in sdir.rglob("*")
                if p.is_file() and p.suffix.lower() in {".tif", ".tiff"}
                and p.name.lower() != "test_tile.tiff"
                and not p.name.lower().endswith(("_full.tif", "_full.tiff"))
                and "sentinel1" not in p.as_posix().lower()
                and not p.name.lower().startswith("sentinel1_")
            ]
            if found:
                candidate_tiles.extend(found)
                if tiles_dir is not None:
                    break

    unique_tiles = list(dict.fromkeys(candidate_tiles))

    def sort_key(path: Path) -> tuple[str, int, str]:
        parent_name = path.parent.name.lower()
        match = re.search(r"(\d+)$", path.stem.lower())
        tile_number = int(match.group(1)) if match else float("inf")
        return (parent_name, tile_number, path.as_posix().lower())

    return sorted(unique_tiles, key=sort_key)


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

    try:
        # Robust multi-band 16-bit GeoTIFF reader
        import rasterio
        with rasterio.open(path) as src:
            count = src.count
            if count >= 3:
                arr = src.read([1, 2, 3]).astype(np.float32)
                arr = np.transpose(arr, (1, 2, 0))
            else:
                b1 = src.read(1).astype(np.float32)
                arr = np.stack([b1, b1, b1], axis=-1)

            p2, p98 = np.percentile(arr[arr > 0] if np.any(arr > 0) else arr, (2, 98))
            if p98 > p2:
                arr = np.clip((arr - p2) / (p98 - p2 + 1e-5) * 255.0, 0, 255).astype(np.uint8)
            else:
                arr = np.clip(arr / 10000.0 * 255.0, 0, 255).astype(np.uint8)
            pil_img = Image.fromarray(arr, mode="RGB")
            image_tensor = preprocess(pil_img).unsqueeze(0)
    except Exception:
        with Image.open(path) as image:
            rgb_image = image.convert("RGB")
            image_tensor = preprocess(rgb_image).unsqueeze(0)

    with torch.no_grad():
        features = model.encode_image(image_tensor)
        normalized_features = torch.nn.functional.normalize(features, p=2, dim=-1)

    embedding = normalized_features.squeeze(0).cpu().numpy().astype(np.float32)
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
