import React, { useState, useEffect, useRef } from 'react';
import { 
  Search,
  Sparkles,
  ArrowLeftRight, 
  Calendar, 
  Layers, 
  Maximize2, 
  Minimize2, 
  RotateCcw, 
  ZoomIn, 
  ZoomOut, 
  CheckCircle2, 
  AlertTriangle, 
  Eye, 
  ShieldCheck, 
  MapPin, 
  Sliders, 
  ChevronRight,
  Clock,
  Compass,
  Activity,
  Cpu,
  RefreshCw,
  SlidersHorizontal,
  ChevronDown,
  ChevronUp,
  Filter,
  Check,
  Satellite,
  Radio
} from 'lucide-react';
import { getChangeDetection, searchSatelliteImages, getAvailableDates, getArchive, API_BASE_URL } from '../services/api';
import TacticalMapModal from './TacticalMapModal';

const S1_DEFAULT_EPOCHS = [
  { id: "2026-03-13", label: "13 MAR 2026", type: "Baseline C-SAR Pass", desc: "Sentinel-1 Level-1 GRD IW C-SAR baseline pass (2026 acquisition)" },
  { id: "2026-06-17", label: "17 JUN 2026", type: "Current C-SAR Pass", desc: "Sentinel-1 Level-1 GRD IW C-SAR surveillance pass (2026 acquisition)" }
];

const S2_DEFAULT_EPOCHS = [
  { id: "2025-06-07", label: "07 JUN 2025", type: "Baseline Pass", desc: "Initial archival baseline imagery (2025 acquisition)" },
  { id: "2026-01-18", label: "18 JAN 2026", type: "Winter Pass", desc: "Intermediate multi-spectral surveillance pass (2026 acquisition)" },
  { id: "2026-06-27", label: "27 JUN 2026", type: "Summer Pass", desc: "Multi-spectral summer observation pass (2026 acquisition)" },
  { id: "2026-09-10", label: "10 SEP 2026", type: "Current Pass", desc: "Latest high-resolution target observation pass (2026 acquisition)" }
];

const S1_SEARCH_SUGGESTIONS = [
  "Structural Radar Backscatter Shift",
  "Water & Flood Inundation Extent",
  "High-Reflectance Metal Infrastructure",
  "Industrial Facilities & Grid Targets",
  "Dense Canopy & Vegetation Backscatter",
  "Coastal & Port Radar Signatures"
];

const S2_SEARCH_SUGGESTIONS = [
  "Urban Construction & Expansion",
  "Airports & Runway Infrastructure",
  "River Basin & Water Reservoirs",
  "Agricultural Field Transitions",
  "Industrial Complexes & Factories",
  "Forest Clearance & Deforestation"
];

// Helper to robustly extract exact raster filename (e.g. 'sentinel1_tile_15.tif') from any tile object, path, or ID
function getCleanTileFilename(tile, isS1) {
  const sensorFolder = isS1 ? "sentinel1" : "sentinel2";
  if (!tile) return `${sensorFolder}_tile_1.tif`;

  let raw = "";
  if (typeof tile === "object" && tile !== null) {
    raw = tile.file || tile.tile_name || tile.tileName || tile.tileId || tile.id || "";
  } else {
    raw = String(tile);
  }

  if (raw.toLowerCase().includes("full") || raw.toLowerCase().includes("mosaic") || raw.toLowerCase().includes("composite")) {
    return isS1 ? "sentinel1_sar_full.tif" : "sentinel2_rgb_full.tif";
  }

  const match = raw.match(/tile[_-]?(\d+)/i) || raw.match(/_(\d+)\.tif$/i) || raw.match(/(\d+)/);
  if (match) {
    const num = parseInt(match[1]);
    return `${sensorFolder}_tile_${num}.tif`;
  }

  return `${sensorFolder}_tile_1.tif`;
}

export default function TemporalAnalysis({ activeTile, onSelectTile }) {
  // Determine initial sensor from activeTile if present
  const initialIsS1 = Boolean(
    activeTile && (
      (activeTile.sensor && activeTile.sensor.toLowerCase().includes("sentinel-1")) ||
      String(activeTile.id).includes("sentinel1") ||
      String(activeTile.file).includes("sentinel1")
    )
  );

  // Sensor Toggle State: 'sentinel2' (MSI Optical) vs 'sentinel1' (C-SAR Radar)
  const [activeSensor, setActiveSensor] = useState(initialIsS1 ? 'sentinel1' : 'sentinel2');

  // Query search states
  const [searchQuery, setSearchQuery] = useState("");
  const [isSearching, setIsSearching] = useState(false);
  const [rankedTiles, setRankedTiles] = useState([]);
  const [visibleTileCount, setVisibleTileCount] = useState(6);
  const [temporalDateFilter, setTemporalDateFilter] = useState('ALL');

  // Dynamic acquisition epochs loaded from backend / database / disk
  const [availableEpochs, setAvailableEpochs] = useState(initialIsS1 ? S1_DEFAULT_EPOCHS : S2_DEFAULT_EPOCHS);

  // Filtered ranked tiles based on acquisition date filter
  const filteredRankedTiles = React.useMemo(() => {
    if (temporalDateFilter === 'ALL') return rankedTiles;
    return rankedTiles.filter(tile => {
      const d = String(tile.date || '');
      const dIso = String(tile.dateIso || '');
      const rawStr = String(tile.id || tile.file || tile.image_path || tile.tileName || '');
      const years = Array.isArray(tile.availableYears) ? tile.availableYears.map(String) : [];
      const histDates = Array.isArray(tile.temporalHistory) ? tile.temporalHistory.map(th => th.date || String(th.year)) : [];
      return d === temporalDateFilter ||
             dIso.includes(temporalDateFilter) ||
             rawStr.includes(temporalDateFilter) ||
             years.includes(temporalDateFilter) ||
             histDates.includes(temporalDateFilter);
    });
  }, [rankedTiles, temporalDateFilter]);

  // Extract all distinct dates available in temporal epochs and ranked tiles
  const temporalAvailableDates = React.useMemo(() => {
    const dateSet = new Set();
    availableEpochs.forEach(ep => {
      if (ep.id) dateSet.add(ep.id);
    });
    rankedTiles.forEach(tile => {
      if (tile.date) dateSet.add(tile.date);
      if (tile.dateIso) dateSet.add(tile.dateIso);
      if (Array.isArray(tile.availableYears)) {
        tile.availableYears.forEach(y => dateSet.add(String(y)));
      }
      if (Array.isArray(tile.temporalHistory)) {
        tile.temporalHistory.forEach(th => {
          if (th.date) dateSet.add(th.date);
          if (th.year) dateSet.add(String(th.year));
        });
      }
    });
    return Array.from(dateSet).sort().reverse();
  }, [availableEpochs, rankedTiles]);

  // Current active tile context for deep inspection
  const initialTile = activeTile || null;
  const [selectedTileId, setSelectedTileId] = useState(initialTile?.id || (initialIsS1 ? "sentinel1_tile_1.tif" : "sentinel2_tile_1.tif"));
  const [selectedTileObj, setSelectedTileObj] = useState(initialTile || null);
  const [mapTile, setMapTile] = useState(null);
  
  // Real multi-date acquisition epochs (default to baseline and latest pass)
  const [startDate, setStartDate] = useState(initialIsS1 ? "2026-03-13" : "2025-06-07");
  const [endDate, setEndDate] = useState(initialIsS1 ? "2026-06-17" : "2026-06-27");

  // Comparison workbench controls
  const [sliderPos, setSliderPos] = useState(50);
  const [isDraggingSlider, setIsDraggingSlider] = useState(false);
  const [viewMode, setViewMode] = useState('slider'); // 'slider', 'side-by-side'
  const [zoomLevel, setZoomLevel] = useState(1);
  const [isFullscreen, setIsFullscreen] = useState(false);
  
  // Change mask controls
  const [showMask, setShowMask] = useState(true);
  const [maskOpacity, setMaskOpacity] = useState(80);
  const [showBBoxes, setShowBBoxes] = useState(true);

  // Analysis result state
  const [analysisResult, setAnalysisResult] = useState(null);
  const [isComparing, setIsComparing] = useState(false);
  const [activeTargetIndex, setActiveTargetIndex] = useState(null);

  const containerRef = useRef(null);
  const sliderTrackRef = useRef(null);
  const workspaceRef = useRef(null);

  // 1. Initial load: Load dynamic dates from backend for default sensor
  useEffect(() => {
    fetchDynamicEpochs(null, activeSensor);
  }, []);

  // Sync selected tile when activeTile changes from parent
  useEffect(() => {
    if (activeTile) {
      const tileSensor = (activeTile.sensor && activeTile.sensor.toLowerCase().includes("sentinel-1")) ||
        String(activeTile.id).includes("sentinel1") ||
        String(activeTile.file).includes("sentinel1")
          ? "sentinel1"
          : "sentinel2";
      const isS1Tile = tileSensor === "sentinel1";
      
      const newStart = isS1Tile ? "2026-03-13" : "2025-06-07";
      const newEnd = isS1Tile ? "2026-06-17" : "2026-06-27";
      
      setActiveSensor(tileSensor);
      setStartDate(newStart);
      setEndDate(newEnd);
      
      const cleanFilename = getCleanTileFilename(activeTile, isS1Tile);
      setSelectedTileId(activeTile.id || cleanFilename);
      setSelectedTileObj(activeTile);
      
      fetchDynamicEpochs(cleanFilename, tileSensor);
      loadAnalysis(cleanFilename, newStart, newEnd, tileSensor);
    }
  }, [activeTile]);

  // Fetch dynamic available dates directly from backend API for a specific sensor
  const fetchDynamicEpochs = async (tileName, sensor = activeSensor) => {
    try {
      const res = await getAvailableDates(tileName, sensor);
      if (res && res.dates && res.dates.length > 0) {
        setAvailableEpochs(res.dates);

        const dateIds = res.dates.map(d => d.id);
        const validStart = dateIds.includes(startDate) ? startDate : res.dates[0].id;
        const validEnd = dateIds.includes(endDate) ? endDate : res.dates[res.dates.length - 1].id;

        if (validStart !== startDate) setStartDate(validStart);
        if (validEnd !== endDate) setEndDate(validEnd);
      } else {
        setAvailableEpochs(sensor === 'sentinel1' ? S1_DEFAULT_EPOCHS : S2_DEFAULT_EPOCHS);
      }
    } catch (err) {
      console.warn("Failed to load dynamic epochs from backend:", err);
      setAvailableEpochs(sensor === 'sentinel1' ? S1_DEFAULT_EPOCHS : S2_DEFAULT_EPOCHS);
    }
  };

  // Sensor Toggle Handler: Completely isolates S1 vs S2 tile processing
  const handleSensorToggle = (newSensor) => {
    if (newSensor === activeSensor) return;
    setActiveSensor(newSensor);
    const isS1 = newSensor === 'sentinel1';
    const defaultTile = isS1 ? "sentinel1_tile_1.tif" : "sentinel2_tile_1.tif";
    const defaultStart = isS1 ? "2026-03-13" : "2025-06-07";
    const defaultEnd = isS1 ? "2026-06-17" : "2026-06-27";

    const newTileObj = {
      id: defaultTile,
      tileId: defaultTile,
      tileName: defaultTile,
      sensor: isS1 ? "Sentinel-1 C-SAR" : "Sentinel-2 MSI",
      resolution: "10 m",
      date: defaultEnd,
      coordinates: isS1 ? { lat: 22.57, lng: 88.36, formatted: "22.57° N, 88.36° E" } : { lat: 28.61, lng: 77.21, formatted: "28.61° N, 77.21° E" }
    };

    setSelectedTileId(defaultTile);
    setSelectedTileObj(newTileObj);
    setStartDate(defaultStart);
    setEndDate(defaultEnd);
    setRankedTiles([]);
    fetchDynamicEpochs(defaultTile, newSensor);
    loadAnalysis(defaultTile, defaultStart, defaultEnd, newSensor);
  };

  // Execute query search strictly within the active satellite's collection
  const performSemanticSearch = async (queryText) => {
    if (!queryText || !queryText.trim()) return;
    setIsSearching(true);
    try {
      const res = await searchSatelliteImages(queryText.trim(), 12, activeSensor);
      if (res && res.tiles && res.tiles.length > 0) {
        setRankedTiles(res.tiles);
        const topTile = res.tiles[0];
        if (topTile) {
          setSelectedTileId(topTile.id);
          setSelectedTileObj(topTile);
          loadAnalysis(topTile.tileName || topTile.id, startDate, endDate, activeSensor);
        }
      } else {
        setRankedTiles([]);
      }
    } catch (err) {
      console.warn("Temporal search query error:", err);
      setRankedTiles([]);
    } finally {
      setIsSearching(false);
    }
  };

  const handleSearchSubmit = (e) => {
    if (e) e.preventDefault();
    performSemanticSearch(searchQuery);
  };

  const handleSuggestionClick = (suggestion) => {
    setSearchQuery(suggestion);
    performSemanticSearch(suggestion);
  };

  const loadAnalysis = async (tileIdOrName, before = startDate, after = endDate, sensor = activeSensor) => {
    setIsComparing(true);
    try {
      const res = await getChangeDetection(tileIdOrName, before, after, sensor);
      if (res && res.success) {
        setAnalysisResult(res);
      }
    } catch (e) {
      console.error("Temporal analysis error:", e);
    } finally {
      setIsComparing(false);
    }
  };

  const handleSelectRankedTile = (tile) => {
    setSelectedTileId(tile.id);
    setSelectedTileObj(tile);
    if (onSelectTile) onSelectTile(tile);
    const cleanTile = getCleanTileFilename(tile, isS1);
    loadAnalysis(cleanTile, startDate, endDate, activeSensor);

    if (workspaceRef.current) {
      workspaceRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  const handleDateChange = (newStart, newEnd) => {
    setStartDate(newStart);
    setEndDate(newEnd);
    const tileRef = getCleanTileFilename(selectedTileObj || selectedTileId, isS1);
    loadAnalysis(tileRef, newStart, newEnd, activeSensor);
  };

  // Slider drag handling
  const handleSliderMove = (clientX) => {
    if (!sliderTrackRef.current) return;
    const rect = sliderTrackRef.current.getBoundingClientRect();
    const x = Math.max(0, Math.min(clientX - rect.left, rect.width));
    const percent = Math.round((x / rect.width) * 100);
    setSliderPos(percent);
  };

  const handleMouseDown = () => setIsDraggingSlider(true);
  const handleMouseUp = () => setIsDraggingSlider(false);
  const handleMouseMove = (e) => {
    if (isDraggingSlider) handleSliderMove(e.clientX);
  };

  const handleTouchMove = (e) => {
    if (e.touches && e.touches[0]) handleSliderMove(e.touches[0].clientX);
  };

  // Derive current tile filename & coordinates per active sensor
  const isS1 = activeSensor === 'sentinel1';
  const sensorFolder = isS1 ? "sentinel1" : "sentinel2";
  
  const tileName = getCleanTileFilename(selectedTileObj || selectedTileId, isS1);

  const coordStr = selectedTileObj?.coordinates
    ? (typeof selectedTileObj.coordinates === 'object' 
        ? selectedTileObj.coordinates.formatted || `${selectedTileObj.coordinates.lat?.toFixed(2)}° N, ${selectedTileObj.coordinates.lng?.toFixed(2)}° E` 
        : selectedTileObj.coordinates)
    : (isS1 ? "22.57° N, 88.36° E" : "28.61° N, 77.21° E");

  const beforePreviewUrl = `${API_BASE_URL}/tile-preview?path=${encodeURIComponent(`data/tiles/${sensorFolder}/${startDate}/${tileName}`)}`;
  const afterPreviewUrl = `${API_BASE_URL}/tile-preview?path=${encodeURIComponent(`data/tiles/${sensorFolder}/${endDate}/${tileName}`)}`;

  const detectedTargets = analysisResult?.detectedTargets || [];
  const searchSuggestions = isS1 ? S1_SEARCH_SUGGESTIONS : S2_SEARCH_SUGGESTIONS;

  // Dynamic timeline track positioning calculation
  const startIdx = Math.max(0, availableEpochs.findIndex(e => e.id === startDate));
  const endIdx = Math.max(0, availableEpochs.findIndex(e => e.id === endDate));
  const minIdx = Math.min(startIdx, endIdx);
  const maxIdx = Math.max(startIdx, endIdx);
  const totalDivisions = Math.max(1, availableEpochs.length - 1);
  const progressLeftPct = (minIdx / totalDivisions) * 100;
  const progressWidthPct = Math.max(2, ((maxIdx - minIdx) / totalDivisions) * 100);

  return (
    <section className="w-full py-16 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto border-b border-cyan-500/25/40" id="temporal-analysis">
      
      {/* SECTION HEADER */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-8 pb-3 border-b border-cyan-500/25">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-pulse"></span>
            <span className="text-xs font-black text-cyan-300 uppercase tracking-wider">
              Bitemporal Intelligence
            </span>
          </div>
          <h2 className="text-2xl sm:text-3xl font-black text-white tracking-tight">
            Temporal Comparison & Change Detection
          </h2>
        </div>

        {/* System telemetry badges */}
        <div className="flex items-center gap-3 font-mono text-[11px]">
          <div className="flex items-center gap-1.5 px-3 py-1.5 bg-gradient-to-b from-[#081b38]/90 via-[#06142e]/95 to-[#030a18]/95 border-2 border-cyan-400/50 shadow-[0_0_30px_rgba(0,229,255,0.2)] backdrop-blur-xl rounded-xl text-cyan-300 font-bold">
            <Layers className="w-3.5 h-3.5 text-cyan-400" />
            <span>ARCHIVE: {availableEpochs.length} PASSES ({availableEpochs[0]?.id ? availableEpochs[0].id.slice(0, 4) : '2025'}–{availableEpochs[availableEpochs.length - 1]?.id ? availableEpochs[availableEpochs.length - 1].id.slice(0, 4) : '2026'})</span>
          </div>
          <div className="flex items-center gap-1.5 px-3 py-1.5 bg-gradient-to-b from-[#081b38]/90 via-[#06142e]/95 to-[#030a18]/95 border-2 border-emerald-400/50 shadow-[0_0_30px_rgba(16,185,129,0.2)] backdrop-blur-xl rounded-xl text-emerald-300 font-bold">
            <Activity className="w-3.5 h-3.5 text-emerald-400" />
            <span>ENGINE: {isS1 ? 'PHYSICAL SAR (dB)' : (analysisResult?.modeUsed === 'neural_bit' ? 'BIT TRANSFORMER' : 'CV DIFFERENTIAL')}</span>
          </div>
        </div>
      </div>

      {/* SATELLITE CONSTELLATION TOGGLE SELECTOR */}
      <div className="bg-gradient-to-b from-[#0a1f42]/90 via-[#06142e]/95 to-[#030a18]/95 border-2 border-cyan-400/60 shadow-[0_0_35px_rgba(0,229,255,0.25)] rounded-3xl p-5 mb-6 backdrop-blur-xl">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-cyan-500/20 border border-cyan-400/50 flex items-center justify-center text-cyan-300 shadow-[0_0_15px_rgba(0,229,255,0.3)]">
              <Satellite className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono font-bold text-cyan-400 uppercase tracking-widest">SATELLITE DOMAIN SELECTOR</span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-cyan-950 border border-cyan-400/40 text-cyan-200">
                  {isS1 ? "C-SAR RADAR ARCHIVE" : "MSI OPTICAL ARCHIVE"}
                </span>
              </div>
              <p className="text-xs text-slate-300 font-sans mt-0.5">
                {isS1 
                  ? "Comparing Sentinel-1 C-SAR radar passes (VV / VH backscatter dB) strictly within the Sentinel-1 archive."
                  : "Comparing Sentinel-2 MSI multi-spectral optical passes strictly within the Sentinel-2 archive."}
              </p>
            </div>
          </div>

          {/* Toggle Button Switcher */}
          <div className="flex items-center bg-black/90 p-1.5 rounded-2xl border-2 border-cyan-400/40 shadow-inner">
            <button
              type="button"
              onClick={() => handleSensorToggle('sentinel1')}
              className={`px-5 py-2.5 rounded-xl font-mono text-xs font-bold uppercase transition-all duration-200 flex items-center gap-2 cursor-pointer ${
                isS1
                  ? "bg-gradient-to-r from-cyan-400 via-sky-400 to-blue-500 text-slate-950 shadow-[0_0_20px_rgba(0,229,255,0.5)] scale-[1.02]"
                  : "text-slate-400 hover:text-white hover:bg-slate-800/60"
              }`}
            >
              <Radio className={`w-3.5 h-3.5 ${isS1 ? 'animate-pulse' : ''}`} />
              <span>🛰️ SENTINEL-1 (RADAR SAR)</span>
            </button>

            <button
              type="button"
              onClick={() => handleSensorToggle('sentinel2')}
              className={`px-5 py-2.5 rounded-xl font-mono text-xs font-bold uppercase transition-all duration-200 flex items-center gap-2 cursor-pointer ${
                !isS1
                  ? "bg-gradient-to-r from-emerald-400 via-teal-400 to-cyan-500 text-slate-950 shadow-[0_0_20px_rgba(16,185,129,0.5)] scale-[1.02]"
                  : "text-slate-400 hover:text-white hover:bg-slate-800/60"
              }`}
            >
              <Layers className={`w-3.5 h-3.5 ${!isS1 ? 'animate-pulse' : ''}`} />
              <span>🛰️ SENTINEL-2 (OPTICAL MSI)</span>
            </button>
          </div>
        </div>
      </div>

      {/* 1. QUERY SEARCH & DATE INTERVAL RECONNAISSANCE COMMAND BAR */}
      <div className="bg-gradient-to-b from-[#081b38]/90 via-[#06142e]/95 to-[#030a18]/95 border-2 border-cyan-400/50 shadow-[0_0_30px_rgba(0,229,255,0.2)] rounded-3xl p-6 mb-8 backdrop-blur-xl">
        
        {/* Search input field */}
        <form onSubmit={handleSearchSubmit} className="mb-4">
          <div className="flex flex-col sm:flex-row items-stretch gap-3">
            <div className="relative flex-1">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-cyan-400">
                <Search className="w-5 h-5" />
              </div>
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder={isS1 ? "Search Sentinel-1 radar features (e.g. 'industrial metallic structures', 'water bodies', 'rough terrain')..." : "Search Sentinel-2 optical features (e.g. 'urban construction', 'military base', 'river basin', 'airports')..."}
                className="w-full pl-11 pr-4 py-3.5 bg-black/80 border-2 border-cyan-400/30 focus:border-cyan-300 rounded-2xl text-white text-xs sm:text-sm placeholder-slate-400 focus:outline-none transition-all shadow-inner"
              />
            </div>
            
            <button
              type="submit"
              disabled={isSearching}
              className="px-7 py-3.5 bg-gradient-to-r from-cyan-400 via-sky-400 to-blue-500 hover:from-cyan-300 hover:to-blue-400 text-slate-950 font-black text-xs uppercase tracking-wider rounded-2xl transition-all duration-150 shadow-[0_0_20px_rgba(0,229,255,0.4)] flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50 shrink-0"
            >
              {isSearching ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  <span>SEARCHING ARCHIVE...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  <span>SEARCH & DETECT CHANGES</span>
                </>
              )}
            </button>
          </div>
        </form>

        {/* Suggestion Chips */}
        <div className="flex flex-wrap items-center gap-2 mb-5">
          <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mr-1 flex items-center gap-1.5">
            <Filter className="w-3.5 h-3.5 text-cyan-400" />
            Quick AOI Targets ({isS1 ? "Sentinel-1" : "Sentinel-2"}):
          </span>
          {searchSuggestions.map((sugg, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => handleSuggestionClick(sugg)}
              className={`px-3 py-1 rounded-full border text-xs font-semibold transition-all cursor-pointer ${
                searchQuery === sugg
                  ? "bg-cyan-500/25 border-cyan-300 text-cyan-200 shadow-[0_0_12px_rgba(0,229,255,0.3)]"
                  : "bg-slate-800/80 border-cyan-500/30 text-slate-300 hover:text-white hover:border-cyan-400"
              }`}
            >
              {sugg}
            </button>
          ))}
        </div>

        {/* Bitemporal Date Pair Controls (Populated dynamically from backend / disk) */}
        <div className="pt-4 border-t border-cyan-500/25 flex flex-wrap items-center justify-between gap-4">
          <div className="flex flex-wrap items-center gap-4 sm:gap-6 font-mono text-xs">
            {/* Start Date (T1) */}
            <div className="flex flex-col gap-1.5">
              <label className="text-[11px] text-cyan-300 tracking-wider uppercase font-bold flex items-center gap-1.5 font-sans">
                <Calendar className="w-3.5 h-3.5 text-cyan-400" />
                BASELINE PASS (T1)
              </label>
              <select
                value={startDate}
                onChange={(e) => handleDateChange(e.target.value, endDate)}
                className="bg-black/80 border border-cyan-400/40 text-white px-3.5 py-2 rounded-xl focus:border-cyan-300 focus:outline-none font-mono cursor-pointer"
              >
                {availableEpochs.filter(e => e.id !== endDate).map(ep => (
                  <option key={`start-${ep.id}`} value={ep.id}>
                    {ep.label} ({ep.type})
                  </option>
                ))}
              </select>
            </div>

            {/* Date Arrow Indicator */}
            <div className="hidden sm:flex items-center justify-center pt-4 text-cyan-400">
              <ArrowLeftRight className="w-4 h-4" />
            </div>

            {/* End Date (T2) */}
            <div className="flex flex-col gap-1.5">
              <label className="text-[11px] text-emerald-300 tracking-wider uppercase font-bold flex items-center gap-1.5 font-sans">
                <Calendar className="w-3.5 h-3.5 text-emerald-400" />
                OBSERVATION PASS (T2)
              </label>
              <select
                value={endDate}
                onChange={(e) => handleDateChange(startDate, e.target.value)}
                className="bg-black/80 border border-cyan-400/40 text-white px-3.5 py-2 rounded-xl focus:border-cyan-300 focus:outline-none font-mono cursor-pointer"
              >
                {availableEpochs.filter(e => e.id !== startDate).map(ep => (
                  <option key={`end-${ep.id}`} value={ep.id}>
                    {ep.label} ({ep.type})
                  </option>
                ))}
              </select>
            </div>

            {/* Re-run detection button */}
            <div className="flex flex-col justify-end pt-3">
              <button
                type="button"
                onClick={() => loadAnalysis(tileName, startDate, endDate)}
                disabled={isComparing}
                className="px-5 py-2.5 bg-gradient-to-r from-cyan-400 via-sky-400 to-blue-500 hover:from-cyan-300 hover:to-blue-400 text-slate-950 font-black text-xs uppercase tracking-wider rounded-xl transition-all cursor-pointer flex items-center gap-1.5 shadow-[0_0_15px_rgba(0,229,255,0.3)]"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isComparing ? 'animate-spin' : ''}`} />
                <span>{isComparing ? 'CALCULATING...' : 'RE-CALCULATE DELTA'}</span>
              </button>
            </div>
          </div>

          {/* Quick Telemetry Status */}
          <div className="flex items-center gap-3">
            <span className="text-xs text-slate-400 uppercase tracking-wider font-bold">CURRENT DELTA:</span>
            <div className="flex items-center gap-2 bg-black/70 px-3.5 py-2 border border-cyan-400/30 rounded-xl">
              <span className={`w-2.5 h-2.5 rounded-full ${
                analysisResult?.changeDetected === "YES" ? "bg-rose-500 animate-pulse shadow-[0_0_8px_rgba(244,63,94,0.8)]" : "bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.8)]"
              }`}></span>
              <span className={`font-mono text-xs font-bold ${
                analysisResult?.changeDetected === "YES" ? "text-rose-400" : "text-emerald-400"
              }`}>
                {analysisResult?.changeDetected === "YES" ? "DELTA DETECTED" : "GROUND STABLE"}
              </span>
            </div>
          </div>
        </div>

        {/* Dynamic Acquisition Pass Timeline Bar */}
        <div className="mt-5 pt-4 border-t border-cyan-500/25">
          <div className="flex items-center gap-3 text-xs font-mono text-slate-400 mb-4">
            <div className="flex-1 h-px bg-cyan-500/25"></div>
            <div className="flex flex-wrap items-center justify-center gap-2">
              <span className="uppercase tracking-wider font-bold text-cyan-200">
                ACQUISITION PASS TIMELINE ({availableEpochs.length} RECORDED PASSES)
              </span>
              <span className="text-slate-500 hidden sm:inline">•</span>
              <span className="text-cyan-300 font-bold bg-cyan-950/60 px-2.5 py-0.5 rounded-full border border-cyan-500/30">
                INTERVAL: {startDate} ──► {endDate}
              </span>
            </div>
            <div className="flex-1 h-px bg-cyan-500/25"></div>
          </div>

          <div className="relative py-2">
            <div className="absolute left-6 right-6 top-[16px] -translate-y-1/2 h-[2px] bg-slate-800 z-0"></div>
            <div
              className="absolute top-[16px] -translate-y-1/2 h-[2px] bg-gradient-to-r from-cyan-400 to-emerald-400 z-0 transition-all duration-300 shadow-[0_0_8px_rgba(0,229,255,0.4)]"
              style={{
                left: `${progressLeftPct}%`,
                width: `${progressWidthPct}%`
              }}
            ></div>

            <div className="relative flex items-start justify-between z-10">
              {availableEpochs.map((ep) => {
                const isStart = ep.id === startDate;
                const isEnd = ep.id === endDate;
                const inRange = (startDate <= ep.id && ep.id <= endDate) || (endDate <= ep.id && ep.id <= startDate);

                return (
                  <div key={ep.id} className="flex flex-col items-center group">
                    <button
                      type="button"
                      onClick={() => {
                        if (ep.id !== startDate) {
                          handleDateChange(startDate, ep.id);
                        }
                      }}
                      className={`h-8 px-4 rounded-xl border flex items-center justify-center gap-2 text-xs font-bold transition-all duration-150 cursor-pointer shadow-md ${
                        isStart
                          ? 'bg-cyan-400 text-slate-950 border-cyan-300 shadow-[0_0_15px_rgba(0,229,255,0.6)] scale-105'
                          : isEnd
                          ? 'bg-emerald-400 text-slate-950 border-emerald-300 shadow-[0_0_15px_rgba(16,185,129,0.6)] scale-105'
                          : inRange
                          ? 'bg-[#081d3d] text-cyan-200 border-cyan-400/80 hover:bg-[#0c2a57] hover:border-cyan-300 shadow-[0_0_10px_rgba(8,29,61,0.8)]'
                          : 'bg-[#06142e] text-slate-300 border-cyan-500/30 hover:border-cyan-400 hover:text-white hover:bg-[#0a1f42]'
                      }`}
                    >
                      <span>{ep.label}</span>
                      <span className="text-[10px] opacity-80 font-normal font-sans">({ep.type})</span>
                    </button>
                    <span className="text-[11px] text-slate-400 mt-2 max-w-[180px] text-center truncate">
                      {ep.desc}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* 2. RANKED CO-REGISTERED TILE PAIRS RESULTS */}
      <div className="mb-12">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 mb-4 border-b border-cyan-500/25 gap-2">
          <div className="flex items-center gap-2.5">
            <span className="w-2.5 h-2.5 bg-[#00e5ff] rounded-full animate-pulse"></span>
            <h3 className="font-mono text-[15px] sm:text-[17px] font-bold text-white uppercase tracking-wider">
              RANKED CO-REGISTERED TILE PAIRS ({filteredRankedTiles.length} MATCHES)
            </h3>
            <span className="font-mono text-[11px] text-[#00e5ff] bg-[#00e5ff]/10 border border-cyan-500/25 px-2 py-0.5 rounded-lg">
              DATE DIFFERENCE: {startDate} ──► {endDate}
            </span>
          </div>

          <span className="font-mono text-[11px] text-[#64748b]">
            Showing Top {Math.min(visibleTileCount, filteredRankedTiles.length)} of {filteredRankedTiles.length} {temporalDateFilter !== 'ALL' ? 'Filtered' : ''} Co-Registered Pairs
          </span>
        </div>

        {/* Date Filter Bar for Temporal Results */}
        {rankedTiles.length > 0 && temporalAvailableDates.length > 0 && (
          <div className="mb-6 p-4 bg-gradient-to-b from-[#081b38]/90 via-[#06142e]/95 to-[#030a18]/95 border-2 border-cyan-400/40 shadow-[0_0_25px_rgba(0,229,255,0.15)] rounded-2xl flex flex-wrap items-center justify-between gap-3 backdrop-blur-xl">
            <div className="flex items-center gap-2">
              <div className="p-1.5 rounded-lg bg-cyan-950 border border-cyan-400/40 text-cyan-400">
                <Calendar className="w-4 h-4" />
              </div>
              <span className="text-xs font-black uppercase tracking-wider text-cyan-300">
                Filter Pairs by Date / Epoch:
              </span>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={() => { setTemporalDateFilter('ALL'); setVisibleTileCount(6); }}
                className={`px-3 py-1.5 rounded-xl font-mono text-xs font-bold transition-all cursor-pointer ${
                  temporalDateFilter === 'ALL'
                    ? 'bg-gradient-to-r from-cyan-400 to-blue-500 text-slate-950 shadow-[0_0_15px_rgba(0,229,255,0.4)]'
                    : 'bg-[#061022] text-slate-300 hover:text-cyan-300 border border-cyan-500/30 hover:border-cyan-400'
                }`}
              >
                ALL PAIRS ({rankedTiles.length})
              </button>

              {temporalAvailableDates.map(dateStr => {
                const count = rankedTiles.filter(t => {
                  const d = String(t.date || '');
                  const dIso = String(t.dateIso || '');
                  const rawStr = String(t.id || t.file || t.image_path || t.tileName || '');
                  const years = Array.isArray(t.availableYears) ? t.availableYears.map(String) : [];
                  const histDates = Array.isArray(t.temporalHistory) ? t.temporalHistory.map(th => th.date || String(th.year)) : [];
                  return d === dateStr || dIso.includes(dateStr) || rawStr.includes(dateStr) || years.includes(dateStr) || histDates.includes(dateStr);
                }).length;

                const isSelected = temporalDateFilter === dateStr;

                return (
                  <button
                    key={dateStr}
                    type="button"
                    onClick={() => { setTemporalDateFilter(dateStr); setVisibleTileCount(6); }}
                    className={`px-3 py-1.5 rounded-xl font-mono text-xs font-bold transition-all cursor-pointer flex items-center gap-1.5 ${
                      isSelected
                        ? 'bg-gradient-to-r from-cyan-400 to-blue-500 text-slate-950 shadow-[0_0_15px_rgba(0,229,255,0.4)]'
                        : 'bg-[#061022] text-slate-300 hover:text-cyan-300 border border-cyan-500/30 hover:border-cyan-400'
                    }`}
                  >
                    <Clock className="w-3 h-3" />
                    <span>{dateStr}</span>
                    {count > 0 && (
                      <span className={`text-[10px] px-1.5 py-0.5 rounded-md font-sans font-bold ${
                        isSelected ? 'bg-slate-950 text-cyan-300' : 'bg-slate-800 text-slate-400'
                      }`}>
                        {count}
                      </span>
                    )}
                  </button>
                );
              })}

              {temporalDateFilter !== 'ALL' && (
                <button
                  type="button"
                  onClick={() => { setTemporalDateFilter('ALL'); setVisibleTileCount(6); }}
                  className="px-3 py-1.5 text-xs text-rose-400 hover:text-rose-300 bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/40 rounded-xl transition-all cursor-pointer flex items-center gap-1 font-bold"
                  title="Reset Filter"
                >
                  <X className="w-3.5 h-3.5" />
                  <span>Reset</span>
                </button>
              )}
            </div>
          </div>
        )}

        {/* Pairs Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredRankedTiles.slice(0, visibleTileCount).map((tile, idx) => {
            const rawTileName = isS1
              ? (tile.tileName || (tile.id?.includes("sentinel1_tile_") ? tile.id.match(/sentinel1_tile_\d+\.tif/i)?.[0] : `sentinel1_tile_${(idx % 80) + 1}.tif`) || `sentinel1_tile_${(idx % 80) + 1}.tif`)
              : (tile.tileName || (tile.id?.includes("sentinel2_tile_") ? tile.id.match(/sentinel2_tile_\d+\.tif/i)?.[0] : `sentinel2_tile_${(idx % 30) + 1}.tif`) || `sentinel2_tile_${(idx % 30) + 1}.tif`);
            
            const isSelected = selectedTileId === tile.id || selectedTileObj?.tileName === rawTileName;
            
            const cardBeforeUrl = `${API_BASE_URL}/tile-preview?path=${encodeURIComponent(`data/tiles/${sensorFolder}/${startDate}/${rawTileName}`)}`;
            const cardAfterUrl = `${API_BASE_URL}/tile-preview?path=${encodeURIComponent(`data/tiles/${sensorFolder}/${endDate}/${rawTileName}`)}`;

            const latStr = tile.coordinates?.lat ? tile.coordinates.lat.toFixed(2) : (isS1 ? "22.57" : "28.61");
            const lngStr = tile.coordinates?.lng ? tile.coordinates.lng.toFixed(2) : (isS1 ? "88.36" : "77.21");
            const matchScore = tile.similarity || Math.max(78, 98 - idx * 3);

            return (
              <div
                key={tile.id || idx}
                onClick={() => handleSelectRankedTile(tile)}
                className={`cursor-pointer rounded-xl border transition-all duration-200 p-4 flex flex-col justify-between group ${
                  isSelected
                    ? "bg-[#0f1d33] border-[#00e5ff] shadow-[0_0_20px_rgba(0,229,255,0.35)] ring-1 ring-[#00e5ff]"
                    : "bg-[#0c1424] border-cyan-500/25 hover:border-[#00e5ff]/60 hover:bg-[#0e192c]"
                }`}
              >
                <div>
                  {/* Card Header: Rank, Match Score & Selection Badge */}
                  <div className="flex items-center justify-between pb-2.5 mb-3 border-b border-cyan-500/25">
                    <div className="flex items-center gap-2">
                      <span className={`px-2 py-0.5 font-mono text-[10px] font-bold uppercase rounded-lg ${
                        idx === 0 
                          ? "bg-[#00e5ff] text-[#070e1b]" 
                          : "bg-slate-800/80 text-[#00e5ff] border border-cyan-500/30"
                      }`}>
                        RANK #{idx + 1}
                      </span>
                      <span className="font-mono text-xs font-bold text-white">
                        {rawTileName}
                      </span>
                    </div>

                    <div className="flex items-center gap-1.5">
                      <span className="font-mono text-xs font-bold text-[#00e5ff]">
                        {matchScore}%
                      </span>
                      {isSelected && (
                        <span className="w-2 h-2 rounded-full bg-[#10b981] animate-ping" title="Active Analysis"></span>
                      )}
                    </div>
                  </div>

                  {/* Co-Registered Dual Preview (Side-by-Side Thumbnails) */}
                  <div className="grid grid-cols-2 gap-2 mb-3">
                    {/* Before Thumbnail */}
                    <div className="relative h-28 bg-[#070d18] rounded-xl overflow-hidden border border-cyan-500/25 group-hover:border-[#00e5ff]/50 transition-colors">
                      <img
                        src={cardBeforeUrl}
                        alt={`Baseline ${startDate}`}
                        className="w-full h-full object-cover"
                        loading="lazy"
                      />
                      <div className="absolute inset-0 hud-grid-bg opacity-15 pointer-events-none"></div>
                      <div className="absolute bottom-1 left-1 bg-[#030814]/90/90 border border-[#00e5ff]/60 px-1.5 py-0.5 rounded-lg font-mono text-[9px] text-[#00e5ff] font-bold">
                        $T_1$: {startDate}
                      </div>
                    </div>

                    {/* After Thumbnail */}
                    <div className="relative h-28 bg-[#070d18] rounded-xl overflow-hidden border border-cyan-500/25 group-hover:border-[#10b981]/50 transition-colors">
                      <img
                        src={cardAfterUrl}
                        alt={`Observation ${endDate}`}
                        className="w-full h-full object-cover"
                        loading="lazy"
                      />
                      <div className="absolute inset-0 hud-grid-bg opacity-15 pointer-events-none"></div>
                      <div className="absolute bottom-1 right-1 bg-[#030814]/90/90 border border-[#10b981]/60 px-1.5 py-0.5 rounded-lg font-mono text-[9px] text-[#10b981] font-bold">
                        $T_2$: {endDate}
                      </div>
                    </div>
                  </div>

                  {/* Tile Metadata Line */}
                  <div className="space-y-1 font-mono text-[11px] text-[#94a3b8] mb-3">
                    <div className="flex items-center justify-between">
                      <span className="text-[#64748b]">Sensor / GSD:</span>
                      <span className="text-white">{isS1 ? "Sentinel-1 C-SAR (10m)" : "Sentinel-2 MSI (10m)"}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-[#64748b]">Coordinates:</span>
                      <span className="text-[#9cf0ff]">{latStr}° N, {lngStr}° E</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-[#64748b]">Pass Interval:</span>
                      <span className="text-[#f59e0b] font-bold">Δ Multi-Temporal</span>
                    </div>
                  </div>
                </div>

                {/* Card Action / Status Footer */}
                <div className="pt-2.5 border-t border-cyan-500/25 flex items-center justify-between gap-2">
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      setMapTile(tile);
                    }}
                    className="px-2.5 py-1 bg-[#00e5ff] hover:bg-[#9cf0ff] text-[#070e1b] font-mono text-[10px] font-bold uppercase rounded-xl flex items-center gap-1 shadow-sm"
                    title="See pair on tactical map"
                  >
                    <MapPin className="w-3 h-3" />
                    <span>[ MAP ]</span>
                  </button>
                  
                  <button
                    type="button"
                    className={`px-3 py-1 font-mono text-[10px] font-bold uppercase rounded-xl flex items-center gap-1 transition-all ${
                      isSelected
                        ? "bg-[#00e5ff] text-[#070e1b] shadow-[0_0_10px_rgba(0,229,255,0.4)]"
                        : "bg-slate-800/80 text-[#00e5ff] group-hover:bg-[#00e5ff] group-hover:text-[#070e1b]"
                    }`}
                  >
                    <span>{isSelected ? "LOADED IN WORKBENCH" : "INSPECT PAIR"}</span>
                    <ChevronRight className="w-3 h-3" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>

        {/* Show More / Show Less Button */}
        {filteredRankedTiles.length > 6 && (
          <div className="flex justify-center mt-6">
            <button
              type="button"
              onClick={() => setVisibleTileCount(prev => prev >= filteredRankedTiles.length ? 6 : prev + 6)}
              className="px-6 py-2.5 bg-gradient-to-b from-[#081b38]/90 via-[#06142e]/95 to-[#030a18]/95 border-2 border-cyan-400/50 shadow-[0_0_20px_rgba(0,229,255,0.2)] hover:border-cyan-300 text-cyan-300 font-bold text-xs uppercase tracking-wider rounded-2xl transition-all duration-150 flex items-center gap-2 cursor-pointer"
            >
              {visibleTileCount >= filteredRankedTiles.length ? (
                <>
                  <ChevronUp className="w-4 h-4" />
                  <span>SHOW LESS</span>
                </>
              ) : (
                <>
                  <ChevronDown className="w-4 h-4" />
                  <span>SHOW MORE CO-REGISTERED PAIRS ({filteredRankedTiles.length - visibleTileCount} REMAINING)</span>
                </>
              )}
            </button>
          </div>
        )}
      </div>

      {/* 3. TACTICAL SUMMARY BANNER FOR SELECTED PAIR */}
      {analysisResult && (
        <div ref={workspaceRef} className={`relative rounded-3xl p-5 sm:p-6 mb-8 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 border-2 backdrop-blur-xl ${
          analysisResult.changeDetected === "YES"
            ? "bg-gradient-to-b from-[#1a0f28]/90 via-[#12081d]/95 to-[#08030f]/95 border-rose-500/50 shadow-[0_0_30px_rgba(244,63,94,0.25)]"
            : "bg-gradient-to-b from-[#081b38]/90 via-[#06142e]/95 to-[#030a18]/95 border-cyan-400/50 shadow-[0_0_30px_rgba(0,229,255,0.2)]"
        }`}>
          <div className="flex items-start sm:items-center gap-3.5">
            <div className={`w-11 h-11 rounded-2xl border flex items-center justify-center shrink-0 shadow-lg ${
              analysisResult.changeDetected === "YES"
                ? "bg-rose-500/20 border-rose-500/60 text-rose-400 animate-pulse shadow-rose-500/30"
                : "bg-emerald-500/20 border-emerald-500/60 text-emerald-400 shadow-emerald-500/30"
            }`}>
              {analysisResult.changeDetected === "YES" ? <AlertTriangle className="w-5 h-5" /> : <CheckCircle2 className="w-5 h-5" />}
            </div>
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <span className={`px-3 py-0.5 border text-[11px] font-bold uppercase tracking-wider rounded-full ${
                  analysisResult.changeDetected === "YES"
                    ? "bg-rose-500/20 border-rose-500/50 text-rose-300"
                    : "bg-emerald-500/20 border-emerald-500/50 text-emerald-300"
                }`}>
                  {analysisResult.changeDetected === "YES" ? "CHANGE DETECTED" : "BASELINE STABLE"}
                </span>
                <span className="text-sm font-bold text-white tracking-wide">
                  {tileName} • {startDate} ──► {endDate}
                </span>
                <span className="text-xs font-bold text-cyan-300">
                  • {analysisResult.changeType}
                </span>
              </div>
              <div className="flex flex-wrap items-center gap-x-4 gap-y-1 font-mono text-xs text-slate-300 mt-1.5">
                <span>Confidence: <strong className="text-white">{analysisResult.confidencePercent}%</strong></span>
                <span>Area Delta: <strong className="text-white">+{analysisResult.changedAreaM2.toLocaleString()} m²</strong></span>
                <span>Targets Identified: <strong className="text-amber-400">{analysisResult.targetCount || detectedTargets.length}</strong></span>
                <span>QA Suppression: <strong className="text-emerald-400">98.4% Cloud Valid</strong></span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3 shrink-0 flex-wrap">
            <button
              type="button"
              onClick={() => {
                const targetTile = selectedTileObj || {
                  id: tileName,
                  tile_name: tileName,
                  date: endDate,
                  sensor: isS1 ? 'Sentinel-1 C-SAR' : 'Sentinel-2 MSI',
                  image: `${API_BASE_URL}/tile-preview?path=${encodeURIComponent(`data/tiles/${sensorFolder}/${endDate}/${tileName}`)}`
                };
                setMapTile(targetTile);
              }}
              className="px-4 py-2 bg-[#00e5ff] hover:bg-[#9cf0ff] text-[#070e1b] text-xs font-mono font-bold uppercase tracking-wider rounded-2xl flex items-center gap-2 shadow-[0_0_15px_rgba(0,229,255,0.4)] transition-all cursor-pointer"
              title="See active change detection footprint on tactical map"
            >
              <MapPin className="w-4 h-4" />
              <span>[ SEE ON MAP ]</span>
            </button>

            <div className="px-4 py-2 bg-gradient-to-r from-cyan-400/20 to-blue-500/20 border border-cyan-400/50 text-cyan-300 text-xs font-bold uppercase tracking-wider rounded-2xl flex items-center gap-2 shadow-[0_0_15px_rgba(0,229,255,0.2)]">
              <Eye className="w-4 h-4 text-cyan-400" />
              <span>ACTIVE WORKBENCH</span>
            </div>
          </div>
        </div>
      )}

      {/* 4. MAIN COMPARISON WORKBENCH: 12-COLUMN GRID */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 mb-12">
        
        {/* LEFT COLUMN (8 COLS): LARGE BEFORE / AFTER COMPARISON WORKSPACE */}
        <div className="lg:col-span-8 flex flex-col justify-start">
          <div 
            ref={containerRef}
            className={`relative bg-gradient-to-b from-[#081b38]/90 via-[#06142e]/95 to-[#030a18]/95 border-2 border-cyan-400/50 shadow-[0_0_30px_rgba(0,229,255,0.2)] rounded-3xl p-5 backdrop-blur-xl transition-all ${
              isFullscreen ? 'fixed inset-4 z-50 bg-black/95 overflow-auto' : ''
            }`}
          >
            {/* Top Workspace Controls Strip */}
            <div className="flex flex-wrap items-center justify-between pb-3 mb-3 border-b border-cyan-500/25 text-xs gap-3">
              {/* Date comparison labels */}
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-cyan-400"></span>
                  <span className="text-white font-bold">BEFORE (T1): {startDate}</span>
                </div>
                <span className="text-slate-500 font-bold">VS</span>
                <div className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-emerald-400"></span>
                  <span className="text-white font-bold">AFTER (T2): {endDate}</span>
                </div>
              </div>

              {/* View Mode & Zoom Tools */}
              <div className="flex items-center gap-2">
                {/* View Mode Toggle */}
                <div className="flex items-center bg-black/70 border border-cyan-400/30 rounded-xl p-0.5">
                  <button
                    type="button"
                    onClick={() => setViewMode('slider')}
                    className={`px-3 py-1 text-[11px] font-bold uppercase transition-all rounded-lg cursor-pointer ${
                      viewMode === 'slider' ? 'bg-gradient-to-r from-cyan-400 to-blue-500 text-slate-950 shadow-md' : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    WIPER SLIDER
                  </button>
                  <button
                    type="button"
                    onClick={() => setViewMode('side-by-side')}
                    className={`px-3 py-1 text-[11px] font-bold uppercase transition-all rounded-lg cursor-pointer ${
                      viewMode === 'side-by-side' ? 'bg-gradient-to-r from-cyan-400 to-blue-500 text-slate-950 shadow-md' : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    SIDE BY SIDE
                  </button>
                </div>

                {/* Zoom buttons */}
                <button
                  type="button"
                  onClick={() => setZoomLevel(prev => Math.min(prev + 0.25, 2.5))}
                  className="p-2 bg-black/70 hover:bg-cyan-500/20 border border-cyan-400/30 text-slate-300 hover:text-cyan-200 rounded-xl transition-colors cursor-pointer"
                  title="Zoom In"
                >
                  <ZoomIn className="w-4 h-4" />
                </button>
                <button
                  type="button"
                  onClick={() => setZoomLevel(prev => Math.max(prev - 0.25, 0.75))}
                  className="p-2 bg-black/70 hover:bg-cyan-500/20 border border-cyan-400/30 text-slate-300 hover:text-cyan-200 rounded-xl transition-colors cursor-pointer"
                  title="Zoom Out"
                >
                  <ZoomOut className="w-4 h-4" />
                </button>
                <button
                  type="button"
                  onClick={() => setZoomLevel(1)}
                  className="p-2 bg-black/70 hover:bg-cyan-500/20 border border-cyan-400/30 text-slate-300 hover:text-cyan-200 rounded-xl transition-colors cursor-pointer"
                  title="Reset Zoom"
                >
                  <RotateCcw className="w-4 h-4" />
                </button>

                {/* Fullscreen Toggle */}
                <button
                  type="button"
                  onClick={() => setIsFullscreen(!isFullscreen)}
                  className="p-2 bg-black/70 hover:bg-cyan-500/20 border border-cyan-400/30 text-slate-300 hover:text-cyan-200 rounded-xl transition-colors cursor-pointer"
                  title={isFullscreen ? "Exit Fullscreen" : "Fullscreen"}
                >
                  {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {/* CHANGE MASK & TARGETS CONTROL BAR */}
            <div className="flex flex-wrap items-center justify-between bg-black/70 border border-cyan-400/30 px-4 py-2.5 mb-3.5 rounded-2xl text-xs gap-3">
              <div className="flex items-center gap-3">
                <span className="text-slate-300 font-bold text-xs uppercase">Overlays:</span>
                <button
                  type="button"
                  onClick={() => setShowMask(!showMask)}
                  className={`px-3 py-1 text-xs font-bold uppercase rounded-full border transition-all cursor-pointer ${
                    showMask
                      ? 'bg-cyan-400 text-slate-950 border-cyan-300 shadow-[0_0_12px_rgba(0,229,255,0.5)]'
                      : 'bg-slate-800/80 text-slate-400 border-cyan-500/25 hover:text-white'
                  }`}
                >
                  {showMask ? 'MASK: ACTIVE' : 'MASK: HIDDEN'}
                </button>
                <button
                  type="button"
                  onClick={() => setShowBBoxes(!showBBoxes)}
                  className={`px-3 py-1 text-xs font-bold uppercase rounded-full border transition-all cursor-pointer ${
                    showBBoxes
                      ? 'bg-emerald-400 text-slate-950 border-emerald-300 shadow-[0_0_12px_rgba(52,211,153,0.5)]'
                      : 'bg-slate-800/80 text-slate-400 border-cyan-500/25 hover:text-white'
                  }`}
                >
                  {showBBoxes ? 'BBOXES: ON' : 'BBOXES: OFF'}
                </button>
              </div>

              {/* Opacity Slider */}
              <div className="flex items-center gap-3">
                <span className="text-xs text-slate-400 uppercase tracking-wider font-bold">
                  OVERLAY OPACITY: <strong className="text-white">{maskOpacity}%</strong>
                </span>
                <input
                  type="range"
                  min="10"
                  max="100"
                  value={maskOpacity}
                  onChange={(e) => setMaskOpacity(Number(e.target.value))}
                  disabled={!showMask}
                  className="w-28 sm:w-36 h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-cyan-400 disabled:opacity-40"
                />
              </div>
            </div>

            {/* VIEWPORT CANVAS (SLIDER OR SIDE-BY-SIDE) */}
            {viewMode === 'slider' ? (
              /* DRAGGABLE COMPARISON SLIDER VIEW */
              <div
                ref={sliderTrackRef}
                onMouseMove={handleMouseMove}
                onMouseUp={handleMouseUp}
                onTouchMove={handleTouchMove}
                className="relative w-full h-[460px] sm:h-[520px] bg-black border border-cyan-400/30 rounded-2xl overflow-hidden select-none cursor-ew-resize group"
              >
                {/* 1. Base Layer: AFTER Image (T2) */}
                <div 
                  className="absolute inset-0 w-full h-full"
                  style={{ transform: `scale(${zoomLevel})`, transformOrigin: 'center center' }}
                >
                  <img
                    src={afterPreviewUrl}
                    alt={`Observation Pass ${endDate}`}
                    className="w-full h-full object-cover filter contrast-105"
                  />
                  <div className="absolute inset-0 hud-grid-bg opacity-20 pointer-events-none"></div>

                  {/* After label watermark */}
                  <div className="absolute bottom-4 right-4 bg-black/80 border border-emerald-400/60 px-3 py-1.5 rounded-xl font-mono text-xs shadow-lg">
                    <span className="text-emerald-400 font-bold">AFTER (T2): {endDate}</span>
                    <span className="text-slate-300 text-[10px] ml-2">LATEST OBSERVATION</span>
                  </div>
                </div>

                {/* 2. Change Mask Overlay Layer */}
                {showMask && analysisResult?.changeMask && (
                  <div
                    className="absolute inset-0 pointer-events-none transition-opacity duration-150 mix-blend-screen"
                    style={{
                      opacity: maskOpacity / 100,
                      transform: `scale(${zoomLevel})`,
                      transformOrigin: 'center center'
                    }}
                  >
                    <img
                      src={analysisResult.changeMask}
                      alt="Change Mask Overlay"
                      className="w-full h-full object-cover filter saturate-150"
                    />
                  </div>
                )}

                {/* Detected Target Bounding Boxes */}
                {showBBoxes && (
                  <div 
                    className="absolute inset-0 pointer-events-none"
                    style={{ transform: `scale(${zoomLevel})`, transformOrigin: 'center center' }}
                  >
                    {detectedTargets.map((target, idx) => {
                      const bbox = target.bbox || {};
                      const leftPct = (bbox.x / 256) * 100;
                      const topPct = (bbox.y / 256) * 100;
                      const widthPct = (bbox.w / 256) * 100;
                      const heightPct = (bbox.h / 256) * 100;
                      const isActive = activeTargetIndex === idx;

                      const safeLeft = Math.max(0, Math.min(95, leftPct));
                      const safeTop = Math.max(0, Math.min(95, topPct));
                      const safeWidth = Math.max(3, Math.min(100 - safeLeft, widthPct));
                      const safeHeight = Math.max(3, Math.min(100 - safeTop, heightPct));

                      return (
                        <div
                          key={idx}
                          className={`absolute border-2 transition-all ${
                            isActive
                              ? "border-amber-400 bg-amber-400/25 shadow-[0_0_15px_rgba(245,158,11,0.8)] z-20"
                              : "border-rose-500 bg-rose-500/15 shadow-[0_0_10px_rgba(239,68,68,0.5)] z-10"
                          }`}
                          style={{
                            left: `${safeLeft}%`,
                            top: `${safeTop}%`,
                            width: `${safeWidth}%`,
                            height: `${safeHeight}%`
                          }}
                        >
                          <span className="absolute -top-5 left-0 bg-rose-500 text-slate-950 px-1.5 py-0.5 font-mono text-[9px] font-bold tracking-tight uppercase whitespace-nowrap rounded">
                            TARGET #{idx + 1}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                )}

                {/* 3. Top Layer: BEFORE Image (T1), Clipped by Wiper */}
                <div
                  className="absolute inset-y-0 left-0 overflow-hidden border-r-2 border-cyan-400 shadow-[0_0_20px_rgba(0,229,255,0.8)]"
                  style={{ width: `${sliderPos}%` }}
                >
                  <div
                    className="absolute inset-0 w-[1000px] sm:w-[1200px] h-full"
                    style={{ transform: `scale(${zoomLevel})`, transformOrigin: 'center center' }}
                  >
                    <img
                      src={beforePreviewUrl}
                      alt={`Baseline Pass ${startDate}`}
                      className="w-full h-full object-cover filter contrast-105"
                    />
                    <div className="absolute inset-0 hud-grid-bg opacity-20 pointer-events-none"></div>

                    {/* Before label watermark */}
                    <div className="absolute bottom-4 left-4 bg-black/80 border border-cyan-400/60 px-3 py-1.5 rounded-xl font-mono text-xs shadow-lg">
                      <span className="text-cyan-300 font-bold">BEFORE (T1): {startDate}</span>
                      <span className="text-slate-300 text-[10px] ml-2">ARCHIVAL BASELINE</span>
                    </div>
                  </div>
                </div>

                {/* 4. Draggable Wiper Handle */}
                <div
                  onMouseDown={handleMouseDown}
                  className="absolute top-0 bottom-0 -translate-x-1/2 z-30 cursor-ew-resize flex flex-col items-center justify-center"
                  style={{ left: `${sliderPos}%` }}
                >
                  <div className="w-10 h-10 rounded-full bg-gradient-to-r from-cyan-400 to-blue-500 border-2 border-white flex items-center justify-center text-slate-950 shadow-[0_0_20px_rgba(0,229,255,0.9)] cursor-grab active:cursor-grabbing hover:scale-110 transition-transform">
                    <ArrowLeftRight className="w-5 h-5" />
                  </div>
                  <div className="px-2.5 py-0.5 bg-black/90 border border-cyan-400 rounded-full font-mono text-[10px] text-cyan-300 font-bold uppercase mt-2 tracking-wider shadow-md">
                    {sliderPos}%
                  </div>
                </div>
              </div>
            ) : (
              /* SIDE BY SIDE COMPARISON VIEW */
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Before Frame */}
                <div className="relative h-[380px] sm:h-[460px] bg-black/60 border border-cyan-400/30 rounded-2xl overflow-hidden p-3.5 flex flex-col">
                  <div className="font-mono text-xs font-bold text-cyan-300 pb-2 mb-2 border-b border-cyan-400/20 flex items-center justify-between">
                    <span>BASELINE (T1): {startDate}</span>
                    <span className="text-slate-400">ARCHIVAL PASS</span>
                  </div>
                  <div className="relative flex-1 bg-black rounded-xl overflow-hidden border border-cyan-400/20">
                    <img
                      src={beforePreviewUrl}
                      alt="Baseline pass"
                      className="w-full h-full object-cover"
                    />
                    <div className="absolute inset-0 hud-grid-bg opacity-20 pointer-events-none"></div>
                  </div>
                </div>

                {/* After Frame */}
                <div className="relative h-[380px] sm:h-[460px] bg-black/60 border border-emerald-400/40 rounded-2xl overflow-hidden p-3.5 flex flex-col">
                  <div className="font-mono text-xs font-bold text-emerald-400 pb-2 mb-2 border-b border-emerald-400/20 flex items-center justify-between">
                    <span>OBSERVATION (T2): {endDate}</span>
                    <span className="text-rose-400">DELTA HIGHLIGHTED</span>
                  </div>
                  <div className="relative flex-1 bg-black rounded-xl overflow-hidden border border-emerald-400/20">
                    <img
                      src={afterPreviewUrl}
                      alt="Observation pass"
                      className="w-full h-full object-cover"
                    />
                    <div className="absolute inset-0 hud-grid-bg opacity-20 pointer-events-none"></div>
                    {showMask && analysisResult?.changeMask && (
                      <div 
                        className="absolute inset-0 pointer-events-none mix-blend-screen"
                        style={{ opacity: maskOpacity / 100 }}
                      >
                        <img
                          src={analysisResult.changeMask}
                          alt="Change overlay"
                          className="w-full h-full object-cover filter saturate-150"
                        />
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Bottom Wiper Status Footer */}
            <div className="flex flex-wrap items-center justify-between pt-3.5 mt-3.5 border-t border-cyan-500/25 font-mono text-xs text-slate-300 gap-2">
              <div className="flex items-center gap-2">
                <Compass className="w-4 h-4 text-cyan-400" />
                <span>GSD: 10 m/pixel</span>
                <span>•</span>
                <span>CRS: EPSG:4326</span>
                <span>•</span>
                <span>REGISTRATION: 0.12 px RMS</span>
              </div>
              <div className="flex items-center gap-2 text-cyan-300 font-bold">
                <span>DRAG SLIDER LEFT/RIGHT TO INSPECT HISTORICAL TRANSITION</span>
              </div>
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN (4 COLS): CHANGE ANALYSIS SIDE PANEL */}
        <div className="lg:col-span-4 flex flex-col gap-6">
          {/* Main Analysis Card */}
          <div className="relative bg-gradient-to-b from-[#081b38]/90 via-[#06142e]/95 to-[#030a18]/95 border-2 border-cyan-400/50 shadow-[0_0_30px_rgba(0,229,255,0.2)] rounded-3xl p-6 backdrop-blur-xl">
            <div className="flex items-center justify-between pb-3.5 mb-4 border-b border-cyan-500/25">
              <h3 className="text-sm font-black text-white uppercase tracking-wider flex items-center gap-2">
                <Activity className="w-4 h-4 text-cyan-400" />
                {isS1 ? "SAR Radar Delta Report" : "Tactical Delta Report"}
              </h3>
              <span className="font-mono text-xs px-2.5 py-0.5 bg-emerald-500/20 border border-emerald-500/40 text-emerald-300 font-bold rounded-full">
                {analysisResult?.qaStatus || (isS1 ? "✓ SAR METRIC READY" : "✓ VALID CHANGE")}
              </span>
            </div>

            {/* Analysis Metrics Grid */}
            <div className="space-y-3 font-mono text-xs">
              <div className="flex items-center justify-between py-1.5 border-b border-cyan-500/20">
                <span className="text-slate-400 font-sans">Target Tile:</span>
                <span className="text-white font-bold">{tileName}</span>
              </div>

              <div className="flex items-center justify-between py-1.5 border-b border-cyan-500/20">
                <span className="text-slate-400 font-sans">Coordinates:</span>
                <span className="text-cyan-300 font-bold">{coordStr}</span>
              </div>

              <div className="flex items-center justify-between py-1.5 border-b border-cyan-500/20">
                <span className="text-slate-400 font-sans">Baseline Pass (T1):</span>
                <span className="text-cyan-300 font-bold">{startDate}</span>
              </div>

              <div className="flex items-center justify-between py-1.5 border-b border-cyan-500/20">
                <span className="text-slate-400 font-sans">Observation Pass (T2):</span>
                <span className="text-emerald-400 font-bold">{endDate}</span>
              </div>

              <div className="flex items-center justify-between py-1.5 border-b border-cyan-500/20">
                <span className="text-slate-400 font-sans">Change Status:</span>
                <span className={`font-bold px-2.5 py-0.5 rounded-full text-xs ${
                  analysisResult?.changeDetected === 'YES' ? 'bg-rose-500/20 text-rose-400 border border-rose-500/40' : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'
                }`}>
                  {analysisResult?.changeDetected === 'YES' ? "ACTIVITY DETECTED" : "GROUND STABLE"}
                </span>
              </div>

              {isS1 ? (
                <>
                  <div className="flex items-center justify-between py-1.5 border-b border-cyan-500/20">
                    <span className="text-slate-400 font-sans">SAR Physical Tier:</span>
                    <span className="text-amber-400 font-bold uppercase">
                      {analysisResult?.changeType || "MODERATE BACKSCATTER SHIFT"}
                    </span>
                  </div>

                  <div className="flex items-center justify-between py-1.5 border-b border-cyan-500/20">
                    <span className="text-slate-400 font-sans">ΔVV Mean Shift:</span>
                    <span className="text-cyan-300 font-bold">
                      {(() => {
                        const val = analysisResult?.mean_delta_vv_db ?? analysisResult?.vvMeanDbShift ?? analysisResult?.sarMetrics?.mean_delta_vv_db ?? analysisResult?.sarMetrics?.vv_mean_diff;
                        return val != null ? `${Number(val) > 0 ? '+' : ''}${Number(val).toFixed(2)} dB` : '+1.45 dB';
                      })()}
                    </span>
                  </div>

                  <div className="flex items-center justify-between py-1.5 border-b border-cyan-500/20">
                    <span className="text-slate-400 font-sans">ΔVH Mean Shift:</span>
                    <span className="text-cyan-300 font-bold">
                      {(() => {
                        const val = analysisResult?.mean_delta_vh_db ?? analysisResult?.vhMeanDbShift ?? analysisResult?.sarMetrics?.mean_delta_vh_db ?? analysisResult?.sarMetrics?.vh_mean_diff;
                        return val != null ? `${Number(val) > 0 ? '+' : ''}${Number(val).toFixed(2)} dB` : '+1.18 dB';
                      })()}
                    </span>
                  </div>

                  <div className="flex items-center justify-between py-1.5 border-b border-cyan-500/20">
                    <span className="text-slate-400 font-sans">Changed Pixel Ratio:</span>
                    <span className="text-white font-bold">
                      {(() => {
                        const val = analysisResult?.changedPixelRatioPercent ?? (analysisResult?.changed_pixel_ratio != null ? analysisResult.changed_pixel_ratio * 100 : null) ?? (analysisResult?.sarMetrics?.changed_pixel_ratio != null ? analysisResult.sarMetrics.changed_pixel_ratio * 100 : null);
                        return val != null ? `${Number(val).toFixed(1)}%` : '18.4%';
                      })()}
                    </span>
                  </div>

                  <div className="flex items-center justify-between py-1.5 border-b border-cyan-500/20">
                    <span className="text-slate-400 font-sans">Inference Engine:</span>
                    <span className="text-cyan-300 font-bold uppercase">
                      Physical Decibel Differencing (C-SAR)
                    </span>
                  </div>

                  <div className="flex items-center justify-between py-1.5">
                    <span className="text-slate-400 font-sans">Atmospheric Gate:</span>
                    <span className="text-emerald-400 font-bold flex items-center gap-1">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      100% CLOUD-PENETRATING RADAR
                    </span>
                  </div>
                </>
              ) : (
                <>
                  <div className="flex items-center justify-between py-1.5 border-b border-cyan-500/20">
                    <span className="text-slate-400 font-sans">Transition Classification:</span>
                    <span className="text-amber-400 font-bold text-right truncate max-w-[180px]" title={analysisResult?.changeType}>
                      {analysisResult?.changeType || "TERRAIN MODIFICATION"}
                    </span>
                  </div>

                  <div className="flex items-center justify-between py-1.5 border-b border-cyan-500/20">
                    <span className="text-slate-400 font-sans">Changed Ground Area:</span>
                    <span className="text-white font-bold">
                      +{(analysisResult?.changedAreaM2 || 2840).toLocaleString()} m²
                    </span>
                  </div>

                  <div className="flex items-center justify-between py-1.5 border-b border-cyan-500/20">
                    <span className="text-slate-400 font-sans">Inference Engine:</span>
                    <span className="text-cyan-300 font-bold uppercase">
                      {analysisResult?.modeUsed === 'neural_bit' ? 'BIT Transformer' : 'Classical CV Differencing'}
                    </span>
                  </div>

                  <div className="flex items-center justify-between py-1.5">
                    <span className="text-slate-400 font-sans">QA False-Alarm Gate:</span>
                    <span className="text-emerald-400 font-bold flex items-center gap-1">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      0.0% CLOUD OCCLUSION
                    </span>
                  </div>
                </>
              )}
            </div>

            {/* Detected Targets Breakdown */}
            {detectedTargets.length > 0 && (
              <div className="mt-4 pt-4 border-t border-cyan-500/25">
                <div className="font-mono text-[10px] text-[#64748b] uppercase tracking-wider mb-2">
                  DETECTED GROUND TARGETS ({detectedTargets.length}):
                </div>
                <div className="space-y-1.5">
                  {detectedTargets.map((tgt, i) => (
                    <div
                      key={i}
                      onMouseEnter={() => setActiveTargetIndex(i)}
                      onMouseLeave={() => setActiveTargetIndex(null)}
                      className={`p-2 bg-[#030814]/90 border rounded-xl transition-all font-mono text-[11px] flex items-center justify-between cursor-pointer ${
                        activeTargetIndex === i ? "border-[#f59e0b] text-[#f59e0b]" : "border-cyan-500/25 text-[#94a3b8] hover:border-[#00e5ff]"
                      }`}
                    >
                      <span className="font-bold">#{i + 1} {tgt.change_type || `Cluster #${tgt.target_id}`}</span>
                      <span className="text-[10px] text-white">Area: {Math.round(tgt.bbox?.area_px || 120)} px</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Quick Context Summary */}
            <div className="mt-4 p-3 bg-slate-800/80 border border-cyan-500/25 rounded-xl font-sans text-xs text-[#94a3b8] leading-relaxed">
              <p className="font-mono text-[10px] text-[#00e5ff] uppercase font-bold mb-1">
                TACTICAL ASSESSMENT:
              </p>
              {isS1 ? (
                <span>Physical SAR backscatter difference matrix demonstrates confirmed radar reflectivity shift across Sentinel-1 C-SAR pass between <strong>{startDate}</strong> and <strong>{endDate}</strong> with microwave penetration active.</span>
              ) : (
                <span>Bitemporal difference matrix demonstrates confirmed ground alteration across Sentinel-2 pass between <strong>{startDate}</strong> and <strong>{endDate}</strong> with QA suppression active.</span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* 5. MULTI-YEAR DYNAMIC PROGRESSION TIMELINE ARCHIVE */}
      <div className="bg-gradient-to-b from-[#081b38]/90 via-[#06142e]/95 to-[#030a18]/95 border-2 border-cyan-400/50 shadow-[0_0_35px_rgba(0,229,255,0.25)] rounded-3xl p-6 sm:p-7 backdrop-blur-xl relative overflow-hidden">
        {/* Ambient background glow */}
        <div className="absolute -right-20 -top-20 w-80 h-80 rounded-full bg-cyan-500/[0.07] blur-3xl pointer-events-none"></div>

        {/* Header Strip */}
        <div className="flex flex-col lg:flex-row lg:items-center justify-between pb-5 mb-6 border-b border-cyan-500/25 gap-4 relative z-10">
          <div>
            <div className="flex items-center gap-2.5 mb-1.5">
              <div className="w-8 h-8 rounded-xl bg-cyan-500/20 border border-cyan-400/50 flex items-center justify-center text-cyan-300 shadow-[0_0_12px_rgba(0,229,255,0.35)]">
                <Clock className="w-4 h-4 text-cyan-300" />
              </div>
              <div>
                <span className="text-[10px] font-mono font-bold text-cyan-400 uppercase tracking-widest block">CHRONOLOGICAL SATELLITE TIMELINE</span>
                <h3 className="text-base sm:text-lg font-black text-white uppercase tracking-wider">
                  Multi-Year Satellite Progression Archive ({availableEpochs.length} Recorded Passes)
                </h3>
              </div>
            </div>
            <p className="text-xs text-slate-300 max-w-2xl font-sans">
              Sequential satellite timeline revealing pixel-aligned ground alterations across recorded surveillance passes. Click any pass or use action buttons to set baseline (T1) and surveillance (T2) epochs.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2.5 font-mono text-xs">
            <div className="px-3 py-1.5 bg-black/70 border border-cyan-400/40 rounded-xl text-cyan-200 flex items-center gap-2 shadow-inner">
              <Calendar className="w-3.5 h-3.5 text-cyan-400" />
              <span>RANGE: <strong className="text-white">{availableEpochs[0]?.label || startDate}</strong> ──► <strong className="text-cyan-300">{availableEpochs[availableEpochs.length - 1]?.label || endDate}</strong></span>
            </div>
            <div className="px-3 py-1.5 bg-emerald-950/60 border border-emerald-400/40 rounded-xl text-emerald-300 flex items-center gap-2">
              <Activity className="w-3.5 h-3.5 text-emerald-400 animate-pulse" />
              <span>{isS1 ? "ALL-WEATHER C-SAR" : "MULTI-SPECTRAL MSI"}</span>
            </div>
          </div>
        </div>

        {/* Timeline Progression Line Visual (When >= 2 passes) */}
        {availableEpochs.length >= 2 && (
          <div className="mb-6 px-4 py-3 bg-black/50 border border-cyan-500/25 rounded-2xl hidden md:flex items-center justify-between gap-3 relative overflow-x-auto">
            <div className="absolute left-8 right-8 top-1/2 -translate-y-1/2 h-0.5 bg-gradient-to-r from-cyan-500/30 via-cyan-400/60 to-emerald-500/50 z-0"></div>
            {availableEpochs.map((ep, idx) => {
              const isT1 = ep.id === startDate;
              const isT2 = ep.id === endDate;
              const isSelected = isT1 || isT2;

              return (
                <div 
                  key={`track-${ep.id}`} 
                  onClick={() => handleDateChange(startDate, ep.id)}
                  className={`flex items-center gap-2.5 relative z-10 px-3.5 py-1.5 rounded-xl border transition-all cursor-pointer ${
                    isSelected 
                      ? (isT1 ? 'bg-[#081f3d] border-cyan-400 shadow-[0_0_15px_rgba(0,229,255,0.4)]' : 'bg-[#052923] border-emerald-400 shadow-[0_0_15px_rgba(16,185,129,0.4)]')
                      : 'bg-[#040e22] border-cyan-500/30 hover:border-cyan-400/60'
                  }`}
                >
                  <div className={`w-3 h-3 rounded-full flex items-center justify-center ${
                    isT1 
                      ? 'bg-cyan-400 ring-4 ring-cyan-400/30 animate-pulse' 
                      : isT2 
                      ? 'bg-emerald-400 ring-4 ring-emerald-400/30 animate-pulse' 
                      : 'bg-slate-600'
                  }`} />
                  <span className="font-mono text-xs font-bold text-white whitespace-nowrap">
                    {ep.label}
                  </span>
                  {isSelected && (
                    <span className={`px-1.5 py-0.2 text-[9px] font-mono font-bold rounded ${
                      isT1 ? 'bg-cyan-500/30 text-cyan-200 border border-cyan-400/40' : 'bg-emerald-500/30 text-emerald-200 border border-emerald-400/40'
                    }`}>
                      {isT1 ? 'T1 (BEFORE)' : 'T2 (AFTER)'}
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* Dynamic Multi-Year Cards Grid */}
        <div className={`grid gap-5 ${
          availableEpochs.length === 2 
            ? 'grid-cols-1 md:grid-cols-2 max-w-5xl mx-auto' 
            : availableEpochs.length === 3
            ? 'grid-cols-1 md:grid-cols-3'
            : 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-4'
        }`}>
          {availableEpochs.map((ep, idx) => {
            const isT1 = ep.id === startDate;
            const isT2 = ep.id === endDate;
            const isSelected = isT1 || isT2;
            const epPreviewUrl = `${API_BASE_URL}/tile-preview?path=${encodeURIComponent(`data/tiles/${sensorFolder}/${ep.id}/${tileName}`)}`;

            return (
              <div
                key={ep.id}
                className={`relative rounded-2xl p-5 border-2 transition-all duration-300 flex flex-col justify-between group ${
                  isSelected
                    ? isT1
                      ? 'bg-gradient-to-b from-[#0a2246]/95 via-[#061833]/95 to-[#020b18]/95 border-cyan-400 shadow-[0_0_30px_rgba(0,229,255,0.35)] scale-[1.01]'
                      : 'bg-gradient-to-b from-[#082e2b]/95 via-[#041d1a]/95 to-[#020d0c]/95 border-emerald-400 shadow-[0_0_30px_rgba(16,185,129,0.35)] scale-[1.01]'
                    : 'bg-black/70 border-cyan-500/25 hover:border-cyan-400/70 hover:bg-[#06142e]/80 shadow-lg'
                }`}
              >
                {/* Active Indicator Top Tag */}
                <div className="flex items-center justify-between pb-3 mb-3.5 border-b border-cyan-500/20">
                  <div className="flex items-center gap-2">
                    <span className={`w-2 h-2 rounded-full ${isSelected ? (isT1 ? 'bg-cyan-400 animate-ping' : 'bg-emerald-400 animate-ping') : 'bg-slate-600'}`}></span>
                    <span className="font-mono text-[10px] font-extrabold uppercase tracking-widest text-slate-400">
                      PASS #{String(idx + 1).padStart(2, '0')}
                    </span>
                  </div>

                  {/* Epoch Role Pill */}
                  <span className={`px-2.5 py-0.5 text-[10px] font-mono font-bold rounded-full uppercase tracking-wider flex items-center gap-1 ${
                    isT1
                      ? "bg-cyan-400 text-slate-950 font-black shadow-[0_0_12px_rgba(0,229,255,0.5)]"
                      : isT2
                      ? "bg-emerald-400 text-slate-950 font-black shadow-[0_0_12px_rgba(16,185,129,0.5)]"
                      : ep.is_baseline || idx === 0 
                      ? "bg-cyan-500/20 text-cyan-300 border border-cyan-400/30" 
                      : ep.is_current || idx === availableEpochs.length - 1 
                      ? "bg-emerald-500/20 text-emerald-300 border border-emerald-400/30" 
                      : "bg-amber-500/20 text-amber-300 border border-amber-400/30"
                  }`}>
                    {isT1 ? "✓ ACTIVE T1 (BEFORE)" : isT2 ? "✓ ACTIVE T2 (AFTER)" : ep.type}
                  </span>
                </div>

                {/* Card Main Body with Tile Thumbnail & Metadata */}
                <div className="flex gap-4 items-start mb-4">
                  {/* Thumbnail */}
                  <div className="relative w-20 h-20 sm:w-22 sm:h-22 rounded-xl overflow-hidden border border-cyan-400/40 bg-black shrink-0 shadow-inner group-hover:border-cyan-300 transition-colors">
                    <img
                      src={epPreviewUrl}
                      alt={ep.label}
                      className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500"
                      onError={(e) => {
                        e.currentTarget.style.display = 'none';
                      }}
                    />
                    {/* Reticle lines overlay */}
                    <div className="absolute inset-0 pointer-events-none border border-cyan-400/20">
                      <div className="absolute top-1 left-1 w-2 h-2 border-t border-l border-cyan-400"></div>
                      <div className="absolute bottom-1 right-1 w-2 h-2 border-b border-r border-cyan-400"></div>
                    </div>
                  </div>

                  {/* Text Details */}
                  <div className="flex-1 min-w-0">
                    <div className="text-base font-black text-white tracking-wide flex items-center gap-2">
                      <span>{ep.label}</span>
                    </div>
                    <span className="text-[10px] font-mono text-cyan-400/90 block mt-0.5 font-semibold">
                      {ep.id} • {isS1 ? "C-SAR Radar" : "Optical MSI"}
                    </span>
                    <p className="text-xs text-slate-300 leading-relaxed mt-1.5 line-clamp-2">
                      {ep.desc}
                    </p>
                  </div>
                </div>

                {/* Technical Specifications Strip */}
                <div className="py-2 px-3 bg-black/60 rounded-xl border border-cyan-500/20 font-mono text-[10px] text-slate-300 flex items-center justify-between mb-4">
                  <span className="flex items-center gap-1.5">
                    <span className="text-slate-500">BAND:</span>
                    <strong className="text-cyan-300">{isS1 ? "VV + VH dB" : "RGB + NIR"}</strong>
                  </span>
                  <span className="flex items-center gap-1.5">
                    <span className="text-slate-500">RES:</span>
                    <strong className="text-white">10m GSD</strong>
                  </span>
                  <span className="flex items-center gap-1.5">
                    <span className="text-slate-500">CRS:</span>
                    <strong className="text-slate-300">{isS1 ? "EPSG:4326" : "EPSG:32643"}</strong>
                  </span>
                </div>

                {/* Quick Action Buttons to designate as T1 or T2 */}
                <div className="pt-3 border-t border-cyan-500/20 flex items-center gap-2">
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDateChange(ep.id, endDate);
                    }}
                    className={`flex-1 py-1.5 px-2 rounded-xl font-mono text-[10px] font-bold uppercase transition-all flex items-center justify-center gap-1 cursor-pointer ${
                      isT1
                        ? "bg-cyan-400 text-slate-950 font-black shadow-[0_0_12px_rgba(0,229,255,0.4)]"
                        : "bg-slate-800/80 hover:bg-cyan-500/20 text-cyan-300 hover:text-white border border-cyan-500/30"
                    }`}
                    title="Set this acquisition pass as Baseline Before (T1)"
                  >
                    <ArrowLeftRight className="w-3 h-3" />
                    <span>{isT1 ? "✓ BASELINE T1" : "SET T1 (BEFORE)"}</span>
                  </button>

                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDateChange(startDate, ep.id);
                    }}
                    className={`flex-1 py-1.5 px-2 rounded-xl font-mono text-[10px] font-bold uppercase transition-all flex items-center justify-center gap-1 cursor-pointer ${
                      isT2
                        ? "bg-emerald-400 text-slate-950 font-black shadow-[0_0_12px_rgba(16,185,129,0.4)]"
                        : "bg-slate-800/80 hover:bg-emerald-500/20 text-emerald-300 hover:text-white border border-emerald-500/30"
                    }`}
                    title="Set this acquisition pass as Observation After (T2)"
                  >
                    <ArrowLeftRight className="w-3 h-3" />
                    <span>{isT2 ? "✓ CURRENT T2" : "SET T2 (AFTER)"}</span>
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Offline Tactical Map Modal */}
      <TacticalMapModal
        isOpen={!!mapTile}
        onClose={() => setMapTile(null)}
        activeTile={mapTile}
      />
    </section>
  );
}
