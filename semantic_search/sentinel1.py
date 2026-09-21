"""Sentinel-1 C-SAR GRD raw-band ingestion, dual-pol compositing, and geospatial tiling.

This module supports:
- Automatic single-date and multi-date Sentinel-1 discovery
- Detection of VV and VH polarizations (*VV*.tif*, *VH*.tif*) or pre-composited SAR rasters
- Decibel (dB) log-transformed amplitude normalization:
    dB = 10 * log10(amplitude^2 + eps) or 20 * log10(amplitude + eps), mapped to [0, 255] uint8
- Dual-polarization false-color 3-channel SAR composite:
    - Channel 1 (Red): VV (surface roughness, urban structures)
    - Channel 2 (Green): VH (volume scattering, vegetation / canopy)
    - Channel 3 (Blue): VV/VH ratio (polarimetric contrast, water / moisture distinction)
- 256x256 geospatial tiling preserving CRS, affine transform, geographic bounding box, date, and provenance
- Incremental indexing integration into dedicated Qdrant collection 'sentinel1_tiles'
"""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any

import numpy as np
import rasterio
from rasterio.windows import Window

from semantic_search.sentinel1_indexer import index_sentinel1_tiles


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_RAW_DIR = PROJECT_ROOT / "data" / "raw" / "sentinel1"
DEFAULT_OUTPUT_TILES_DIR = PROJECT_ROOT / "data" / "tiles" / "sentinel1"

REQUIRED_POLARIZATIONS = ("VV", "VH")


# ---------------------------------------------------------------------------
# DATE / BAND DISCOVERY
# ---------------------------------------------------------------------------


def extract_acquisition_date(filepath_or_name: str | Path) -> str:
    """Extract YYYY-MM-DD from a Sentinel-1 filename or path."""
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


def clean_filename_for_pol(filename: str) -> str:
    """Mask combined dual-pol metadata substrings so individual polarizations can be accurately matched."""
    name = filename.upper()
    # Mask Copernicus / Sentinel Hub / ESA dataset mode prefixes like Sentinel-1_IW_VV_VH, S1_IW_VV_VH, etc.
    name = re.sub(r"SENTINEL[-_]?1.*?IW[-_]?(VV[-_+/&]?VH|VH[-_+/&]?VV)", "SENTINEL1_SAR", name)
    # Mask generic combined VV_VH, VV+VH, VV-VH, VV/VH tokens
    name = re.sub(r"(?<![A-Z0-9])(VV[-_+/&]VH|VH[-_+/&]VV|VV_AND_VH|VH_AND_VV)(?![A-Z0-9])", "DUALPOL", name)
    return name


def _score_s1_band_candidate(file_path: Path, pol: str) -> int:
    """Score SAR band candidate files to prioritize raw amplitude GeoTIFFs over auxiliary products."""
    name_upper = file_path.name.upper()
    score = 10
    # Prioritize raw / linear amplitude files
    if re.search(r"(\bRAW\b|\(RAW\)|_RAW|[-_]RAW|AMPLITUDE|LINEAR)", name_upper):
        score += 100
    # Prioritize exact polarization stem e.g. VV.tif, 2026-06-27_VV.tif
    stem_upper = file_path.stem.upper()
    if stem_upper == pol or stem_upper.endswith(f"_{pol}") or stem_upper.endswith(f"-{pol}") or stem_upper.endswith(f" {pol}"):
        score += 80
    # Fallback score for decibel / gamma0 products if raw is absent
    if re.search(r"(GAMMA0|DECIBEL|\bDB\b|SIGMA0|BETA0)", name_upper):
        score += 40
    return score


def find_sentinel1_bands(raw_dir: str | Path) -> dict[str, Path]:
    """Find VV and VH polarization files inside one date directory.

    Expected structure:
        data/raw/sentinel1/2026-06-27/
            ...VV...tiff (or VV (Raw).tiff)
            ...VH...tiff (or VH (Raw).tiff)
    """
    dir_path = Path(raw_dir)

    if not dir_path.is_dir():
        raise FileNotFoundError(
            f"Sentinel-1 raw directory not found: {dir_path}"
        )

    files = sorted(
        [
            *dir_path.glob("*.tif"),
            *dir_path.glob("*.tiff"),
            *dir_path.glob("*.jp2"),
        ]
    )

    if not files:
        date_dirs = discover_sentinel1_date_dirs(dir_path)
        if date_dirs:
            return find_sentinel1_bands(date_dirs[-1])

    band_paths: dict[str, Path] = {}

    for pol in REQUIRED_POLARIZATIONS:
        matches: list[Path] = []
        for file_path in files:
            cleaned_name = clean_filename_for_pol(file_path.name)
            if re.search(rf"(?<![A-Z0-9]){pol}(?![A-Z0-9])", cleaned_name):
                matches.append(file_path)

        if matches:
            # If multiple matches exist (e.g. raw and gamma0/dB files uploaded together),
            # pick the best candidate (preferring raw amplitude)
            best_match = max(matches, key=lambda f: _score_s1_band_candidate(f, pol))
            band_paths[pol] = best_match

    missing = [pol for pol in REQUIRED_POLARIZATIONS if pol not in band_paths]

    if missing:
        raise FileNotFoundError(
            f"Missing required Sentinel-1 polarization files {missing} in {dir_path}"
        )

    return band_paths


def find_sentinel1_composite_image(raw_dir: str | Path) -> Path | None:
    """Find a pre-composited dual-pol or multi-channel SAR GeoTIFF in a date directory."""
    dir_path = Path(raw_dir)
    if not dir_path.is_dir():
        return None

    files = sorted(
        [
            *dir_path.glob("*.tif"),
            *dir_path.glob("*.tiff"),
            *dir_path.glob("*.jp2"),
        ]
    )

    sar_patterns = [r"SAR", r"DUAL[-_]?POL", r"COMPOSITE", r"GRD", r"IW", r"SENTINEL1", r"S1"]
    for file_path in files:
        cleaned_name = clean_filename_for_pol(file_path.name)
        if any(re.search(rf"(?<![A-Z0-9]){pol}(?![A-Z0-9])", cleaned_name) for pol in REQUIRED_POLARIZATIONS):
            continue
        for pattern in sar_patterns:
            if re.search(pattern, file_path.name, re.IGNORECASE):
                try:
                    with rasterio.open(file_path) as src:
                        if src.count >= 2:
                            return file_path
                except Exception:
                    continue

    for file_path in files:
        cleaned_name = clean_filename_for_pol(file_path.name)
        if any(re.search(rf"(?<![A-Z0-9]){pol}(?![A-Z0-9])", cleaned_name) for pol in REQUIRED_POLARIZATIONS):
            continue
        try:
            with rasterio.open(file_path) as src:
                if src.count >= 2:
                    return file_path
        except Exception:
            continue

    return None


def detect_sentinel1_raw_inputs(raw_dir: str | Path) -> dict[str, Any]:
    """Inspect a Sentinel-1 date directory and determine input type (Separate VV/VH vs Multi-Band Composite)."""
    dir_path = Path(raw_dir)
    if not dir_path.is_dir():
        raise FileNotFoundError(f"Directory not found: {dir_path}")

    try:
        bands = find_sentinel1_bands(dir_path)
        return {"mode": "separate_polarizations", "bands": bands}
    except (FileNotFoundError, ValueError):
        pass

    composite_img = find_sentinel1_composite_image(dir_path)
    if composite_img is not None:
        return {"mode": "sar_composite", "composite_path": composite_img}

    raise FileNotFoundError(
        f"No valid Sentinel-1 separate polarizations (VV, VH) or multi-channel SAR image found in: {dir_path}"
    )


def discover_sentinel1_date_dirs(
    raw_root: str | Path = DEFAULT_RAW_DIR,
) -> list[Path]:
    """Automatically discover valid YYYY-MM-DD Sentinel-1 date folders."""
    root = Path(raw_root)

    if not root.is_dir():
        return []

    discovered: list[Path] = []

    for candidate in sorted(root.iterdir()):
        if not candidate.is_dir():
            continue

        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", candidate.name):
            continue

        try:
            detect_sentinel1_raw_inputs(candidate)
        except (FileNotFoundError, ValueError):
            continue

        discovered.append(candidate)

    return discovered


# ---------------------------------------------------------------------------
# SAR NORMALIZATION & COMPOSITING
# ---------------------------------------------------------------------------


def normalize_sar_to_uint8(
    band: np.ndarray,
    p_low: float = 2.0,
    p_high: float = 98.0,
    is_db: bool = False,
) -> np.ndarray:
    """Normalize SAR amplitude / intensity or dB data to [0, 255] uint8.

    Applies log-transformation to dB if raw amplitude/intensity is passed:
        dB = 10 * log10(band^2 + 1e-6)
    Then performs robust percentile clipping [p_low, p_high] and linear stretching to uint8.
    """
    arr = np.asarray(band, dtype=np.float32)
    valid_mask = np.isfinite(arr) & (arr > 0)

    if not np.any(valid_mask):
        return np.zeros(arr.shape, dtype=np.uint8)

    if not is_db:
        # Convert amplitude / linear power to decibels (dB)
        db_arr = np.zeros_like(arr)
        db_arr[valid_mask] = 10.0 * np.log10(np.square(arr[valid_mask]) + 1e-6)
    else:
        db_arr = arr.copy()

    valid_vals = db_arr[valid_mask]
    low_val = float(np.percentile(valid_vals, p_low))
    high_val = float(np.percentile(valid_vals, p_high))

    if high_val <= low_val:
        normalized = np.clip(db_arr, 0.0, 255.0)
    else:
        stretched = (db_arr - low_val) / (high_val - low_val) * 255.0
        normalized = np.clip(stretched, 0.0, 255.0)

    normalized[~valid_mask] = 0
    return normalized.astype(np.uint8)


def create_sentinel1_sar_composite(
    vv_band: np.ndarray,
    vh_band: np.ndarray,
    p_low: float = 2.0,
    p_high: float = 98.0,
) -> np.ndarray:
    """Create a 3-channel false-color SAR composite from VV and VH polarizations.

    Channels:
      - Channel 1 (R): VV (surface roughness, urban, specular reflection)
      - Channel 2 (G): VH (volume scattering, vegetation, canopy)
      - Channel 3 (B): VV / (VH + eps) ratio or normalized difference for moisture / polarimetric contrast.

    Returns uint8 array of shape (3, H, W).
    """
    norm_vv = normalize_sar_to_uint8(vv_band, p_low=p_low, p_high=p_high)
    norm_vh = normalize_sar_to_uint8(vh_band, p_low=p_low, p_high=p_high)

    # Compute polarimetric ratio VV / (VH + eps) in linear or normalized space
    vv_f = np.asarray(vv_band, dtype=np.float32)
    vh_f = np.asarray(vh_band, dtype=np.float32)
    ratio = np.where((vh_f > 0) & (vv_f > 0), vv_f / (vh_f + 1e-5), 0.0)
    norm_ratio = normalize_sar_to_uint8(ratio, p_low=p_low, p_high=p_high, is_db=False)

    composite = np.stack([norm_vv, norm_vh, norm_ratio], axis=0)
    return composite.astype(np.uint8)


# ---------------------------------------------------------------------------
# TILING & SLICING
# ---------------------------------------------------------------------------


def split_sar_tile_windows(
    width: int,
    height: int,
    tile_size: int = 256,
) -> list[tuple[int, int, Window]]:
    """Compute grid window slices with complete boundary coverage."""
    windows: list[tuple[int, int, Window]] = []
    num_rows = int(np.ceil(height / tile_size))
    num_cols = int(np.ceil(width / tile_size))

    for r in range(num_rows):
        for c in range(num_cols):
            row_off = r * tile_size
            col_off = c * tile_size
            w = min(tile_size, width - col_off)
            h = min(tile_size, height - row_off)
            windows.append((r, c, Window(col_off=col_off, row_off=row_off, width=w, height=h)))

    return windows


def tile_sentinel1_sar(
    composite_array: np.ndarray,
    meta: dict[str, Any],
    output_dir: Path | str,
    date: str,
    tile_size: int = 256,
    overwrite: bool = True,
) -> list[Path]:
    """Slice a 3-channel SAR composite into georeferenced 256x256 GeoTIFF tiles."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    _, height, width = composite_array.shape
    windows = split_sar_tile_windows(width=width, height=height, tile_size=tile_size)
    created_tiles: list[Path] = []

    transform = meta.get("transform")
    crs = meta.get("crs")

    for idx, (r, c, window) in enumerate(windows, start=1):
        tile_filename = f"sentinel1_tile_{idx}.tif"
        tile_filepath = out_path / tile_filename

        if tile_filepath.is_file() and not overwrite:
            created_tiles.append(tile_filepath)
            continue

        tile_data = composite_array[:, int(window.row_off):int(window.row_off + window.height), int(window.col_off):int(window.col_off + window.width)]

        tile_transform = rasterio.windows.transform(window, transform) if transform else None

        tile_profile = {
            "driver": "GTiff",
            "height": int(window.height),
            "width": int(window.width),
            "count": 3,
            "dtype": "uint8",
            "crs": crs,
            "transform": tile_transform,
            "nodata": None,
        }

        with rasterio.open(tile_filepath, "w", **tile_profile) as dst:
            dst.write(tile_data)
            dst.update_tags(
                date=date,
                acquisition_date=date,
                sensor="Sentinel-1",
                polarization="VV, VH, VV/VH ratio",
                provenance="Sentinel-1 C-SAR GRD IW",
                bands="Channel 1: VV, Channel 2: VH, Channel 3: VV/VH ratio",
                tile_row=str(r),
                tile_col=str(c),
            )

        created_tiles.append(tile_filepath)

    return created_tiles


# ---------------------------------------------------------------------------
# INGESTION ENTRYPOINTS
# ---------------------------------------------------------------------------


def ingest_sentinel1_date(
    raw_date_dir: str | Path,
    output_date_dir: str | Path | None = None,
    tile_size: int = 256,
    p_low: float = 2.0,
    p_high: float = 98.0,
    overwrite: bool = True,
    save_full_composite: bool = True,
    force_reindex: bool = False,
    verbose: bool = True,
    client: Any = None,
) -> dict[str, Any]:
    """Ingest one single Sentinel-1 date directory and incrementally index tiles."""
    raw_path = Path(raw_date_dir)
    if not raw_path.is_dir():
        raise FileNotFoundError(f"Directory not found: {raw_path}")

    date_str = extract_acquisition_date(raw_path)
    out_dir = Path(output_date_dir) if output_date_dir is not None else DEFAULT_OUTPUT_TILES_DIR / date_str
    out_dir.mkdir(parents=True, exist_ok=True)

    inputs = detect_sentinel1_raw_inputs(raw_path)

    if inputs["mode"] == "separate_polarizations":
        bands = inputs["bands"]
        with rasterio.open(bands["VV"]) as src_vv, rasterio.open(bands["VH"]) as src_vh:
            vv_data = src_vv.read(1)
            vh_data = src_vh.read(1)
            meta = src_vv.meta.copy()

        composite = create_sentinel1_sar_composite(vv_data, vh_data, p_low=p_low, p_high=p_high)

    elif inputs["mode"] == "sar_composite":
        comp_path = inputs["composite_path"]
        with rasterio.open(comp_path) as src:
            meta = src.meta.copy()
            count = src.count
            if count >= 3:
                b1 = src.read(1)
                b2 = src.read(2)
                b3 = src.read(3)
                composite = np.stack([
                    normalize_sar_to_uint8(b1, p_low, p_high),
                    normalize_sar_to_uint8(b2, p_low, p_high),
                    normalize_sar_to_uint8(b3, p_low, p_high),
                ], axis=0)
            elif count == 2:
                b1 = src.read(1)
                b2 = src.read(2)
                composite = create_sentinel1_sar_composite(b1, b2, p_low, p_high)
            else:
                b1 = src.read(1)
                norm_b1 = normalize_sar_to_uint8(b1, p_low, p_high)
                composite = np.stack([norm_b1, norm_b1, norm_b1], axis=0)
    else:
        raise ValueError(f"Unknown input mode: {inputs['mode']}")

    if save_full_composite:
        full_path = out_dir / "sentinel1_sar_full.tif"
        full_prof = {
            "driver": "GTiff",
            "height": composite.shape[1],
            "width": composite.shape[2],
            "count": 3,
            "dtype": "uint8",
            "crs": meta.get("crs"),
            "transform": meta.get("transform"),
        }
        with rasterio.open(full_path, "w", **full_prof) as dst:
            dst.write(composite)
            dst.update_tags(
                date=date_str,
                sensor="Sentinel-1",
                polarization="VV, VH, VV/VH ratio",
                provenance="Sentinel-1 C-SAR GRD IW",
            )

    tiles = tile_sentinel1_sar(
        composite_array=composite,
        meta=meta,
        output_dir=out_dir,
        date=date_str,
        tile_size=tile_size,
        overwrite=overwrite,
    )

    # Trigger incremental indexer for Sentinel-1
    index_report = index_sentinel1_tiles(
        tiles_dir=out_dir,
        force=force_reindex,
        verbose=verbose,
        client=client,
    )

    return {
        "date": date_str,
        "mode": inputs["mode"],
        "tiles_generated": len(tiles),
        "output_dir": str(out_dir),
        "tiles_new": index_report.get("new", 0),
        "tiles_changed": index_report.get("changed", 0),
        "tiles_unchanged": index_report.get("already_indexed", 0),
        "embeddings_generated": index_report.get("embeddings_generated", 0),
        "qdrant_points_added": index_report.get("qdrant_points_upserted", 0),
        "qdrant_points_updated": 0,
        "failed": index_report.get("failed", 0),
    }


def ingest_new_sentinel1(
    raw_root: str | Path = DEFAULT_RAW_DIR,
    output_root: str | Path = DEFAULT_OUTPUT_TILES_DIR,
    tile_size: int = 256,
    p_low: float = 2.0,
    p_high: float = 98.0,
    overwrite: bool = True,
    save_full_composite: bool = True,
    force_reindex: bool = False,
    verbose: bool = True,
    client: Any = None,
) -> dict[str, Any]:
    """Scan data/raw/sentinel1/, discover all date directories, and incrementally process each date."""
    raw_root_path = Path(raw_root)
    output_root_path = Path(output_root)

    if not raw_root_path.is_dir():
        if verbose:
            print(f"Sentinel-1 raw root directory not found: {raw_root_path}")
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

    date_dirs = discover_sentinel1_date_dirs(raw_root=raw_root_path)
    dates_discovered = len(date_dirs)

    if verbose:
        print("=" * 70)
        print("AUTOMATIC SENTINEL-1 MULTI-DATE INGESTION & INCREMENTAL INDEXER")
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
            print(f"\n[{idx}/{dates_discovered}] Checking Sentinel-1 Date: {date_str} ...")

        report = ingest_sentinel1_date(
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
        print("ALL SENTINEL-1 DATES INGESTION COMPLETED")
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
    "REQUIRED_POLARIZATIONS",
    "extract_acquisition_date",
    "find_sentinel1_bands",
    "find_sentinel1_composite_image",
    "detect_sentinel1_raw_inputs",
    "discover_sentinel1_date_dirs",
    "normalize_sar_to_uint8",
    "create_sentinel1_sar_composite",
    "split_sar_tile_windows",
    "tile_sentinel1_sar",
    "ingest_sentinel1_date",
    "ingest_new_sentinel1",
]
