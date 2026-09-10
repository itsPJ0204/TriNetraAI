# 🛰️ TriNetraAI — Unified Earth Observation & Satellite Intelligence Engine

**Smart India Hackathon (SIH 2026)** — *Automated Natural Language & Multimodal Search, False-Alarm Suppression & Semantic Change Detective for Multi-Temporal Earth Observation Archives.*

[![Architecture](https://img.shields.io/badge/Architecture-5--Layer%20Decoupled-00E5FF)](presentation/index.html)
[![Semantic Search MRR](https://img.shields.io/badge/Semantic%20MRR-0.9333-10B981)](data/evaluation/retrieval_metrics.json)
[![Temporal Model](https://img.shields.io/badge/Temporal%20AI-BIT%20Transformer-8B5CF6)](src/neural_cd.py)
[![False Alarm Filter](https://img.shields.io/badge/QA%20Suppression-Just--In--Time%20SCL-F59E0B)](qa_mask.py)
[![Multimodal Search](https://img.shields.io/badge/Search-Text%20%2B%20Image%20Fusion-EC4899)](scripts/search_by_image.py)
[![Offline Ready](https://img.shields.io/badge/Deployment-100%25%20Air--Gapped%20Edge-3B82F6)](local_ingest.py)

---

## 🏛️ End-to-End System Architecture

TriNetraAI operates as an on-premises, multi-modal pipeline with zero external cloud dependencies:

```
                            [ RAW SATELLITE ARCHIVE ]
                 (Sentinel-2 L2A, Landsat-9, PlanetScope, Drone)
                                       │
                                       ▼
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │ LAYER 1: DATA INGESTION & SPATIAL PROVENANCE (Role 1 — Md Huzaifa Hayat)   │
 │ • Windowed 512×512 Grid Tiling & CRS Alignment (ingestion/tiling.py)        │
 │ • SQLite Spatial Metadata Registry (bounds, transform, timestamps, crs)     │
 │ • Provenance Export: data/tiles_metadata.csv (Single Source of Truth)       │
 └─────────────────────────────────────┬───────────────────────────────────────┘
                                       │
                    ┌──────────────────┴──────────────────┐
                    ▼                                     ▼
 ┌───────────────────────────────────────┐  ┌──────────────────────────────────┐
 │ LAYER 2: MULTIMODAL SEMANTIC SEARCH   │  │ TERRAIN SIMILARITY CLUSTERING    │
 │ (Role 2 — Rahim)                      │  │ (Role 4 — Piyush)                │
 │ • RemoteCLIP (ViT-B/32, 512-D)        │  │ • PCA-50 + K-Means (k=5) Groups  │
 │ • Text-to-Image & Image-to-Image Query│  │ • Similar tile discovery         │
 │ • Qdrant Vector DB (Cosine Similarity)│  │ • clustering.py                  │
 │ • Domain Query Expansion (search.py)  │  └──────────────────────────────────┘
 │ • 0.9333 MRR / 86.7% Top-1 Accuracy   │
 └──────────────────┬────────────────────┘
                    │
                    │ Analyst selects bitemporal pair (t1, t2) for inspection
                    ▼
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │ LAYER 3: JUST-IN-TIME (JIT) QA FALSE-ALARM SUPPRESSION (Role 4 — Piyush)   │
 │ • Trigger: Executed ON-DEMAND during bitemporal ingestion of (t1, t2)       │
 │ • SCL Band Filter: Class 3 (Shadows), Classes 8-10 (Clouds), Class 11 (Snow)│
 │ • Dynamic Band Detection: Automatic optical cloud fallback for 3/4-band TIFs│
 │ • Adaptive Halo Erosion: Scaled kernel removes cloud boundary penumbra      │
 │ • Joint Valid Mask: M_valid = QA(t1) ∩ QA(t2)                               │
 └─────────────────────────────────────┬───────────────────────────────────────┘
                                       │
                                       ▼
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │ LAYER 4: TEMPORAL DETECTIVE & SEMANTIC CLASSIFIER (Role 3 — Krishna)        │
 │ • Early-Exit Occlusion Guard: Skips BIT if valid ground < 15% (heavy clouds)│
 │ • Dual-Engine Change Detection:                                             │
 │    1. Primary: Deep Learning Bitemporal Image Transformer (BIT) (bit_core/) │
 │    2. Fallback: High-Speed Gaussian Difference + Otsu Thresholding          │
 │ • Cleansing: Clean_Mask = Raw_Change ∩ QA(t1) ∩ QA(t2)                      │
 │ • Zero-Shot Semantic Transition Matrix (RemoteCLIP Classifier):             │
 │    - Classifies WHAT changed (e.g. Vegetation → New Construction)           │
 │ • Post-Processing: Sub-pixel BBoxes (x, y, w, h), Surface %, 40% Red Overlay│
 └─────────────────────────────────────┬───────────────────────────────────────┘
                                       │
                                       ▼ Structured Domain JSON
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │ LAYER 5: ANALYST COMMAND DASHBOARD & REVIEW QUEUE (Role 5 — Full-Stack)     │
 │ • Unified REST Endpoints (/api/search, /api/changes, /api/similar)          │
 │ • Leaflet.js Interactive Map & Before/After Visual Split-Slider             │
 │ • Human-In-The-Loop: 1-Click Approve/Reject Verification Audit Log          │
 └─────────────────────────────────────────────────────────────────────────────┘
```

---

## 👥 Team Roles & Responsibilities

| Role | Responsibility | Core Deliverables | Status |
|:---|:---|:---|:---:|
| **Role 1: Data Engineering** *(Md Huzaifa Hayat)* | Ingestion, 512×512 grid tiling, CRS alignment, SQLite metadata database, CSV handoff contract. | `ingestion/tiling.py`, `ingestion/db.py`, `ingestion/ingest.py`, `spatial/queries.py` | ✅ **Complete** |
| **Role 2: Semantic AI** *(Rahim)* | Vision-Language foundation model (RemoteCLIP ViT-B/32), 512-D vector embeddings, Qdrant vector retrieval, text & **image-to-image** search, query expansion. | `semantic_search/model.py`, `semantic_search/embeddings.py`, `semantic_search/vector_store.py`, `semantic_search/search.py`, `scripts/search_by_image.py` | ✅ **Complete** |
| **Role 3: Temporal AI** *(Krishna)* | Dual-Engine BIT Transformer + Classical CV fallback, Zero-Shot Semantic Transition Matrix, BBox extraction, overlays. | `detective_api.py`, `src/neural_cd.py`, `src/classical_cd.py`, `src/semantic_classifier.py`, `src/postprocessor.py` | ✅ **Complete** |
| **Role 4: QA & False-Alarm AI** *(Piyush)* | Just-In-Time SCL cloud/shadow suppression, adaptive halo erosion, offline `s2cloudless` edge node, K-Means clustering. | `qa_mask.py`, `local_ingest.py`, `clustering.py`, `run_qa_pipeline.py` | ✅ **Complete** |
| **Role 5: Frontend & Integration** *(Lead)* | Interactive SIH presentation deck, unified CLI, REST API endpoints, Leaflet map client, review audit trail. | `main.py`, `presentation/index.html`, `presentation/app.js`, `presentation/styles.css` | ✅ **Complete** |

---

## 🚀 Quickstart & Usage

### 1. Unified Command-Line Interface (`main.py`)

```bash
# Initialize SQLite Spatial Registry
python main.py init-db

# Ingest a satellite scene into 512x512 tiles & export metadata registry
python main.py ingest "sih_dataset/year_1/default.tif" --tile-size 512

# Execute Natural Language Semantic Search (RemoteCLIP + Qdrant)
python main.py search "dense urban residential area" --top-k 5

# Compare bitemporal tiles with JIT QA False-Alarm Suppression
python main.py compare "sample_pairs/tile_000_t1.tif" "sample_pairs/tile_000_t2.tif"

# Run K-Means Terrain Clustering across tile embeddings
python main.py cluster --k 5
```

---

### 2. Multimodal & Image-to-Image Search (Role 2)

```bash
# 1. Image-to-Image Search (Find tiles visually matching a query image)
python -m scripts.search_by_image sample_pairs/tile_000_t1.tif --top-k 5

# 2. Multimodal Fusion Search (Image + Text Query with 50/50 weighting)
python -m scripts.search_by_image sample_pairs/tile_000_t1.tif --query "dense vegetation" --alpha 0.5
```

---

### 3. Programmatic Python API

```python
# A. Multimodal Search
from semantic_search.search import search, search_by_image

# Natural Language Search
results = search(query="coastal harbor and shipping port", top_k=5)

# Image-to-Image Similarity Search
img_results = search_by_image(image="query_crop.png", top_k=5)

# B. Temporal Change Detective with JIT QA Masking
from detective_api import compare_tiles

report = compare_tiles(
    tile_t1_path="sample_pairs/tile_000_t1.tif",
    tile_t2_path="sample_pairs/tile_000_t2.tif",
    apply_qa_suppression=True,
    min_area=100
)

print(f"Mode Used: {report['mode_used']}")
print(f"Changes Detected: {report['target_count']}")
for target in report['detected_targets']:
    print(f" - BBox: {target['bbox']} | Transition: {target['semantic_transition']['transition']}")
```

---

## 📄 Interactive Presentation & Technical Reports

- **Interactive Presentation Deck:** Open [`presentation/index.html`](presentation/index.html) in any browser (16:9 interactive SIH slide deck with live modals & PDF export).
- **Master Junction Audit PDF:** [`TriNetraAI_Complete_Junction_Audit.pdf`](TriNetraAI_Complete_Junction_Audit.pdf).
- **Defense Project Flow & 3D Web Prompt PDF:** [`TriNetraAI_Project_Flow_and_3D_Defense_Prompt.pdf`](TriNetraAI_Project_Flow_and_3D_Defense_Prompt.pdf).

---
*Built with ❤️ for Smart India Hackathon 2026.*
