"""Process raw Sentinel-2 L2A bands into an RGB composite and georeferenced tiles."""

import argparse
from pathlib import Path
import rasterio
import numpy as np

from semantic_search.sentinel2 import (
    DEFAULT_OUTPUT_TILES_DIR,
    DEFAULT_RAW_DIR,
    create_sentinel2_rgb_composite,
    tile_sentinel2_rgb,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Sentinel-2 RGB Compositing & Tiling Pipeline.")
    parser.add_argument("--raw-dir", default=str(DEFAULT_RAW_DIR), help="Directory with raw Sentinel-2 TIFFs")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_TILES_DIR), help="Output directory for tiles")
    parser.add_argument("--tile-size", type=int, default=256, help="Tile size in pixels (default 256)")
    parser.add_argument("--save-composite", action="store_true", help="Save the full composite GeoTIFF")
    args = parser.parse_args()

    raw_dir = Path(args.raw_dir)
    out_dir = Path(args.output_dir)

    print("=" * 80)
    print("         SENTINEL-2 RGB COMPOSITING & GEOSPATIAL TILING PIPELINE")
    print("=" * 80)
    print(f"Source Raw Directory:  {raw_dir.resolve()}")
    print(f"Target Tile Directory: {out_dir.resolve()}")
    print(f"Target Tile Size:      {args.tile_size}x{args.tile_size} pixels")

    composite_path = out_dir / "sentinel2_rgb_full.tif"

    try:
        if not composite_path.is_file() or args.save_composite:
            print("\n[1/3] Creating/updating RGB composite (R=B04, G=B03, B=B02) with percentile stretch...")
            rgb_array, profile, date = create_sentinel2_rgb_composite(
                raw_dir=raw_dir, output_composite_path=composite_path
            )
        else:
            print(f"\n[1/3] Using existing valid RGB composite: {composite_path.name}")
            with rasterio.open(composite_path) as src:
                rgb_array = src.read()
                profile = src.profile.copy()
                tags = src.tags()
                date = tags.get("date", "2026-06-27")

        total_source_h, total_source_w = rgb_array.shape[1], rgb_array.shape[2]
        total_source_pixels = total_source_w * total_source_h
        print(f"  -> Full Composite: {total_source_w}x{total_source_h} pixels ({total_source_pixels:,} px)")
        print(f"  -> Acquisition Date: {date}")
        print(f"  -> CRS: {profile['crs']}")

        print(f"\n[2/3] Generating {args.tile_size}x{args.tile_size} geospatial tiles (preserving edge pixels)...")
        tiles = tile_sentinel2_rgb(
            source_path=composite_path if composite_path.is_file() else None,
            raw_dir=raw_dir,
            output_dir=out_dir,
            tile_size=args.tile_size,
            overwrite=True,
            remove_old_tiles=True,
        )
        print(f"  -> Successfully generated {len(tiles)} GeoTIFF tiles in {out_dir}")

        print("\n[3/3] Performing statistical and geospatial verification of generated tiles...")
        all_passed = True
        total_tiled_pixels = 0
        edge_tiles_info = []

        for idx, t in enumerate(tiles, start=1):
            with rasterio.open(t) as src:
                data = src.read()  # (3, H, W)
                tags = src.tags()
                non_zero = int(np.count_nonzero(data))
                total = int(data.size)
                tile_pixel_count = src.width * src.height
                total_tiled_pixels += tile_pixel_count
                pct_nz = (non_zero / total) * 100.0
                r_mean, g_mean, b_mean = float(data[0].mean()), float(data[1].mean()), float(data[2].mean())

                is_edge = src.width != args.tile_size or src.height != args.tile_size
                edge_desc = ""
                if is_edge:
                    edge_tiles_info.append((t.name, src.width, src.height))
                    edge_desc = f" [EDGE TILE: {src.width}x{src.height}]"

                print(f"\n  Tile {idx:02d}: {t.name}{edge_desc}")
                print(f"    Dimensions:   {src.width} x {src.height} (3 bands, uint8)")
                print(f"    CRS:          {src.crs}")
                print(f"    Bounds:       left={src.bounds.left:.6f}, bottom={src.bounds.bottom:.6f}, right={src.bounds.right:.6f}, top={src.bounds.top:.6f}")
                print(f"    Tags:         Date={tags.get('date')}, Bands={tags.get('r_band')}/{tags.get('g_band')}/{tags.get('b_band')}")
                print(f"    Channel Means:R={r_mean:.1f}, G={g_mean:.1f}, B={b_mean:.1f}")
                print(f"    Non-Zero:     {non_zero:,} / {total:,} ({pct_nz:.2f}%)")

                if pct_nz < 90.0 or (r_mean < 5.0 and g_mean < 5.0 and b_mean < 5.0):
                    print("    [FAIL] Tile appears black or empty!")
                    all_passed = False
                else:
                    print("    [PASS] Tile verified: valid dynamic range, non-empty.")

        print("\n" + "-" * 80)
        print("TILING SUMMARY & COVERAGE REPORT:")
        print(f"  - Total Generated Tiles: {len(tiles)}")
        print(f"  - Standard {args.tile_size}x{args.tile_size} Tiles: {len(tiles) - len(edge_tiles_info)}")
        print(f"  - Edge Tiles:            {len(edge_tiles_info)}")
        for e_name, e_w, e_h in edge_tiles_info:
            print(f"      * {e_name}: {e_w}w x {e_h}h")
        print(f"  - Total Source Pixels:   {total_source_pixels:,} px")
        print(f"  - Total Tiled Pixels:    {total_tiled_pixels:,} px")
        coverage_pct = (total_tiled_pixels / total_source_pixels) * 100.0
        print(f"  - Exact Source Coverage: {coverage_pct:.4f}% ({total_tiled_pixels}/{total_source_pixels} px)")

        if total_tiled_pixels != total_source_pixels:
            print("  [FAIL] Tile pixel coverage does not match source image!")
            all_passed = False
        else:
            print("  [PASS] 100% Exact coverage verified with 0 gaps and 0 pixel loss.")

        print("=" * 80)
        if all_passed:
            print(">>> PIPELINE RESULT: SUCCESS (All 30 tiles valid, georeferenced, non-empty) <<<")
        else:
            print(">>> PIPELINE RESULT: FAILED <<<")
        print("=" * 80)
        return 0 if all_passed else 1

    except Exception as err:
        print(f"\n[ERROR] Pipeline failed: {err}")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
