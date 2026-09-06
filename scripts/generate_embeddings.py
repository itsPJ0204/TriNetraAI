"""Generate and save RemoteCLIP embeddings for all local satellite tiles."""

import json

import numpy as np

from semantic_search.embeddings import PROJECT_ROOT, generate_tile_embeddings


EMBEDDINGS_DIRECTORY = PROJECT_ROOT / "data" / "embeddings"
EMBEDDINGS_PATH = EMBEDDINGS_DIRECTORY / "image_embeddings.npy"
IMAGE_PATHS_PATH = EMBEDDINGS_DIRECTORY / "image_paths.json"


def main() -> int:
    """Generate embeddings and save paths in the identical tile order."""
    try:
        embeddings, image_paths = generate_tile_embeddings()
    except FileNotFoundError as error:
        print(f"ERROR: {error}")
        return 1

    EMBEDDINGS_DIRECTORY.mkdir(parents=True, exist_ok=True)
    np.save(EMBEDDINGS_PATH, embeddings)
    relative_paths = [path.relative_to(PROJECT_ROOT).as_posix() for path in image_paths]
    IMAGE_PATHS_PATH.write_text(json.dumps(relative_paths, indent=2), encoding="utf-8")

    print(f"Embedding matrix shape: {embeddings.shape}")
    print(f"Embedding dtype: {embeddings.dtype}")
    print(f"Processed tiles: {len(image_paths)}")
    print(f"Saved embeddings: {EMBEDDINGS_PATH}")
    print(f"Saved image paths: {IMAGE_PATHS_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
