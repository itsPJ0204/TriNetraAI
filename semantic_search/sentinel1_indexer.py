"""
semantic_search/sentinel1_indexer.py — Sentinel-1 SAR Incremental Tile Indexer
=============================================================================
Dedicated incremental indexer for Sentinel-1 C-SAR dual-pol tiles:
  - Collection: 'sentinel1_tiles' (isolated from 'satellite_tiles')
  - Deterministic stable tile identities: sentinel1:{date}:{normalized_relative_path}
  - Deterministic Qdrant point IDs: UUIDv5("trinetra:sentinel1:{date}:{rel_path}")
  - SHA-256 fingerprinting for change detection
  - Dedicated persistent manifest: data/embeddings/sentinel1_indexing_manifest.json
  - Dedicated cache: data/embeddings/sentinel1_embeddings_cache.npz
  - Incremental execution: unchanged tiles are skipped with 0 re-embedding
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
from qdrant_client import QdrantClient, models
import rasterio

from semantic_search.sentinel1_model import (
    extract_sentinel1_image_embedding,
    load_sentinel1_model,
)
from semantic_search.vector_store import get_qdrant_client


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SENTINEL1_COLLECTION_NAME = "sentinel1_tiles"
DEFAULT_TILES_DIR = PROJECT_ROOT / "data" / "tiles" / "sentinel1"
EMBEDDINGS_DIR = PROJECT_ROOT / "data" / "embeddings"

S1_MANIFEST_PATH = EMBEDDINGS_DIR / "sentinel1_indexing_manifest.json"
S1_EMBEDDINGS_NPY_PATH = EMBEDDINGS_DIR / "sentinel1_image_embeddings.npy"
S1_IMAGE_PATHS_JSON_PATH = EMBEDDINGS_DIR / "sentinel1_image_paths.json"
S1_EMBEDDINGS_CACHE_NPZ_PATH = EMBEDDINGS_DIR / "sentinel1_embeddings_cache.npz"


def compute_file_fingerprint(filepath: Path | str) -> str:
    """Compute SHA-256 checksum of a file in 64KB chunks."""
    path = Path(filepath)
    if not path.is_file():
        raise FileNotFoundError(f"File not found for fingerprint: {path}")

    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def find_sentinel1_tiles(
    tiles_dir: Path | str | None = None,
) -> list[Path]:
    """Find all Sentinel-1 GeoTIFF tiles across date subdirectories."""
    root = Path(tiles_dir) if tiles_dir is not None else DEFAULT_TILES_DIR
    if not root.is_dir():
        return []

    discovered: list[Path] = []
    for ext in ("*.tif", "*.tiff"):
        for f in root.rglob(ext):
            # Skip full composites / scenes if standard 256x256 tiles are preferred
            # or keep all valid raster tiles
            if f.is_file():
                discovered.append(f)

    # Sort deterministically
    return sorted(discovered, key=lambda p: p.as_posix())


def extract_sentinel1_tile_metadata_and_identity(image_path: Path | str) -> dict[str, Any]:
    """Extract CRS, bounds, metadata tags, stable tile ID, point ID, and file fingerprint."""
    path = PROJECT_ROOT / image_path if not Path(image_path).is_absolute() else Path(image_path)
    if not path.is_file():
        raise FileNotFoundError(f"Sentinel-1 tile file not found: {path}")

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

    # Determine date
    date_val = tags.get("date") or tags.get("acquisition_date")
    if not date_val:
        m = re.search(r"(\d{4}-\d{2}-\d{2})", path.as_posix())
        date_val = m.group(1) if m else "2026-01-01"

    stable_tile_id = f"sentinel1:{date_val}:{rel_path}"
    point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"trinetra:{stable_tile_id}"))
    fingerprint = compute_file_fingerprint(path)

    return {
        "tile_id": stable_tile_id,
        "point_id": point_id,
        "relative_path": rel_path,
        "tile_name": path.name,
        "sensor": "sentinel1",
        "date": date_val,
        "crs": crs_str,
        "bounds": bounds,
        "width": width,
        "height": height,
        "tags": tags,
        "fingerprint": fingerprint,
        "filepath": str(path.resolve()),
    }


def load_sentinel1_manifest() -> dict[str, Any]:
    """Load persistent Sentinel-1 manifest JSON."""
    if not S1_MANIFEST_PATH.is_file():
        return {
            "version": 1,
            "collection_name": SENTINEL1_COLLECTION_NAME,
            "updated_at": None,
            "tiles": {},
        }
    try:
        data = json.loads(S1_MANIFEST_PATH.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or "tiles" not in data:
            return {
                "version": 1,
                "collection_name": SENTINEL1_COLLECTION_NAME,
                "updated_at": None,
                "tiles": {},
            }
        return data
    except Exception:
        return {
            "version": 1,
            "collection_name": SENTINEL1_COLLECTION_NAME,
            "updated_at": None,
            "tiles": {},
        }


def save_sentinel1_manifest(manifest: dict[str, Any]) -> None:
    """Save persistent Sentinel-1 manifest JSON atomically."""
    EMBEDDINGS_DIR.mkdir(parents=True, exist_ok=True)
    manifest["updated_at"] = datetime.now(timezone.utc).isoformat()
    temp_path = S1_MANIFEST_PATH.with_suffix(".tmp")
    temp_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    temp_path.replace(S1_MANIFEST_PATH)


def load_sentinel1_cached_embeddings() -> dict[str, np.ndarray]:
    """Load cached Sentinel-1 vectors from sentinel1_embeddings_cache.npz."""
    if not S1_EMBEDDINGS_CACHE_NPZ_PATH.is_file():
        return {}
    try:
        with np.load(S1_EMBEDDINGS_CACHE_NPZ_PATH) as data:
            return {k: data[k].astype(np.float32) for k in data.files}
    except Exception:
        return {}


def save_sentinel1_cached_embeddings(cache: dict[str, np.ndarray]) -> None:
    """Save Sentinel-1 cached embeddings and sync matrices."""
    EMBEDDINGS_DIR.mkdir(parents=True, exist_ok=True)
    if cache:
        np.savez_compressed(S1_EMBEDDINGS_CACHE_NPZ_PATH, **cache)
        keys = sorted(cache.keys())
        matrix = np.stack([cache[k] for k in keys]).astype(np.float32, copy=False)
        manifest = load_sentinel1_manifest()
        paths = [
            manifest.get("tiles", {}).get(k, {}).get("relative_path", k)
            for k in keys
        ]
        np.save(S1_EMBEDDINGS_NPY_PATH, matrix)
        S1_IMAGE_PATHS_JSON_PATH.write_text(json.dumps(paths, indent=2), encoding="utf-8")


def create_sentinel1_collection_if_needed(
    client: QdrantClient,
    vector_dimension: int = 512,
) -> None:
    """Ensure the 'sentinel1_tiles' cosine-distance collection exists in Qdrant."""
    if not client.collection_exists(SENTINEL1_COLLECTION_NAME):
        client.create_collection(
            collection_name=SENTINEL1_COLLECTION_NAME,
            vectors_config=models.VectorParams(
                size=vector_dimension,
                distance=models.Distance.COSINE,
            ),
        )
        return

    collection = client.get_collection(SENTINEL1_COLLECTION_NAME)
    configured_dimension = collection.config.params.vectors.size
    if configured_dimension != vector_dimension:
        raise ValueError(
            f"Collection '{SENTINEL1_COLLECTION_NAME}' dimension is {configured_dimension}, "
            f"expected {vector_dimension}."
        )


def index_sentinel1_tiles(
    tiles_dir: Path | str | None = None,
    force: bool = False,
    verbose: bool = True,
    client: QdrantClient | None = None,
) -> dict[str, Any]:
    """
    Incremental Sentinel-1 Tile Indexer:
      1. Discovers all Sentinel-1 GeoTIFF tiles.
      2. Compares stable tile identity & SHA-256 fingerprint against manifest.
      3. Skips unchanged tiles without re-embedding.
      4. Embeds only new or modified SAR tiles into 512-D vectors.
      5. Upserts points into the Qdrant 'sentinel1_tiles' collection.
      6. Updates the persistent manifest and cache.
    """
    if client is None:
        client = get_qdrant_client()

    create_sentinel1_collection_if_needed(client, vector_dimension=512)

    discovered_paths = find_sentinel1_tiles(tiles_dir=tiles_dir)
    discovered_count = len(discovered_paths)

    if verbose:
        print("=" * 60)
        print("TRINETRA-AI SENTINEL-1 INCREMENTAL TILE INDEXER")
        print("=" * 60)
        print(f"Target Collection : {SENTINEL1_COLLECTION_NAME}")
        print(f"Force Re-index    : {force}")
        print(f"Discovered Tiles  : {discovered_count}")

    if discovered_count == 0:
        if verbose:
            print("No Sentinel-1 tiles found to index.")
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

    manifest = load_sentinel1_manifest()
    manifest_tiles = manifest.setdefault("tiles", {})
    cache = load_sentinel1_cached_embeddings()

    tiles_to_process: list[dict[str, Any]] = []
    already_indexed = 0
    new_tiles = 0
    changed_tiles = 0

    for path in discovered_paths:
        try:
            meta = extract_sentinel1_tile_metadata_and_identity(path)
            tile_id = meta["tile_id"]
            existing = manifest_tiles.get(tile_id)

            if not force and existing is not None:
                if existing.get("fingerprint") == meta["fingerprint"] and tile_id in cache:
                    already_indexed += 1
                    continue
                else:
                    changed_tiles += 1
                    tiles_to_process.append({"meta": meta, "is_new": False})
            else:
                new_tiles += 1
                tiles_to_process.append({"meta": meta, "is_new": True})
        except Exception as exc:
            if verbose:
                print(f"[WARN] Error inspecting Sentinel-1 tile {path}: {exc}")

    if verbose:
        print(f"Status: {already_indexed} unchanged, {new_tiles} new, {changed_tiles} modified")

    if not tiles_to_process:
        if verbose:
            print("All Sentinel-1 tiles are up to date. Zero embedding / indexing needed.")
        return {
            "discovered": discovered_count,
            "already_indexed": already_indexed,
            "new": 0,
            "changed": 0,
            "embeddings_generated": 0,
            "qdrant_points_upserted": 0,
            "skipped": already_indexed,
            "failed": 0,
        }

    # Generate embeddings and upsert
    embeddings_generated = 0
    points_upserted = 0
    failed = 0

    for item in tiles_to_process:
        meta = item["meta"]
        tile_id = meta["tile_id"]
        point_id = meta["point_id"]
        filepath = meta["filepath"]

        try:
            emb = extract_sentinel1_image_embedding(filepath)
            embeddings_generated += 1

            payload = {
                "tile_id": tile_id,
                "tile_name": meta["tile_name"],
                "image_path": meta["relative_path"],
                "sensor": "sentinel1",
                "date": meta["date"],
                "crs": meta["crs"],
                "bounds": meta["bounds"],
                "width": meta["width"],
                "height": meta["height"],
                "provenance": meta["tags"].get("provenance", "Sentinel-1 C-SAR GRD IW"),
                "polarization": meta["tags"].get("polarization", "VV, VH, VV/VH ratio"),
                "bands": meta["tags"].get("bands", "VV, VH, VV/VH ratio"),
            }

            client.upsert(
                collection_name=SENTINEL1_COLLECTION_NAME,
                points=[
                    models.PointStruct(
                        id=point_id,
                        vector=emb.tolist(),
                        payload=payload,
                    )
                ],
                wait=True,
            )
            points_upserted += 1

            # Update cache and manifest
            cache[tile_id] = emb
            manifest_tiles[tile_id] = {
                "point_id": point_id,
                "relative_path": meta["relative_path"],
                "sensor": "sentinel1",
                "date": meta["date"],
                "fingerprint": meta["fingerprint"],
                "crs": meta["crs"],
                "bounds": meta["bounds"],
                "width": meta["width"],
                "height": meta["height"],
                "indexed_at": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as exc:
            failed += 1
            if verbose:
                print(f"[ERROR] Failed to process Sentinel-1 tile {filepath}: {exc}")

    save_sentinel1_manifest(manifest)
    save_sentinel1_cached_embeddings(cache)

    summary = {
        "discovered": discovered_count,
        "already_indexed": already_indexed,
        "new": new_tiles,
        "changed": changed_tiles,
        "embeddings_generated": embeddings_generated,
        "qdrant_points_upserted": points_upserted,
        "skipped": already_indexed,
        "failed": failed,
    }

    if verbose:
        print("-" * 60)
        print(f"Sentinel-1 Indexing Complete:")
        print(f"  - Points Upserted: {points_upserted}")
        print(f"  - Skipped        : {already_indexed}")
        print(f"  - Failed         : {failed}")
        print("=" * 60)

    return summary
