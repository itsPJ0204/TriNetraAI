"""Run reproducible baseline, complex multi-concept, and prompt-ensemble evaluation for Semantic AI satellite search."""

import argparse
from pathlib import Path
from semantic_search.evaluation import (
    BASELINE_QUERIES,
    COMPLEX_QUERIES,
    DEFAULT_EVALUATION_DIR,
    evaluate_queries,
    format_evaluation_report,
    save_evaluation_results,
)
from semantic_search.metrics import (
    evaluate_ensemble_retrieval_metrics,
    evaluate_retrieval_metrics,
    generate_retrieval_metrics_report,
    save_metrics_results,
)
from semantic_search.query_expansion import (
    ALL_BENCHMARK_QUERIES,
    evaluate_query_ensemble,
    format_ensemble_report,
    save_ensemble_results,
)


def run_benchmark(
    queries: tuple[str, ...],
    benchmark_name: str,
    filename_prefix: str,
    output_dir: Path,
    top_k: int,
) -> None:
    print(f"\n--- Running {benchmark_name} ({len(queries)} queries, top_k={top_k}) ---")
    evaluation_data = evaluate_queries(queries=queries, top_k=top_k)
    report_text = format_evaluation_report(
        evaluation_data, title=f"SEMANTIC AI {benchmark_name.upper()} REPORT"
    )
    print(report_text)

    json_path, csv_path = save_evaluation_results(
        evaluation_data,
        output_dir=output_dir,
        filename_prefix=filename_prefix,
    )
    print(f"Results saved to:")
    print(f"  JSON: {json_path}")
    print(f"  CSV:  {csv_path}")


def run_ensemble_benchmark(output_dir: Path, top_k: int) -> None:
    print(f"\n--- Running Prompt Ensemble Experiment ({len(ALL_BENCHMARK_QUERIES)} queries, top_k={top_k}) ---")
    ensemble_data = evaluate_query_ensemble(top_k=top_k)
    report_text = format_ensemble_report(ensemble_data)
    print(report_text)

    json_path, csv_path = save_ensemble_results(
        ensemble_data,
        output_dir=output_dir,
        filename_prefix="query_ensemble_results",
    )
    print(f"Ensemble results saved to:")
    print(f"  JSON: {json_path}")
    print(f"  CSV:  {csv_path}")


def run_retrieval_metrics_benchmark(output_dir: Path, top_k: int) -> None:
    print(f"\n--- Running Retrieval Quality Metrics Evaluation ({len(ALL_BENCHMARK_QUERIES)} queries, top_k={top_k}) ---")
    single_metrics = evaluate_retrieval_metrics(top_k=top_k)
    ensemble_metrics = evaluate_ensemble_retrieval_metrics(top_k=top_k)

    single_json, single_csv = save_metrics_results(
        single_metrics, output_dir=output_dir, filename_prefix="retrieval_metrics"
    )
    ens_json, ens_csv = save_metrics_results(
        ensemble_metrics, output_dir=output_dir, filename_prefix="ensemble_metrics"
    )

    report_path = output_dir / "retrieval_metrics_report.txt"
    report_text = generate_retrieval_metrics_report(
        single_metrics, ensemble_metrics, output_path=report_path
    )
    print(report_text)
    print(f"\nRetrieval metrics saved to:")
    print(f"  JSON (Single)   : {single_json}")
    print(f"  CSV (Single)    : {single_csv}")
    print(f"  JSON (Ensemble) : {ens_json}")
    print(f"  CSV (Ensemble)  : {ens_csv}")
    print(f"  Report (Text)   : {report_path}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run reproducible Semantic AI search evaluation benchmarks."
    )
    parser.add_argument(
        "--mode",
        choices=["baseline", "complex", "ensemble", "metrics", "all"],
        default="all",
        help="Evaluation benchmark mode: 'baseline', 'complex', 'ensemble', 'metrics', or 'all' (default: all)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_EVALUATION_DIR,
        help=f"Directory to save evaluation reports (default: {DEFAULT_EVALUATION_DIR})",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=4,
        help="Number of top search results per query (default: 4)",
    )
    args = parser.parse_args()

    try:
        if args.mode in ("baseline", "all"):
            run_benchmark(
                queries=BASELINE_QUERIES,
                benchmark_name="Simple Baseline Evaluation",
                filename_prefix="baseline_results",
                output_dir=args.output_dir,
                top_k=args.top_k,
            )

        if args.mode in ("complex", "all"):
            run_benchmark(
                queries=COMPLEX_QUERIES,
                benchmark_name="Multi-Concept Complex Query Evaluation",
                filename_prefix="complex_query_results",
                output_dir=args.output_dir,
                top_k=args.top_k,
            )

        if args.mode in ("ensemble", "all"):
            run_ensemble_benchmark(
                output_dir=args.output_dir,
                top_k=args.top_k,
            )

        if args.mode in ("metrics", "all"):
            run_retrieval_metrics_benchmark(
                output_dir=args.output_dir,
                top_k=args.top_k,
            )
    except Exception as error:
        print(f"ERROR during evaluation: {error}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())


