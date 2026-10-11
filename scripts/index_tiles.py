"""
scripts/index_tiles.py — Unified Multi-Sensor Satellite Tile Indexing CLI
========================================================================
Usage:
  # 1. Index all sensors (Sentinel-2 Optical & Sentinel-1 SAR):
  python -m scripts.index_tiles --sensor all --force

  # 2. Index only Sentinel-1 SAR:
  python -m scripts.index_tiles --sensor sentinel1 --force

  # 3. Index only Sentinel-2 Optical:
  python -m scripts.index_tiles --sensor sentinel2 --force
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from semantic_search.indexer import index_satellite_tiles
from semantic_search.sentinel1_indexer import index_sentinel1_tiles


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="TriNetraAI — Unified Multi-Sensor Tile Indexer for Qdrant Vector DB"
    )
    parser.add_argument(
        "--sensor",
        type=str,
        default="all",
        choices=["sentinel2", "sentinel1", "all"],
        help="Sensor archive to index: 'sentinel2', 'sentinel1', or 'all' (default: all)",
    )
    parser.add_argument(
        "--tiles-dir",
        type=Path,
        default=None,
        help="Optional custom root directory containing tiles",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-generation/upsert of embeddings into Qdrant",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress detailed progress logging",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    failed_total = 0
    verbose = not args.quiet

    # Index Sentinel-2
    if args.sensor in ("sentinel2", "all"):
        if verbose:
            print("\n" + "=" * 60)
            print("[*] Indexing Sentinel-2 Optical Tiles...")
            print("=" * 60)
        try:
            s2_dir = args.tiles_dir or Path("data/tiles/sentinel2")
            stats = index_satellite_tiles(
                tiles_dir=s2_dir,
                force=args.force,
                verbose=verbose,
            )
            failed_total += stats.get("failed", 0)
        except Exception as exc:
            print(f"[ERROR] Sentinel-2 Indexing Failed: {exc}", file=sys.stderr)
            failed_total += 1

    # Index Sentinel-1
    if args.sensor in ("sentinel1", "all"):
        if verbose:
            print("\n" + "=" * 60)
            print("[*] Indexing Sentinel-1 Radar (SAR) Tiles...")
            print("=" * 60)
        try:
            s1_dir = args.tiles_dir or Path("data/tiles/sentinel1")
            stats_s1 = index_sentinel1_tiles(
                tiles_dir=s1_dir,
                force=args.force,
                verbose=verbose,
            )
            failed_total += stats_s1.get("failed", 0)
        except Exception as exc:
            print(f"[ERROR] Sentinel-1 Indexing Failed: {exc}", file=sys.stderr)
            failed_total += 1

    if failed_total > 0:
        print(f"\n[WARN] Indexing completed with {failed_total} total failure(s).")
        return 1

    if verbose:
        print("\n[SUCCESS] All requested satellite sensor tiles successfully indexed into Qdrant!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
