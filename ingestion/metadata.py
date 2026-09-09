from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Optional

import rasterio


def _extract_date(tags: dict[str, Any]) -> Optional[str]:
    keys = ("acquisition_date", "acquisition_datetime", "datetime", "date_acquired", "sensing_time", "sensing_date", "date")
    lowered = {str(k).lower(): v for k, v in tags.items()}
    for key in keys:
        value = lowered.get(key)
        if value:
            return str(value)
    for value in tags.values():
        if value is None:
            continue
        match = re.search(r"\b(20\d{2}-\d{2}-\d{2}(?:[T ][0-9:.+-]+)?)\b", str(value))
        if match:
            return match.group(1)
    return None


def get_metadata(filepath: str | Path) -> dict[str, Any]:
    path = Path(filepath)
    if path.suffix.lower() not in {".tif", ".tiff"}:
        raise ValueError("Only .tif and .tiff files are accepted")
    if not path.is_file():
        raise FileNotFoundError(f"Raster file not found: {path}")
    try:
        with rasterio.open(path) as src:
            bounds = src.bounds
            return {
                "filepath": str(path.resolve()),
                "filename": path.name,
                "width": int(src.width),
                "height": int(src.height),
                "bands": int(src.count),
                "dtype": str(src.dtypes[0]),
                "nodata": float(src.nodata) if src.nodata is not None else None,
                "crs": src.crs.to_string() if src.crs else None,
                "minx": float(bounds.left),
                "miny": float(bounds.bottom),
                "maxx": float(bounds.right),
                "maxy": float(bounds.top),
                "transform": list(src.transform[:6]),
                "acquisition_date": _extract_date(src.tags()),
            }
    except Exception as exc:
        raise ValueError(f"Unable to read raster '{path}': {exc}") from exc


def transform_to_json(transform: Any) -> str:
    return json.dumps(list(transform[:6]), separators=(",", ":"))
