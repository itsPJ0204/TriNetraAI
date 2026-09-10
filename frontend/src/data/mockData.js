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

export const CANDIDATE_TILES = [
  {
    id: "T027",
    sensor: "Sentinel-2 MSI",
    resolution: "10 m",
    date: "14 JUN 2023",
    timestamp: "2023-06-14T05:42:18Z",
    coordinates: { lat: 22.57, lng: 88.36, formatted: "22.57° N, 88.36° E" },
    crs: "EPSG:4326",
    similarity: 92,
    status: "CANDIDATE VERIFIED",
    detectedObjects: [
      { label: "CAMP_CLUSTER", count: 18, confidence: 91.4 },
      { label: "ARMOR_COL_T90", count: 4, confidence: 87.2 },
      { label: "BUILDING", count: 12, confidence: 78.5 },
      { label: "ACCESS_ROAD", count: 2, confidence: 84.1 }
    ],
    boundingBoxes: [
      { id: "box1", label: "CAMP_HQ_CLUSTER", x: 24, y: 18, width: 38, height: 30, confidence: 91.4, color: "#00e5ff" },
      { id: "box2", label: "ARMOR_COL_T90", x: 62, y: 55, width: 28, height: 22, confidence: 87.2, color: "#10b981" },
      { id: "box3", label: "BUNKER_ARTILLERY", x: 68, y: 22, width: 24, height: 18, confidence: 93.8, color: "#f59e0b" }
    ],
    hydrology: {
      nearestRiver: "River Galwan / Riparian Channel",
      distanceMeters: 350,
      thresholdMeters: 500,
      isNearRiver: true,
      status: "CONDITION PASSED // COMPLIANT"
    },
    qa: {
      status: "VALID CHANGE",
      score: 95.8,
      cloudOcclusion: "0.0% (PRISTINE)",
      shadowArtifacts: "LOW",
      passed: true
    },
    markerState: "high_confidence",
    availableYears: [2020, 2021, 2022, 2023, 2024, 2025],
    temporalHistory: [
      {
        year: 2020,
        date: "2020-06-14",
        label: "No structure",
        status: "BASELINE",
        description: "Pristine undeveloped riverbank & alluvial soil",
        detectedChange: false,
        structuresCount: 0,
        activityLevel: "Zero human footprint",
        preview: "Natural terrain, vegetation along riverbank"
      },
      {
        year: 2021,
        date: "2021-06-18",
        label: "No structure",
        status: "STABLE",
        description: "Minimal seasonal variance, zero military presence",
        detectedChange: false,
        structuresCount: 0,
        activityLevel: "Stable terrain, no alterations",
        preview: "Unaltered river boundary buffer"
      },
      {
        year: 2022,
        date: "2022-07-02",
        label: "Construction detected",
        status: "FIRST_OBSERVED",
        description: "Ground grading, initial trenching, earthmoving machinery detected",
        detectedChange: true,
        structuresCount: 6,
        activityLevel: "Active earthworks & excavation",
        preview: "Heavy vehicle tracks and initial foundation cuts"
      },
      {
        year: 2023,
        date: "2023-06-14",
        label: "Structure completed",
        status: "HIGH_CONFIDENCE_CHANGE",
        description: "Fortified military base, concrete pads, perimeter revetments",
        detectedChange: true,
        structuresCount: 22,
        activityLevel: "High garrison & armor staging",
        preview: "Full barracks cluster, radar dome, armed checkpoint"
      },
      {
        year: 2024,
        date: "2024-05-20",
        label: "Operational activity",
        status: "ACTIVE_CAMP",
        description: "Armored convoy transit, communications tower active",
        detectedChange: true,
        structuresCount: 28,
        activityLevel: "Battalion HQ command presence",
        preview: "Expanded helipad apron and underground ammo revetment"
      },
      {
        year: 2025,
        date: "2025-05-07",
        label: "Hardened perimeter",
        status: "FORTIFIED_COMPLEX",
        description: "Reinforced bunker roofing, secondary security berm, SAM coverage",
        detectedChange: true,
        structuresCount: 34,
        activityLevel: "Permanent fortified tactical installation",
        preview: "Heavily fortified perimeter with multi-layered defensive buffer"
      }
    ],
    changeAnalysis: {
      baselineYear: 2020,
      currentYear: 2023,
      beforeDate: "2020-06-14",
      afterDate: "2023-06-14",
      changeDetected: "YES",
      changeType: "NEW STRUCTURE",
      detectedChange: "NEW FORTIFIED MILITARY STRUCTURES",
      confidence: 91.4,
      firstObservedYear: 2022,
      changedAreaM2: 4280,
      qaStatus: "✓ VALID CHANGE",
      needsReview: true,
      newStructuresCount: 22,
      beforeDesc: "OCT 2020 // Pristine undeveloped alluvial riverbank",
      afterDesc: "NOV 2023 // Fortified military base, concrete pads, perimeter revetments"
    }
  },
  {
    id: "T084",
    sensor: "Cartosat-3 PAN",
    resolution: "0.25 m",
    date: "08 MAY 2023",
    timestamp: "2023-05-08T06:15:02Z",
    coordinates: { lat: 34.15, lng: 77.58, formatted: "34.15° N, 77.58° E" },
    crs: "EPSG:4326 (UTM 43N)",
    similarity: 89,
    status: "HIGH ANOMALY",
    detectedObjects: [
      { label: "FORTIFIED_STAGING", count: 1, confidence: 88.9 },
      { label: "HEAVY_REVETMENT", count: 8, confidence: 92.1 },
      { label: "RADAR_DOME", count: 2, confidence: 86.4 }
    ],
    boundingBoxes: [
      { id: "box4", label: "FORTIFIED_STAGING", x: 30, y: 25, width: 42, height: 35, confidence: 88.9, color: "#f59e0b" },
      { id: "box5", label: "RADAR_DOME", x: 74, y: 15, width: 16, height: 16, confidence: 86.4, color: "#00e5ff" }
    ],
    hydrology: {
      nearestRiver: "Shyok River Tributary",
      distanceMeters: 410,
      thresholdMeters: 500,
      isNearRiver: true,
      status: "CONDITION PASSED // COMPLIANT"
    },
    qa: {
      status: "VALID CHANGE",
      score: 93.2,
      cloudOcclusion: "0.4%",
      shadowArtifacts: "MINIMAL",
      passed: true
    },
    markerState: "change_detected",
    availableYears: [2020, 2021, 2022, 2023, 2024, 2025],
    temporalHistory: [
      { year: 2020, date: "2020-05-12", label: "No structure", status: "BASELINE", description: "Remote ridge terrain, unpaved footpath", detectedChange: false, structuresCount: 0 },
      { year: 2021, date: "2021-05-15", label: "No structure", status: "STABLE", description: "Zero vehicular access, natural scree slope", detectedChange: false, structuresCount: 0 },
      { year: 2022, date: "2022-08-10", label: "Construction detected", status: "FIRST_OBSERVED", description: "Access switchbacks blasted, concrete foundation pouring", detectedChange: true, structuresCount: 4 },
      { year: 2023, date: "2023-05-08", label: "Structure completed", status: "CHANGE_DETECTED", description: "High-altitude hardened surveillance & radar dome installed", detectedChange: true, structuresCount: 14 },
      { year: 2024, date: "2024-06-11", label: "Operational activity", status: "ACTIVE_OUTPOST", description: "Secondary communication dish and perimeter fence", detectedChange: true, structuresCount: 18 },
      { year: 2025, date: "2025-04-30", label: "Hardened perimeter", status: "FORTIFIED_SITE", description: "Underground bunker reinforced with stone revetments", detectedChange: true, structuresCount: 22 }
    ],
    changeAnalysis: {
      baselineYear: 2020,
      currentYear: 2023,
      beforeDate: "2020-05-12",
      afterDate: "2023-05-08",
      changeDetected: "YES",
      changeType: "RADAR & STAGING EXTENSION",
      detectedChange: "RADAR & STAGING EXTENSION",
      changedAreaM2: 3150,
      confidence: 88.9,
      firstObservedYear: 2022,
      qaStatus: "✓ VALID CHANGE",
      needsReview: true,
      newStructuresCount: 14,
      beforeDesc: "SEP 2020 // Mountain ridge outpost",
      afterDesc: "MAY 2023 // High-altitude hardened surveillance facility"
    }
  },
  {
    id: "T119",
    sensor: "RISAT-2BR1 SAR",
    resolution: "0.35 m",
    date: "22 SEP 2022",
    timestamp: "2022-09-22T21:48:33Z",
    coordinates: { lat: 27.58, lng: 91.86, formatted: "27.58° N, 91.86° E" },
    crs: "EPSG:4326 (UTM 45N)",
    similarity: 86,
    status: "MONITORED",
    markerState: "search_result",
    availableYears: [2020, 2021, 2022, 2023, 2024, 2025],
    temporalHistory: [
      { year: 2020, date: "2020-09-10", label: "No structure", status: "BASELINE", description: "High-altitude pasture and alpine forest edge", detectedChange: false, structuresCount: 0 },
      { year: 2021, date: "2021-10-04", label: "No structure", status: "CLEARING", description: "Tree felling and preliminary land clearing", detectedChange: false, structuresCount: 1 },
      { year: 2022, date: "2022-09-22", label: "Construction detected", status: "FIRST_OBSERVED", description: "All-weather reinforced aviation pad & apron grading", detectedChange: true, structuresCount: 9 },
      { year: 2023, date: "2023-08-14", label: "Structure completed", status: "OPERATIONAL_APRON", description: "Dual helipad active, logistics depot operational", detectedChange: true, structuresCount: 15 },
      { year: 2024, date: "2024-07-22", label: "Operational activity", status: "EXPANDED_HUB", description: "Helicopter maintenance hangar added", detectedChange: true, structuresCount: 19 },
      { year: 2025, date: "2025-05-02", label: "Hardened perimeter", status: "TACTICAL_BASE", description: "Perimeter watchtowers and underground fuel depot", detectedChange: true, structuresCount: 24 }
    ],
    detectedObjects: [
      { label: "REINFORCED_APRON", count: 1, confidence: 86.1 },
      { label: "HELI_PAD", count: 3, confidence: 89.7 },
      { label: "LOGISTICS_DEPOT", count: 6, confidence: 82.0 }
    ],
    boundingBoxes: [
      { id: "box6", label: "REINFORCED_APRON", x: 18, y: 35, width: 48, height: 26, confidence: 86.1, color: "#00e5ff" },
      { id: "box7", label: "HELI_PAD", x: 70, y: 40, width: 20, height: 20, confidence: 89.7, color: "#10b981" }
    ],
    hydrology: {
      nearestRiver: "Tawang Chu River",
      distanceMeters: 280,
      thresholdMeters: 500,
      isNearRiver: true,
      status: "CONDITION PASSED // COMPLIANT"
    },
    qa: {
      status: "VALID CHANGE",
      score: 91.0,
      cloudOcclusion: "ALL-WEATHER SAR",
      shadowArtifacts: "NONE (RADAR)",
      passed: true
    },
    changeAnalysis: {
      baselineYear: 2021,
      currentYear: 2022,
      beforeDate: "2021-10-04",
      afterDate: "2022-09-22",
      changeDetected: "YES",
      changeType: "RUNWAY & HELIPAD EXPANSION",
      detectedChange: "RUNWAY & HELIPAD EXPANSION",
      changedAreaM2: 5600,
      confidence: 86.1,
      firstObservedYear: 2022,
      qaStatus: "✓ VALID CHANGE",
      needsReview: true,
      newStructuresCount: 9,
      beforeDesc: "OCT 2021 // Unpaved clearing",
      afterDesc: "SEP 2022 // All-weather reinforced aviation pad"
    }
  }
];

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

export const INITIAL_ARCHIVE = [
  {
    id: "T026",
    sensor: "Sentinel-2",
    date: "2025-04-19",
    status: "ACTIVE",
    file: "S2A_MSIL2A_20250419T054218.tif",
    resolution: "10 m",
    crs: "EPSG:4326",
    lat: 34.15,
    lng: 77.58,
    cloudCover: "2%",
    region: "Ladakh LAC Sector"
  },
  {
    id: "T025",
    sensor: "Landsat 8",
    date: "2025-03-12",
    status: "ACTIVE",
    file: "LC08_L2SP_145044_20250312.tif",
    resolution: "30 m",
    crs: "EPSG:4326",
    lat: 22.57,
    lng: 88.36,
    cloudCover: "8%",
    region: "Kolkata Maritime"
  },
  {
    id: "T024",
    sensor: "Cartosat-3 PAN",
    date: "2025-02-28",
    status: "ACTIVE",
    file: "CART3_PAN_20250228_WGS84.tif",
    resolution: "0.25 m",
    crs: "EPSG:4326",
    lat: 23.75,
    lng: 68.15,
    cloudCover: "0%",
    region: "Sir Creek Tidal Flat"
  },
  {
    id: "T023",
    sensor: "RISAT-2BR1 SAR",
    date: "2025-01-15",
    status: "ACTIVE",
    file: "RISAT2BR1_SAR_20250115_POL.tif",
    resolution: "0.35 m",
    crs: "EPSG:4326",
    lat: 27.58,
    lng: 91.86,
    cloudCover: "0% (All-Weather SAR)",
    region: "Arunachal LAC Foothills"
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

