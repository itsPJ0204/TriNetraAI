from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

from ingestion.db import get_connection, init_db
from ingestion.ingest import add_band_folder


def test_band_folder_ingest(tmp_path: Path):
    folder = tmp_path / "2024-06"
    folder.mkdir()
    transform = from_origin(500000, 2600000, 24, 24)
    for band in (2, 3, 4, 5):
        with rasterio.open(folder / f"BAND{band}.tif", "w", driver="GTiff", width=1024, height=1024, count=1,
                           dtype="uint16", crs="EPSG:32645", transform=transform) as dst:
            dst.write(np.full((1024, 1024), band, dtype=np.uint16), 1)

    db = tmp_path / "registry.sqlite"
    result = add_band_folder(folder, db_path=db, tile_size=512, acquisition_date="2024-06-15")
    assert result["tiles_created"] == 4

    with get_connection(db) as conn:
        row = conn.execute("SELECT bands, acquisition_date FROM images").fetchone()
        assert row["bands"] == 4
        assert row["acquisition_date"] == "2024-06-15"
        assert conn.execute("SELECT COUNT(*) FROM tiles").fetchone()[0] == 4

    again = add_band_folder(folder, db_path=db, tile_size=512, acquisition_date="2024-06-15")
    assert again["status"] == "already_exists"
