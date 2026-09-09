from ingestion.metadata import get_metadata


def test_metadata(sample_raster):
    meta = get_metadata(sample_raster)
    assert meta["width"] == 1024
    assert meta["height"] == 700
    assert meta["bands"] == 1
    assert meta["crs"] == "EPSG:4326"
    assert meta["acquisition_date"] == "2026-01-15"
    assert len(meta["transform"]) == 6
