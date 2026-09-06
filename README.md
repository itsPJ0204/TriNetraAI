# Satellite Image Semantic Search

This project supports semantic search over satellite imagery: a user describes a scene in natural language, and the system retrieves satellite-image tiles that are visually and semantically similar to that description.

## Role 2: Semantic AI

Role 2 is responsible for the Semantic AI module. This includes preparing image tiles for embedding, using RemoteCLIP to create image and text embeddings, and using Qdrant to store and compare those vectors.

---

## Quickstart & Developer Setup (For Role 3 / Team Members)

Follow these steps to set up and run the Semantic AI module locally from a fresh clone:

### 1. Create and Activate a Python Virtual Environment

```bash
# Windows (PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Obtain & Place the RemoteCLIP Model Checkpoint

The project uses the official **RemoteCLIP ViT-B-32** model weights. Ensure the checkpoint file `RemoteCLIP-ViT-B-32.pt` is placed in:

```text
models/remoteclip/RemoteCLIP-ViT-B-32.pt
```

*(Note: Model checkpoints are excluded from Git via `.gitignore` to keep repository size lean).*

### 4. Start Local Qdrant Vector Database

Start Qdrant using Docker:

```bash
docker run -d -p 6333:6333 -p 6334:6334 -v qdrant_storage:/qdrant/storage --name qdrant qdrant/qdrant
```

Verify Qdrant is running by checking `http://localhost:6333/dashboard` or `curl http://localhost:6333`.

### 5. Generate Embeddings & Index Tiles (If Starting Fresh)

If the Qdrant collection has not been indexed yet:

```bash
# Generate image embeddings from GeoTIFF tiles
python -m scripts.generate_embeddings

# Index tile vectors and geospatial metadata into Qdrant
python -m scripts.index_embeddings
```

### 6. Run Full Test Suite

```bash
python -m pytest
```

### 7. Import & Use in Role 3 (FastAPI / Application Layer)

Role 3 can import and consume the semantic search engine directly:

```python
from semantic_search import search, SearchResult

# 1. Unconstrained natural-language semantic search
results: list[SearchResult] = search("buildings near a river", top_k=5)

for r in results:
    print(f"Tile: {r.tile_name} | Score: {r.score:.4f}")
    print(f"  Path: {r.image_path}")
    print(f"  CRS: {r.crs}")
    print(f"  Bounds: {r.bounds}")
    print(f"  Dimensions: {r.width}x{r.height}")
    print(f"  Acquisition Date: {r.date}")

# 2. Semantic search with 2D geographic bounding-box filtering
bbox = {"left": 88.345, "bottom": 22.572, "right": 88.360, "top": 22.585}
filtered_results = search("urban area near water", bbox=bbox, top_k=3)

# 3. Convert to dictionary for FastAPI JSON responses
payload = [item.to_dict() for item in results]
```

---

## Planned architecture


1. Rasterio will read GeoTIFF imagery and help prepare tiles.
2. RemoteCLIP will later turn satellite-image tiles and text queries into
   comparable embeddings.
3. Qdrant will later store embeddings and perform similarity search.
4. A FastAPI service may expose the completed functionality in a future phase.

## Phase 1 contents

Phase 1 provides only a clean folder layout, dependency list, Python-module
placeholders, and a small Python environment check. It intentionally does not
download or load RemoteCLIP, create embeddings, connect to Qdrant, create a
Qdrant collection, or implement search.

## Check Python

From this project directory, run:

```bash
python scripts/check_python.py
```

RemoteCLIP and Qdrant integration will be added in later phases.

## Phase 2: RemoteCLIP setup

Phase 2 prepares the official **RemoteCLIP ViT-B-32** model for CPU inference.
Its checkpoint is stored at:

```text
models/remoteclip/RemoteCLIP-ViT-B-32.pt
```

The checkpoint is loaded locally by `semantic_search/model.py`; it is not
downloaded again when it is already present. The loader returns the model,
RemoteCLIP tokenizer, and image preprocessing transform, with the model in
evaluation mode.

Run the setup test from the project directory with:

```bash
python -m tests.test_remoteclip
```

This phase only verifies model setup. It does not create image or text
embeddings, connect to Qdrant, create a collection, or implement search.

## Phase 3: One image to an embedding

An **embedding** is a list of numbers that represents the visual meaning of an
image. In this phase, RemoteCLIP converts one satellite tile into a normalized
vector. The input is one `.tif` or `.tiff` satellite tile in `data/tiles/` and
the output is one in-memory NumPy `float32` RemoteCLIP vector. Nothing is saved
to disk.

Place a single satellite tile in `data/tiles/`, then run:

```bash
python -m tests.test_image_embedding
```

The test prints the input image, embedding shape, data type, and L2 norm. The
vector is normalized to an L2 norm of approximately 1. Normalization makes
similarity scores depend on vector direction (semantic content) rather than
vector magnitude, which makes later similarity comparisons consistent.

This phase handles only one image and does not create text embeddings, a Qdrant
collection, a search system, or an API.

## Phase 4: Multiple tiles to embeddings

Each satellite tile needs its own embedding so that it can later be compared
individually with a query. This phase scans `data/tiles/` for `.tif` and
`.tiff` files, creates one normalized `float32` RemoteCLIP vector per tile, and
keeps the tiles in a stable alphabetical order.

Generate and save all embeddings with:

```bash
python -m scripts.generate_embeddings
```

The embedding matrix is saved to `data/embeddings/image_embeddings.npy`. The
matching tile paths are saved to `data/embeddings/image_paths.json`.
`image_paths.json` is required to retain the image identity after the vectors
are stored: `embeddings[i]` always belongs to `image_paths[i]`.

Validate the tile embeddings with:

```bash
python -m tests.test_multiple_embeddings
```

This phase saves only local NumPy and JSON files. It does not create or connect
to Qdrant, implement vector search or text embeddings, or create an API.

## Phase 5: Qdrant vector store

Qdrant is the local vector store for this project. A vector is the normalized
list of numbers created by RemoteCLIP for one tile. Phase 5 stores those vectors
in the `satellite_tiles` collection at `http://localhost:6333`.

The collection uses cosine similarity because the embeddings are normalized:
cosine similarity compares their direction (semantic meaning) rather than their
size. Each Qdrant point also has a payload, which is descriptive metadata kept
with the vector. Here the payload contains `image_path` and `tile_name`.

If Qdrant is not already running, start it with Docker:

```bash
docker run -p 6333:6333 -p 6334:6334 -v qdrant_storage:/qdrant/storage qdrant/qdrant
```

Index the Phase 4 files with:

```bash
python -m scripts.index_embeddings
```

The script is safe to run again: each point has a stable integer ID and Qdrant
upserts it instead of creating a duplicate. Validate the local collection with:

```bash
python -m tests.test_qdrant
```

This phase stores vectors only. It does not implement semantic search, text
embeddings, FastAPI, FAISS, or another database.

## Phase 6: Text to semantic search

A text embedding is a normalized list of numbers representing the meaning of a
natural-language query. RemoteCLIP tokenizes a query such as `river`, encodes
it as a text vector, and normalizes that vector. Qdrant then compares it with
the existing RemoteCLIP image vectors in `satellite_tiles` using cosine
similarity and returns the most similar tiles.

A similarity score measures how closely the query vector and image vector
align; it is not a percentage or probability. Larger scores indicate a closer
vector match for this query.

Run an interactive search with:

```bash
python -m scripts.search
```

Try queries such as `river`, `urban area`, `forest`, `buildings`, or
`residential area`. In Python, you can choose the result limit with:

```python
search("river", top_k=3)
```

This phase reads the existing Qdrant collection only. It does not regenerate
image embeddings, create a new collection, upload vectors, or implement
filtering, FastAPI, or a frontend.

## Phase 6.5: Split one satellite image into tiles

Satellite images are tiled so later processing can work with smaller, localized
areas instead of one large image. Rasterio is used rather than cropping with
Pillow because it preserves GeoTIFF metadata, including each tile's coordinate
reference system (CRS), datatype, bands, compression settings, and geographic
transform. The transform is essential: it maps each tile's pixels to the
correct real-world location.

Split `data/tiles/test_tile.tiff` into a 2×2 grid with:

```bash
python -m scripts.tile_image
```

This creates `tile_1.tif` through `tile_4.tif` in `data/tiles/` without
overwriting existing tiles. Validate them with:

```bash
python -m tests.test_tiling
```

This is a GeoTIFF preparation step only. It does not create embeddings or
change RemoteCLIP, Qdrant, or semantic search.

## Semantic AI Public Search Interface

The public integration contract provides a clean Python interface for search:

```python
from semantic_search import search, SearchResult

# Unconstrained semantic search
results: list[SearchResult] = search("river", top_k=3)

# Semantic search with optional 2D geographic bounding box filter
bbox = {"left": 88.34, "bottom": 22.57, "right": 88.36, "top": 22.58}
results = search("river", bbox=bbox, top_k=5)

for r in results:
    print(r.tile_name, r.score, r.crs, r.bounds, r.width, r.height, r.date)
```

## Semantic AI Evaluation Framework (Phases 11 & 12)

A reproducible evaluation framework measures search retrieval behavior across two distinct benchmark query sets:

1. **Simple Baseline Queries** (Phase 11): Single-concept queries (`river`, `water`, `road`, `buildings`, `urban area`, `vegetation`, `green area`).
2. **Multi-Concept Complex Queries** (Phase 12): Realistic natural-language queries combining concepts (`urban areas near water`, `buildings near a river`, `roads through green areas`, `water surrounded by vegetation`, `urban area with roads`, `buildings and roads`, `green area near water`, `dense urban area`).

> **Note**: This benchmark measures cosine similarity retrieval rankings without ground-truth labels. Scores indicate embedding alignment rather than verified spatial relationship detection.

### Evaluation Modes

- `baseline`: Simple baseline queries (Phase 11)
- `complex`: Multi-concept complex queries (Phase 12)
- `ensemble`: Prompt ensemble / query expansion experiment (Phase 13)
- `all`: Run all evaluation suites

### Run Evaluation

```bash
# Run all evaluation suites (baseline, complex, ensemble)
python -m scripts.evaluate --mode all

# Run dedicated prompt ensemble evaluation
python -m scripts.evaluate_ensemble

# Or run via evaluate script
python -m scripts.evaluate --mode ensemble
```

### Evaluation Artifacts

- Simple baseline results (Phase 11):
  - `data/evaluation/baseline_results.json`
  - `data/evaluation/baseline_results.csv`
- Complex multi-concept results (Phase 12):
  - `data/evaluation/complex_query_results.json`
  - `data/evaluation/complex_query_results.csv`
- Prompt ensemble / query expansion results (Phase 13):
  - `data/evaluation/query_ensemble_results.json`
  - `data/evaluation/query_ensemble_results.csv`

## Phase 13: Query Expansion / Prompt Ensemble Experiment

Phase 13 introduces an experimental prompt ensembling technique for RemoteCLIP satellite semantic search without modifying the underlying vector database or production `search()` behavior.

For each of the 15 benchmark queries, domain-specific formulations (synonyms, context qualifiers, descriptive rewrites) are evaluated individually and aggregated using mean cosine similarity.

```python
from semantic_search import compare_query_ensemble

# Compare single-query baseline against prompt ensemble
comparison = compare_query_ensemble("river", top_k=4)
print("Baseline top tile:", comparison["single_query_results"][0]["tile_name"])
print("Ensemble top tile:", comparison["ensemble_results"][0]["tile_name"])
print("Ranking changed:", comparison["top_rank_changed"])
```

## Phase 14: Ground-Truth Dataset for Semantic AI Evaluation

Phase 14 establishes a human visual ground-truth dataset across all 15 benchmark concepts and 4 satellite tiles.

### Why Ground Truth is Needed
Vector retrieval scores (cosine similarity) only measure embedding distance in RemoteCLIP space and do not guarantee physical presence or absence of geographical features. Ground truth provides an objective human visual baseline against which future retrieval quality metrics (e.g. Precision@K, Recall@K, MRR) can be computed.

### Labeling Methodology & Storage
- **File location**: [`data/evaluation/ground_truth.json`](file:///c:/Users/rahim/OneDrive/Desktop/semantic-search/satellite-semantic-search/data/evaluation/ground_truth.json)
- **Labeling Rules**: Conservative visual relevance. A tile is marked relevant only if the queried concept is visibly present at a meaningful level upon direct inspection of the 3-band GeoTIFF imagery.
- **Uncertainty Tracking**: Boundary or ambiguous features (such as narrow canals vs. major rivers) are explicitly documented in the dataset metadata.
- **Evaluation Metrics**: Metric calculations (Precision@K, Recall@K, MRR, MAP) will be implemented in a subsequent phase.

### Validate Ground Truth Dataset

```bash
# Run CLI ground truth validator
python -m scripts.validate_ground_truth
```

In Python:
```python
from semantic_search import load_ground_truth, validate_ground_truth, get_relevant_tiles

# Load dataset and check validity
errors = validate_ground_truth()
assert errors == []

# Get relevant tiles for a concept
river_tiles = get_relevant_tiles("river")
print("Relevant tiles for 'river':", river_tiles)
```

## Phase 15: Objective Retrieval Quality Metrics

Phase 15 computes deterministic retrieval quality metrics comparing single-query baseline search and prompt ensemble against human ground-truth visual labels.

### Metric Definitions

- **Hit@K**: Binary indicator (1 or 0) indicating whether at least one human-verified relevant tile appears in the top-$K$ retrieved results.
- **Precision@K**: $\frac{\text{Count of relevant tiles in top } K}{K}$.
- **Recall@K**: $\frac{\text{Count of relevant tiles in top } K}{\text{Total relevant tiles in ground truth}}$.
- **MRR (Mean Reciprocal Rank)**: $\frac{1}{N} \sum_{i=1}^N \frac{1}{\text{rank}_i}$, where $\text{rank}_i$ is the 1-indexed rank of the first relevant tile retrieved for query $i$ (or 0 if none found).

### Run Metrics Evaluation

```bash
# Run dedicated retrieval metrics evaluation & generate comparison report
python -m scripts.evaluate_metrics

# Or run via benchmark CLI
python -m scripts.evaluate --mode metrics
```

### Generated Artifacts

- **Single Query Metrics**:
  - `data/evaluation/retrieval_metrics.json`
  - `data/evaluation/retrieval_metrics.csv`
- **Ensemble Comparison Metrics**:
  - `data/evaluation/ensemble_metrics.json`
  - `data/evaluation/ensemble_metrics.csv`
- **Comprehensive Text Report**:
  - `data/evaluation/retrieval_metrics_report.txt`

### Dataset Scale & Methodological Limitations
The evaluation index contains exactly 4 satellite tiles. With $N=4$, metrics at $K=4$ naturally equal $1.0$ whenever candidate features exist. These metrics provide an objective prototype baseline rather than large-scale statistical validation.

## Phase 16: Search Robustness & Query Handling

Phase 16 ensures that the semantic search interface operates reliably across a wide variety of user query formats without altering model weights or adding unnecessary dependencies.

### Key Robustness Capabilities

1. **Whitespace Normalization (`normalize_query`)**:
   - Trims leading and trailing whitespace.
   - Collapses arbitrary internal whitespace sequences (spaces, tabs, newlines) into single spaces (e.g. `"buildings    near    a    river"` $\rightarrow$ `"buildings near a river"`).
2. **Input Validation**:
   - Explicitly checks query type and content, raising a descriptive `ValueError` for empty strings, whitespace-only strings, or non-string inputs.
   - Rejects non-positive or invalid `top_k` values.
   - Validates 2D geographic bounding boxes (`left < right` and `bottom < top`).
3. **Casing Invariance**:
   - Uppercase (`"RIVER"`), mixed-case (`"RiVeR"`), and lowercase (`"river"`) queries produce consistent vector embeddings and identical top-ranked retrieval results.
4. **Supported Query Forms**:
   - Simple keyword queries (e.g. `"river"`, `"buildings"`).
   - Synonym and alternative expressions (e.g. `"water body"`, `"constructed buildings"`).
   - Multi-concept and natural-language queries (e.g. `"find urban areas with roads and green spaces"`).
   - Out-of-domain and ambiguous queries gracefully return similarity-ranked tiles without runtime failures.

### Run Robustness Evaluation

```bash
python -m scripts.evaluate_robustness
```

### Important Retrieval Boundaries
- **Ranking Signals vs. Object Detection**: Cosine similarity scores represent embedding alignment in multi-modal vector space, not deterministic object detection or area segmentation.
- **Spatial Reasoning Limitations**: Complex relational queries (such as `"buildings near a river"`) retrieve tiles matching joint semantic concepts, but RemoteCLIP does not perform formal geometric or topological spatial reasoning.

## Phase 17: Search Performance & Resource Efficiency

Phase 17 profiles search latency components, eliminates redundant disk and network I/O, and introduces safe in-memory caching to optimize CPU search performance.

### Architectural Optimizations

1. **RemoteCLIP Model & Tokenizer Reuse**:
   - Cached in memory using thread-safe locking (`load_remoteclip()`).
   - Eliminates redundant ~350MB checkpoint reads from disk, reducing warm inference latency from ~2.88s to ~58ms.
2. **Qdrant Client Connection Reuse**:
   - Connection pool is safely reused across queries via `get_qdrant_client()`, avoiding repeated collection lookups and connection teardowns.
3. **In-Memory Query Embedding Cache**:
   - Normalized queries are cached in a bounded in-memory store (max 128 entries).
   - Re-evaluating frequent queries executes in sub-millisecond time.
   - Note: Search results themselves are not cached, ensuring dynamic `top_k` and `bbox` parameters always query Qdrant.
4. **Optimized Inference**:
   - Uses `torch.inference_mode()` on CPU for tensor encoding without autograd tracking overhead.

### Run Performance Benchmark

```bash
python -m scripts.benchmark_search
```

### Measured Performance Summary (CPU Execution)

| Operation | Baseline (Cold / Uncached) | Optimized (Warm Search) | Speedup Factor |
| :--- | :--- | :--- | :--- |
| **Model Load Time** | ~3,166 ms (~3.17 s) | *Cached in memory* | Instant reuse |
| **Text Embedding Latency** | ~2,880 ms (~2.88 s) | **~58 ms** (initial) / **<0.1 ms** (cached) | **~50x - 28000x** |
| **Qdrant Vector Query** | ~27 ms | **~25 ms** | Reused TCP pool |
| **End-to-End Search Latency**| ~2,608 ms (~2.61 s) | **~77 ms** (0.077 s) | **~33.6x faster** |

> **Hardware Note**: Benchmark figures reflect local CPU execution (Intel/AMD multi-core). Absolute latencies vary depending on host CPU clock speed, RAM bandwidth, and system load.
