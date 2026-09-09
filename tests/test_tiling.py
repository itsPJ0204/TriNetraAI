import rasterio

from ingestion.tiling import create_tiles


def test_tiling(sample_raster, tmp_path):
    records = create_tiles(sample_raster, image_id=7, output_root=tmp_path / "tiles")
    assert len(records) == 4
    assert records[0]["width"] == 512
    assert records[0]["height"] == 512
    assert records[-1]["width"] == 512
    assert records[-1]["height"] == 188

    for record in records:
        with rasterio.open(record["filepath"]) as src:
            assert src.crs.to_string() == "EPSG:4326"
            assert src.width == record["width"]
            assert src.height == record["height"]
