from pathlib import Path

from PIL import Image

from semantic_search import search_by_image


def print_results(title, results):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)

    if not results:
        print("No results found.")
        return

    for i, result in enumerate(results, start=1):
        print(
            f"{i}. tile={result.tile_name} "
            f"| score={result.score:.4f} "
            f"| date={result.date}"
        )
        print(f"   path={result.image_path}")
        print(f"   bounds={result.bounds}")


def main():
    # Query image already present in the Qdrant index.
    image_path = Path(
        "data/tiles/sentinel2/2026-06-27/sentinel2_tile_10.tif"
    )

    if not image_path.exists():
        raise FileNotFoundError(
            f"Query image not found: {image_path}"
        )

    print(f"Query image: {image_path}")

    image = Image.open(image_path)

    # ---------------------------------------------------------
    # 1. IMAGE-ONLY SEARCH
    # ---------------------------------------------------------
    results = search_by_image(
        image=image,
        top_k=5,
    )

    print_results(
        "1. IMAGE-ONLY SEARCH",
        results,
    )

    # ---------------------------------------------------------
    # 2. IMAGE + TEXT SEARCH
    # ---------------------------------------------------------
    results = search_by_image(
        image=image,
        query="dense urban area near water",
        top_k=5,
    )

    print_results(
        "2. IMAGE + TEXT SEARCH",
        results,
    )

    # ---------------------------------------------------------
    # 3. IMAGE + TEXT + BBOX SEARCH
    # ---------------------------------------------------------
    bbox = {
        "left": 77.20,
        "bottom": 28.58,
        "right": 77.25,
        "top": 28.64,
    }

    results = search_by_image(
        image=image,
        query="urban area near water",
        top_k=5,
        bbox=bbox,
    )

    print_results(
        "3. IMAGE + TEXT + BBOX SEARCH",
        results,
    )

    # ---------------------------------------------------------
    # 4. IMAGE SEARCH USING FILE PATH
    # ---------------------------------------------------------
    results = search_by_image(
        image=image_path,
        top_k=3,
    )

    print_results(
        "4. IMAGE SEARCH USING FILE PATH",
        results,
    )

    # ---------------------------------------------------------
    # 5. BBOX-ONLY SANITY TEST
    # ---------------------------------------------------------
    # This bbox is tightly around tile_10 of 2026-06-27.
    bbox_tight = {
        "left": 77.2259,
        "bottom": 28.6233,
        "right": 77.2490,
        "top": 28.6436,
    }

    results = search_by_image(
        image=image,
        top_k=10,
        bbox=bbox_tight,
    )

    print_results(
        "5. IMAGE-ONLY + TIGHT BBOX SEARCH",
        results,
    )


if __name__ == "__main__":
    main()