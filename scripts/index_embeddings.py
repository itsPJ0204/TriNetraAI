"""Index locally saved RemoteCLIP embeddings in local Qdrant."""

from semantic_search.vector_store import (
    COLLECTION_NAME,
    create_collection_if_needed,
    get_qdrant_client,
    load_embeddings_and_paths,
    remove_stale_points,
    upload_embeddings,
)


def main() -> int:
    """Create the collection if needed and upsert every saved embedding."""
    try:
        embeddings, image_paths = load_embeddings_and_paths()
        client = get_qdrant_client()
        create_collection_if_needed(client, vector_dimension=embeddings.shape[1])
        removed_count = remove_stale_points(client, image_paths)
        print(f"Removed stale vectors: {removed_count}")
        upload_embeddings(client, embeddings, image_paths)
    except (FileNotFoundError, ValueError) as error:
        print(f"ERROR: {error}")
        return 1

    stored_count = client.count(COLLECTION_NAME, exact=True).count
    print(f"Collection: {COLLECTION_NAME}")
    print(f"Vector dimension: {embeddings.shape[1]}")
    print(f"Vectors stored: {stored_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
