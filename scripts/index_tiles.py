"""
scripts/index_tiles.py — Command-Line Interface for Incremental Satellite Tile Indexing
=======================================================================================
Usage:
  # 1. First run / incremental update (only embeds and indexes new or changed tiles):
  python -m scripts.index_tiles

  # 2. Optional forced re-indexing (re-embeds all discovered tiles):
  python -m scripts.index_tiles --force

  # 3. Custom tiles directory:
  python -m scripts.index_tiles --tiles-dir data/tiles/sentinel2
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from semantic_search.indexer import index_satellite_tiles


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="TriNetraAI — Incremental Satellite Tile Indexer for Qdrant Vector DB"
    )
    parser.add_argument(
        "--tiles-dir",
        type=Path,
        default=None,
        help="Optional root directory containing date-wise tile folders (default: auto-discovery)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-generation of embeddings and overwrite existing Qdrant points",
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

    try:
        stats = index_satellite_tiles(
            tiles_dir=args.tiles_dir,
            force=args.force,
            verbose=not args.quiet,
        )
        if stats.get("failed", 0) > 0:
            print(f"[WARN] Completed with {stats['failed']} failure(s).")
            return 1
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
