from __future__ import annotations

import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable

import rasterio

from ingestion.db import DEFAULT_DB_PATH, get_connection, init_db


def _rows_to_dicts(rows: Iterable[sqlite3.Row]) -> list[dict[str, Any]]:
    result = []
    for row in rows:
        item = dict(row)
        if all(k in item for k in ("minx", "miny", "maxx", "maxy")):
            item["bbox"] = [item.pop("minx"), item.pop("miny"), item.pop("maxx"), item.pop("maxy")]
        result.append(item)
    return result


def get_all_tiles(db_path=DEFAULT_DB_PATH) -> list[dict[str, Any]]:
    init_db(db_path)
    with get_connection(db_path) as conn:
        rows = conn.execute("SELECT t.*, i.filename AS source_filename, i.acquisition_date FROM tiles t JOIN images i ON i.id=t.image_id ORDER BY t.id").fetchall()
    return _rows_to_dicts(rows)


def get_tile(tile_id: str, db_path=DEFAULT_DB_PATH) -> dict[str, Any] | None:
    init_db(db_path)
    with get_connection(db_path) as conn:
        row = conn.execute("SELECT t.*, i.filename AS source_filename, i.acquisition_date FROM tiles t JOIN images i ON i.id=t.image_id WHERE t.tile_id=?", (tile_id,)).fetchone()
    return _rows_to_dicts([row])[0] if row else None


def get_tiles_by_bbox(minx: float, miny: float, maxx: float, maxy: float, db_path=DEFAULT_DB_PATH) -> list[dict[str, Any]]:
    if minx > maxx or miny > maxy:
        raise ValueError("Bounding box minimums must not exceed maximums")
    init_db(db_path)
    with get_connection(db_path) as conn:
        rows = conn.execute("""
            SELECT t.*, i.filename AS source_filename, i.acquisition_date
            FROM tiles t JOIN images i ON i.id=t.image_id
            WHERE t.minx <= ? AND t.maxx >= ? AND t.miny <= ? AND t.maxy >= ?
            ORDER BY i.acquisition_date, t.id
        """, (maxx, minx, maxy, miny)).fetchall()
    return _rows_to_dicts(rows)


def get_tiles_by_location_and_date(minx: float, miny: float, maxx: float, maxy: float, start_date: str | date | datetime | None = None, end_date: str | date | datetime | None = None, db_path=DEFAULT_DB_PATH) -> list[dict[str, Any]]:
    if minx > maxx or miny > maxy:
        raise ValueError("Bounding box minimums must not exceed maximums")
    init_db(db_path)
    start = start_date.isoformat() if hasattr(start_date, "isoformat") else start_date
    end = end_date.isoformat() if hasattr(end_date, "isoformat") else end_date
    query = """
        SELECT t.*, i.filename AS source_filename, i.acquisition_date
        FROM tiles t JOIN images i ON i.id=t.image_id
        WHERE t.minx <= :maxx AND t.maxx >= :minx AND t.miny <= :maxy AND t.maxy >= :miny
    """
    params = {"minx": minx, "miny": miny, "maxx": maxx, "maxy": maxy}
    if start is not None:
        query += " AND i.acquisition_date >= :start_date"; params["start_date"] = str(start)
    if end is not None:
        query += " AND i.acquisition_date <= :end_date"; params["end_date"] = str(end)
    query += " ORDER BY i.acquisition_date, t.grid_row, t.grid_col"
    with get_connection(db_path) as conn:
        rows = conn.execute(query, params).fetchall()
    return _rows_to_dicts(rows)


def get_temporal_pair(grid_key: str, date1: str, date2: str, db_path=DEFAULT_DB_PATH) -> dict[str, Any] | None:
    """Return two tiles covering the same grid cell for temporal AI."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        rows = conn.execute("""
            SELECT t.*, i.filename AS source_filename, i.acquisition_date
            FROM tiles t JOIN images i ON i.id=t.image_id
            WHERE t.grid_key=? AND i.acquisition_date IN (?, ?)
            ORDER BY i.acquisition_date
        """, (grid_key, date1, date2)).fetchall()
    items = _rows_to_dicts(rows)
    by_date = {str(x["acquisition_date"]): x for x in items}
    if date1 not in by_date or date2 not in by_date:
        return None
    return {"grid_key": grid_key, "before": by_date[date1], "after": by_date[date2]}


def load_tile_array(tile_id: str, db_path=DEFAULT_DB_PATH):
    """Load the actual TIFF pixels for a downstream AI module."""
    tile = get_tile(tile_id, db_path)
    if tile is None:
        raise KeyError(f"Unknown tile_id: {tile_id}")
    path = Path(tile["filepath"])
    if not path.is_file():
        raise FileNotFoundError(f"Tile file not found: {path}")
    with rasterio.open(path) as src:
        return src.read(), dict(src.meta)
