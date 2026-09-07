from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import rasterio
from rasterio.windows import Window

from ingestion.tiling import PROJECT_ROOT, DEFAULT_TILE_SIZE


def find_band_files(folder: str | Path, bands: tuple[int, ...] = (2, 3, 4, 5)) -> list[Path]:
    folder = Path(folder)
    if not folder.is_dir():
        raise FileNotFoundError(f"Band folder not found: {folder}")
    files = []
    for band in bands:
        matches = sorted(folder.glob(f"BAND{band}.tif")) + sorted(folder.glob(f"BAND{band}.tiff"))
        if not matches:
            raise FileNotFoundError(f"Missing BAND{band}.tif/.tiff in {folder}")
        files.append(matches[0])
    return files


def band_manifest_hash(files: list[Path]) -> str:
    import hashlib
    digest = hashlib.sha256()
    for path in files:
        stat = path.stat()
        digest.update(path.name.encode())
        digest.update(str(stat.st_size).encode())
        digest.update(str(stat.st_mtime_ns).encode())
    return digest.hexdigest()


def create_tiles_from_band_folder(
    folder: str | Path,
    image_id: int | None = None,
    tile_size: int = DEFAULT_TILE_SIZE,
    output_root: str | Path | None = None,
    bands: tuple[int, ...] = (2, 3, 4, 5),
) -> list[dict[str, Any]]:
    """Tile aligned single-band Bhuvan files as one multi-band tile without making fake imagery."""
    if tile_size <= 0:
        raise ValueError("tile_size must be greater than zero")
    files = find_band_files(folder, bands)
    sources = [rasterio.open(p) for p in files]
    try:
        ref = sources[0]
        for src in sources[1:]:
            if (src.width, src.height, src.crs, src.transform) != (ref.width, ref.height, ref.crs, ref.transform):
                raise ValueError("BAND2-BAND5 are not spatially aligned (size/CRS/transform mismatch)")
            if src.dtypes[0] != ref.dtypes[0]:
                raise ValueError("BAND2-BAND5 have different data types")

        root = Path(output_root) if output_root else PROJECT_ROOT / "data" / "tiles"
        scene_name = Path(folder).name
        image_dir = root / scene_name
        image_dir.mkdir(parents=True, exist_ok=True)
        records: list[dict[str, Any]] = []

        for grid_row, row_off in enumerate(range(0, ref.height, tile_size)):
            for grid_col, col_off in enumerate(range(0, ref.width, tile_size)):
                width = min(tile_size, ref.width - col_off)
                height = min(tile_size, ref.height - row_off)
                window = Window(col_off, row_off, width, height)
                data = [src.read(1, window=window) for src in sources]
                tile_transform = ref.window_transform(window)
                left, bottom, right, top = rasterio.windows.bounds(window, ref.transform)
                grid_key = f"r{grid_row:05d}_c{grid_col:05d}"
                tile_id = f"{scene_name}_{grid_key}"
                tile_path = image_dir / f"{tile_id}.tif"
                profile = ref.profile.copy()
                profile.update(driver="GTiff", count=len(data), width=width, height=height,
                               transform=tile_transform, tiled=False)
                profile.pop("blockxsize", None); profile.pop("blockysize", None)
                with rasterio.open(tile_path, "w", **profile) as dst:
                    for idx, arr in enumerate(data, start=1):
                        dst.write(arr, idx)
                    dst.update_tags(source_bands=",".join(f"BAND{b}" for b in bands))

                records.append({
                    "tile_id": tile_id, "grid_key": grid_key, "grid_row": grid_row, "grid_col": grid_col,
                    "image_id": image_id, "filepath": str(tile_path.resolve()),
                    "minx": float(left), "miny": float(bottom), "maxx": float(right), "maxy": float(top),
                    "width": int(width), "height": int(height), "row_off": int(row_off), "col_off": int(col_off),
                    "bands": len(data), "dtype": str(ref.dtypes[0]),
                    "nodata": float(ref.nodata) if ref.nodata is not None else None,
                    "crs": ref.crs.to_string() if ref.crs else None,
                    "transform": json.dumps(list(tile_transform[:6]), separators=(",", ":")),
                })
        return records
    finally:
        for src in sources:
            src.close()
