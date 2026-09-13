"""Sentinel-2 L2A raw-band ingestion, RGB compositing, and geospatial tiling.

This module supports:
- single-date Sentinel-2 processing
- automatic multi-date discovery
- B04/B03/B02 -> RGB compositing
- preservation of B08 (NIR)
- deterministic uint16 -> uint8 normalization
- 256x256 tiling with complete edge coverage
- preservation of CRS, transform, bounds, date, and provenance
"""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any

import numpy as np
import rasterio
from rasterio.windows import Window

from semantic_search.indexer import index_satellite_tiles
from semantic_search.vector_store import DEFAULT_SCENE_DATE


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_RAW_DIR = PROJECT_ROOT / "data" / "raw" / "sentinel2"
DEFAULT_OUTPUT_TILES_DIR = PROJECT_ROOT / "data" / "tiles" / "sentinel2"

REQUIRED_BANDS = ("B02", "B03", "B04", "B08")


# ---------------------------------------------------------------------------
# DATE / BAND DISCOVERY
# ---------------------------------------------------------------------------


def extract_acquisition_date(filepath_or_name: str | Path) -> str:
    """Extract YYYY-MM-DD from a Sentinel-2 filename or path."""
    p = Path(filepath_or_name)

    match = re.search(r"(\d{4}-\d{2}-\d{2})", p.name)
    if match:
        return match.group(1)

    match_path = re.search(r"(\d{4}-\d{2}-\d{2})", p.as_posix())
    if match_path:
        return match_path.group(1)

    raise ValueError(
        f"Could not extract acquisition date from filename or path: {filepath_or_name}"
    )


def find_sentinel2_bands(raw_dir: str | Path) -> dict[str, Path]:
    """Find B02, B03, B04 and B08 files inside one date directory.

    Expected structure:

        data/raw/sentinel2/2026-06-27/
            ...B02...tiff
            ...B03...tiff
            ...B04...tiff
            ...B08...tiff
    """
    dir_path = Path(raw_dir)

    if not dir_path.is_dir():
        raise FileNotFoundError(
            f"Sentinel-2 raw directory not found: {dir_path}"
        )

    files = sorted(
        [
            *dir_path.glob("*.tif"),
            *dir_path.glob("*.tiff"),
            *dir_path.glob("*.jp2"),
        ]
    )

    if not files:
        date_dirs = discover_sentinel2_date_dirs(dir_path)
        if date_dirs:
            return find_sentinel2_bands(date_dirs[-1])

    band_paths: dict[str, Path] = {}

    for band in REQUIRED_BANDS:
        matches = [
            file_path
            for file_path in files
            if re.search(
                rf"(?<![A-Z0-9]){band}(?![A-Z0-9])",
                file_path.name.upper(),
            )
        ]

        if len(matches) > 1:
            raise ValueError(
                f"Multiple {band} files found in {dir_path}: "
                f"{[str(path) for path in matches]}"
            )

        if matches:
            band_paths[band] = matches[0]

    missing = [band for band in REQUIRED_BANDS if band not in band_paths]

    if missing:
        raise FileNotFoundError(
            f"Missing required Sentinel-2 band files {missing} "
            f"in {dir_path}"
        )

    return band_paths


def find_sentinel2_rgb_image(raw_dir: str | Path) -> Path | None:
    """Find a pre-composited True-Colour (RGB) GeoTIFF or image file in a date directory.

    Supports:
        - Files named with RGB indicators (e.g. *TCI*, *RGB*, *true_color*, *visual*, *composite*)
        - Any multi-band (>= 3 channels) GeoTIFF (.tif, .tiff, .jp2)
    """
    dir_path = Path(raw_dir)
    if not dir_path.is_dir():
        return None

    files = sorted(
        [
            *dir_path.glob("*.tif"),
            *dir_path.glob("*.tiff"),
            *dir_path.glob("*.jp2"),
            *dir_path.glob("*.png"),
            *dir_path.glob("*.jpg"),
            *dir_path.glob("*.jpeg"),
        ]
    )

    # 1. First priority: look for explicit RGB / True Color naming
    rgb_patterns = [r"TCI", r"TRUE[-_]?COLOU?R", r"RGB", r"COMPOSITE", r"VISUAL"]
    for file_path in files:
        # Ignore individual single-band raw files like ..._B02.tiff
        if any(re.search(rf"(?<![A-Z0-9]){band}(?![A-Z0-9])", file_path.name.upper()) for band in REQUIRED_BANDS):
            continue
        for pattern in rgb_patterns:
            if re.search(pattern, file_path.name, re.IGNORECASE):
                try:
                    with rasterio.open(file_path) as src:
                        if src.count >= 3:
                            return file_path
                except Exception:
                    continue

    # 2. Second priority: any GeoTIFF with at least 3 channels (and not a single-band file)
    for file_path in files:
        if any(re.search(rf"(?<![A-Z0-9]){band}(?![A-Z0-9])", file_path.name.upper()) for band in REQUIRED_BANDS):
            continue
        try:
            with rasterio.open(file_path) as src:
                if src.count >= 3:
                    return file_path
        except Exception:
            continue

    # 3. Third priority: any valid raster file in the directory
    for file_path in files:
        try:
            with rasterio.open(file_path) as src:
                if src.count >= 1:
                    return file_path
        except Exception:
            continue

    return None


def detect_sentinel2_raw_inputs(raw_dir: str | Path) -> dict[str, Any]:
    """Inspect a Sentinel-2 date directory and determine input type (Separate Bands vs True-Colour Image).

    Priority:
        1. Separate Bands (B02, B03, B04, B08): Preferred because B08 (NIR) is preserved for QA/vegetation.
        2. True-Colour (RGB) Image: 3+ band pre-composited GeoTIFF.

    Returns
    -------
    dict[str, Any]
        {"mode": "separate_bands", "bands": {...}} OR
        {"mode": "true_colour", "rgb_path": Path(...)}
    """
    dir_path = Path(raw_dir)
    if not dir_path.is_dir():
        raise FileNotFoundError(f"Directory not found: {dir_path}")

    # Check for separate bands first
    try:
        bands = find_sentinel2_bands(dir_path)
        return {"mode": "separate_bands", "bands": bands}
    except (FileNotFoundError, ValueError):
        pass

    # Check for true colour RGB image
    rgb_img = find_sentinel2_rgb_image(dir_path)
    if rgb_img is not None:
        return {"mode": "true_colour", "rgb_path": rgb_img}

    raise FileNotFoundError(
        f"No valid Sentinel-2 separate bands (B02, B03, B04, B08) or True-Colour RGB image found in: {dir_path}"
    )


def discover_sentinel2_date_dirs(
    raw_root: str | Path = DEFAULT_RAW_DIR,
) -> list[Path]:
    """Automatically discover valid YYYY-MM-DD Sentinel-2 date folders supporting both Separate Bands and True-Colour RGB images."""
    root = Path(raw_root)

    if not root.is_dir():
        raise FileNotFoundError(
            f"Sentinel-2 raw root directory not found: {root}"
        )

    discovered: list[Path] = []

    for candidate in sorted(root.iterdir()):
        if not candidate.is_dir():
            continue

        # Only date-named directories are considered.
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", candidate.name):
            continue

        try:
            detect_sentinel2_raw_inputs(candidate)
        except (FileNotFoundError, ValueError):
            # Incomplete/invalid scene is ignored by discovery.
            continue

        discovered.append(candidate)

    return discovered


# ---------------------------------------------------------------------------
# RASTER VALIDATION
# ---------------------------------------------------------------------------


def validate_sentinel2_band_alignment(
    band_paths: dict[str, Path],
) -> dict[str, Any]:
    """Validate that all required bands share the same spatial grid."""
    required = set(REQUIRED_BANDS)

    if set(band_paths) != required:
        missing = sorted(required - set(band_paths))
        raise ValueError(
            f"Band set is incomplete. Missing: {missing}"
        )

    reference_band = "B04"

    with rasterio.open(band_paths[reference_band]) as reference:
        reference_width = reference.width
        reference_height = reference.height
        reference_crs = reference.crs
        reference_transform = reference.transform
        reference_bounds = reference.bounds

    results: dict[str, Any] = {
        "width": reference_width,
        "height": reference_height,
        "crs": str(reference_crs) if reference_crs else None,
        "bounds": {
            "left": reference_bounds.left,
            "bottom": reference_bounds.bottom,
            "right": reference_bounds.right,
            "top": reference_bounds.top,
        },
        "bands": {},
    }

    for band_name in REQUIRED_BANDS:
        with rasterio.open(band_paths[band_name]) as src:
            same_dimensions = (
                src.width == reference_width
                and src.height == reference_height
            )

            same_crs = src.crs == reference_crs
            same_transform = src.transform == reference_transform
            same_bounds = src.bounds == reference_bounds

            if not (
                same_dimensions
                and same_crs
                and same_transform
                and same_bounds
            ):
                raise ValueError(
                    f"{band_name} is not spatially aligned with {reference_band}."
                )

            results["bands"][band_name] = {
                "width": src.width,
                "height": src.height,
                "dtype": src.dtypes[0],
                "crs": str(src.crs) if src.crs else None,
                "nodata": src.nodata,
                "bounds": {
                    "left": src.bounds.left,
                    "bottom": src.bounds.bottom,
                    "right": src.bounds.right,
                    "top": src.bounds.top,
                },
            }

    return results


# ---------------------------------------------------------------------------
# NORMALIZATION
# ---------------------------------------------------------------------------


def normalize_uint16_to_uint8(
    band_data: np.ndarray,
    p_low: float = 2.0,
    p_high: float = 98.0,
) -> np.ndarray:
    """Apply deterministic percentile stretch from uint16 to uint8."""
    if band_data.size == 0:
        return np.empty_like(band_data, dtype=np.uint8)

    low = float(np.percentile(band_data, p_low))
    high = float(np.percentile(band_data, p_high))

    if high <= low:
        high = low + 1.0

    scaled = (
        (band_data.astype(np.float32) - low)
        / (high - low)
        * 255.0
    )

    return np.clip(scaled, 0, 255).astype(np.uint8)


# ---------------------------------------------------------------------------
# RGB COMPOSITE
# ---------------------------------------------------------------------------


def create_sentinel2_rgb_composite(
    raw_dir: str | Path = DEFAULT_RAW_DIR,
    output_composite_path: str | Path | None = None,
    p_low: float = 2.0,
    p_high: float = 98.0,
) -> tuple[np.ndarray, dict[str, Any], str]:
    """Create RGB composite using B04/B03/B02.

    Mapping:
        B04 -> Red
        B03 -> Green
        B02 -> Blue

    B08 is intentionally not mixed into RGB.
    """
    raw_dir = Path(raw_dir)

    bands = find_sentinel2_bands(raw_dir)

    # Verify all bands share the same spatial grid before composing.
    validation = validate_sentinel2_band_alignment(bands)

    with rasterio.open(bands["B04"]) as src_r:
        r_raw = src_r.read(1)
        profile = src_r.profile.copy()

    with rasterio.open(bands["B03"]) as src_g:
        g_raw = src_g.read(1)

    with rasterio.open(bands["B02"]) as src_b:
        b_raw = src_b.read(1)

    date = extract_acquisition_date(bands["B04"])

    # Deterministic percentile normalization.
    r_u8 = normalize_uint16_to_uint8(
        r_raw,
        p_low=p_low,
        p_high=p_high,
    )

    g_u8 = normalize_uint16_to_uint8(
        g_raw,
        p_low=p_low,
        p_high=p_high,
    )

    b_u8 = normalize_uint16_to_uint8(
        b_raw,
        p_low=p_low,
        p_high=p_high,
    )

    # RGB = R, G, B
    rgb_array = np.stack(
        [r_u8, g_u8, b_u8],
        axis=0,
    )

    profile.update(
        count=3,
        dtype="uint8",
        nodata=None,
        driver="GTiff",
        photometric="RGB",
    )

    if output_composite_path is not None:
        output_path = Path(output_composite_path)
        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with rasterio.open(
            output_path,
            "w",
            **profile,
        ) as dst:
            dst.write(rgb_array)

            dst.update_tags(
                date=date,
                crs=str(profile.get("crs")),
                r_band="B04",
                g_band="B03",
                b_band="B02",
                nir_band="B08 preserved separately",
                provenance="Sentinel-2 L2A",
                normalization=f"percentile_{p_low:g}_{p_high:g}",
                source_directory=str(raw_dir),
            )

    return rgb_array, profile, date


def process_true_colour_composite(
    rgb_path: str | Path,
    output_composite_path: str | Path | None = None,
    p_low: float = 2.0,
    p_high: float = 98.0,
) -> tuple[np.ndarray, dict[str, Any], str]:
    """Process a pre-composited True-Colour (RGB) GeoTIFF or multi-band image file.

    Normalizes 16-bit / float rasters to 8-bit RGB if necessary and extracts date and geospatial metadata.
    """
    path = Path(rgb_path)
    if not path.is_file():
        raise FileNotFoundError(f"True-Colour image file not found: {path}")

    with rasterio.open(path) as src:
        profile = src.profile.copy()
        count = src.count
        tags = src.tags()
        dtype = src.dtypes[0]

        if count >= 3:
            r_raw = src.read(1)
            g_raw = src.read(2)
            b_raw = src.read(3)
        elif count == 1:
            r_raw = src.read(1)
            g_raw = r_raw
            b_raw = r_raw
        else:
            r_raw = src.read(1)
            g_raw = src.read(2)
            b_raw = r_raw

    # Extract date
    try:
        date = tags.get("date") or extract_acquisition_date(path)
    except ValueError:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", path.parent.name):
            date = path.parent.name
        else:
            date = DEFAULT_SCENE_DATE

    # Normalize if needed
    if np.issubdtype(np.dtype(dtype), np.integer) and dtype != "uint8":
        r_u8 = normalize_uint16_to_uint8(r_raw, p_low=p_low, p_high=p_high)
        g_u8 = normalize_uint16_to_uint8(g_raw, p_low=p_low, p_high=p_high)
        b_u8 = normalize_uint16_to_uint8(b_raw, p_low=p_low, p_high=p_high)
    elif np.issubdtype(np.dtype(dtype), np.floating):
        if np.nanmax(r_raw) <= 1.0 and np.nanmax(g_raw) <= 1.0 and np.nanmax(b_raw) <= 1.0:
            r_u8 = np.clip(r_raw * 255.0, 0, 255).astype(np.uint8)
            g_u8 = np.clip(g_raw * 255.0, 0, 255).astype(np.uint8)
            b_u8 = np.clip(b_raw * 255.0, 0, 255).astype(np.uint8)
        else:
            r_u8 = normalize_uint16_to_uint8(r_raw, p_low=p_low, p_high=p_high)
            g_u8 = normalize_uint16_to_uint8(g_raw, p_low=p_low, p_high=p_high)
            b_u8 = normalize_uint16_to_uint8(b_raw, p_low=p_low, p_high=p_high)
    else:
        r_u8 = r_raw.astype(np.uint8)
        g_u8 = g_raw.astype(np.uint8)
        b_u8 = b_raw.astype(np.uint8)

    rgb_array = np.stack([r_u8, g_u8, b_u8], axis=0)

    profile.update(
        count=3,
        dtype="uint8",
        nodata=None,
        driver="GTiff",
        photometric="RGB",
    )

    if output_composite_path is not None:
        output_path = Path(output_composite_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with rasterio.open(output_path, "w", **profile) as dst:
            dst.write(rgb_array)
            dst.update_tags(
                date=date,
                crs=str(profile.get("crs")),
                r_band="Red",
                g_band="Green",
                b_band="Blue",
                provenance="True-Colour Composite",
                source_file=str(path),
            )

    return rgb_array, profile, date


# ---------------------------------------------------------------------------
# TILE WINDOWS
# ---------------------------------------------------------------------------


def split_tile_windows(
    width: int,
    height: int,
    tile_size: int = 256,
) -> list[Window]:
    """Create non-overlapping tile windows covering the entire image."""
    if tile_size <= 0:
        raise ValueError("tile_size must be greater than zero.")

    windows: list[Window] = []

    for row_off in range(0, height, tile_size):
        tile_height = min(
            tile_size,
            height - row_off,
        )

        for col_off in range(0, width, tile_size):
            tile_width = min(
                tile_size,
                width - col_off,
            )

            windows.append(
                Window(
                    col_off,
                    row_off,
                    tile_width,
                    tile_height,
                )
            )

    return windows


def split_grid_windows(
    width: int,
    height: int,
    rows: int = 2,
    cols: int = 2,
) -> list[Window]:
    """Create a fixed rows x cols grid covering the full image."""
    if rows <= 0 or cols <= 0:
        raise ValueError("rows and cols must be greater than zero.")

    col_width_base = width // cols
    row_height_base = height // rows

    windows: list[Window] = []

    for row in range(rows):
        row_off = row * row_height_base

        tile_height = (
            row_height_base
            if row < rows - 1
            else height - row_off
        )

        for col in range(cols):
            col_off = col * col_width_base

            tile_width = (
                col_width_base
                if col < cols - 1
                else width - col_off
            )

            windows.append(
                Window(
                    col_off,
                    row_off,
                    tile_width,
                    tile_height,
                )
            )

    return windows


# ---------------------------------------------------------------------------
# SINGLE-SCENE TILING
# ---------------------------------------------------------------------------


def tile_sentinel2_rgb(
    source_path: str | Path | None = None,
    raw_dir: str | Path = DEFAULT_RAW_DIR,
    output_dir: str | Path = DEFAULT_OUTPUT_TILES_DIR,
    tile_size: int = 256,
    rows: int | None = None,
    cols: int | None = None,
    overwrite: bool = True,
    remove_old_tiles: bool = True,
) -> list[Path]:
    """Create georeferenced RGB tiles from an RGB composite."""
    out_dir = Path(output_dir)
    out_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Remove ONLY generated Sentinel-2 tile files.
    if remove_old_tiles:
        for old_tile in out_dir.glob("sentinel2_tile_*.tif"):
            old_tile.unlink(missing_ok=True)

    # ------------------------------------------------------------
    # Load RGB source
    # ------------------------------------------------------------

    if source_path is not None and Path(source_path).is_file():
        src_path = Path(source_path)

        with rasterio.open(src_path) as src:
            rgb_array = src.read()
            profile = src.profile.copy()
            tags = src.tags()

        date = tags.get("date") or extract_acquisition_date(src_path)

    else:
        candidate_composite = out_dir / "sentinel2_rgb_full.tif"

        if candidate_composite.is_file():
            with rasterio.open(candidate_composite) as src:
                rgb_array = src.read()
                profile = src.profile.copy()
                tags = src.tags()

            date = tags.get("date") or extract_acquisition_date(
                candidate_composite
            )

        else:
            input_info = detect_sentinel2_raw_inputs(raw_dir)
            if input_info["mode"] == "true_colour":
                rgb_array, profile, date = process_true_colour_composite(
                    input_info["rgb_path"],
                    output_composite_path=out_dir / "sentinel2_rgb_full.tif" if save_full_composite else None,
                    p_low=p_low,
                    p_high=p_high,
                )
            else:
                rgb_array, profile, date = create_sentinel2_rgb_composite(
                    raw_dir=raw_dir,
                    output_composite_path=out_dir / "sentinel2_rgb_full.tif" if save_full_composite else None,
                    p_low=p_low,
                    p_high=p_high,
                )

    # Validate expected RGB shape.
    if rgb_array.ndim != 3:
        raise ValueError(
            f"Expected RGB array with 3 dimensions, got {rgb_array.shape}"
        )

    if rgb_array.shape[0] != 3:
        raise ValueError(
            f"Expected 3 RGB channels, got {rgb_array.shape[0]}"
        )

    _, height, width = rgb_array.shape

    # ------------------------------------------------------------
    # Determine windows
    # ------------------------------------------------------------

    if rows is not None or cols is not None:
        if rows is None or cols is None:
            raise ValueError(
                "Provide both rows and cols, or neither."
            )

        windows = split_grid_windows(
            width,
            height,
            rows=rows,
            cols=cols,
        )

    else:
        windows = split_tile_windows(
            width,
            height,
            tile_size=tile_size,
        )

    transform = profile["transform"]
    crs = profile["crs"]

    generated_tiles: list[Path] = []

    # ------------------------------------------------------------
    # Write tiles
    # ------------------------------------------------------------

    for index, window in enumerate(
        windows,
        start=1,
    ):
        tile_path = out_dir / f"sentinel2_tile_{index}.tif"

        if tile_path.exists() and not overwrite:
            raise FileExistsError(
                f"Tile already exists and overwrite is False: "
                f"{tile_path}"
            )

        window_transform = rasterio.windows.transform(
            window,
            transform,
        )

        tile_width = int(window.width)
        tile_height = int(window.height)

        col_start = int(window.col_off)
        col_end = col_start + tile_width

        row_start = int(window.row_off)
        row_end = row_start + tile_height

        tile_data = rgb_array[
            :,
            row_start:row_end,
            col_start:col_end,
        ]

        tile_profile = profile.copy()

        tile_profile.update(
            width=tile_width,
            height=tile_height,
            transform=window_transform,
            count=3,
            dtype="uint8",
            driver="GTiff",
            photometric="RGB",
        )

        with rasterio.open(
            tile_path,
            "w",
            **tile_profile,
        ) as dst:
            dst.write(tile_data)

            dst.update_tags(
                tile_name=tile_path.name,
                date=date,
                crs=str(crs),
                r_band="B04",
                g_band="B03",
                b_band="B02",
                nir_band="B08 preserved separately",
                provenance="Sentinel-2 L2A",
                grid_index=f"{index}/{len(windows)}",
                tile_size=f"{tile_width}x{tile_height}",
            )

        generated_tiles.append(tile_path)

    return generated_tiles


# ---------------------------------------------------------------------------
# MULTI-DATE PROCESSING
# ---------------------------------------------------------------------------


def process_all_sentinel2_dates(
    raw_root: str | Path = DEFAULT_RAW_DIR,
    output_root: str | Path = DEFAULT_OUTPUT_TILES_DIR,
    tile_size: int = 256,
    overwrite: bool = True,
) -> dict[str, list[Path]]:
    """Process every valid Sentinel-2 date directory automatically.

    Example:

        data/raw/sentinel2/
            2024-04-02/
            2025-03-29/
            2026-06-27/

    becomes:

        data/tiles/sentinel2/
            2024-04-02/
                sentinel2_rgb_full.tif
                sentinel2_tile_1.tif
                ...
            2025-03-29/
                sentinel2_rgb_full.tif
                sentinel2_tile_1.tif
                ...
            2026-06-27/
                sentinel2_rgb_full.tif
                sentinel2_tile_1.tif
                ...

    Adding a new valid date directory requires no code changes.
    """
    raw_root = Path(raw_root)
    output_root = Path(output_root)

    date_dirs = discover_sentinel2_date_dirs(
        raw_root=raw_root,
    )

    if not date_dirs:
        raise FileNotFoundError(
            f"No complete Sentinel-2 date folders found in: "
            f"{raw_root}"
        )

    results: dict[str, list[Path]] = {}

    for date_dir in date_dirs:
        date = date_dir.name

        date_output_dir = output_root / date
        date_output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        print("=" * 70)
        print(f"Processing Sentinel-2 date: {date}")
        print(f"Raw:    {date_dir}")
        print(f"Output: {date_output_dir}")
        print("=" * 70)

        # Always rebuild this date's RGB composite from its
        # original raw bands.
        composite_path = (
            date_output_dir
            / "sentinel2_rgb_full.tif"
        )

        create_sentinel2_rgb_composite(
            raw_dir=date_dir,
            output_composite_path=composite_path,
        )

        # Create 256x256 tiles + edge tiles.
        generated_tiles = tile_sentinel2_rgb(
            source_path=composite_path,
            output_dir=date_output_dir,
            tile_size=tile_size,
            overwrite=overwrite,
            remove_old_tiles=True,
        )

        results[date] = generated_tiles

        print(
            f"Completed {date}: "
            f"{len(generated_tiles)} tiles generated."
        )

    return results


# ---------------------------------------------------------------------------
# CONVENIENCE / VALIDATION
# ---------------------------------------------------------------------------


def inspect_all_sentinel2_dates(
    raw_root: str | Path = DEFAULT_RAW_DIR,
) -> dict[str, dict[str, Any]]:
    """Inspect every valid date folder without generating outputs."""
    date_dirs = discover_sentinel2_date_dirs(
        raw_root=raw_root,
    )

    report: dict[str, dict[str, Any]] = {}

    for date_dir in date_dirs:
        input_info = detect_sentinel2_raw_inputs(date_dir)
        mode = input_info["mode"]

        if mode == "separate_bands":
            bands = input_info["bands"]
            alignment = validate_sentinel2_band_alignment(bands)
            report[date_dir.name] = {
                "directory": str(date_dir),
                "mode": "separate_bands",
                "bands": {
                    band: str(path)
                    for band, path in bands.items()
                },
                "alignment": alignment,
            }
        else:
            rgb_path = input_info["rgb_path"]
            with rasterio.open(rgb_path) as src:
                b = src.bounds
                alignment = {
                    "width": src.width,
                    "height": src.height,
                    "count": src.count,
                    "crs": str(src.crs) if src.crs else None,
                    "bounds": {"left": b.left, "bottom": b.bottom, "right": b.right, "top": b.top},
                }
            report[date_dir.name] = {
                "directory": str(date_dir),
                "mode": "true_colour",
                "rgb_path": str(rgb_path),
                "alignment": alignment,
            }

    return report


def generate_sentinel2_rgb_tiles(
    raw_date_dir: str | Path,
    output_date_dir: str | Path | None = None,
    tile_size: int = 256,
    p_low: float = 2.0,
    p_high: float = 98.0,
    overwrite: bool = True,
    save_full_composite: bool = True,
) -> dict[str, Any]:
    """Convert raw Sentinel-2 inputs (Separate bands B02/B03/B04/B08 or True-Colour RGB GeoTIFF) into date-wise georeferenced RGB GeoTIFF tiles.

    Band Mapping:
        - Separate Bands Mode: Band 1 = B04 (Red), Band 2 = B03 (Green), Band 3 = B02 (Blue), B08 preserved for NIR.
        - True-Colour Mode: Band 1 = Red, Band 2 = Green, Band 3 = Blue.

    Parameters
    ----------
    raw_date_dir : str | Path
        Path to date-wise raw directory (e.g. data/raw/sentinel2/2026-09-10).
    output_date_dir : str | Path | None, optional
        Path to date-wise tile output directory (e.g. data/tiles/sentinel2/2026-09-10).
        If None, automatically defaults to data/tiles/sentinel2/{date}.
    tile_size : int, default 256
        Tile dimension in pixels (256x256). Edge tiles covering remaining borders are preserved.
    p_low : float, default 2.0
        Lower percentile for contrast stretch.
    p_high : float, default 98.0
        Upper percentile for contrast stretch.
    overwrite : bool, default True
        Whether to overwrite existing tile files.
    save_full_composite : bool, default True
        Whether to save the full scene composite (sentinel2_rgb_full.tif) in the output directory.

    Returns
    -------
    dict[str, Any]
        Structured dictionary containing tiling and geospatial metadata.
    """
    raw_dir = Path(raw_date_dir)
    if not raw_dir.is_dir():
        raise FileNotFoundError(f"Raw Sentinel-2 directory not found: {raw_dir}")

    input_info = detect_sentinel2_raw_inputs(raw_dir)
    mode = input_info["mode"]

    if mode == "separate_bands":
        bands = input_info["bands"]
        alignment_info = validate_sentinel2_band_alignment(bands)

        try:
            date = extract_acquisition_date(bands["B04"])
        except ValueError:
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw_dir.name):
                date = raw_dir.name
            else:
                date = DEFAULT_SCENE_DATE

        if output_date_dir is not None:
            out_dir = Path(output_date_dir)
        else:
            out_dir = DEFAULT_OUTPUT_TILES_DIR / date

        out_dir.mkdir(parents=True, exist_ok=True)

        composite_path = out_dir / "sentinel2_rgb_full.tif" if save_full_composite else None
        rgb_array, profile, _ = create_sentinel2_rgb_composite(
            raw_dir=raw_dir,
            output_composite_path=composite_path,
            p_low=p_low,
            p_high=p_high,
        )

        generated_tiles = tile_sentinel2_rgb(
            source_path=composite_path,
            raw_dir=raw_dir,
            output_dir=out_dir,
            tile_size=tile_size,
            overwrite=overwrite,
            remove_old_tiles=True,
        )

        bounds = alignment_info.get("bounds", {})
        return {
            "date": date,
            "mode": "separate_bands",
            "input_directory": str(raw_dir.resolve()),
            "output_directory": str(out_dir.resolve()),
            "tile_size": tile_size,
            "num_tiles": len(generated_tiles),
            "tiles": generated_tiles,
            "band_mapping": {
                "band_1": "B04 (Red)",
                "band_2": "B03 (Green)",
                "band_3": "B02 (Blue)",
                "preserved_raw_nir": "B08 (NIR)",
            },
            "raw_bands_verified": {band: str(path.resolve()) for band, path in bands.items()},
            "crs": alignment_info.get("crs", str(profile.get("crs"))),
            "bounds": bounds,
            "raster_dimensions": {
                "width": alignment_info.get("width", profile.get("width")),
                "height": alignment_info.get("height", profile.get("height")),
            },
        }

    else:
        # True-Colour RGB Image Mode
        rgb_path = input_info["rgb_path"]

        try:
            date = extract_acquisition_date(rgb_path)
        except ValueError:
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw_dir.name):
                date = raw_dir.name
            else:
                date = DEFAULT_SCENE_DATE

        if output_date_dir is not None:
            out_dir = Path(output_date_dir)
        else:
            out_dir = DEFAULT_OUTPUT_TILES_DIR / date

        out_dir.mkdir(parents=True, exist_ok=True)

        composite_path = out_dir / "sentinel2_rgb_full.tif" if save_full_composite else None
        rgb_array, profile, _ = process_true_colour_composite(
            rgb_path=rgb_path,
            output_composite_path=composite_path,
            p_low=p_low,
            p_high=p_high,
        )

        generated_tiles = tile_sentinel2_rgb(
            source_path=composite_path,
            raw_dir=raw_dir,
            output_dir=out_dir,
            tile_size=tile_size,
            overwrite=overwrite,
            remove_old_tiles=True,
        )

        with rasterio.open(rgb_path) as src_meta:
            b = src_meta.bounds
            bounds = {"left": b.left, "bottom": b.bottom, "right": b.right, "top": b.top}
            crs_str = str(src_meta.crs) if src_meta.crs else None
            width = src_meta.width
            height = src_meta.height

        return {
            "date": date,
            "mode": "true_colour",
            "input_directory": str(raw_dir.resolve()),
            "output_directory": str(out_dir.resolve()),
            "tile_size": tile_size,
            "num_tiles": len(generated_tiles),
            "tiles": generated_tiles,
            "band_mapping": {
                "band_1": "Red",
                "band_2": "Green",
                "band_3": "Blue",
                "input_type": "True-Colour (RGB) Composite",
            },
            "raw_bands_verified": {"RGB": str(rgb_path.resolve())},
            "crs": crs_str,
            "bounds": bounds,
            "raster_dimensions": {
                "width": width,
                "height": height,
            },
        }


def ingest_sentinel2_date(
    raw_date_dir: str | Path,
    output_date_dir: str | Path | None = None,
    tile_size: int = 256,
    p_low: float = 2.0,
    p_high: float = 98.0,
    overwrite: bool = True,
    save_full_composite: bool = True,
    force_reindex: bool = False,
    verbose: bool = True,
) -> dict[str, Any]:
    """End-to-end single-date Sentinel-2 ingestion and incremental indexing.

    Executes the full pipeline:
      1. Validates presence and spatial alignment of raw B02, B03, B04, and B08 bands.
      2. Creates georeferenced RGB composite using B04 (Red), B03 (Green), B02 (Blue).
         (B08 is preserved untouched in the raw directory for NIR / change detection).
      3. Generates 256x256 GeoTIFF tiles (+ edge tiles) saved in date-wise directory.
      4. Incrementally embeds and indexes new or changed tiles into Qdrant collection
         'satellite_tiles' using RemoteCLIP, skipping unchanged tiles.
      5. Updates indexing manifest and embedding caches.

    Parameters
    ----------
    raw_date_dir : str | Path
        Directory containing raw Sentinel-2 TIFF bands (e.g. data/raw/sentinel2/2026-09-10).
    output_date_dir : str | Path | None, optional
        Target directory for generated RGB tiles (e.g. data/tiles/sentinel2/2026-09-10).
        If None, automatically defaults to data/tiles/sentinel2/{date}.
    tile_size : int, default 256
        Tile dimension in pixels.
    p_low : float, default 2.0
        Lower contrast stretch percentile.
    p_high : float, default 98.0
        Upper contrast stretch percentile.
    overwrite : bool, default True
        Whether to overwrite existing tile files.
    save_full_composite : bool, default True
        Whether to save full scene composite GeoTIFF in output directory.
    force_reindex : bool, default False
        Whether to force re-embedding of already-indexed tiles.
    verbose : bool, default True
        Whether to print progress details.

    Returns
    -------
    dict[str, Any]
        Structured dictionary containing:
            - date: Acquisition date string (YYYY-MM-DD)
            - raw_directory: Absolute path to raw input directory
            - tile_directory: Absolute path to tile output directory
            - tiles_discovered: Total tiles discovered for this date
            - tiles_new: Number of newly embedded tiles
            - tiles_unchanged: Number of unchanged tiles skipped without re-embedding
            - tiles_changed: Number of modified tiles re-embedded
            - embeddings_generated: Total new embeddings generated
            - qdrant_points_added: New points added to Qdrant
            - qdrant_points_updated: Updated points in Qdrant
            - failed: Number of failed tiles
            - tiles: List of generated tile Path objects
            - tile_size: Tile dimension in pixels
            - crs: Coordinate Reference System
            - bounds: Bounding box dictionary
            - band_mapping: Band mapping dictionary
            - raw_bands_verified: Dictionary of verified raw bands
    """
    raw_dir = Path(raw_date_dir)
    if not raw_dir.is_dir():
        raise FileNotFoundError(f"Raw Sentinel-2 directory not found: {raw_dir}")

    # Step 1: Generate date-wise georeferenced RGB tiles
    tiling_report = generate_sentinel2_rgb_tiles(
        raw_date_dir=raw_dir,
        output_date_dir=output_date_dir,
        tile_size=tile_size,
        p_low=p_low,
        p_high=p_high,
        overwrite=overwrite,
        save_full_composite=save_full_composite,
    )

    date = tiling_report["date"]
    out_dir = Path(tiling_report["output_directory"])
    tiles = tiling_report["tiles"]

    if verbose:
        print("=" * 70)
        print(f"SENTINEL-2 INGESTION & INCREMENTAL INDEXING: {date}")
        print(f"Raw Input:   {raw_dir.resolve()}")
        print(f"Tile Output: {out_dir.resolve()}")
        print(f"Tiles Count: {len(tiles)}")
        print("=" * 70)

    # Step 2: Incremental indexing into Qdrant collection 'satellite_tiles'
    indexer_stats = index_satellite_tiles(
        tiles_dir=out_dir,
        force=force_reindex,
        verbose=verbose,
    )

    discovered = indexer_stats.get("discovered", len(tiles))
    new_count = indexer_stats.get("new", 0)
    unchanged_count = indexer_stats.get("already_indexed", 0)
    changed_count = indexer_stats.get("changed", 0)
    emb_count = indexer_stats.get("embeddings_generated", 0)
    failed = indexer_stats.get("failed", 0)

    return {
        "date": date,
        "raw_directory": str(raw_dir.resolve()),
        "tile_directory": str(out_dir.resolve()),
        "tiles_discovered": discovered,
        "tiles_new": new_count,
        "tiles_unchanged": unchanged_count,
        "tiles_changed": changed_count,
        "embeddings_generated": emb_count,
        "qdrant_points_added": new_count,
        "qdrant_points_updated": changed_count,
        "failed": failed,
        "tiles": tiles,
        "tile_size": tile_size,
        "crs": tiling_report.get("crs"),
        "bounds": tiling_report.get("bounds"),
        "band_mapping": tiling_report.get("band_mapping"),
        "raw_bands_verified": tiling_report.get("raw_bands_verified"),
    }


def ingest_new_sentinel2(
    raw_root: str | Path = DEFAULT_RAW_DIR,
    output_root: str | Path = DEFAULT_OUTPUT_TILES_DIR,
    tile_size: int = 256,
    p_low: float = 2.0,
    p_high: float = 98.0,
    overwrite: bool = True,
    save_full_composite: bool = True,
    force_reindex: bool = False,
    verbose: bool = True,
) -> dict[str, Any]:
    """Discover all Sentinel-2 raw date folders and incrementally ingest and index new/changed dates and tiles.

    Scans the raw root directory (default: data/raw/sentinel2/), discovers all date-wise
    folders automatically, determines which dates and tiles require processing, and invokes
    `ingest_sentinel2_date` for each date.

    Features:
      - Automatic discovery of all YYYY-MM-DD date folders
      - Zero re-embedding / re-indexing for unchanged tiles
      - Full preservation of date-wise hierarchy and geospatial metadata
      - Idempotent: repeated runs produce 0 embeddings and 0 Qdrant writes

    Parameters
    ----------
    raw_root : str | Path, default data/raw/sentinel2
        Root folder containing date-wise Sentinel-2 raw band folders.
    output_root : str | Path, default data/tiles/sentinel2
        Root folder for date-wise output RGB tiles.
    tile_size : int, default 256
        Tile dimension in pixels.
    p_low : float, default 2.0
        Lower percentile for contrast stretch.
    p_high : float, default 98.0
        Upper percentile for contrast stretch.
    overwrite : bool, default True
        Whether to overwrite existing tile files.
    save_full_composite : bool, default True
        Whether to save full scene composite GeoTIFF.
    force_reindex : bool, default False
        Whether to force re-embedding of all tiles.
    verbose : bool, default True
        Whether to print detailed progress.

    Returns
    -------
    dict[str, Any]
        Structured summary report:
            - dates_discovered: Total valid Sentinel-2 date folders found
            - dates_processed: Number of dates that had new or changed tiles processed
            - dates_skipped: Number of dates that were already fully up-to-date
            - tiles_new: Total new tiles embedded and indexed
            - tiles_changed: Total modified tiles re-embedded and updated
            - tiles_unchanged: Total unchanged tiles skipped without re-embedding
            - embeddings_generated: Total RemoteCLIP embeddings generated
            - qdrant_points_added: Total new points upserted into Qdrant
            - qdrant_points_updated: Total modified points updated in Qdrant
            - failed: Total failed tiles
            - date_summaries: Dictionary mapping date strings to per-date reports
    """
    raw_root_path = Path(raw_root)
    output_root_path = Path(output_root)

    if not raw_root_path.is_dir():
        if verbose:
            print(f"Sentinel-2 raw root directory not found: {raw_root_path}")
        return {
            "dates_discovered": 0,
            "dates_processed": 0,
            "dates_skipped": 0,
            "tiles_new": 0,
            "tiles_changed": 0,
            "tiles_unchanged": 0,
            "embeddings_generated": 0,
            "qdrant_points_added": 0,
            "qdrant_points_updated": 0,
            "failed": 0,
            "date_summaries": {},
        }

    date_dirs = discover_sentinel2_date_dirs(raw_root=raw_root_path)
    dates_discovered = len(date_dirs)

    if verbose:
        print("=" * 70)
        print("AUTOMATIC SENTINEL-2 MULTI-DATE INGESTION & INCREMENTAL INDEXER")
        print("=" * 70)
        print(f"Raw Root Directory   : {raw_root_path.resolve()}")
        print(f"Tile Root Directory  : {output_root_path.resolve()}")
        print(f"Discovered Dates ({dates_discovered}): {[d.name for d in date_dirs]}")
        print("=" * 70)

    if dates_discovered == 0:
        return {
            "dates_discovered": 0,
            "dates_processed": 0,
            "dates_skipped": 0,
            "tiles_new": 0,
            "tiles_changed": 0,
            "tiles_unchanged": 0,
            "embeddings_generated": 0,
            "qdrant_points_added": 0,
            "qdrant_points_updated": 0,
            "failed": 0,
            "date_summaries": {},
        }

    date_summaries: dict[str, dict[str, Any]] = {}
    dates_processed = 0
    dates_skipped = 0
    total_tiles_new = 0
    total_tiles_changed = 0
    total_tiles_unchanged = 0
    total_embeddings_generated = 0
    total_qdrant_points_added = 0
    total_qdrant_points_updated = 0
    total_failed = 0

    for idx, date_dir in enumerate(date_dirs, start=1):
        date_str = date_dir.name
        date_output_dir = output_root_path / date_str

        if verbose:
            print(f"\n[{idx}/{dates_discovered}] Checking Sentinel-2 Date: {date_str} ...")

        report = ingest_sentinel2_date(
            raw_date_dir=date_dir,
            output_date_dir=date_output_dir,
            tile_size=tile_size,
            p_low=p_low,
            p_high=p_high,
            overwrite=overwrite,
            save_full_composite=save_full_composite,
            force_reindex=force_reindex,
            verbose=verbose,
        )

        date_summaries[date_str] = report

        t_new = report.get("tiles_new", 0)
        t_changed = report.get("tiles_changed", 0)
        t_unchanged = report.get("tiles_unchanged", 0)
        t_emb = report.get("embeddings_generated", 0)
        t_added = report.get("qdrant_points_added", 0)
        t_updated = report.get("qdrant_points_updated", 0)
        t_failed = report.get("failed", 0)

        total_tiles_new += t_new
        total_tiles_changed += t_changed
        total_tiles_unchanged += t_unchanged
        total_embeddings_generated += t_emb
        total_qdrant_points_added += t_added
        total_qdrant_points_updated += t_updated
        total_failed += t_failed

        if t_new > 0 or t_changed > 0:
            dates_processed += 1
        else:
            dates_skipped += 1

    summary = {
        "dates_discovered": dates_discovered,
        "dates_processed": dates_processed,
        "dates_skipped": dates_skipped,
        "tiles_new": total_tiles_new,
        "tiles_changed": total_tiles_changed,
        "tiles_unchanged": total_tiles_unchanged,
        "embeddings_generated": total_embeddings_generated,
        "qdrant_points_added": total_qdrant_points_added,
        "qdrant_points_updated": total_qdrant_points_updated,
        "failed": total_failed,
        "date_summaries": date_summaries,
    }

    if verbose:
        print("\n" + "=" * 70)
        print("ALL SENTINEL-2 DATES INGESTION COMPLETED")
        print("=" * 70)
        print(f"Dates Discovered     : {summary['dates_discovered']}")
        print(f"Dates Processed      : {summary['dates_processed']}")
        print(f"Dates Skipped        : {summary['dates_skipped']}")
        print(f"Tiles New (Embedded) : {summary['tiles_new']}")
        print(f"Tiles Changed        : {summary['tiles_changed']}")
        print(f"Tiles Unchanged      : {summary['tiles_unchanged']}")
        print(f"Embeddings Generated : {summary['embeddings_generated']}")
        print(f"Qdrant Points Added  : {summary['qdrant_points_added']}")
        print(f"Qdrant Points Updated: {summary['qdrant_points_updated']}")
        print(f"Failures             : {summary['failed']}")
        print("=" * 70)

    return summary


__all__ = [
    "PROJECT_ROOT",
    "DEFAULT_RAW_DIR",
    "DEFAULT_OUTPUT_TILES_DIR",
    "REQUIRED_BANDS",
    "extract_acquisition_date",
    "find_sentinel2_bands",
    "discover_sentinel2_date_dirs",
    "validate_sentinel2_band_alignment",
    "normalize_uint16_to_uint8",
    "create_sentinel2_rgb_composite",
    "split_tile_windows",
    "split_grid_windows",
    "tile_sentinel2_rgb",
    "process_all_sentinel2_dates",
    "inspect_all_sentinel2_dates",
    "generate_sentinel2_rgb_tiles",
    "ingest_sentinel2_date",
    "ingest_new_sentinel2",
]
