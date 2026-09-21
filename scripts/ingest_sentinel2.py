"""
scripts/ingest_sentinel2.py — End-to-End Sentinel-2 Ingestion & Incremental Indexer CLI
========================================================================================
Usage:
  # Ingest a single raw Sentinel-2 date directory:
  python -m scripts.ingest_sentinel2 data/raw/sentinel2/2026-09-10

  # With options:
  python -m scripts.ingest_sentinel2 data/raw/sentinel2/2026-09-10 --tile-size 256 --force
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from semantic_search.sentinel2 import ingest_sentinel2_date


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="TriNetraAI — End-to-end Sentinel-2 Raw Ingestion & Incremental Indexing"
    )
    parser.add_argument(
        "raw_dir",
        type=Path,
        nargs="?",
        default=None,
        help="Path to date-wise raw Sentinel-2 directory containing B02, B03, B04, B08 TIFFs",
    )
    parser.add_argument(
        "--raw-dir",
        dest="raw_dir_opt",
        type=Path,
        default=None,
        help="Explicit flag for raw Sentinel-2 directory",
    )
    parser.add_argument(
        "--output-dir",
        "--output-date-dir",
        dest="output_dir",
        type=Path,
        default=None,
        help="Optional custom output directory for date-wise tiles",
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

    raw_dir = args.raw_dir or args.raw_dir_opt
    if raw_dir is None:
        parser.print_help()
        print("\n[ERROR] Please specify a raw Sentinel-2 date directory.", file=sys.stderr)
        return 1

    try:
        stats = ingest_sentinel2_date(
            raw_date_dir=raw_dir,
            output_date_dir=args.output_dir,
            tile_size=args.tile_size,
            force_reindex=args.force,
            verbose=not args.quiet,
        )

        if not args.quiet:
            print("\n" + "=" * 60)
            print("INGESTION & INDEXING SUMMARY")
            print("=" * 60)
            print(f"Date                 : {stats['date']}")
            print(f"Raw Directory        : {stats['raw_directory']}")
            print(f"Tile Directory       : {stats['tile_directory']}")
            print(f"Tiles Discovered     : {stats['tiles_discovered']}")
            print(f"New Tiles (Embedded) : {stats['tiles_new']}")
            print(f"Unchanged (Skipped)  : {stats['tiles_unchanged']}")
            print(f"Changed (Updated)    : {stats['tiles_changed']}")
            print(f"Embeddings Generated : {stats['embeddings_generated']}")
            print(f"Qdrant Points Added  : {stats['qdrant_points_added']}")
            print(f"Qdrant Points Updated: {stats['qdrant_points_updated']}")
            print(f"Failures             : {stats['failed']}")
            print("=" * 60)

        if stats.get("failed", 0) > 0:
            return 1
        return 0

    except Exception as exc:
        print(f"\n[ERROR] Ingestion failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
