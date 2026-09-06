"""Run query expansion and prompt ensemble evaluation against satellite search."""

import argparse
from pathlib import Path

from semantic_search.evaluation import DEFAULT_EVALUATION_DIR
from semantic_search.query_expansion import (
    ALL_BENCHMARK_QUERIES,
    evaluate_query_ensemble,
    format_ensemble_report,
    save_ensemble_results,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run query expansion / prompt ensemble experiment for Semantic AI."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_EVALUATION_DIR,
        help=f"Directory to save experiment results (default: {DEFAULT_EVALUATION_DIR})",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=4,
        help="Number of top search results per query (default: 4)",
    )
    args = parser.parse_args()

    print(f"Starting query expansion / prompt ensemble experiment ({len(ALL_BENCHMARK_QUERIES)} queries)...")
    try:
        ensemble_data = evaluate_query_ensemble(top_k=args.top_k)
        report_text = format_ensemble_report(ensemble_data)
        print(report_text)

        json_path, csv_path = save_ensemble_results(
            ensemble_data,
            output_dir=args.output_dir,
            filename_prefix="query_ensemble_results",
        )
        print(f"\nEnsemble experiment results successfully saved to:")
        print(f"  JSON: {json_path}")
        print(f"  CSV:  {csv_path}")
    except Exception as error:
        print(f"ERROR during ensemble experiment: {error}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
