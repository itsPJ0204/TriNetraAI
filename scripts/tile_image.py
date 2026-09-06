"""Split the project test GeoTIFF into four georeferenced GeoTIFF tiles."""

from pathlib import Path

import rasterio
from rasterio.windows import Window


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TILES_DIRECTORY = PROJECT_ROOT / "data" / "tiles"
SOURCE_PATH = TILES_DIRECTORY / "test_tile.tiff"
OUTPUT_PATHS = [TILES_DIRECTORY / f"tile_{number}.tif" for number in range(1, 5)]


def split_windows(width: int, height: int) -> list[Window]:
    """Return four windows that cover every source pixel, including odd edges."""
    left_width = width // 2
    top_height = height // 2
    right_width = width - left_width
    bottom_height = height - top_height

    return [
        Window(0, 0, left_width, top_height),
        Window(left_width, 0, right_width, top_height),
        Window(0, top_height, left_width, bottom_height),
        Window(left_width, top_height, right_width, bottom_height),
    ]


def tile_image() -> list[Path]:
    """Create four tiles while preserving the source GeoTIFF metadata."""
    if not SOURCE_PATH.is_file():
        raise FileNotFoundError(f"Source GeoTIFF was not found: {SOURCE_PATH}")

    existing_outputs = [path for path in OUTPUT_PATHS if path.exists()]
    if existing_outputs:
        names = ", ".join(path.name for path in existing_outputs)
        raise FileExistsError(f"Output tile(s) already exist and were not overwritten: {names}")

    with rasterio.open(SOURCE_PATH) as source:
        print(f"Original dimensions: {source.width} x {source.height}")
        print(f"CRS: {source.crs}")

        for output_path, window in zip(OUTPUT_PATHS, split_windows(source.width, source.height)):
            tile_profile = source.profile.copy()
            tile_profile.update(
                width=int(window.width),
                height=int(window.height),
                transform=source.window_transform(window),
            )

            with rasterio.open(output_path, "w", **tile_profile) as destination:
                destination.write(source.read(window=window))

            print(f"Tile dimensions: {int(window.width)} x {int(window.height)}")
            print(f"Output path: {output_path}")

    return OUTPUT_PATHS


def main() -> int:
    """Run tiling and provide clear messages for expected input/output issues."""
    try:
        tile_image()
    except (FileNotFoundError, FileExistsError) as error:
        print(f"ERROR: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
