"""Run an interactive or argument-based text search against indexed satellite tiles."""

import argparse
from semantic_search.search import search


def main() -> int:
    """Parse CLI args or ask for a query and print Qdrant's ranked tile matches."""
    parser = argparse.ArgumentParser(description="Semantic search for satellite tiles.")
    parser.add_argument("query", nargs="?", default="", help="Text search query")
    parser.add_argument(
        "--bbox",
        nargs=4,
        type=float,
        metavar=("LEFT", "BOTTOM", "RIGHT", "TOP"),
        help="Optional geographic bounding box filter: left bottom right top",
    )
    args = parser.parse_args()

    query = args.query.strip()
    if not query:
        query = input("Enter search query: ").strip()

    bbox = None
    if args.bbox is not None:
        bbox = {
            "left": args.bbox[0],
            "bottom": args.bbox[1],
            "right": args.bbox[2],
            "top": args.bbox[3],
        }

    try:
        results = search(query, bbox=bbox)
    except (ConnectionError, RuntimeError, ValueError) as error:
        print(f"ERROR: {error}")
        return 1

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

