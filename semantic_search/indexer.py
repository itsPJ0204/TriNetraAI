"""
semantic_search/indexer.py — True Incremental Satellite Tile Indexer
=====================================================================
Features:
  - Automatic discovery of date-wise tile folders (data/tiles/sentinel2/YYYY-MM-DD/, sample_pairs/, etc.)
  - Deterministic stable tile identities: {sensor}:{date}:{normalized_relative_path}
  - Deterministic Qdrant point IDs (UUIDv5)
  - Fast SHA-256 file fingerprinting for instant content-change detection
  - Zero re-embedding / re-indexing for unchanged tiles
  - Idempotent execution
  - Partial failure resilience
  - Synchronization with indexing_manifest.json and legacy embedding caches
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any
import uuid

import numpy as np
from qdrant_client import models
import rasterio

from semantic_search.embeddings import (
    PROJECT_ROOT,
    find_satellite_tiles,
    image_to_embedding,
)
from semantic_search.model import load_remoteclip
from semantic_search.vector_store import (
    COLLECTION_NAME,
    DEFAULT_SCENE_DATE,
    create_collection_if_needed,
    get_qdrant_client,
)

EMBEDDINGS_DIR = PROJECT_ROOT / "data" / "embeddings"
MANIFEST_PATH = EMBEDDINGS_DIR / "indexing_manifest.json"
EMBEDDINGS_NPY_PATH = EMBEDDINGS_DIR / "image_embeddings.npy"
IMAGE_PATHS_JSON_PATH = EMBEDDINGS_DIR / "image_paths.json"
EMBEDDINGS_CACHE_NPZ_PATH = EMBEDDINGS_DIR / "tile_embeddings_cache.npz"


def compute_file_fingerprint(filepath: Path | str) -> str:
    """Compute SHA-256 checksum of a file in chunks."""
    path = Path(filepath)
    if not path.is_file():
        raise FileNotFoundError(f"File not found for fingerprint: {path}")

    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def extract_sensor_name(path: Path) -> str:
    """Infer satellite sensor / source from file path."""
    posix = path.as_posix().lower()
    if "sentinel2" in posix or "sentinel-2" in posix or "s2" in posix:
        return "sentinel2"
    if "landsat" in posix:
        return "landsat"
    if "planet" in posix:
        return "planetscope"
    return "sentinel2"


def extract_tile_date(path: Path, tags: dict[str, Any] | None = None) -> str:
    """Extract acquisition date (YYYY-MM-DD or YYYY-MM) from metadata tags, folder hierarchy, or filename."""
    if tags:
        for k in ("date", "acquisition_date", "datetime", "sensing_date", "sensing_time"):
            val = tags.get(k)
            if val:
                match = re.search(r"(\d{4}-\d{2}-\d{2})", str(val))
                if match:
                    return match.group(1)

    for parent in [path.parent, path.parent.parent]:
        match = re.search(r"(\d{4}-\d{2}-\d{2})", parent.name)
        if match:
            return match.group(1)
        match_my = re.search(r"(\d{4}[-_]\d{2})", parent.name)
        if match_my:
            return match_my.group(1).replace("_", "-")

    match = re.search(r"(\d{4}-\d{2}-\d{2})", path.stem)
    if match:
        return match.group(1)
    match_fn = re.search(r"(\d{4}[-_]\d{2})", path.stem)
    if match_fn:
        return match_fn.group(1).replace("_", "-")

    match_yr = re.search(r"year_(\d+)", path.as_posix().lower())
    if match_yr:
        yr = int(match_yr.group(1))
        return f"202{3 + yr}-01-01"

    return DEFAULT_SCENE_DATE


def extract_tile_metadata_and_identity(image_path: Path | str) -> dict[str, Any]:
    """Extract geospatial metadata, CRS, bounds, stable tile ID, point ID, and file fingerprint."""
    path = PROJECT_ROOT / image_path if not Path(image_path).is_absolute() else Path(image_path)
    if not path.is_file():
        raise FileNotFoundError(f"Tile image file not found: {path}")

    try:
        rel_path = path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError:
        rel_path = path.as_posix()

    with rasterio.open(path) as src:
        crs_str = str(src.crs) if src.crs else "EPSG:4326"
        bounds = {
            "left": float(src.bounds.left),
            "bottom": float(src.bounds.bottom),
            "right": float(src.bounds.right),
            "top": float(src.bounds.top),
        }
        width = int(src.width)
        height = int(src.height)
        tags = src.tags()

    sensor = extract_sensor_name(path)
    date = extract_tile_date(path, tags)
    stable_tile_id = f"{sensor}:{date}:{rel_path}"
    point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"trinetra:{stable_tile_id}"))
    fingerprint = compute_file_fingerprint(path)

    return {
        "tile_id": stable_tile_id,
        "point_id": point_id,
        "relative_path": rel_path,
        "tile_name": path.name,
        "sensor": sensor,
        "date": date,
        "crs": crs_str,
        "bounds": bounds,
        "width": width,
        "height": height,
        "tags": tags,
        "fingerprint": fingerprint,
        "filepath": str(path.resolve()),
    }


def load_indexing_manifest() -> dict[str, Any]:
    """Load the persistent indexing manifest JSON from disk."""
    if not MANIFEST_PATH.is_file():
        return {
            "version": 1,
            "collection_name": COLLECTION_NAME,
            "updated_at": None,
            "tiles": {},
        }
    try:
        data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or "tiles" not in data:
            return {
                "version": 1,
                "collection_name": COLLECTION_NAME,
                "updated_at": None,
                "tiles": {},
            }
        return data
    except Exception:
        return {
            "version": 1,
            "collection_name": COLLECTION_NAME,
            "updated_at": None,
            "tiles": {},
        }


def save_indexing_manifest(manifest: dict[str, Any]) -> None:
    """Save the persistent indexing manifest JSON atomically to disk."""
    EMBEDDINGS_DIR.mkdir(parents=True, exist_ok=True)
    manifest["updated_at"] = datetime.now(timezone.utc).isoformat()
    temp_path = MANIFEST_PATH.with_suffix(".tmp")
    temp_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    temp_path.replace(MANIFEST_PATH)


def load_cached_embeddings() -> dict[str, np.ndarray]:
    """Load previously saved embedding vectors from tile_embeddings_cache.npz."""
    if not EMBEDDINGS_CACHE_NPZ_PATH.is_file():
        return {}
    try:
        with np.load(EMBEDDINGS_CACHE_NPZ_PATH) as data:
            return {k: data[k].astype(np.float32) for k in data.files}
    except Exception:
        return {}


def save_cached_embeddings(cache: dict[str, np.ndarray]) -> None:
    """Save all current embeddings into tile_embeddings_cache.npz and sync legacy .npy."""
    EMBEDDINGS_DIR.mkdir(parents=True, exist_ok=True)
    if cache:
        np.savez_compressed(EMBEDDINGS_CACHE_NPZ_PATH, **cache)

        keys = sorted(cache.keys())
        matrix = np.stack([cache[k] for k in keys]).astype(np.float32, copy=False)
        manifest = load_indexing_manifest()
        paths = [
            manifest.get("tiles", {}).get(k, {}).get("relative_path", k)
            for k in keys
        ]
        np.save(EMBEDDINGS_NPY_PATH, matrix)
        IMAGE_PATHS_JSON_PATH.write_text(json.dumps(paths, indent=2), encoding="utf-8")


def index_satellite_tiles(
    tiles_dir: Path | str | None = None,
    force: bool = False,
    verbose: bool = True,
) -> dict[str, Any]:
    """
    True Incremental Satellite Tile Indexer:
      1. Discovers all date-wise GeoTIFF tiles recursively.
      2. Compares stable tile identity & SHA-256 fingerprint against the manifest.
      3. Skips unchanged, already-indexed tiles without re-embedding.
      4. Embeds only new or modified tiles using RemoteCLIP ViT-B-32.
      5. Upserts points into the Qdrant 'satellite_tiles' collection.
      6. Updates the persistent manifest and synced embedding matrices.
    """
    client = get_qdrant_client()
    create_collection_if_needed(client, vector_dimension=512)

    discovered_paths = find_satellite_tiles(tiles_dir=tiles_dir)
    discovered_count = len(discovered_paths)

    if verbose:
        print("=" * 60)
        print("TRINETRA-AI INCREMENTAL TILE INDEXER")
        print("=" * 60)
        print(f"Target Collection : {COLLECTION_NAME}")
        print(f"Force Re-index    : {force}")
        print(f"Discovered Tiles  : {discovered_count}")

    if discovered_count == 0:
        if verbose:
            print("No tiles found to index.")
        return {
            "discovered": 0,
            "already_indexed": 0,
            "new": 0,
            "changed": 0,
            "embeddings_generated": 0,
            "qdrant_points_upserted": 0,
            "skipped": 0,
            "failed": 0,
        }

    manifest = load_indexing_manifest()
    manifest_tiles = manifest.setdefault("tiles", {})
    embeddings_cache = load_cached_embeddings()

    to_process: list[dict[str, Any]] = []
    already_indexed_count = 0
    new_count = 0
    changed_count = 0

    for path in discovered_paths:
        try:
            meta = extract_tile_metadata_and_identity(path)
        except Exception as err:
            if verbose:
                print(f"[WARN] Failed to read metadata for {path}: {err}")
            continue

        tile_id = meta["tile_id"]
        fingerprint = meta["fingerprint"]

        if not force and tile_id in manifest_tiles:
            cached_meta = manifest_tiles[tile_id]
            if cached_meta.get("fingerprint") == fingerprint and tile_id in embeddings_cache:
                already_indexed_count += 1
                continue
            else:
                meta["is_changed"] = True
                changed_count += 1
                to_process.append(meta)
        else:
            meta["is_changed"] = False
            new_count += 1
            to_process.append(meta)

    if verbose:
        print(f"Already Indexed   : {already_indexed_count}")
        print(f"New Tiles         : {new_count}")
        print(f"Changed Tiles     : {changed_count}")
        print(f"Pending Embedding : {len(to_process)}")
        print("-" * 60)

    if len(to_process) == 0:
        if verbose:
            print("[SUCCESS] All tiles are already up to date. Zero new embeddings needed.")
            print("=" * 60)
        return {
            "discovered": discovered_count,
            "already_indexed": already_indexed_count,
            "new": 0,
            "changed": 0,
            "embeddings_generated": 0,
            "qdrant_points_upserted": 0,
            "skipped": already_indexed_count,
            "failed": 0,
        }

    if verbose:
        print("[INIT] Loading RemoteCLIP model for new embeddings...")
    model, _, preprocess = load_remoteclip(device="cpu")

    embeddings_generated = 0
    qdrant_points_upserted = 0
    failed_count = 0

    for idx, meta in enumerate(to_process, start=1):
        tile_path = Path(meta["filepath"])
        tile_id = meta["tile_id"]
        point_id = meta["point_id"]
        action = "Updating changed" if meta.get("is_changed") else "Embedding new"

        if verbose:
            print(f"[{idx}/{len(to_process)}] {action} tile: {meta['relative_path']}")

        try:
            embedding = image_to_embedding(tile_path, model=model, preprocess=preprocess)
            embeddings_generated += 1

            tags = meta.get("tags", {})
            payload = {
                "tile_id": tile_id,
                "image_path": meta["relative_path"],
                "tile_name": meta["tile_name"],
                "crs": meta["crs"],
                "bounds": meta["bounds"],
                "width": meta["width"],
                "height": meta["height"],
                "date": meta["date"],
                "sensor": meta["sensor"],
                "fingerprint": meta["fingerprint"],
                "provenance": tags.get("provenance", "Sentinel-2 L2A"),
                "r_band": tags.get("r_band", "B04"),
                "g_band": tags.get("g_band", "B03"),
                "b_band": tags.get("b_band", "B02"),
                "bands": "B04 (Red), B03 (Green), B02 (Blue)",
            }

            client.upsert(
                collection_name=COLLECTION_NAME,
                points=[
                    models.PointStruct(
                        id=point_id,
                        vector=embedding.tolist(),
                        payload=payload,
                    )
                ],
                wait=True,
            )
            qdrant_points_upserted += 1

            manifest_tiles[tile_id] = {
                "tile_id": tile_id,
                "point_id": point_id,
                "relative_path": meta["relative_path"],
                "tile_name": meta["tile_name"],
                "sensor": meta["sensor"],
                "date": meta["date"],
                "fingerprint": meta["fingerprint"],
                "indexed_at": datetime.now(timezone.utc).isoformat(),
            }
            embeddings_cache[tile_id] = embedding

        except Exception as err:
            failed_count += 1
            if verbose:
                print(f"  ERROR processing {tile_path.name}: {err}")

    save_indexing_manifest(manifest)
    save_cached_embeddings(embeddings_cache)

    stored_total = client.count(COLLECTION_NAME, exact=True).count

    if verbose:
        print("=" * 60)
        print("INCREMENTAL INDEXING COMPLETED")
        print("=" * 60)
        print(f"Discovered tiles             : {discovered_count}")
        print(f"Already indexed (skipped)    : {already_indexed_count}")
        print(f"New tiles                    : {new_count}")
        print(f"Changed tiles                : {changed_count}")
        print(f"Embeddings generated         : {embeddings_generated}")
        print(f"Qdrant points added/updated  : {qdrant_points_upserted}")
        print(f"Failed                       : {failed_count}")
        print(f"Total points in Qdrant       : {stored_total}")
        print("=" * 60)

    return {
        "discovered": discovered_count,
        "already_indexed": already_indexed_count,
        "new": new_count,
        "changed": changed_count,
        "embeddings_generated": embeddings_generated,
        "qdrant_points_upserted": qdrant_points_upserted,
        "skipped": already_indexed_count,
        "failed": failed_count,
        "total_in_qdrant": stored_total,
    }
