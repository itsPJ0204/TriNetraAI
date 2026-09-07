from __future__ import annotations

import argparse
import json
from pathlib import Path

from ingestion.db import DEFAULT_DB_PATH, init_db
from ingestion.ingest import add_image, add_band_folder, export_metadata_csv
from spatial.queries import get_all_tiles, get_tile, get_tiles_by_bbox


def build_parser():
    parser = argparse.ArgumentParser(description="Offline Bhuvan/NRSC GeoTIFF ingestion and tile registry")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init-db", help="Create the offline tile registry")
    ingest = sub.add_parser("ingest", help="Ingest one original .tif/.tiff")
    ingest.add_argument("filepath", type=Path)
    ingest.add_argument("--tile-size", type=int, default=512)
    ingest.add_argument("--csv", type=Path, default=None)
    folder = sub.add_parser("ingest-folder", help="Ingest a Bhuvan scene folder containing BAND2-BAND5")
    folder.add_argument("folder", type=Path)
    folder.add_argument("--date", default=None, help="Acquisition date, e.g. 2024-06-15")
    folder.add_argument("--tile-size", type=int, default=512)
    folder.add_argument("--csv", type=Path, default=None)
    sub.add_parser("export-csv", help="Export the tile registry for the Semantic AI team")
    bbox = sub.add_parser("search-bbox", help="Find tiles overlapping a bounding box")
    bbox.add_argument("minx", type=float); bbox.add_argument("miny", type=float); bbox.add_argument("maxx", type=float); bbox.add_argument("maxy", type=float)
    tile = sub.add_parser("get-tile", help="Get one tile's complete metadata")
    tile.add_argument("tile_id")
    sub.add_parser("list-tiles", help="List all indexed tiles")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "init-db":
        init_db(); print(f"Registry ready: {DEFAULT_DB_PATH}"); return 0
    try:
        if args.command == "ingest":
            print(json.dumps(add_image(args.filepath, tile_size=args.tile_size, csv_path=args.csv), indent=2))
        elif args.command == "ingest-folder":
            print(json.dumps(add_band_folder(args.folder, tile_size=args.tile_size, csv_path=args.csv, acquisition_date=args.date), indent=2))
        elif args.command == "export-csv":
            print(f"CSV ready: {export_metadata_csv()}")
        elif args.command == "search-bbox":
            result = get_tiles_by_bbox(args.minx, args.miny, args.maxx, args.maxy); print(json.dumps(result, indent=2)); print(f"Found {len(result)} matching tile(s).")
        elif args.command == "get-tile":
            print(json.dumps(get_tile(args.tile_id), indent=2))
        elif args.command == "list-tiles":
            result = get_all_tiles(); print(json.dumps(result, indent=2)); print(f"Total tiles: {len(result)}")
    except Exception as exc:
        print(f"ERROR: {exc}"); return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
