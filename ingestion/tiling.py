from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import rasterio
from rasterio.windows import Window

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TILE_SIZE = 512


def create_tiles(
    filepath: str | Path,
    image_id: int | None = None,
    tile_size: int = DEFAULT_TILE_SIZE,
    output_root: str | Path | None = None,
) -> list[dict[str, Any]]:
    """Split a GeoTIFF/COG into georeferenced tiles with stable spatial keys."""
    path = Path(filepath)
    if path.suffix.lower() not in {".tif", ".tiff"}:
        raise ValueError("Only .tif and .tiff files are accepted")
    if tile_size <= 0:
        raise ValueError("tile_size must be greater than zero")
    if not path.is_file():
        raise FileNotFoundError(f"Raster file not found: {path}")

    root = Path(output_root) if output_root else PROJECT_ROOT / "data" / "tiles"
    image_dir = root / path.stem
    image_dir.mkdir(parents=True, exist_ok=True)

    records: list[dict[str, Any]] = []
    with rasterio.open(path) as src:
        if src.count < 1 or src.width < 1 or src.height < 1:
            raise ValueError(f"Raster has no readable pixels: {path}")

        for grid_row, row_off in enumerate(range(0, src.height, tile_size)):
            for grid_col, col_off in enumerate(range(0, src.width, tile_size)):
                width = min(tile_size, src.width - col_off)
                height = min(tile_size, src.height - row_off)
                window = Window(col_off, row_off, width, height)
                data = src.read(window=window)
                tile_transform = src.window_transform(window)
                left, bottom, right, top = rasterio.windows.bounds(window, src.transform)

                grid_key = f"r{grid_row:05d}_c{grid_col:05d}"
                tile_id = f"{path.stem}_{grid_key}"
                tile_path = image_dir / f"{tile_id}.tif"

                profile = src.profile.copy()
                profile.update(
                    driver="GTiff",
                    width=width,
                    height=height,
                    transform=tile_transform,
                    tiled=False,
                )
                profile.pop("blockxsize", None)
                profile.pop("blockysize", None)

                with rasterio.open(tile_path, "w", **profile) as dst:
                    dst.write(data)

                records.append({
                    "tile_id": tile_id,
                    "grid_key": grid_key,
                    "grid_row": grid_row,
                    "grid_col": grid_col,
                    "image_id": image_id,
                    "filepath": str(tile_path.resolve()),
                    "minx": float(left),
                    "miny": float(bottom),
                    "maxx": float(right),
                    "maxy": float(top),
                    "width": int(width),
                    "height": int(height),
                    "row_off": int(row_off),
                    "col_off": int(col_off),
                    "bands": int(src.count),
                    "dtype": str(src.dtypes[0]),
                    "nodata": float(src.nodata) if src.nodata is not None else None,
                    "crs": src.crs.to_string() if src.crs else None,
                    "transform": json.dumps(list(tile_transform[:6]), separators=(",", ":")),
                })

    return records
