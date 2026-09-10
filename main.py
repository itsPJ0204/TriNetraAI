"""
main.py — TriNetraAI Unified Command-Line Interface (CLI)
==========================================================
Unifies all 5 team roles:
  1. Ingest (Role 1 — Ingestion & SQLite Spatial Registry)
  2. Search (Role 2 — Semantic AI RemoteCLIP & Qdrant Search)
  3. Compare (Role 3 & Role 4 — Temporal Detective + JIT QA False-Alarm Suppression)
  4. Cluster (Role 4 — K-Means Terrain Similarity Clustering)
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from ingestion.db import DEFAULT_DB_PATH, init_db
from ingestion.ingest import add_image, add_band_folder, export_metadata_csv
from spatial.queries import get_all_tiles, get_tile, get_tiles_by_bbox, get_temporal_pair


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="TriNetraAI — Unified Satellite Search, QA Filtering & Change Detective Platform"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # 1. Ingestion Commands (Role 1)
    sub.add_parser("init-db", help="Initialize the local SQLite spatial metadata registry")
    
    ingest = sub.add_parser("ingest", help="Ingest a multi-band GeoTIFF scene and generate 512x512 tiles")
    ingest.add_argument("filepath", type=Path, help="Path to input .tif or .tiff scene")
    ingest.add_argument("--tile-size", type=int, default=512, help="Patch size in pixels (default: 512)")
    ingest.add_argument("--csv", type=Path, default=None, help="Custom export path for tiles_metadata.csv")

    folder = sub.add_parser("ingest-folder", help="Ingest a Bhuvan scene folder containing band sub-files")
    folder.add_argument("folder", type=Path, help="Path to folder containing band GeoTIFFs")
    folder.add_argument("--date", default=None, help="Acquisition timestamp, e.g. 2024-06-15")
    folder.add_argument("--tile-size", type=int, default=512)
    folder.add_argument("--csv", type=Path, default=None)

    sub.add_parser("export-csv", help="Export the SQLite spatial registry to data/tiles_metadata.csv")

    # Spatial Queries (Role 1)
    bbox = sub.add_parser("search-bbox", help="Query spatial database for tiles overlapping bounding box")
    bbox.add_argument("minx", type=float)
    bbox.add_argument("miny", type=float)
    bbox.add_argument("maxx", type=float)
    bbox.add_argument("maxy", type=float)

    tile = sub.add_parser("get-tile", help="Get spatial metadata and provenance for one tile ID")
    tile.add_argument("tile_id", type=str)

    sub.add_parser("list-tiles", help="List all indexed tiles in the spatial registry")

    # 2. Semantic Search Commands (Role 2)
    search_cmd = sub.add_parser("search", help="Execute Natural Language Semantic Search via RemoteCLIP")
    search_cmd.add_argument("query", type=str, help="Free-form search text (e.g., 'dense urban area', 'coastal port')")
    search_cmd.add_argument("--top-k", type=int, default=5, help="Number of results to return (default: 5)")
    search_cmd.add_argument("--bbox", nargs=4, type=float, default=None, metavar=('MINX', 'MINY', 'MAXX', 'MAXY'), help="Optional geographic bounding box filter")

    # 3. Temporal Change Detection (Role 3 & Role 4)
    compare_cmd = sub.add_parser("compare", help="Compare bitemporal tile pair with JIT QA False-Alarm Suppression")
    compare_cmd.add_argument("t1_path", type=str, help="Path to Time 1 (Before) tile")
    compare_cmd.add_argument("t2_path", type=str, help="Path to Time 2 (After) tile")
    compare_cmd.add_argument("--classical", action="store_true", help="Force Classical CV engine instead of BIT Transformer")
    compare_cmd.add_argument("--output-dir", type=str, default="outputs", help="Output directory for masks and overlays")
    compare_cmd.add_argument("--min-area", type=int, default=100, help="Minimum change contour area in pixels")

    # 4. Clustering (Role 4)
    cluster_cmd = sub.add_parser("cluster", help="Run K-Means terrain similarity clustering across tile embeddings")
    cluster_cmd.add_argument("--k", type=int, default=5, help="Number of clusters (default: 5)")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "init-db":
        init_db()
        print(f"Registry ready: {DEFAULT_DB_PATH}")
        return 0

    try:
        # Role 1: Ingestion
        if args.command == "ingest":
            result = add_image(args.filepath, tile_size=args.tile_size, csv_path=args.csv)
            print(json.dumps(result, indent=2))
        elif args.command == "ingest-folder":
            result = add_band_folder(args.folder, tile_size=args.tile_size, csv_path=args.csv, acquisition_date=args.date)
            print(json.dumps(result, indent=2))
        elif args.command == "export-csv":
            csv_path = export_metadata_csv()
            print(f"CSV exported successfully: {csv_path}")
        elif args.command == "search-bbox":
            result = get_tiles_by_bbox(args.minx, args.miny, args.maxx, args.maxy)
            print(json.dumps(result, indent=2))
            print(f"Found {len(result)} matching tile(s).")
        elif args.command == "get-tile":
            print(json.dumps(get_tile(args.tile_id), indent=2))
        elif args.command == "list-tiles":
            result = get_all_tiles()
            print(json.dumps(result, indent=2))
            print(f"Total tiles: {len(result)}")

        # Role 2: Semantic Search
        elif args.command == "search":
            from semantic_search.search import search
            bbox_tuple = tuple(args.bbox) if args.bbox else None
            results = search(query=args.query, bbox=bbox_tuple, top_k=args.top_k)
            print(f"\n[Semantic Search] Results for: '{args.query}' (Top {len(results)} matches)")
            print("=" * 60)
            for idx, r in enumerate(results, 1):
                print(f"{idx}. Tile: {r.tile_name}")
                print(f"   Score: {r.score:.4f} | Date: {r.date} | Path: {r.image_path}")
                print(f"   Bounds: {r.bounds}")
                print("-" * 60)

        # Role 3 & Role 4: Temporal Detective with JIT QA Suppression
        elif args.command == "compare":
            from detective_api import compare_tiles
            print(f"\n[Detective] Comparing tiles with Just-In-Time QA False-Alarm Suppression...")
            print(f"   T1 (Before): {args.t1_path}")
            print(f"   T2 (After) : {args.t2_path}")
            report = compare_tiles(
                tile_t1_path=args.t1_path,
                tile_t2_path=args.t2_path,
                force_classical=args.classical,
                output_dir=args.output_dir,
                min_area=args.min_area
            )
            # Serialize for display
            display_report = {k: v for k, v in report.items() if not k.endswith("_array")}
            print(json.dumps(display_report, indent=2))

        # Role 4: Clustering
        elif args.command == "cluster":
            from clustering import run_clustering_pipeline
            print(f"\n[Clustering] Running K-Means clustering (k={args.k})...")
            summary = run_clustering_pipeline(k=args.k)
            print("Clustering completed successfully.")

    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
