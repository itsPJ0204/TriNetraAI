"""Run image-to-image or multimodal search against indexed satellite tiles from CLI."""

import argparse
from pathlib import Path
import sys

from semantic_search.search import search_by_image


def main(argv: list[str] | None = None) -> int:
    """Parse CLI args and print Qdrant's ranked tile matches for image/multimodal queries."""
    parser = argparse.ArgumentParser(
        description="Image-to-image and multimodal semantic search for satellite tiles."
    )
    parser.add_argument("image", help="Path to query image file or GeoTIFF tile")
    parser.add_argument(
        "--query",
        "-q",
        default=None,
        help="Optional text query for multimodal image + text fusion",
    )
    parser.add_argument(
        "--top-k",
        "-k",
        type=int,
        default=5,
        help="Number of ranked results to return (default: 5)",
    )
    parser.add_argument(
        "--bbox",
        nargs=4,
        type=float,
        metavar=("LEFT", "BOTTOM", "RIGHT", "TOP"),
        help="Optional geographic bounding box filter: left bottom right top",
    )
    parser.add_argument(
        "--alpha",
        type=float,
        default=0.5,
        help="Image weight factor in multimodal fusion [0.0 to 1.0] (default: 0.5)",
    )
    parser.add_argument(
        "--fusion-strategy",
        choices=["weighted_sum", "average", "image_only", "text_only"],
        default="weighted_sum",
        help="Multimodal fusion strategy (default: weighted_sum)",
    )
    parser.add_argument(
        "--image-weight",
        type=float,
        default=None,
        help="Explicit image weight for multimodal fusion",
    )
    parser.add_argument(
        "--text-weight",
        type=float,
        default=None,
        help="Explicit text weight for multimodal fusion",
    )

    args = parser.parse_args(argv)

    # 1. Validate image path
    image_path = Path(args.image)
    if not image_path.exists():
        print(f"ERROR: Image file not found: {args.image}")
        return 1
    if not image_path.is_file():
        print(f"ERROR: Image path is not a file: {args.image}")
        return 1

    # 2. Validate top_k
    if args.top_k <= 0:
        print("ERROR: --top-k must be a positive integer.")
        return 1

    # 3. Validate alpha
    if args.alpha < 0.0 or args.alpha > 1.0:
        print(f"ERROR: --alpha must be between 0.0 and 1.0, got {args.alpha}.")
        return 1

    # 4. Validate query
    query = None
    if args.query is not None:
        cleaned_query = args.query.strip()
        if not cleaned_query:
            print("ERROR: --query cannot be empty or whitespace only.")
            return 1
        query = cleaned_query

    # 5. Validate bounding box
    bbox = None
    if args.bbox is not None:
        left, bottom, right, top = args.bbox
        if left >= right:
            print(
                f"ERROR: Invalid bounding box: 'left' ({left}) must be strictly less than 'right' ({right})."
            )
            return 1
        if bottom >= top:
            print(
                f"ERROR: Invalid bounding box: 'bottom' ({bottom}) must be strictly less than 'top' ({top})."
            )
            return 1
        bbox = {
            "left": left,
            "bottom": bottom,
            "right": right,
            "top": top,
        }

    # 6. Execute search
    try:
        results = search_by_image(
            image=image_path,
            query=query,
            top_k=args.top_k,
            bbox=bbox,
            alpha=args.alpha,
            fusion_strategy=args.fusion_strategy,
            image_weight=args.image_weight,
            text_weight=args.text_weight,
        )
    except (ConnectionError, RuntimeError, ValueError, TypeError, FileNotFoundError) as error:
        print(f"ERROR: {error}")
        return 1

    # 7. Print ranked results
    print("\nSearch Results:")
    if not results:
        print("No matching satellite tiles found.")
        return 0

    for rank, result in enumerate(results, start=1):
        print(f"{rank}. {result.tile_name} — score: {result.score:.6f}")
        print(f"   Path:       {result.image_path}")
        print(f"   CRS:        {result.crs}")
        print(f"   Bounds:     {result.bounds}")
        print(f"   Dimensions: {result.width}x{result.height}")
        print(f"   Date:       {result.date}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
