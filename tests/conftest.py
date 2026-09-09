from __future__ import annotations

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from ingestion.db import get_connection, init_db


@pytest.fixture
def test_db(tmp_path):
    db = tmp_path / "satellite.db"
    init_db(db)
    return db


def make_raster(path, width=1024, height=700, date_value="2026-01-15"):
    transform = from_origin(80, 30, 0.01, 0.01)
    data = np.arange(width * height, dtype=np.uint16).reshape(height, width) % 1000
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=width,
        height=height,
        count=1,
        dtype="uint16",
        crs="EPSG:4326",
        transform=transform,
    ) as dst:
        dst.write(data, 1)
        dst.update_tags(acquisition_date=date_value)
    return path


@pytest.fixture
def sample_raster(tmp_path):
    return make_raster(tmp_path / "sample.tif")
