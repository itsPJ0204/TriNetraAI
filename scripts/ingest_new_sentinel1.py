"""
scripts/ingest_new_sentinel1.py — Automatic Multi-Date Sentinel-1 Incremental Ingestion CLI
============================================================================================
Usage:
  # Scan data/raw/sentinel1/, auto-discover all date folders, and process only new/changed dates/tiles:
  python -m scripts.ingest_new_sentinel1

  # Custom options:
  python -m scripts.ingest_new_sentinel1 --raw-root data/raw/sentinel1 --tile-size 256
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from semantic_search.sentinel1 import (
    DEFAULT_OUTPUT_TILES_DIR,
    DEFAULT_RAW_DIR,
    ingest_new_sentinel1,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="TriNetraAI — Automatic Multi-Date Sentinel-1 Incremental Ingestion & Indexing"
    )
    parser.add_argument(
        "--raw-root",
        type=Path,
        default=DEFAULT_RAW_DIR,
        help="Root directory containing Sentinel-1 date folders (default: data/raw/sentinel1)",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT_TILES_DIR,
        help="Root directory for date-wise output tiles (default: data/tiles/sentinel1)",
    )
    parser.add_argument(
        "--tile-size",
        type=int,
        default=256,
        help="Tile dimension in pixels (default: 256)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-embedding and re-indexing of tiles even if unchanged",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress detailed console logging",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        stats = ingest_new_sentinel1(
            raw_root=args.raw_root,
            output_root=args.output_root,
            tile_size=args.tile_size,
            force_reindex=args.force,
            verbose=not args.quiet,
        )

        if not args.quiet:
            print("\n" + "=" * 60)
            print("AUTOMATIC SENTINEL-1 MULTI-DATE INGESTION SUMMARY")
            print("=" * 60)
            print(f"Dates Discovered     : {stats['dates_discovered']}")
            print(f"Dates Processed      : {stats['dates_processed']}")
            print(f"Dates Skipped        : {stats['dates_skipped']}")
            print(f"Tiles New (Embedded) : {stats['tiles_new']}")
            print(f"Tiles Changed        : {stats['tiles_changed']}")
            print(f"Tiles Unchanged      : {stats['tiles_unchanged']}")
            print(f"Embeddings Generated : {stats['embeddings_generated']}")
            print(f"Qdrant Points Added  : {stats['qdrant_points_added']}")
            print(f"Qdrant Points Updated: {stats['qdrant_points_updated']}")
            print(f"Failures             : {stats['failed']}")
            print("=" * 60)

        if stats.get("failed", 0) > 0:
            return 1
        return 0

    except Exception as exc:
        print(f"\n[ERROR] Sentinel-1 multi-date ingestion failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
