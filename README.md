# TriNetraAI

TriNetraAI is an offline satellite imagery search and change detection system designed for high-performance geospatial intelligence.

The **Semantic AI** module enables users to discover and rank satellite image tiles using natural-language descriptions (such as *"buildings near a river"*, *"dense urban area"*, or *"water surrounded by vegetation"*) combined with optional 2D geographic bounding-box spatial filters.

---

## Key Features

- **Natural Language Satellite Search**: Query satellite imagery directly with natural language using RemoteCLIP (ViT-B/32) vision-language embeddings.
- **2D Geographic Filtering**: Intersect semantic search with spatial bounding boxes (latitude/longitude coordinates) via native Qdrant payload filters.
- **CPU Inference Optimized**: In-memory singleton caching and query embedding reuse deliver fast response times (~77ms warm search latency on standard multi-core CPUs).
- **Clean Decoupled API**: Exposes a stable, typed Python interface (`search()` -> `list[SearchResult]`) isolating downstream APIs (FastAPI / Web Clients) from vector store internals.
- **Geospatial Integrity**: Full preservation of Coordinate Reference Systems (CRS), affine transforms, and geographic extents using Rasterio.

---

## Architecture & Tech Stack

```
+-------------------------------------------------------------------------+
|                              TriNetraAI                                 |
|                                                                         |
|   +-------------------+    +--------------------+    +--------------+   |
|   |  GeoTIFF Imagery  | -> |  RemoteCLIP Vision | -> | 512-D L2-Norm|   |
|   | (Rasterio Tiles)  |    |   Encoder (CPU)    |    |   Vectors    |   |
|   +-------------------+    +--------------------+    +-------+------+   |
|                                                              |          |
|                                                              v          |
|   +-------------------+    +--------------------+    +--------------+   |
|   |  Text Query (CLI/ | -> |  RemoteCLIP Text   | -> | Qdrant Vector|   |
|   |  FastAPI / Python)|    |   Encoder (CPU)    |    |   Database   |   |
|   +-------------------+    +--------------------+    +-------+------+   |
|                                                              |          |
|                                                              v          |
|                                                     +---------------+   |
|                                                     |  SearchResult |   |
|                                                     | Domain Models |   |
|                                                     +---------------+   |
+-------------------------------------------------------------------------+
```

- **Vision-Language Model**: [RemoteCLIP](https://github.com/ChenDelong1999/RemoteCLIP) (ViT-B/32)
- **Vector Database**: [Qdrant](https://qdrant.tech/) (Cosine Similarity, 512 dimensions)
- **Geospatial Processing**: [Rasterio](https://rasterio.readthedocs.io/) & [Pillow](https://python-pillow.org/)
- **Runtime**: Python 3.10+ (PyTorch CPU)

---

## Project Structure

```text
satellite-semantic-search/
├── data/
│   ├── evaluation/         # Ground-truth visual labels & benchmark results
│   ├── embeddings/         # Generated tile vector embeddings (.npy, .json)
│   └── tiles/              # GeoTIFF satellite image tiles (.tif)
├── docs/
│   └── semantic_ai_integration.md  # Detailed team integration specification
├── models/
│   └── remoteclip/         # RemoteCLIP ViT-B-32 checkpoint location
├── scripts/
│   ├── benchmark_search.py # CPU latency and memory benchmarking
│   ├── evaluate.py         # Search evaluation orchestrator
│   ├── evaluate_ensemble.py# Prompt ensemble / expansion evaluation
│   ├── evaluate_metrics.py # Retrieval quality metrics (MRR, Precision@K, Hit@K)
│   ├── evaluate_robustness.py # Query normalization and edge-case testing
│   ├── generate_embeddings.py # Generate RemoteCLIP vectors from tiles
│   ├── index_embeddings.py # Upsert vectors and metadata into Qdrant
│   ├── search.py           # Interactive CLI search utility
│   ├── tile_image.py       # Split satellite GeoTIFF into tiles
│   └── validate_production_readiness.py # Master system audit suite
├── semantic_search/
│   ├── __init__.py         # Public exports (search, SearchResult, metrics)
│   ├── config.py           # System configuration & default paths
│   ├── embeddings.py       # Image embedding extraction
│   ├── evaluation.py       # Benchmark query suites
│   ├── ground_truth.py     # Ground-truth dataset loaders
│   ├── metrics.py          # Metric calculations (Precision, Recall, MRR, Hit)
│   ├── model.py            # Thread-safe RemoteCLIP model loader
│   ├── query_expansion.py  # Multi-prompt ensembling & expansion
│   ├── schemas.py          # SearchResult domain models
│   ├── search.py           # Core search API & geographic filter builder
│   └── vector_store.py     # Qdrant client connection & collection manager
├── tests/                  # Complete test suite (76 tests)
├── requirements.txt        # Python package dependencies
└── README.md
```

---

## Setup & Installation

### 1. Create Virtual Environment

```bash
# Windows
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

### 3. Model Checkpoint Setup

Download the official **RemoteCLIP ViT-B-32** model weights and place the checkpoint file in:

```text
models/remoteclip/RemoteCLIP-ViT-B-32.pt
```

*(Note: Model checkpoints are excluded from Git via `.gitignore` to keep repository size minimal).*

### 4. Start Qdrant Vector Database

Start a local Qdrant instance using Docker:

```bash
docker run -d -p 6333:6333 -p 6334:6334 \
  -v qdrant_storage:/qdrant/storage \
  --name qdrant qdrant/qdrant
```

## Ingestion & Indexing Pipeline

When adding new satellite imagery or starting with a fresh vector index:

```bash
# 1. (Optional) Tile a large GeoTIFF into smaller grid tiles
python -m scripts.tile_image

# 2. Generate 512-D RemoteCLIP embeddings for all tiles in data/tiles/
python -m scripts.generate_embeddings

# 3. Index vectors and geospatial metadata into Qdrant
python -m scripts.index_embeddings
```

---

## Usage

### 1. CLI Search

Run interactive or argument-based natural language searches from the terminal:

```bash
# Simple natural language query
python -m scripts.search "buildings near a river"

# Search with geographic bounding-box filter [left, bottom, right, top]
python -m scripts.search "urban area" --bbox 88.345 22.572 88.360 22.585
```

### 2. Programmatic Python API

Import and call the search engine directly in your Python applications:

```python
from semantic_search import search, SearchResult

# Unconstrained natural-language search
results: list[SearchResult] = search("buildings near a river", top_k=5)

for r in results:
    print(f"Tile: {r.tile_name} | Score: {r.score:.4f}")
    print(f"  Path:       {r.image_path}")
    print(f"  CRS:        {r.crs}")
    print(f"  Bounds:     {r.bounds}")
    print(f"  Dimensions: {r.width}x{r.height}")
    print(f"  Date:       {r.date}")

# Search with 2D spatial bounding-box constraint
bbox = {
    "left": 88.345,
    "bottom": 22.572,
    "right": 88.360,
    "top": 22.585,
}
filtered_results = search("urban area near water", bbox=bbox, top_k=3)
```

### SearchResult Schema

Every result returned is a typed `SearchResult` instance containing:

| Attribute | Type | Description | Example |
| :--- | :--- | :--- | :--- |
| `tile_name` | `str` | Filename identifier of the tile | `"tile_1.tif"` |
| `image_path` | `str` | Relative file path to the GeoTIFF | `"data/tiles/tile_1.tif"` |
| `score` | `float` | Cosine similarity score | `0.2814` |
| `crs` | `str` | Coordinate Reference System | `"EPSG:4326"` |
| `bounds` | `dict[str, float]` | Extent coordinates (`left`, `bottom`, `right`, `top`) | `{"left": 88.34, "bottom": 22.57, "right": 88.36, "top": 22.58}` |
| `width` | `int` | Raster pixel width | `233` |
| `height` | `int` | Raster pixel height | `191` |
| `date` | `str` | Acquisition date (ISO 8601: `YYYY-MM-DD`) | `"2025-03-29"` |

---

## FastAPI Integration Example (Role 3)

Downstream backend services can easily expose semantic search endpoints:

```python
from fastapi import FastAPI, HTTPException, Query
from semantic_search import search

app = FastAPI(title="TriNetraAI Semantic Search API")

@app.get("/api/search")
def search_satellite_tiles(
    q: str = Query(..., description="Natural language search query"),
    top_k: int = Query(5, ge=1, le=50, description="Max results"),
    min_lon: float | None = None,
    min_lat: float | None = None,
    max_lon: float | None = None,
    max_lat: float | None = None,
):
    try:
        bbox = None
        if None not in (min_lon, min_lat, max_lon, max_lat):
            bbox = {
                "left": min_lon,
                "bottom": min_lat,
                "right": max_lon,
                "top": max_lat,
            }
        results = search(query=q, bbox=bbox, top_k=top_k)
        return {
            "query": q,
            "count": len(results),
            "results": [r.to_dict() for r in results]
        }
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Search service error: {err}")
```

---

## Evaluation & Benchmarks

The project includes an objective evaluation suite measuring search retrieval quality and CPU performance:

```bash
# 1. Evaluate retrieval metrics (MRR, Precision@K, Hit@K) against human ground truth
python -m scripts.evaluate_metrics

# 2. Evaluate prompt expansion / ensembling experiments
python -m scripts.evaluate_ensemble

# 3. Profile CPU latency and caching speedups
python -m scripts.benchmark_search

# 4. Validate query robustness across whitespace, casing, and complex strings
python -m scripts.evaluate_robustness

# 5. Run master system validation and production readiness audit
python -m scripts.validate_production_readiness
```

---

## Testing

Run the full automated test suite (76 unit and integration tests):

```bash
python -m pytest
```

To run a specific test module:

```bash
python -m pytest tests/test_integration_contract.py
```

