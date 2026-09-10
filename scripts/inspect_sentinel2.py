"""Inspection and validation script for raw Sentinel-2 TIFF files."""

from pathlib import Path
import rasterio
import numpy as np


def main() -> int:
    raw_dir = Path("data/raw/sentinel2")
    if not raw_dir.is_dir():
        print(f"Error: Directory {raw_dir} does not exist.")
        return 1

    files = sorted(list(raw_dir.glob("*.tiff")) + list(raw_dir.glob("*.tif")))
    print("=" * 80)
    print("              SENTINEL-2 RAW TIF FILES INSPECTION REPORT")
    print("=" * 80)
    print(f"\nDirectory: {raw_dir.resolve()}")
    print(f"Total TIFF files found: {len(files)}")

    bands = {}
    for f in files:
        for b in ["B02", "B03", "B04", "B08"]:
            if b in f.name:
                bands[b] = f
                break

    required_bands = ["B02", "B03", "B04", "B08"]
    missing = [b for b in required_bands if b not in bands]
    if missing:
        print(f"\n[FAIL] Missing required bands: {missing}")
        return 1

    reports = {}
    for b in required_bands:
        fpath = bands[b]
        with rasterio.open(fpath) as src:
            data = src.read(1)
            nodata = src.nodata
            non_zero_count = int(np.count_nonzero(data))
            total_pixels = int(data.size)
            pct_non_zero = (non_zero_count / total_pixels) * 100.0
            min_val = float(np.min(data))
            max_val = float(np.max(data))
            reports[b] = {
                "filename": fpath.name,
                "count": src.count,
                "width": src.width,
                "height": src.height,
                "dtype": str(src.dtypes[0]),
                "crs": str(src.crs),
                "bounds": src.bounds,
                "transform": src.transform,
                "nodata": nodata,
                "min_val": min_val,
                "max_val": max_val,
                "total_pixels": total_pixels,
                "non_zero_count": non_zero_count,
                "pct_non_zero": pct_non_zero,
            }

    # Print individual band reports
    for b in required_bands:
        rep = reports[b]
        print("\n" + "-" * 80)
        print(f"BAND: {b} ({'Blue' if b=='B02' else 'Green' if b=='B03' else 'Red' if b=='B04' else 'Near-Infrared (NIR)'})")
        print("-" * 80)
        print(f"  Filename:             {rep['filename']}")
        print(f"  Band Count:           {rep['count']}")
        print(f"  Dimensions (WxH):     {rep['width']} x {rep['height']} pixels")
        print(f"  Data Type:            {rep['dtype']}")
        print(f"  CRS:                  {rep['crs']}")
        print(f"  Bounds:               left={rep['bounds'].left:.6f}, bottom={rep['bounds'].bottom:.6f}, right={rep['bounds'].right:.6f}, top={rep['bounds'].top:.6f}")
        print(f"  Transform:            {rep['transform']}")
        print(f"  NoData Value:         {rep['nodata']}")
        print(f"  Pixel Value Min / Max:{rep['min_val']} / {rep['max_val']}")
        print(f"  Total Pixels:         {rep['total_pixels']:,}")
        print(f"  Non-Zero Pixels:      {rep['non_zero_count']:,} ({rep['pct_non_zero']:.2f}%)")

    # Validations
    print("\n" + "=" * 80)
    print("                         VALIDATION CHECKS")
    print("=" * 80)

    all_passed = True

    # 1. Check RGB (B02, B03, B04) alignment
    print("\n[Check 1] RGB Bands (B02, B03, B04) Alignment:")
    rgb_dims_match = (
        reports["B02"]["width"] == reports["B03"]["width"] == reports["B04"]["width"]
        and reports["B02"]["height"] == reports["B03"]["height"] == reports["B04"]["height"]
    )
    rgb_crs_match = reports["B02"]["crs"] == reports["B03"]["crs"] == reports["B04"]["crs"]
    rgb_bounds_match = reports["B02"]["bounds"] == reports["B03"]["bounds"] == reports["B04"]["bounds"]
    rgb_transform_match = reports["B02"]["transform"] == reports["B03"]["transform"] == reports["B04"]["transform"]

    print(f"  - Dimensions Match (WxH):  {'PASS' if rgb_dims_match else 'FAIL'} ({reports['B02']['width']}x{reports['B02']['height']})")
    print(f"  - CRS Match:               {'PASS' if rgb_crs_match else 'FAIL'} ({reports['B02']['crs']})")
    print(f"  - Geographic Bounds Match: {'PASS' if rgb_bounds_match else 'FAIL'}")
    print(f"  - Affine Transform Match:  {'PASS' if rgb_transform_match else 'FAIL'}")

    if not (rgb_dims_match and rgb_crs_match and rgb_bounds_match and rgb_transform_match):
        all_passed = False

    # 2. Check B08 (NIR) alignment with RGB
    print("\n[Check 2] B08 (NIR) Alignment with RGB (B02/B03/B04):")
    b08_dims_match = (reports["B08"]["width"] == reports["B02"]["width"] and reports["B08"]["height"] == reports["B02"]["height"])
    b08_crs_match = (reports["B08"]["crs"] == reports["B02"]["crs"])
    b08_bounds_match = (reports["B08"]["bounds"] == reports["B02"]["bounds"])
    b08_transform_match = (reports["B08"]["transform"] == reports["B02"]["transform"])

    print(f"  - Dimensions Match (WxH):  {'PASS' if b08_dims_match else 'FAIL'} ({reports['B08']['width']}x{reports['B08']['height']})")
    print(f"  - CRS Match:               {'PASS' if b08_crs_match else 'FAIL'} ({reports['B08']['crs']})")
    print(f"  - Geographic Bounds Match: {'PASS' if b08_bounds_match else 'FAIL'}")
    print(f"  - Affine Transform Match:  {'PASS' if b08_transform_match else 'FAIL'}")

    if not (b08_dims_match and b08_crs_match and b08_bounds_match and b08_transform_match):
        all_passed = False

    # 3. Check for non-zero / non-empty data
    print("\n[Check 3] Non-Zero & Non-Empty Pixel Verification:")
    for b in required_bands:
        is_non_empty = reports[b]["pct_non_zero"] > 0 and reports[b]["max_val"] > reports[b]["min_val"]
        status = "PASS" if is_non_empty else "FAIL"
        print(f"  - Band {b}: {status} ({reports[b]['pct_non_zero']:.2f}% non-zero, range [{reports[b]['min_val']}, {reports[b]['max_val']}])")
        if not is_non_empty:
            all_passed = False

    print("\n" + "=" * 80)
    print(f"FINAL RESULT: {'ALL CHECKS PASSED (PASS)' if all_passed else 'VALIDATION FAILED (FAIL)'}")
    print("=" * 80)
    return 0 if all_passed else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
