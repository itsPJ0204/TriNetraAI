# TriNetra AI (त्रिनेत्र AI) // BHARAT SAT-INTEL — Frontend

Semantic Retrieval and Multi-Temporal Change Analysis of Satellite Imagery.

An air-gapped, offline-first satellite intelligence platform featuring natural language semantic search, image-to-image similarity matching, bitemporal change detection, target classification, and offline tile ingestion.

## 🚀 Features

- **Semantic Retrieval**: Natural language search with query parsing and 8-stage autonomous pipeline.
- **Ranked Candidate Tiles**: Geospatial grid visualization with tactical coordinate cards and similarity scoring.
- **Image-to-Image Search**: Drag-and-drop satellite tile reverse search using ViT visual embeddings.
- **Target Classification**: YOLOv8x sub-pixel optical object detection with automated bounding boxes.
- **Temporal Analysis**: Multi-year progression timeline (2020—2025), interactive Before/After comparison slider, and differential change mask overlay.
- **Data Ingestion**: 7-stage offline ingestion pipeline for GeoTIFF imagery with metadata extraction, vector indexing, and local SQLite archiving.
- **Analyst Review**: Air-gapped mission triage queue and cryptographic audit ledger.

## 🛠️ Quick Start

### Prerequisites
- Node.js (v18+)
- npm or yarn

### Installation & Development

```bash
# Navigate to the frontend directory
cd frontend

# Install dependencies
npm install

# Start the local development server
npm run dev
```

The application will be available at `http://localhost:5173/`.

### Production Build

```bash
npm run build
```

The compiled air-gapped production assets will be generated in `dist/`.
