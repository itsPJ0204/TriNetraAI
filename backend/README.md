# TriNetraAI Backend

FastAPI HTTP backend adapter for the **TriNetraAI** satellite intelligence system.

The backend exposes the repository's core functionality (semantic search, multimodal fusion, bitemporal change detection, spatial indexing, and GeoTIFF metadata inspection) through RESTful endpoints without duplicating or replacing underlying engine implementations.

---

## 🚀 Getting Started

### 1. Requirements & Prerequisites
Ensure Docker Qdrant is running on `http://localhost:6333` with the `satellite_tiles` collection.

Install backend dependencies:
```bash
python -m pip install -r backend/requirements.txt
```

### 2. Start the Server
From the repository root:
```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

- **API Base URL:** `http://127.0.0.1:8000`
- **Interactive Swagger UI:** `http://127.0.0.1:8000/docs`
- **ReDoc UI:** `http://127.0.0.1:8000/redoc`

---

## 📡 API Endpoints Reference

### 1. Health Check

**`GET /health`**

Checks if the backend service is online.

#### Response (`200 OK`)
```json
{
  "status": "ok"
}
```

---

### 2. Natural Language Semantic Search

**`POST /search/text`**

Queries indexed Sentinel-2 satellite tiles using natural language descriptions via RemoteCLIP embeddings in Docker Qdrant.

#### Request Body
```json
{
  "query": "dense forest and vegetation",
  "top_k": 5,
  "bbox": {
    "left": 77.0,
    "bottom": 28.0,
    "right": 78.0,
    "top": 29.0
  }
}
```
*Note: `bbox` is optional.*

#### Response (`200 OK`)
```json
{
  "query": "dense forest and vegetation",
  "top_k": 5,
  "count": 5,
  "results": [
    {
      "tile_name": "sentinel2_tile_19.tif",
      "image_path": "data/tiles/sentinel2/2025-06-07/sentinel2_tile_19.tif",
      "score": 0.0636,
      "crs": "EPSG:4326",
      "bounds": {
        "left": 77.156982,
        "bottom": 28.58296,
        "right": 77.179981,
        "top": 28.603155
      },
      "width": 256,
      "height": 256,
      "date": "2025-06-07",
      "tile_id": "sentinel2:2025-06-07:data/tiles/sentinel2/2025-06-07/sentinel2_tile_19.tif"
    }
  ]
}
```

---

### 3. Image-to-Image / Multimodal Search

**`POST /search/image`**

Searches for similar satellite tiles using an uploaded image (PNG, JPEG, TIFF, or multi-band GeoTIFF) with optional text query fusion.

#### Content Type
`multipart/form-data`

#### Parameters & Form Fields
- `image` *(required file)*: Query image file.
- `top_k` *(query int, default: 5)*: Number of results.
- `query` *(query string, optional)*: Text query for multimodal fusion.
- `alpha` *(query float, default: 0.5)*: Weight balance between image and text features (0.0 = text only, 1.0 = image only).
- `fusion_strategy` *(query string, default: "weighted_sum")*: One of `"weighted_sum"`, `"average"`, `"image_only"`, `"text_only"`.
- `minx`, `miny`, `maxx`, `maxy` *(query float, optional)*: Bounding box coordinates.

#### Response (`200 OK`)
```json
{
  "query": "forest",
  "top_k": 5,
  "fusion_strategy": "weighted_sum",
  "count": 5,
  "results": [
    {
      "tile_name": "sentinel2_tile_29.tif",
      "image_path": "data/tiles/sentinel2/2026-06-27/sentinel2_tile_29.tif",
      "score": 0.0761,
      "crs": "EPSG:4326",
      "bounds": {
        "left": 77.24898,
        "bottom": 28.572468,
        "right": 77.271979,
        "top": 28.58296
      },
      "width": 256,
      "height": 133,
      "date": "2026-06-27",
      "tile_id": "sentinel2:2026-06-27:data/tiles/sentinel2/2026-06-27/sentinel2_tile_29.tif"
    }
  ]
}
```

---

### 4. Bitemporal Change Detection

**`POST /change-detection`**

Performs bi-temporal change detection on a pair of satellite tiles using the dual-engine BIT Transformer / Classical CV pipeline with QA cloud/shadow suppression.

#### Request Body
```json
{
  "before_path": "sample_pairs/tile_000_t1.tif",
  "after_path": "sample_pairs/tile_000_t2.tif",
  "force_classical": true,
  "apply_qa_suppression": true,
  "min_area": 50
}
```

#### Response (`200 OK`)
```json
{
  "status": "success",
  "mode_used": "Classical (SSIM/PCA)",
  "qa_suppression": true,
  "has_change": true,
  "change_ratio": 0.042,
  "target_count": 3,
  "detected_targets": [
    {
      "id": 1,
      "bbox": [45, 60, 110, 140],
      "area": 520,
      "centroid": [77.5, 100.0]
    }
  ],
  "mask_path": "outputs/backend/change_mask_123.png",
  "overlay_path": "outputs/backend/change_overlay_123.png"
}
```

---

### 5. Spatial Tiles Query

**`GET /tiles`**

Queries spatial tile records with optional bounding box and acquisition date filtering.

#### Query Parameters
- `minx`, `miny`, `maxx`, `maxy` *(float, optional)*: Geographic bounding box coordinates.
- `start_date`, `end_date` *(string, optional, YYYY-MM-DD)*: Temporal date window.

#### Response (`200 OK`)
```json
{
  "count": 30,
  "tiles": [
    {
      "id": 1,
      "tile_id": "tile_001",
      "grid_key": "grid_0_0",
      "grid_row": 0,
      "grid_col": 0,
      "filepath": "data/tiles/sentinel2/2026-01-18/sentinel2_tile_1.tif",
      "bbox": [77.15, 28.58, 77.18, 28.60],
      "source_filename": "s2_scene_001.tif",
      "acquisition_date": "2026-01-18"
    }
  ]
}
```

**`GET /tiles/{tile_id}`**

Retrieves metadata and geospatial provenance for a specific tile.

#### Response (`200 OK`)
```json
{
  "id": 1,
  "tile_id": "tile_001",
  "grid_key": "grid_0_0",
  "grid_row": 0,
  "grid_col": 0,
  "filepath": "data/tiles/sentinel2/2026-01-18/sentinel2_tile_1.tif",
  "bbox": [77.15, 28.58, 77.18, 28.60],
  "source_filename": "s2_scene_001.tif",
  "acquisition_date": "2026-01-18"
}
```

---

### 6. GeoTIFF Metadata Inspection

**`GET /metadata`**

Direct GeoTIFF raster inspection returning shape, CRS, affine transform, band count, and spatial bounds.

#### Query Parameters
- `filepath` *(string, required)*: Project-relative path to GeoTIFF file.

#### Response (`200 OK`)
```json
{
  "crs": "EPSG:4326",
  "width": 256,
  "height": 256,
  "count": 3,
  "dtype": "uint8",
  "bounds": {
    "left": 77.156982,
    "bottom": 28.58296,
    "right": 77.179981,
    "top": 28.603155
  },
  "transform": [0.00008983, 0.0, 77.156982, 0.0, -0.00008983, 28.603155]
}
```

---

### 7. Trigger Incremental Ingestion & Indexing

**`POST /index`**

Triggers incremental ingestion from `data/raw/sentinel2/` to `data/tiles/sentinel2/`, generates RemoteCLIP embeddings for only new/modified tiles, and indexes them into Docker Qdrant.

*(Note: Search endpoints `/search/text` and `/search/image` are strictly read-only and never trigger indexing. Indexing occurs exclusively here or via CLI.)*

#### Request Body
```json
{
  "force": false,
  "tile_size": 256
}
```

#### Response (`200 OK`)
```json
{
  "status": "success",
  "summary": {
    "dates_discovered": 3,
    "dates_processed": 0,
    "dates_skipped": 3,
    "tiles_new": 0,
    "tiles_changed": 0,
    "tiles_unchanged": 90,
    "embeddings_generated": 0,
    "qdrant_points_added": 0,
    "qdrant_points_updated": 0,
    "total_manifest_tiles": 90
  }
}
```

---

### 8. Direct Satellite Data Upload & Dual-Mode Ingestion

**`POST /ingest/upload`**

Allows the frontend to upload satellite files directly. Files are automatically saved into `data/raw/sentinel2/{date}/`, tiled into $256 \times 256$ GeoTIFFs, and indexed into Docker Qdrant.

#### Content Type
`multipart/form-data`

#### Parameters & Form Fields
- `files` *(required list of files)*: 1 True-Colour GeoTIFF OR 4 separate band files (`B02`, `B03`, `B04`, `B08`).
- `date` *(optional string, format: YYYY-MM-DD)*: Acquisition date. If omitted, auto-extracted from filename.
- `tile_size` *(optional int, default: 256)*: Tile dimensions in pixels.
- `force` *(optional bool, default: false)*: Force re-embedding if date already indexed.

#### Response (`200 OK`)
```json
{
  "status": "success",
  "date": "2026-09-15",
  "uploaded_files": [
    "scene_2026-09-15_tci.tif"
  ],
  "summary": {
    "date": "2026-09-15",
    "tiles_discovered": 30,
    "tiles_new": 30,
    "tiles_unchanged": 0,
    "embeddings_generated": 30,
    "qdrant_points_added": 30,
    "crs": "EPSG:4326",
    "band_mapping": {
      "band_1": "Red",
      "band_2": "Green",
      "band_3": "Blue",
      "input_type": "True-Colour (RGB) Composite"
    }
  }
}
```

---

## 🔒 Error Handling

All error responses adhere to standard HTTP status codes:
- **`400 Bad Request`**: Validation errors, malformed bounding boxes, or paths outside project root.
- **`404 Not Found`**: Non-existent tile ID or missing file.
- **`503 Service Unavailable`**: External service dependency failure (e.g., Docker Qdrant unreachable).

Example `400 Bad Request` JSON:
```json
{
  "detail": "left must be strictly less than right"
}
```


