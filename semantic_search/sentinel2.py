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


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_RAW_DIR = PROJECT_ROOT / "data" / "raw" / "sentinel2"
DEFAULT_OUTPUT_TILES_DIR = PROJECT_ROOT / "data" / "tiles" / "sentinel2"

REQUIRED_BANDS = ("B02", "B03", "B04", "B08")


# ---------------------------------------------------------------------------
# DATE / BAND DISCOVERY
# ---------------------------------------------------------------------------


def extract_acquisition_date(filepath_or_name: str | Path) -> str:
    """Extract YYYY-MM-DD from a Sentinel-2 filename or path."""
    filename = Path(filepath_or_name).name

    match = re.search(r"(\d{4}-\d{2}-\d{2})", filename)

    if not match:
        raise ValueError(
            f"Could not extract acquisition date from filename: {filename}"
        )

    return match.group(1)


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


def discover_sentinel2_date_dirs(
    raw_root: str | Path = DEFAULT_RAW_DIR,
) -> list[Path]:
    """Automatically discover valid YYYY-MM-DD Sentinel-2 date folders.

    Future workflow:

        data/raw/sentinel2/
            2024-04-02/
            2025-03-29/
            2026-06-27/
            2027-01-15/

    No code change is required when a new date directory is added.
    """
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
            find_sentinel2_bands(candidate)
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
            rgb_array, profile, date = create_sentinel2_rgb_composite(
                raw_dir=raw_dir,
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
        bands = find_sentinel2_bands(date_dir)

        alignment = validate_sentinel2_band_alignment(
            bands,
        )

        report[date_dir.name] = {
            "directory": str(date_dir),
            "bands": {
                band: str(path)
                for band, path in bands.items()
            },
            "alignment": alignment,
        }

    return report


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
]