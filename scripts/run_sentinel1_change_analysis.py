"""
scripts/run_sentinel1_change_analysis.py — Sentinel-1 Temporal Change Detection CLI
===================================================================================
Usage:
  python -m scripts.run_sentinel1_change_analysis --before-date 2026-03-13 --after-date 2026-06-17
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from semantic_search.sentinel1_change import run_sentinel1_temporal_change_analysis


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="TriNetraAI — Sentinel-1 Temporal Dual-Polarization Change Analysis"
    )
    parser.add_argument(
        "--before-date",
        type=str,
        default="2026-03-13",
        help="Baseline/before acquisition date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--after-date",
        type=str,
        default="2026-06-17",
        help="Target/after acquisition date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=35.0,
        help="SAR change magnitude pixel significance threshold (default: 35.0)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Optional custom output directory for change maps and reports",
    )
    parser.add_argument(
        "--no-mosaic",
        action="store_true",
        help="Skip generating the full-AOI GeoTIFF change mosaic",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    print("\n" + "=" * 65)
    print("TRINETRA AI — SENTINEL-1 TEMPORAL SAR CHANGE ENGINE")
    print("=" * 65)
    print(f"Before Acquisition : {args.before_date}")
    print(f"After Acquisition  : {args.after_date}")
    print(f"Change Threshold   : {args.threshold}")

    try:
        report = run_sentinel1_temporal_change_analysis(
            before_date=args.before_date,
            after_date=args.after_date,
            output_dir=args.output_dir,
            change_threshold=args.threshold,
            save_mosaic=not args.no_mosaic,
        )

        print("\n" + "-" * 65)
        print("ANALYSIS RESULTS & SUMMARY")
        print("-" * 65)
        print(f"Tile Pairs Matched     : {report['pairs_matched']}")
        print(f"Tile Pairs Processed   : {report['pairs_processed']}")
        print(f"Tile Pairs Failed      : {report['pairs_failed']}")
        print(f"Average dVV Magnitude  : {report['aoi_summary']['avg_vv_mean_diff']} (uint8 amplitude)")
        print(f"Average dVH Magnitude  : {report['aoi_summary']['avg_vh_mean_diff']} (uint8 amplitude)")
        print(f"Combined Change Score  : {report['aoi_summary']['avg_combined_change_score']} [0.0 - 1.0]")
        print(f"Avg Changed Pixel Ratio: {report['aoi_summary']['avg_changed_pixel_ratio'] * 100:.1f}%")
        print("\nIntensity Distribution :")
        for level, count in report['aoi_summary']['intensity_distribution'].items():
            print(f"  - {level:<12}: {count} tiles")

        print("\nTop 3 Highest SAR Change Tiles:")
        for t in report['top_high_change_tiles'][:3]:
            print(f"  * Tile {t['tile_index']:>2}: Score={t['combined_change_score']:.4f} | dVV={t['vv_mean_diff']:.1f}, dVH={t['vh_mean_diff']:.1f} | Intensity={t['intensity_level']}")

        print("\nTop 3 Lowest SAR Change Tiles:")
        for t in report['top_low_change_tiles'][:3]:
            print(f"  * Tile {t['tile_index']:>2}: Score={t['combined_change_score']:.4f} | dVV={t['vv_mean_diff']:.1f}, dVH={t['vh_mean_diff']:.1f} | Intensity={t['intensity_level']}")

        if report.get('mosaic_path'):
            print(f"\nFull AOI Change Mosaic : {report['mosaic_path']}")
        print(f"Output Directory       : {report['output_directory']}")
        print("=" * 65 + "\n")
        return 0

    except Exception as exc:
        print(f"\n[ERROR] Sentinel-1 change analysis failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
