/**
 * BHARAT SAT-INTEL // TRINETRA AI (त्रिनेत्र AI)
 * Offline Geospatial Intelligence & Mock Vector Database
 * Fully air-gapped data structure for offline SIH demonstration
 */

export const SYSTEM_STATUS = {
  aiEngine: "READY",
  vectorIndex: "READY",
  database: "READY",
  archive: "READY",
  offlineMode: "ACTIVE",
  indexedTiles: 68920,
  latencyMs: 42,
  defconLevel: 2,
  constellationStatus: "NOMINAL",
  sensors: ["Cartosat-3 PAN", "RISAT-2BR1 SAR", "Sentinel-2 MSI", "Oceansat-3"],
  telemetry: {
    lat: "28°36'48.2\"N",
    lng: "77°13'49.1\"E",
    zone: "UTM Zone 43N",
    subSatellitePoint: "18°55'N 72°50'E",
    orbitVelocityKmS: 7.62
  }
};

export const SAMPLE_QUERIES = [
  "Find large camps and tanks near rivers from 2020 to 2023",
  "Detect fortified military staging grids near LAC border",
  "Identify newly constructed aircraft revetments and paved aprons",
  "Scan riparian perimeter for camouflaged vehicle convoys"
];

export const PIPELINE_STAGES = [
  { id: 1, code: "01 // NLP", name: "Query Parsing", desc: "Extracts target entities, temporal intervals, and spatial buffers", status: "completed" },
  { id: 2, code: "02 // EMBED", name: "Vector Tokenizer", desc: "Generates 768-D multimodal tactical space embeddings", status: "completed" },
  { id: 3, code: "03 // INDEX", name: "FAISS Vector Search", desc: "Scans 68,920 local HNSW graph nodes in 42ms", status: "completed" },
  { id: 4, code: "04 // GRID", name: "MGRS Geospatial Filter", desc: "Spatial bounding box clipping across UTM zones 43N & 44N", status: "completed" },
  { id: 5, code: "05 // HYDRO", name: "GIS Proximity Buffer", desc: "Executes rasterized NDWI river channel boundary radius masking", status: "completed" },
  { id: 6, code: "06 // TIME", name: "Bitemporal Match", desc: "Correlates baseline T0 (2020) imagery with current T1 (2023) pass", status: "completed" },
  { id: 7, code: "07 // INFER", name: "YOLOv8 Optical Detector", desc: "Multi-class military asset identification & pixel bounding boxes", status: "completed" },
  { id: 8, code: "08 // AUDIT", name: "Provenance & QA Ledger", desc: "Air-gap SHA-256 cryptographic verification for analyst review", status: "completed" }
];

export const CANDIDATE_TILES = [];

export const MARKER_TYPES = [
  { id: "normal", label: "Normal location", color: "#64748b", dotClass: "bg-[#64748b]" },
  { id: "search_result", label: "Search result", color: "#00e5ff", dotClass: "bg-[#00e5ff]" },
  { id: "change_detected", label: "Change detected", color: "#f59e0b", dotClass: "bg-[#f59e0b]" },
  { id: "high_confidence", label: "High-confidence change", color: "#ef4444", dotClass: "bg-[#ef4444] animate-pulse" }
];

export const THEATER_PRESETS = [
  { name: "Ladakh LAC", lat: 34.15, lng: 77.58, tileId: "T084" },
  { name: "Arunachal LAC", lat: 27.58, lng: 91.86, tileId: "T119" },
  { name: "Galwan Sector", lat: 22.57, lng: 88.36, tileId: "T027" },
  { name: "Sir Creek", lat: 23.75, lng: 68.15, tileId: "T027" },
  { name: "Doklam Plateau", lat: 27.29, lng: 88.92, tileId: "T119" }
];

export const INITIAL_AUDIT_LOG = [
  {
    id: "AUD-091",
    timestamp: "2023-10-09 14:22:04 IST",
    tileId: "T027",
    decision: "APPROVED",
    operator: "OFFICER_RECON_7",
    sha256: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    remarks: "Confirmed unauthorized base construction inside riparian buffer zone"
  },
  {
    id: "AUD-090",
    timestamp: "2023-10-09 11:05:32 IST",
    tileId: "T084",
    decision: "NEEDS_REVIEW",
    operator: "OFFICER_RECON_3",
    sha256: "8f434346648f6b96df89dda901c5176b10a6d83961dd3c1ac88b59b2dc327aa4",
    remarks: "Requested high-res PAN pass to verify radar emitter signature"
  }
];

export const RELATIVE_SECTORS = [
  {
    name: "Kolkata Sector (T027 Baseline)",
    region: "Kolkata Urban",
    crs: "EPSG:4326",
    lat: 22.5726,
    lng: 88.3639,
    coordinates: "22.5726° N, 88.3639° E",
    resolution: "10m",
    image: "/satellite-tiles/T027_2023.jpg",
    description: "Multi-temporal riparian tactical corridor (2020–2025 passes)"
  },
  {
    name: "Ladakh LAC Sector (T026 / T084)",
    region: "Ladakh LAC",
    crs: "EPSG:4326",
    lat: 34.15,
    lng: 77.58,
    coordinates: "34.15° N, 77.58° E",
    resolution: "10m",
    image: "/satellite-tiles/T004.jpg",
    description: "High-altitude mountainous LAC forward staging sector"
  },
  {
    name: "Sir Creek Maritime Sector (T024)",
    region: "Sir Creek",
    crs: "EPSG:4326",
    lat: 23.75,
    lng: 68.15,
    coordinates: "23.75° N, 68.15° E",
    resolution: "0.25m",
    image: "/satellite-tiles/T001.jpg",
    description: "Tidal riverine estuary and littoral border marshes"
  },
  {
    name: "Doklam Plateau Sector (T023)",
    region: "Doklam Plateau",
    crs: "EPSG:4326",
    lat: 27.29,
    lng: 88.92,
    coordinates: "27.29° N, 88.92° E",
    resolution: "1m",
    image: "/satellite-tiles/T003.jpg",
    description: "High-altitude tri-junction tactical ridge line"
  }
];

export const INITIAL_ARCHIVE = [
  {
    id: "T001",
    sensor: "Sentinel",
    date: "2023-04-12",
    dateIso: "2023-04-12",
    status: "READY",
    file: "S2A_MSIL2A_20230412.tif",
    resolution: "10 m",
    crs: "EPSG:4326",
    lat: 22.57,
    lng: 88.36,
    coordinates: "22.5726° N, 88.3639° E",
    cloudCover: "12%",
    location: "Kolkata",
    region: "Kolkata",
    image: "/satellite-tiles/T027_2023.jpg",
    temporalPass: "2023 // Structure Completed",
    processingStatus: {
      metadataExtracted: true,
      tileGenerated: true,
      embeddingGenerated: true,
      faissIndexed: true,
      availableForSearch: true
    }
  },
  {
    id: "T002",
    sensor: "Landsat",
    date: "2022-09-18",
    dateIso: "2022-09-18",
    status: "READY",
    file: "LC08_L2SP_145044_20220918.tif",
    resolution: "30 m",
    crs: "EPSG:32645",
    lat: 22.57,
    lng: 88.36,
    coordinates: "22.5726° N, 88.3639° E",
    cloudCover: "05%",
    location: "Kolkata",
    region: "Kolkata",
    image: "/satellite-tiles/T027_2022.jpg",
    temporalPass: "2022 // Earthworks & Grading",
    processingStatus: {
      metadataExtracted: true,
      tileGenerated: true,
      embeddingGenerated: true,
      faissIndexed: true,
      availableForSearch: true
    }
  },
  {
    id: "T003",
    sensor: "Sentinel",
    date: "2021-03-02",
    dateIso: "2021-03-02",
    status: "READY",
    file: "S2B_MSIL2A_20210302.tif",
    resolution: "10 m",
    crs: "EPSG:4326",
    lat: 22.57,
    lng: 88.36,
    coordinates: "22.5726° N, 88.3639° E",
    cloudCover: "20%",
    location: "Kolkata",
    region: "Kolkata",
    image: "/satellite-tiles/T027_2020.jpg",
    temporalPass: "2021 // Stable Riparian Buffer",
    processingStatus: {
      metadataExtracted: true,
      tileGenerated: true,
      embeddingGenerated: true,
      faissIndexed: true,
      availableForSearch: true
    }
  },
  {
    id: "T004",
    sensor: "Sentinel",
    date: "2024-01-15",
    dateIso: "2024-01-15",
    status: "READY",
    file: "S2A_MSIL2A_20240115.tif",
    resolution: "10 m",
    crs: "EPSG:4326",
    lat: 22.57,
    lng: 88.36,
    coordinates: "22.5726° N, 88.3639° E",
    cloudCover: "00%",
    location: "Kolkata",
    region: "Kolkata",
    image: "/satellite-tiles/T027_2024.jpg",
    temporalPass: "2024 // Active Garrison & Operations",
    processingStatus: {
      metadataExtracted: true,
      tileGenerated: true,
      embeddingGenerated: true,
      faissIndexed: true,
      availableForSearch: true
    }
  },
  {
    id: "T005",
    sensor: "Landsat",
    date: "2020-11-20",
    dateIso: "2020-11-20",
    status: "READY",
    file: "LC08_L2SP_145044_20201120.tif",
    resolution: "30 m",
    crs: "EPSG:32645",
    lat: 22.57,
    lng: 88.36,
    coordinates: "22.5726° N, 88.3639° E",
    cloudCover: "08%",
    location: "Kolkata",
    region: "Kolkata",
    image: "/satellite-tiles/T027_2020.jpg",
    temporalPass: "2020 // Pristine Baseline Riverbank",
    processingStatus: {
      metadataExtracted: true,
      tileGenerated: true,
      embeddingGenerated: true,
      faissIndexed: true,
      availableForSearch: true
    }
  },
  {
    id: "T027",
    sensor: "Landsat-8",
    date: "2023-05-18",
    dateIso: "2023-05-18",
    status: "READY",
    file: "LC08_L2SP_145044_20230518.tif",
    resolution: "10m",
    crs: "EPSG:4326",
    lat: 22.5726,
    lng: 88.3639,
    coordinates: "22.5726° N, 88.3639° E",
    cloudCover: "6%",
    location: "Kolkata Urban",
    region: "Kolkata Urban",
    image: "/satellite-tiles/T027_2023.jpg",
    temporalPass: "2023 // High-Confidence Target Installation",
    processingStatus: {
      metadataExtracted: true,
      tileGenerated: true,
      embeddingGenerated: true,
      faissIndexed: true,
      availableForSearch: true
    }
  },
  {
    id: "T026",
    sensor: "Sentinel-2",
    date: "2025-04-19",
    dateIso: "2025-04-19",
    status: "READY",
    file: "S2A_MSIL2A_20250419T054218.tif",
    resolution: "10 m",
    crs: "EPSG:4326",
    lat: 34.15,
    lng: 77.58,
    coordinates: "34.15, 77.58",
    cloudCover: "2%",
    location: "Ladakh LAC",
    region: "Ladakh",
    image: "/satellite-tiles/T004.jpg",
    temporalPass: "2025 // High-Altitude Mountain Pass",
    processingStatus: {
      metadataExtracted: true,
      tileGenerated: true,
      embeddingGenerated: true,
      faissIndexed: true,
      availableForSearch: true
    }
  },
  {
    id: "T025",
    sensor: "Landsat-8",
    date: "2025-03-12",
    dateIso: "2025-03-12",
    status: "READY",
    file: "LC08_L2SP_145044_20250312.tif",
    resolution: "30 m",
    crs: "EPSG:4326",
    lat: 22.57,
    lng: 88.36,
    coordinates: "22.57, 88.36",
    cloudCover: "8%",
    location: "Kolkata",
    region: "Kolkata",
    image: "/satellite-tiles/T027_2024.jpg",
    temporalPass: "2025 // Fortified Complex Update",
    processingStatus: {
      metadataExtracted: true,
      tileGenerated: true,
      embeddingGenerated: true,
      faissIndexed: true,
      availableForSearch: true
    }
  },
  {
    id: "T024",
    sensor: "Cartosat-3 PAN",
    date: "2025-02-28",
    dateIso: "2025-02-28",
    status: "READY",
    file: "CART3_PAN_20250228_WGS84.tif",
    resolution: "0.25 m",
    crs: "EPSG:4326",
    lat: 23.75,
    lng: 68.15,
    coordinates: "23.75, 68.15",
    cloudCover: "0%",
    location: "Sir Creek",
    region: "Sir Creek",
    image: "/satellite-tiles/T001.jpg",
    temporalPass: "2025 // Littoral Tidal Flats",
    processingStatus: {
      metadataExtracted: true,
      tileGenerated: true,
      embeddingGenerated: true,
      faissIndexed: true,
      availableForSearch: true
    }
  },
  {
    id: "T023",
    sensor: "RISAT-2BR1 SAR",
    date: "2025-01-15",
    dateIso: "2025-01-15",
    status: "READY",
    file: "RISAT2BR1_SAR_20250115_POL.tif",
    resolution: "0.35 m",
    crs: "EPSG:4326",
    lat: 27.58,
    lng: 91.86,
    coordinates: "27.58, 91.86",
    cloudCover: "0%",
    location: "Arunachal LAC",
    region: "Arunachal",
    image: "/satellite-tiles/T003.jpg",
    temporalPass: "2025 // Tawang Chu Riparian Valley",
    processingStatus: {
      metadataExtracted: true,
      tileGenerated: true,
      embeddingGenerated: true,
      faissIndexed: true,
      availableForSearch: true
    }
  }
];

export const DEFAULT_INGESTION_TILE = {
  id: "T027",
  file: "LC08_L2SP_145044_20250507.tif",
  sensor: "Landsat 8",
  date: "2025-05-07",
  lat: 22.57,
  lng: 88.36,
  bbox: "[22.45, 88.20, 22.70, 88.52]",
  crs: "EPSG:4326",
  resolution: "30 m",
  cloudCover: "12%",
  region: "Kolkata",
  fileSize: "24.6 MB",
  format: "GeoTIFF"
};

