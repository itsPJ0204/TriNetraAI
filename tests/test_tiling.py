"""Phase 6.5 verification for Rasterio GeoTIFF tiling."""

import rasterio

from scripts.tile_image import OUTPUT_PATHS, SOURCE_PATH, split_windows


def test_tiling() -> None:
    """Confirm four output tiles preserve source data and geospatial metadata."""
    assert SOURCE_PATH.is_file()
    assert all(path.is_file() for path in OUTPUT_PATHS)

    with rasterio.open(SOURCE_PATH) as source:
        windows = split_windows(source.width, source.height)
        total_pixels = 0

        for output_path, window in zip(OUTPUT_PATHS, windows):
            with rasterio.open(output_path) as tile:
                assert tile.count == source.count
                assert tile.crs == source.crs
                assert tile.transform == source.window_transform(window)
                assert tile.width == int(window.width)
                assert tile.height == int(window.height)
                assert tile.dtypes == source.dtypes
                source_pixels = source.read(window=window)
                assert tile.read().shape == source_pixels.shape
                assert (tile.read() == source_pixels).all()
                total_pixels += tile.width * tile.height

        assert total_pixels == source.width * source.height


if __name__ == "__main__":
    test_tiling()
    print("All four GeoTIFF tiles passed validation.")
