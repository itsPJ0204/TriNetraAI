from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Union

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = PROJECT_ROOT / "database" / "tile_registry.sqlite"

SCHEMA = """
CREATE TABLE IF NOT EXISTS images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filepath TEXT NOT NULL UNIQUE,
    file_hash TEXT NOT NULL UNIQUE,
    filename TEXT NOT NULL,
    width INTEGER NOT NULL,
    height INTEGER NOT NULL,
    bands INTEGER NOT NULL,
    dtype TEXT NOT NULL,
    nodata REAL,
    crs TEXT,
    minx REAL NOT NULL,
    miny REAL NOT NULL,
    maxx REAL NOT NULL,
    maxy REAL NOT NULL,
    transform TEXT NOT NULL,
    acquisition_date TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS tiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tile_id TEXT NOT NULL UNIQUE,
    grid_key TEXT NOT NULL,
    grid_row INTEGER NOT NULL,
    grid_col INTEGER NOT NULL,
    image_id INTEGER NOT NULL,
    filepath TEXT NOT NULL UNIQUE,
    minx REAL NOT NULL,
    miny REAL NOT NULL,
    maxx REAL NOT NULL,
    maxy REAL NOT NULL,
    width INTEGER NOT NULL,
    height INTEGER NOT NULL,
    row_off INTEGER NOT NULL,
    col_off INTEGER NOT NULL,
    bands INTEGER NOT NULL,
    dtype TEXT NOT NULL,
    nodata REAL,
    crs TEXT,
    transform TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (image_id) REFERENCES images(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_tiles_bbox ON tiles (minx, miny, maxx, maxy);
CREATE INDEX IF NOT EXISTS idx_images_date ON images (acquisition_date);
CREATE INDEX IF NOT EXISTS idx_tiles_image_id ON tiles (image_id);
CREATE INDEX IF NOT EXISTS idx_tiles_grid_key ON tiles (grid_key);
CREATE INDEX IF NOT EXISTS idx_tiles_date_grid ON tiles (grid_key, image_id);
"""


def get_connection(db_path: Union[str, Path] = DEFAULT_DB_PATH) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: Union[str, Path] = DEFAULT_DB_PATH) -> None:
    with get_connection(db_path) as conn:
        conn.executescript(SCHEMA)
        conn.commit()
