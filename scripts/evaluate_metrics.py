"""CLI runner for computing objective retrieval quality metrics against human ground truth."""

import argparse
from pathlib import Path
import sys

from semantic_search.evaluation import DEFAULT_EVALUATION_DIR
from semantic_search.metrics import (
    DEFAULT_REPORT_PATH,
    evaluate_ensemble_retrieval_metrics,
    evaluate_retrieval_metrics,
    generate_retrieval_metrics_report,
    save_metrics_results,
)


def main() -> int:
    """Run retrieval quality metrics calculation and output artifacts."""
    parser = argparse.ArgumentParser(
        description="Compute Hit@K, Precision@K, Recall@K, and MRR against ground truth."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_EVALUATION_DIR,
        help="Directory to store metric JSON, CSV, and report files (default: data/evaluation/)",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=4,
        help="Number of retrieved results per query (default: 4)",
    )
    args = parser.parse_args()

    print("Evaluating single-query baseline retrieval metrics...")
    single_metrics = evaluate_retrieval_metrics(top_k=args.top_k)

    print("Evaluating prompt-ensemble retrieval metrics for comparison...")
    ensemble_metrics = evaluate_ensemble_retrieval_metrics(top_k=args.top_k)

    # Save artifacts
    single_json, single_csv = save_metrics_results(
        single_metrics, output_dir=args.output_dir, filename_prefix="retrieval_metrics"
    )
    ensemble_json, ensemble_csv = save_metrics_results(
        ensemble_metrics, output_dir=args.output_dir, filename_prefix="ensemble_metrics"
    )

    report_path = args.output_dir / "retrieval_metrics_report.txt"
    report_text = generate_retrieval_metrics_report(
        single_metrics, ensemble_metrics, output_path=report_path
    )

    print("\n" + report_text)
    print("\nArtifacts successfully written:")
    print(f"  - Single JSON : {single_json.resolve()}")
    print(f"  - Single CSV  : {single_csv.resolve()}")
    print(f"  - Ens JSON    : {ensemble_json.resolve()}")
    print(f"  - Ens CSV     : {ensemble_csv.resolve()}")
    print(f"  - Text Report : {report_path.resolve()}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
