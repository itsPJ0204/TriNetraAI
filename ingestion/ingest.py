from __future__ import annotations

import csv
import hashlib
import sqlite3
import rasterio
from pathlib import Path
from typing import Any

from ingestion.db import DEFAULT_DB_PATH, get_connection, init_db
from ingestion.metadata import get_metadata, transform_to_json
from ingestion.band_folder import find_band_files, band_manifest_hash, create_tiles_from_band_folder
from ingestion.tiling import create_tiles

CSV_FIELDS = [
    "tile_id", "grid_key", "grid_row", "grid_col", "image_id", "source_filename",
    "acquisition_date", "filepath", "minx", "miny", "maxx", "maxy", "width", "height",
    "row_off", "col_off", "bands", "dtype", "nodata", "crs", "transform",
]


def sha256_file(filepath: str | Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with Path(filepath).open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def _existing_image(conn: sqlite3.Connection, filepath: str, file_hash: str):
    return conn.execute("SELECT * FROM images WHERE filepath = ? OR file_hash = ? LIMIT 1", (filepath, file_hash)).fetchone()


def export_metadata_csv(db_path=DEFAULT_DB_PATH, csv_path=None) -> Path:
    """Export the registry in the same contract consumed by Semantic AI."""
    csv_file = Path(csv_path) if csv_path else Path(db_path).resolve().parent.parent / "data" / "tiles_metadata.csv"
    csv_file.parent.mkdir(parents=True, exist_ok=True)
    init_db(db_path)
    with get_connection(db_path) as conn:
        rows = conn.execute("""
            SELECT t.tile_id, t.grid_key, t.grid_row, t.grid_col, t.image_id,
                   i.filename AS source_filename, i.acquisition_date, t.filepath,
                   t.minx, t.miny, t.maxx, t.maxy, t.width, t.height,
                   t.row_off, t.col_off, t.bands, t.dtype, t.nodata, t.crs, t.transform
            FROM tiles t JOIN images i ON i.id = t.image_id
            ORDER BY i.acquisition_date, t.grid_row, t.grid_col
        """).fetchall()
    with csv_file.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows([dict(row) for row in rows])
    return csv_file.resolve()


def add_image(filepath: str | Path, db_path=DEFAULT_DB_PATH, tile_size: int = 512, csv_path=None) -> dict[str, Any]:
    """Incrementally ingest one original Bhuvan/NRSC GeoTIFF and update the handoff registry."""
    path = Path(filepath)
    if path.suffix.lower() not in {".tif", ".tiff"}:
        raise ValueError("Input must be an original .tif or .tiff GeoTIFF/COG")
    if not path.is_file():
        raise FileNotFoundError(f"Raster file not found: {path}")

    init_db(db_path)
    absolute_path = str(path.resolve())
    file_hash = sha256_file(path)
    created_tile_paths: list[Path] = []

    with get_connection(db_path) as conn:
        existing = _existing_image(conn, absolute_path, file_hash)
        if existing:
            csv_file = export_metadata_csv(db_path, csv_path)
            return {"status": "already_exists", "image_id": int(existing["id"]), "filepath": existing["filepath"], "tiles_created": 0, "metadata_csv": str(csv_file), "message": "Image already processed; skipping."}

        metadata = get_metadata(path)
        try:
            cursor = conn.execute("""
                INSERT INTO images
                (filepath, file_hash, filename, width, height, bands, dtype, nodata, crs,
                 minx, miny, maxx, maxy, transform, acquisition_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                absolute_path, file_hash, metadata["filename"], metadata["width"], metadata["height"],
                metadata["bands"], metadata["dtype"], metadata["nodata"], metadata["crs"],
                metadata["minx"], metadata["miny"], metadata["maxx"], metadata["maxy"],
                transform_to_json(metadata["transform"]), metadata["acquisition_date"],
            ))
            image_id = int(cursor.lastrowid)
            conn.commit()

            tile_records = create_tiles(path, image_id=image_id, tile_size=tile_size)
            created_tile_paths = [Path(r["filepath"]) for r in tile_records]
            conn.executemany("""
                INSERT INTO tiles
                (tile_id, grid_key, grid_row, grid_col, image_id, filepath,
                 minx, miny, maxx, maxy, width, height, row_off, col_off,
                 bands, dtype, nodata, crs, transform)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [(
                r["tile_id"], r["grid_key"], r["grid_row"], r["grid_col"], r["image_id"], r["filepath"],
                r["minx"], r["miny"], r["maxx"], r["maxy"], r["width"], r["height"], r["row_off"], r["col_off"],
                r["bands"], r["dtype"], r["nodata"], r["crs"], r["transform"],
            ) for r in tile_records])
            conn.commit()
            csv_file = export_metadata_csv(db_path, csv_path)
            return {"status": "processed", "image_id": image_id, "filepath": absolute_path, "tiles_created": len(tile_records), "metadata_csv": str(csv_file), "message": f"Processed image and created {len(tile_records)} tiles."}
        except Exception:
            conn.rollback()
            for tile_path in created_tile_paths:
                try:
                    tile_path.unlink(missing_ok=True)
                except OSError:
                    pass
            if "image_id" in locals():
                conn.execute("DELETE FROM images WHERE id = ?", (image_id,))
                conn.commit()
            raise


def add_band_folder(folder: str | Path, db_path=DEFAULT_DB_PATH, tile_size: int = 512, csv_path=None, acquisition_date: str | None = None) -> dict[str, Any]:
    """Ingest an original Bhuvan scene folder containing aligned BAND2-BAND5 GeoTIFFs."""
    folder = Path(folder)
    files = find_band_files(folder)
    init_db(db_path)
    absolute_folder = str(folder.resolve())
    file_hash = band_manifest_hash(files)
    with get_connection(db_path) as conn:
        existing = _existing_image(conn, absolute_folder, file_hash)
        if existing:
            csv_file = export_metadata_csv(db_path, csv_path)
            return {"status": "already_exists", "image_id": int(existing["id"]), "filepath": existing["filepath"], "tiles_created": 0, "metadata_csv": str(csv_file), "message": "Band folder already processed; skipping."}

        with rasterio.open(files[0]) as src:
            metadata = {
                "filename": folder.name, "width": src.width, "height": src.height, "bands": len(files),
                "dtype": str(src.dtypes[0]), "nodata": src.nodata,
                "crs": src.crs.to_string() if src.crs else None,
                "minx": src.bounds.left, "miny": src.bounds.bottom, "maxx": src.bounds.right, "maxy": src.bounds.top,
                "transform": src.transform,
                "acquisition_date": acquisition_date or folder.name,
            }
        cursor = conn.execute("""
            INSERT INTO images (filepath, file_hash, filename, width, height, bands, dtype, nodata, crs, minx, miny, maxx, maxy, transform, acquisition_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (absolute_folder, file_hash, metadata["filename"], metadata["width"], metadata["height"], metadata["bands"], metadata["dtype"], metadata["nodata"], metadata["crs"], metadata["minx"], metadata["miny"], metadata["maxx"], metadata["maxy"], transform_to_json(metadata["transform"]), metadata["acquisition_date"]))
        image_id = int(cursor.lastrowid)
        conn.commit()
        created = []
        try:
            records = create_tiles_from_band_folder(folder, image_id=image_id, tile_size=tile_size)
            created = [Path(r["filepath"]) for r in records]
            conn.executemany("""
                INSERT INTO tiles (tile_id, grid_key, grid_row, grid_col, image_id, filepath, minx, miny, maxx, maxy, width, height, row_off, col_off, bands, dtype, nodata, crs, transform)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [(r["tile_id"], r["grid_key"], r["grid_row"], r["grid_col"], r["image_id"], r["filepath"], r["minx"], r["miny"], r["maxx"], r["maxy"], r["width"], r["height"], r["row_off"], r["col_off"], r["bands"], r["dtype"], r["nodata"], r["crs"], r["transform"]) for r in records])
            conn.commit()
            csv_file = export_metadata_csv(db_path, csv_path)
            return {"status": "processed", "image_id": image_id, "filepath": absolute_folder, "bands": [p.name for p in files], "tiles_created": len(records), "metadata_csv": str(csv_file), "message": f"Processed BAND2-BAND5 and created {len(records)} tiles."}
        except Exception:
            conn.rollback()
            for tile_path in created:
                try: tile_path.unlink(missing_ok=True)
                except OSError: pass
            conn.execute("DELETE FROM images WHERE id = ?", (image_id,)); conn.commit()
            raise
