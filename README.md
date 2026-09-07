# 🛰️ TriNetraAI — Unified Earth Observation & Satellite Intelligence Engine

**TriNetraAI** is a comprehensive, offline-first satellite intelligence platform built for Earth Observation, automated monitoring, and reconnaissance. It unifies three core capabilities:

1. **🛡️ QA & False-Alarm Suppression (Role 4)**: Filters out clouds, cloud shadows, snow, and sensor defects using Sentinel-2 SCL bands and edge-optimized `s2cloudless` machine learning models.
2. **🔍 Semantic Natural-Language Search (Role 2)**: Enables analysts to search satellite tiles using free-form text descriptions (*"buildings near a river"*, *"dense urban area"*) powered by **RemoteCLIP (ViT-B/32)** and **Qdrant Vector Database**.
3. **🕵️‍♂️ Temporal Change Detective & Semantic Classifier (Role 3)**: Compares bitemporal satellite tile pairs, pinpoints physical change locations (**BIT Transformer** + **Classical CV**), and classifies **WHAT the actual change is** (*Vegetation &rarr; New Construction*, *Land Clearing*, *Road Expansion*, *Flooding*).

---

## 🏗️ End-to-End System Architecture

```
[ Raw Satellite Scenes / Multi-Band GeoTIFFs ]
                      │
                      ▼
 ┌─────────────────────────────────────────────────────────────┐
 │ 1. QA & FALSE-ALARM SUPPRESSION (Role 4 / qa_mask.py)       │
 │    • SCL Band Filtering (removes clouds, shadows, snow)     │
 │    • Offline s2cloudless Edge Ingestion (local_ingest.py)   │
 │    • Morphological Halo Erosion                             │
 └─────────────────────────────────────────────────────────────┘
                      │
                      ▼
 ┌─────────────────────────────────────────────────────────────┐
 │ 2. DISCOVERY & TILE INDEXING (Role 1 & Role 2)              │
 │    • 512x512 GeoTIFF Patch Extraction with GPS Bounds       │
 │    • RemoteCLIP 512-D Visual Feature Extraction             │
 │    • Qdrant Vector DB Upsert ('satellite_tiles')           │
 │    • K-Means Terrain Similarity Clustering (clustering.py) │
 └─────────────────────────────────────────────────────────────┘
                      │
        ┌─────────────┴─────────────┐
        ▼                           ▼
 ┌───────────────────────────┐ ┌───────────────────────────────────────────────┐
 │ 3. NATURAL LANGUAGE SEARCH│ │ 4. TEMPORAL CHANGE DETECTIVE (Role 3)         │
 │    (Role 2)               │ │    (detective_api.py / src/)                  │
 │    • Query Expansion      │ │    • BIT Deep Learning Transformer Engine     │
 │    • 512-D Text Embedding │ │    • Fast Classical Absolute Diff Fallback    │
 │    • Cosine Similarity    │ │    • Morphological Cleaning & Bounding Boxes  │
 │    • 2D BBox Filter       │ │    • RemoteCLIP Semantic Change Classifier    │
 └───────────────────────────┘ └───────────────────────────────────────────────┘
        │                           │
        └─────────────┬─────────────┘
                      ▼
 ┌─────────────────────────────────────────────────────────────┐
 │ 5. FRONTEND / FASTAPI INTEGRATION (Role 5)                  │
 │    • REST Endpoints (/api/search, /api/changes, /api/similar│
 │    • Leaflet.js Interactive Map & Before/After Slider       │
 │    • Analyst Approve/Reject Review Queue & Audit Log        │
 └─────────────────────────────────────────────────────────────┘
```

---

## 📁 Repository Structure

```plaintext
TriNetraAI/
├── semantic_search/             # 🔍 Role 2: Semantic Natural-Language Search Engine
│   ├── model.py                 # RemoteCLIP ViT-B/32 loader
│   ├── embeddings.py            # 512-D L2-normalized image embeddings
│   ├── vector_store.py          # Qdrant vector database integration & bbox filters
│   ├── query_expansion.py       # Domain-specific remote-sensing prompt ensembling
│   ├── search.py                # Public search(query, bbox, top_k) API
│   ├── schemas.py               # SearchResult typed domain model
│   ├── metrics.py               # Evaluation metrics (MRR, Hit@k, Precision@k)
│   └── evaluation.py            # Automated benchmark evaluation runner
│
├── src/                         # 🕵️‍♂️ Role 3: Temporal AI Detective Engine
│   ├── preprocessor.py          # 16-bit GeoTIFF / Optical RGB normalizer & tensor loader
│   ├── classical_cd.py          # Gaussian absolute difference change detection
│   ├── neural_cd.py             # BIT (Bitemporal Image Transformer) inference engine
│   ├── semantic_classifier.py   # RemoteCLIP Zero-Shot Semantic Transition Classifier
│   └── postprocessor.py         # Morphology, BBoxes, Semantic Labels & Overlay generator
│
├── bit_core/                    # Official BIT Transformer architecture & backbone
│   ├── networks.py              # Model builder, tokenizer & transformer decoder
│   ├── resnet.py / backbone.py  # ResNet feature extractors
│   └── help_funcs.py            # Multi-head attention & position embeddings
│
├── qa_mask.py                   # 🛡️ Role 4: SCL Cloud & Quality Masking engine
├── clustering.py                # 🌐 Role 4: PCA-50 + K-Means Terrain Similarity Clustering
├── local_ingest.py              # ⚡ Role 4: Zero-internet Edge Ingestion with s2cloudless
├── download.py                  # Sentinel-2 L2A satellite scene downloader
├── download_edge_data.py        # 13-band Sentinel-2 L1C edge data simulator
├── run_qa_pipeline.py           # Multi-year QA batch runner (2024–2026)
├── run_clustering.py            # K-Means clustering pipeline runner
│
├── detective_api.py             # 🚀 Public API for Change Detection & Classification
├── standalone_test.py           # Verification script for Temporal Detective
│
├── checkpoints/                 # Pretrained weights (bit_levircd.pth, RemoteCLIP)
├── sample_pairs/                # Sample bitemporal tiles for testing
├── data/                        # Benchmark tile repository & ground truth annotations
│   ├── tiles/                   # Indexed GeoTIFF tiles
│   └── evaluation/              # Human-annotated ground truth & evaluation logs
├── outputs/                     # Generated change masks, overlays, and reports
├── edge_data/                   # Raw 13-band input and processed cloudless outputs
├── sih_dataset/                 # Multi-year Sentinel-2 composite dataset (2024, 2025, 2026)
│
├── docs/                        # Architecture & Role Integration specifications
│   └── semantic_ai_integration.md
├── tests/                       # Unit & integration test suites
├── requirements.txt             # Consolidated project dependencies
└── README.md                    # Main documentation
```

---

## 🚀 Quickstart & Installation

### 1. Environment Setup
Clone the repository and install all dependencies:

```bash
git clone -b integrated-trinetra-ai https://github.com/itsPJ0204/TriNetraAI.git
cd TriNetraAI
pip install -r requirements.txt
```

---

### 2. Running Subsystems Independently

#### A. 🕵️‍♂️ Temporal Change Detective (Role 3)
Compares a Before & After tile, detects changes, and classifies what changed:

```bash
python standalone_test.py
```

Or invoke in Python:
```python
from detective_api import compare_tiles

result = compare_tiles("sample_pairs/tile_000_t1.png", "sample_pairs/tile_000_t2.png")

print("Change Detected:", result["has_change"])
print(f"Surface Area Changed: {result['change_ratio'] * 100:.2f}%")
for target in result["detected_targets"]:
    print(f"Target #{target['target_id']}: {target['change_type']} ({target['confidence']*100:.1f}%)")
    print(f"  Transition: {target['transition']}")
    print(f"  Details: {target['description']}")
```

---

#### B. 🔍 Semantic Natural-Language Search (Role 2)
Search indexed satellite tiles by natural language query:

```python
from semantic_search import search

# Query with text description and optional geographic bounding box
results = search(
    query="buildings near a river",
    bbox={"left": 88.34, "bottom": 22.57, "right": 88.36, "top": 22.58},
    top_k=5
)

for res in results:
    print(f"Match: {res.tile_name} (Similarity Score: {res.score:.4f})")
    print(f"  Path: {res.image_path} | CRS: {res.crs} | Bounds: {res.bounds}")
```

---

#### C. 🛡️ QA & Cloud Masking Pipeline (Role 4)
Run quality assurance and false-alarm suppression across multi-year scenes:

```bash
python run_qa_pipeline.py
```

Outputs clean masks, statistics, and cloud-suppressed RGB imagery in `qa_outputs/`.

---

#### D. ⚡ Offline Edge Computing Node (Role 4)
Process raw 13-band Sentinel-2 imagery offline on an edge device using CPU:

```bash
python local_ingest.py
```

---

#### E. 🌐 Discovery & K-Means Clustering (Role 4)
Cluster terrain patches and search for visually similar sites:

```bash
python run_clustering.py
```

---

## 📊 Evaluation & Verification Results

- **Semantic AI Search**:
  - **MRR (Mean Reciprocal Rank)**: `0.9333`
  - **Top-1 Hit Rate (Hit@1)**: `86.67%`
  - **Hit@3 / Hit@4**: `100.0%`
- **Temporal Change Detective**:
  - **Dual-Engine Precision**: Identifies bounding boxes with zero false speckle noise via morphological Open/Close filters.
  - **Zero-Shot Semantic Classification**: Accurately maps transitions (*Vegetation &rarr; New Construction*, *Land Clearing*, *Infrastructure Expansion*) with confidence scores.

---

## 👥 Team Roles & Responsibilities

| Role | Name | Responsibilities | Module |
|---|---|---|---|
| **Role 1** | Data Engineer | GeoTIFF ingestion, Sentinel-2 downloaders, tile slicing | `download.py`, `data/tiles/` |
| **Role 2** | Semantic AI | RemoteCLIP vision-language encoder, Qdrant vector database, natural language search | `semantic_search/` |
| **Role 3** | Temporal AI | Bitemporal change detection (BIT + Classical), Semantic change classifier | `src/`, `bit_core/`, `detective_api.py` |
| **Role 4** | QA & Discovery | False-alarm cloud/shadow suppression, SCL filter, edge `s2cloudless`, K-Means clustering | `qa_mask.py`, `clustering.py`, `local_ingest.py` |
| **Role 5** | Frontend Lead | FastAPI backend routers, Leaflet.js interactive map, analyst review queue | `docs/semantic_ai_integration.md` |

---

## 📄 License
Internal Team Project for Smart India Hackathon (SIH) Earth Observation & Satellite Intelligence.
