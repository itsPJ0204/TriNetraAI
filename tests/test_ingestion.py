from ingestion.db import get_connection
from ingestion.ingest import add_image
from spatial.queries import get_all_tiles, get_tiles_by_bbox, get_tiles_by_location_and_date


def test_ingestion_and_incremental(sample_raster, test_db, monkeypatch):
    monkeypatch.setattr("ingestion.ingest.DEFAULT_DB_PATH", test_db)
    monkeypatch.setattr("ingestion.tiling.PROJECT_ROOT", sample_raster.parent)

    first = add_image(sample_raster, db_path=test_db)
    assert first["status"] == "processed"
    assert first["tiles_created"] == 4

    second = add_image(sample_raster, db_path=test_db)
    assert second["status"] == "already_exists"

    with get_connection(test_db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM images").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM tiles").fetchone()[0] == 4

    all_tiles = get_all_tiles(test_db)
    assert len(all_tiles) == 4
    assert get_tiles_by_bbox(80, 23, 82, 30, test_db)
    assert get_tiles_by_location_and_date(80, 23, 82, 30, "2026-01-01", "2026-02-01", test_db)


def test_invalid_bbox(test_db):
    import pytest
    with pytest.raises(ValueError):
        get_tiles_by_bbox(2, 1, 1, 2, test_db)


def test_renamed_duplicate_is_detected(sample_raster, test_db, monkeypatch, tmp_path):
    monkeypatch.setattr("ingestion.tiling.PROJECT_ROOT", tmp_path)
    first = add_image(sample_raster, db_path=test_db)
    renamed = tmp_path / "renamed_copy.tif"
    renamed.write_bytes(sample_raster.read_bytes())

    second = add_image(renamed, db_path=test_db)
    assert first["status"] == "processed"
    assert second["status"] == "already_exists"

    with get_connection(test_db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM images").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM tiles").fetchone()[0] == 4
