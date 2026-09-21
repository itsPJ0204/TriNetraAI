# 🛰️ TriNetra AI (त्रिनेत्र AI) — Satellite Intelligence Platform

**Smart India Hackathon (SIH 2026)** — *Automated Natural Language & Multimodal Vector Search, Bitemporal Neural Change Detection, and Multi-Sensor Earth Observation Intelligence.*

---

## 🌟 Key Highlights & Capabilities

- **🔍 Natural Language Vector Search**: Query multi-spectral satellite archives using plain English (e.g., *"Find riverbanks with dense vegetation"*, *"Urban construction sites"*) powered by **RemoteCLIP ViT-B/32** & **Qdrant Vector DB**.
- **🖼️ Image-to-Image Similarity Search**: Upload any satellite tile, crop, or reference image to retrieve visually matching terrain across epochs.
- **⚡ Dual-Engine Bitemporal Change Detection**: Compare Before/After satellite passes using the **BIT Transformer** and **Classical Computer Vision** with automated Just-In-Time (JIT) cloud & shadow false-alarm suppression.
- **📡 Multi-Sensor Intelligence**: Native support for **Sentinel-2 MSI (Optical)** and **Sentinel-1 C-SAR (Radar)** surveillance passes.
- **🤖 TriNetra AI Assistant**: Fully offline conversational agent with natural language routing, automatic workflow execution, and interactive map triage.
- **🔒 100% Offline & Air-Gapped Ready**: Complete on-premises architecture with zero external cloud dependencies.

---

## 📋 System Prerequisites

Before starting, ensure you have the following installed on your system:

| Tool | Recommended Version | Download Link |
| :--- | :--- | :--- |
| **Python** | 3.10, 3.11, or 3.12 | [python.org](https://www.python.org/downloads/) |
| **Node.js & npm** | Node v18+ (LTS) | [nodejs.org](https://nodejs.org/) |
| **Docker Desktop** | Latest (for Qdrant) | [docker.com](https://www.docker.com/products/docker-desktop/) |
| **Git** | Latest | [git-scm.com](https://git-scm.com/) |

---

## 🚀 Step-by-Step Setup & Execution Guide

Follow these exact steps to run TriNetra AI from scratch.

---

### Step 1: Clone the Repository

```bash
git clone https://github.com/itsPJ0204/TriNetraAI.git
cd TriNetraAI
```

*(Optional: Switch to the complete branch if not on it)*:
```bash
git checkout trinetra-ai-complete
```

---

### Step 2: Start Qdrant Vector Database (Docker)

Open your terminal and run Qdrant vector database container on port `6333`:

```bash
docker run -d -p 6333:6333 -p 6334:6334 --name trinetra-qdrant -v ${PWD}/data/qdrant_local:/qdrant/storage qdrant/qdrant
```

> **Verify Qdrant is running:** Open [http://localhost:6333/dashboard](http://localhost:6333/dashboard) or run:
> ```bash
> curl http://localhost:6333/collections
> ```

---

### Step 3: Set Up Python Backend Environment

1. **Create and activate a Python virtual environment**:

   * **Windows (PowerShell):**
     ```powershell
     python -m venv venv
     .\venv\Scripts\Activate.ps1
     ```

   * **Linux / macOS (Bash):**
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```

2. **Install Backend Dependencies**:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

---

### Step 4: (One-Time) Index Satellite Tiles in Qdrant

If your Qdrant database is fresh, populate the vector embeddings for Sentinel-1 and Sentinel-2 tiles:

```bash
# Index Sentinel-2 Optical Tiles (130 tiles)
python -m scripts.index_tiles

# Index Sentinel-1 Radar Tiles (162 tiles)
python -m scripts.ingest_new_sentinel1
```

> **Note:** Pre-generated embeddings and GeoTIFF tiles are already included in `data/tiles/` and `data/embeddings/` so indexing completes in seconds!

---

### Step 5: Start the FastAPI Backend Server

With your virtual environment activated, run:

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

> **Backend Status:** Your API is now live at [http://localhost:8000](http://localhost:8000)  
> **Interactive Swagger Docs:** Explore all endpoints at [http://localhost:8000/docs](http://localhost:8000/docs)

---

### Step 6: Set Up and Start Frontend UI

Open a **new terminal window**, navigate to the `frontend` folder, and start the Vite dev server:

```bash
cd frontend

# Install Node dependencies
npm install

# Start the interactive web UI
npm run dev
```

> **Frontend URL:** Vite will launch the application at [http://localhost:5173](http://localhost:5173)

---

### Step 7: Open in Browser & Start Using TriNetra AI

Open **[http://localhost:5173](http://localhost:5173)** in Chrome, Edge, or Firefox.

```
┌─────────────────────────────────────────────────────────────┐
│               TRINETRA AI // BHARAT SAT-INTEL              │
│       🛰️ Autonomous Reconnaissance & Earth Intelligence     │
├─────────────────────────────────────────────────────────────┤
│ 1. Vector Search: Type "riverbanks near urban areas"        │
│ 2. Candidate Grid: Review ranked 256x256 satellite chips   │
│ 3. Temporal Wiper: Slide before/after epochs to find changes│
│ 4. AI Assistant: Click Bot icon to chat & command the agent │
└─────────────────────────────────────────────────────────────┘
```

---

## 🖥️ Quick Command Summary

Keep **3 terminal tabs** open while running the application:

| Terminal Tab | Directory | Command | Purpose |
| :--- | :--- | :--- | :--- |
| **Tab 1 (Docker)** | Root | `docker start trinetra-qdrant` | Vector database on `:6333` |
| **Tab 2 (Backend)**| Root | `uvicorn backend.main:app --port 8000 --reload` | FastAPI API on `:8000` |
| **Tab 3 (Frontend)**| `frontend/` | `npm run dev` | React UI on `:5173` |

---

## 🧩 Core Architecture & Workflows

```
                           [ RAW SATELLITE ARCHIVE ]
                  (Sentinel-2 Optical / Sentinel-1 Radar GeoTIFFs)
                                       │
                                       ▼
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │ 1. INGESTION & TILING ENGINE (Windowed 256×256 Chips + CRS Projection)      │
 │ • Reads GeoTIFF metadata, bounding boxes, UTM zones, pixel dimensions       │
 │ • SQLite Spatial Registry: database/tile_registry.sqlite                    │
 └─────────────────────────────────────┬───────────────────────────────────────┘
                                       │
                    ┌──────────────────┴──────────────────┐
                    ▼                                     ▼
 ┌───────────────────────────────────────┐  ┌──────────────────────────────────┐
 │ 2. REMOTECLIP VECTOR ENGINE (ViT-B/32)│  │ 3. JUST-IN-TIME QA SUPPRESSION   │
 │ • 512-D Vision-Language Embeddings    │  │ • SCL Cloud & Shadow Filtering   │
 │ • Text-to-Image & Image-to-Image      │  │ • Morphological Halo Erosion     │
 │ • Qdrant Cosine Similarity (Port 6333)│  │ • Joint Mask: M = QA(t1) ∩ QA(t2)│
 └──────────────────┬────────────────────┘  └──────────────────┬───────────────┘
                    │                                          │
                    └──────────────────┬───────────────────────┘
                                       ▼
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │ 4. BITEMPORAL NEURAL CHANGE DETECTIVE (BIT Transformer + Classical CV)      │
 │ • Pixel-aligned anomaly detection across acquisition epochs                 │
 │ • Zero-Shot Semantic Transition Matrix (e.g. Vegetation → New Construction) │
 │ • Post-processing: Sub-pixel Bounding Boxes, Area m², Red Alert Overlays    │
 └─────────────────────────────────────┬───────────────────────────────────────┘
                                       ▼
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │ 5. ANALYST COMMAND DASHBOARD & AI ASSISTANT (React + Tailwind + Lucide)     │
 │ • Interactive 3D Earth Globe, Ranked Candidate Grid, Split-Wiper Viewer     │
 │ • Autonomous AI Assistant bot with direct UI command & dispatch             │
 └─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ API Reference Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/search/text` | Natural language text-to-image semantic search across Qdrant vectors |
| `POST` | `/search/image` | Reverse image similarity search with optional multimodal text fusion |
| `GET` | `/tiles?sensor=all` | Returns complete geospatial catalog & telemetry from SQLite |
| `GET` | `/tile-preview?path=...` | High-performance dynamic GeoTIFF raster rendering to PNG |
| `GET` | `/available-dates` | Returns acquisition epochs for active tile & sensor (`sentinel1`/`sentinel2`) |
| `POST` | `/change-detection` | Executes dual-engine change detection with QA cloud suppression |
| `POST` | `/assistant/chat` | Autonomous AI Assistant reconnaissance chat & intent execution |
| `GET` | `/assistant/health` | Diagnostic status for AI assistant engine and local VLM |

---

## ❓ Troubleshooting & FAQs

### 1. `Could not connect to Docker Qdrant server at 'http://localhost:6333'`
* **Cause**: Docker container is not running.
* **Fix**: Ensure Docker Desktop is started and run:
  ```bash
  docker start trinetra-qdrant
  ```

### 2. `Rasterio DLL / GDAL load error on Windows`
* **Cause**: Missing C++ redistributables or Python version mismatch.
* **Fix**: Ensure you are using **Python 3.10, 3.11, or 3.12 64-bit**. Run:
  ```bash
  pip install --force-reinstall rasterio
  ```

### 3. Frontend displays "Backend Offline" or images fail to load
* **Cause**: FastAPI server on port `8000` is stopped.
* **Fix**: Start the backend server (`uvicorn backend.main:app --port 8000 --reload`).

### 4. `npm run build` Chunk Warnings
* The frontend build is optimized for production. Chunk warnings are normal and build completes with 0 errors.

---

## 📄 License & Attribution

Developed for **Smart India Hackathon (SIH 2026)**.  
Built with **PyTorch**, **RemoteCLIP**, **Qdrant**, **FastAPI**, **Rasterio**, and **React + Vite**.
