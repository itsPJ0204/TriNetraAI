import React, { useState, useEffect, useMemo } from 'react';
import { 
  Eye, Layers, Compass, CheckCircle2, Clock, Calendar, 
  Target, MapPin, Sparkles, Activity, Maximize2, X, 
  ZoomIn, ZoomOut, RotateCcw, ShieldCheck, Database,
  ChevronDown, ChevronUp, ArrowRight, Map, Filter
} from 'lucide-react';
import TacticalMapModal from './TacticalMapModal';
import { API_BASE_URL } from '../services/api';

export default function CandidateTilesGrid({ tiles, selectedTileId, onSelectTile, activeQuery }) {
  const [imageErrorMap, setImageErrorMap] = useState({});
  const [maximizedTile, setMaximizedTile] = useState(null);
  const [modalZoom, setModalZoom] = useState(1);
  const [visibleCount, setVisibleCount] = useState(6);
  const [mapTile, setMapTile] = useState(null);
  const [selectedSensorFilter, setSelectedSensorFilter] = useState('sentinel2');
  const [selectedDateFilter, setSelectedDateFilter] = useState('ALL');

  // Strictly filter out any full scene composites (sentinel2_rgb_full.tif, sentinel1_sar_full.tif) so candidate results only display 256x256 sub-tiles
  const candidateSubTiles = useMemo(() => {
    return tiles.filter(t => {
      const lower = `${t.tileName || ''} ${t.file || ''} ${t.id || ''} ${t.raw_path || ''} ${t.image_path || ''} ${t.filepath || ''}`.toLowerCase();
      const isFull = t.imageType === 'Full' || lower.includes('_full') || lower.includes('rgb_full') || lower.includes('sar_full') || lower.includes('full_scene') || lower.includes('full_composite');
      return !isFull;
    });
  }, [tiles]);

  // Filter sub-tiles by selected satellite sensor (default: Sentinel-2 Optical)
  const filteredBySensorTiles = useMemo(() => {
    if (selectedSensorFilter === 'ALL') return candidateSubTiles;
    const isTargetS1 = selectedSensorFilter === 'sentinel1';
    const matches = candidateSubTiles.filter(t => {
      const lower = `${t.sensor || ''} ${t.tileName || ''} ${t.file || ''} ${t.id || ''} ${t.raw_path || ''} ${t.image_path || ''}`.toLowerCase();
      const isS1 = lower.includes('sentinel1') || lower.includes('sentinel-1') || lower.includes('c-sar');
      return isTargetS1 ? isS1 : !isS1;
    });
    return matches.length > 0 ? matches : candidateSubTiles;
  }, [candidateSubTiles, selectedSensorFilter]);

  // Extract all distinct dates strictly available for the filtered tiles (YYYY-MM-DD only)
  const availableDates = useMemo(() => {
    const dateSet = new Set();
    filteredBySensorTiles.forEach(tile => {
      if (typeof tile.date === 'string') {
        const m = tile.date.match(/\d{4}-\d{2}-\d{2}/);
        if (m) dateSet.add(m[0]);
      }
      if (typeof tile.dateIso === 'string') {
        const m = tile.dateIso.match(/\d{4}-\d{2}-\d{2}/);
        if (m) dateSet.add(m[0]);
      }
      const rawPath = String(tile.image_path || tile.filepath || tile.raw_path || tile.image || tile.file || tile.id || '');
      const pathMatch = rawPath.match(/(\d{4}-\d{2}-\d{2})/);
      if (pathMatch) dateSet.add(pathMatch[1]);
    });
    return Array.from(dateSet).sort().reverse();
  }, [filteredBySensorTiles]);

  // Filter tiles based on selected date
  const filteredTiles = useMemo(() => {
    if (selectedDateFilter === 'ALL') return filteredBySensorTiles;
    return filteredBySensorTiles.filter(tile => {
      const tileDate = String(tile.date || tile.dateIso || '');
      const raw = String(tile.image_path || tile.filepath || tile.raw_path || tile.image || tile.file || tile.id || '');
      return tileDate.includes(selectedDateFilter) || raw.includes(selectedDateFilter);
    });
  }, [filteredBySensorTiles, selectedDateFilter]);

  // Helper to dynamically resolve genuine satellite raster preview URL for active date
  const getTileImageSrc = (tile, dateOverride = selectedDateFilter) => {
    if (!tile) return "/satellite-tiles/default.jpg";

    // 1. If it's a blob or data URL from client file upload, return directly
    if (typeof tile.image === 'string' && (tile.image.startsWith('blob:') || tile.image.startsWith('data:'))) {
      return tile.image;
    }

    // 2. Resolve relative GeoTIFF filepath
    let relativePath = "";

    if (tile.filepath && !tile.filepath.startsWith('http')) {
      relativePath = tile.filepath;
    } else if (tile.raw_path && !tile.raw_path.startsWith('http')) {
      relativePath = tile.raw_path;
    } else if (tile.image_path && !tile.image_path.startsWith('http')) {
      relativePath = tile.image_path;
    } else if (typeof tile.image === 'string') {
      if (tile.image.includes('path=')) {
        try {
          const encoded = tile.image.split('path=')[1]?.split('&')[0];
          relativePath = decodeURIComponent(encoded);
        } catch (e) {
          relativePath = "";
        }
      } else if (!tile.image.startsWith('http://') && !tile.image.startsWith('https://')) {
        relativePath = tile.image;
      }
    }

    // 3. Fallback: synthesize valid dataset filepath from sensor, date, and tile name
    if (!relativePath) {
      const s = String(tile.sensor || '').toLowerCase();
      const isS1 = s.includes('sentinel1') || s.includes('sar') || s.includes('c-sar') || s.includes('s1');
      const folder = isS1 ? 'sentinel1' : 'sentinel2';
      const file = tile.tileName || tile.file || (isS1 ? 'sentinel1_tile_1.tif' : 'sentinel2_tile_1.tif');
      const date = tile.date || tile.dateIso || (isS1 ? '2026-06-17' : '2026-06-27');
      relativePath = `data/tiles/${folder}/${date}/${file}`;
    }

    // Sanitize path (strip leading slashes, fix backslashes)
    let cleanPath = relativePath.replace(/\\/g, '/').replace(/^\/+/, '');
    if (cleanPath.includes('sentinel2_full_scene.tif')) {
      cleanPath = cleanPath.replace('sentinel2_full_scene.tif', 'sentinel2_rgb_full.tif');
    }
    if (cleanPath.includes('sentinel1_full_composite.tif')) {
      cleanPath = cleanPath.replace('sentinel1_full_composite.tif', 'sentinel1_sar_full.tif');
    }

    // 4. If a specific date override is selected (not 'ALL'), rewrite date segment in path
    if (dateOverride && dateOverride !== 'ALL' && /\d{4}-\d{2}-\d{2}/.test(cleanPath)) {
      cleanPath = cleanPath.replace(/\d{4}-\d{2}-\d{2}/, dateOverride);
    }

    const isTif = cleanPath.toLowerCase().endsWith('.tif') || cleanPath.toLowerCase().endsWith('.tiff');
    if (isTif) {
      return `${API_BASE_URL}/tile-preview?path=${encodeURIComponent(cleanPath)}`;
    }
    return `${API_BASE_URL}/${cleanPath}`;
  };

  const getTileDate = (tile, dateOverride = selectedDateFilter) => {
    if (dateOverride && dateOverride !== 'ALL') {
      return dateOverride;
    }
    return tile.date || tile.dateIso || "Recent Acquisition";
  };

  // Reset any previous image error states when filter, query, or tiles change
  useEffect(() => {
    setImageErrorMap({});
  }, [selectedDateFilter, activeQuery, tiles]);

  useEffect(() => {
    setVisibleCount(6);
  }, [activeQuery, tiles.length, selectedDateFilter]);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        setMaximizedTile(null);
        setModalZoom(1);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const handleTemporalClick = (tileId) => {
    onSelectTile(tileId);
    if (maximizedTile) setMaximizedTile(null);
    setTimeout(() => {
      const el = document.getElementById('temporal-analysis');
      if (el) el.scrollIntoView({ behavior: 'smooth' });
    }, 50);
  };

  const handleImageError = (tileId) => {
    setImageErrorMap(prev => ({ ...prev, [tileId]: true }));
  };

  const openTileModal = (tile, e) => {
    if (e) e.stopPropagation();
    onSelectTile(tile.id);
    setMaximizedTile(tile);
    setModalZoom(1);
  };

  const displayedTiles = filteredTiles.slice(0, visibleCount);

  return (
    <section className="w-full py-16 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto border-b border-cyan-500/25 animate-fade-in" id="candidate-tiles">
      {/* Active Search Query Result Banner */}
      {activeQuery && (
        <div className="mb-8 px-5 py-3.5 bg-gradient-to-b from-[#081b38]/90 via-[#06142e]/95 to-[#030a18]/95 border-2 border-cyan-400/50 shadow-[0_0_30px_rgba(0,229,255,0.2)] border border-cyan-500/30 rounded-2xl text-xs flex flex-wrap items-center justify-between gap-3 backdrop-blur-xl shadow-lg shadow-cyan-500/5">
          <div className="flex items-center gap-2.5">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            <span className="text-slate-400 font-medium">Active Search:</span>
            <span className="text-cyan-300 font-semibold">"{activeQuery}"</span>
          </div>
          <div className="flex items-center gap-3 text-xs">
            <span className="text-cyan-400 font-medium">{tiles.length} Candidate Tiles Matched</span>
            <span className="text-slate-700">|</span>
            <span className="text-emerald-400 font-medium">RemoteCLIP &bull; 38ms</span>
          </div>
        </div>
      )}

      {/* Controls Bar */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="w-2 h-2 rounded-full bg-cyan-400"></span>
            <span className="text-xs text-cyan-400 font-semibold tracking-wider uppercase">
              Geospatial Catalog
            </span>
          </div>
          <h2 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
            Ranked Candidate Tiles
          </h2>
          <p className="text-sm text-slate-400 mt-1 max-w-2xl">
            Real-time geospatial vector matches ranked by RemoteCLIP multimodal similarity with high-fidelity satellite imagery.
          </p>
        </div>

        {/* Satellite Constellation & Tiles Count Indicator */}
        <div className="flex flex-wrap items-center gap-3 self-start md:self-center">
          <div className="flex items-center bg-black/80 p-1 rounded-2xl border border-cyan-400/40 shadow-inner">
            <button
              type="button"
              onClick={() => { setSelectedSensorFilter('sentinel2'); setSelectedDateFilter('ALL'); setVisibleCount(6); }}
              className={`px-3.5 py-1.5 rounded-xl font-mono text-xs font-bold transition-all cursor-pointer ${
                selectedSensorFilter === 'sentinel2'
                  ? 'bg-gradient-to-r from-emerald-400 to-teal-500 text-slate-950 shadow-[0_0_15px_rgba(16,185,129,0.4)]'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              🛰️ Sentinel-2 (Optical)
            </button>
            <button
              type="button"
              onClick={() => { setSelectedSensorFilter('sentinel1'); setSelectedDateFilter('ALL'); setVisibleCount(6); }}
              className={`px-3.5 py-1.5 rounded-xl font-mono text-xs font-bold transition-all cursor-pointer ${
                selectedSensorFilter === 'sentinel1'
                  ? 'bg-gradient-to-r from-cyan-400 to-blue-500 text-slate-950 shadow-[0_0_15px_rgba(0,229,255,0.4)]'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              📡 Sentinel-1 (Radar SAR)
            </button>
            <button
              type="button"
              onClick={() => { setSelectedSensorFilter('ALL'); setSelectedDateFilter('ALL'); setVisibleCount(6); }}
              className={`px-3 py-1.5 rounded-xl font-mono text-xs font-bold transition-all cursor-pointer ${
                selectedSensorFilter === 'ALL'
                  ? 'bg-slate-700 text-white'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              All
            </button>
          </div>

          <div className="flex items-center gap-2 text-xs text-slate-300 bg-gradient-to-b from-[#081b38]/90 via-[#06142e]/95 to-[#030a18]/95 border border-cyan-500/25 px-4 py-2 rounded-2xl backdrop-blur-md shadow-sm">
            <Layers className="w-4 h-4 text-cyan-400" />
            <span>
              Showing <strong className="text-white">{Math.min(visibleCount, filteredTiles.length)}</strong> of <strong className="text-cyan-300">{filteredTiles.length}</strong> {selectedDateFilter !== 'ALL' ? 'Filtered' : ''} Tiles
            </span>
          </div>
        </div>
      </div>

      {/* Available Acquisition Dates Filter Bar */}
      {availableDates.length > 0 && (
        <div className="mb-8 p-4 bg-gradient-to-b from-[#081b38]/90 via-[#06142e]/95 to-[#030a18]/95 border-2 border-cyan-400/40 shadow-[0_0_25px_rgba(0,229,255,0.15)] rounded-2xl flex flex-wrap items-center justify-between gap-3 backdrop-blur-xl">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-cyan-950 border border-cyan-400/40 text-cyan-400">
              <Calendar className="w-4 h-4" />
            </div>
            <div>
              <span className="text-xs font-black uppercase tracking-wider text-cyan-300 block">
                Filter by Acquisition Date
              </span>
              <span className="text-[10px] text-slate-400">
                {availableDates.length} distinct acquisition timestamps available in dataset
              </span>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => { setSelectedDateFilter('ALL'); setVisibleCount(6); }}
              className={`px-3.5 py-1.5 rounded-xl font-mono text-xs font-bold transition-all cursor-pointer ${
                selectedDateFilter === 'ALL'
                  ? 'bg-gradient-to-r from-cyan-400 to-blue-500 text-slate-950 shadow-[0_0_15px_rgba(0,229,255,0.4)]'
                  : 'bg-[#061022] text-slate-300 hover:text-cyan-300 border border-cyan-500/30 hover:border-cyan-400'
              }`}
            >
              ALL DATES ({candidateSubTiles.length})
            </button>

            {availableDates.map(dateStr => {
              const count = candidateSubTiles.filter(t => {
                const tileDate = String(t.date || t.dateIso || '');
                const raw = String(t.image_path || t.filepath || t.raw_path || t.image || t.file || t.id || '');
                return tileDate.includes(dateStr) || raw.includes(dateStr);
              }).length;

              const isSelected = selectedDateFilter === dateStr;

              let epochLabel = "";
              if (dateStr === "2026-12-10" || dateStr === "2026-06-17") epochLabel = "ACTIVE";
              else if (dateStr === "2026-09-10") epochLabel = "MONSOON";
              else if (dateStr === "2026-06-27") epochLabel = "SUMMER";
              else if (dateStr === "2026-01-18") epochLabel = "WINTER";
              else if (dateStr === "2025-06-07" || dateStr === "2026-03-13") epochLabel = "BASELINE";

              return (
                <button
                  key={dateStr}
                  type="button"
                  onClick={() => { setSelectedDateFilter(dateStr); setVisibleCount(6); }}
                  className={`px-3 py-1.5 rounded-xl font-mono text-xs font-bold transition-all cursor-pointer flex items-center gap-2 ${
                    isSelected
                      ? 'bg-gradient-to-r from-cyan-400 to-blue-500 text-slate-950 shadow-[0_0_15px_rgba(0,229,255,0.4)]'
                      : 'bg-[#061022] text-slate-300 hover:text-cyan-300 border border-cyan-500/30 hover:border-cyan-400'
                  }`}
                >
                  <Clock className="w-3 h-3" />
                  <span>{dateStr}</span>
                  {epochLabel && (
                    <span className={`text-[9px] px-1 py-0.2 rounded font-sans font-bold uppercase ${
                      isSelected ? 'bg-slate-950/30 text-slate-950' : 'bg-cyan-500/10 text-cyan-400'
                    }`}>
                      {epochLabel}
                    </span>
                  )}
                  <span className={`text-[10px] px-1.5 py-0.5 rounded-md font-sans font-bold ${
                    isSelected ? 'bg-slate-950 text-cyan-300' : 'bg-slate-800 text-slate-400'
                  }`}>
                    {count}
                  </span>
                </button>
              );
            })}

            {selectedDateFilter !== 'ALL' && (
              <button
                type="button"
                onClick={() => { setSelectedDateFilter('ALL'); setVisibleCount(6); }}
                className="px-3 py-1.5 text-xs text-rose-400 hover:text-rose-300 bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/40 rounded-xl transition-all cursor-pointer flex items-center gap-1 font-bold"
                title="Reset Date Filter"
              >
                <X className="w-3.5 h-3.5" />
                <span>Reset</span>
              </button>
            )}
          </div>
        </div>
      )}

      {/* Candidate Tiles Bento Cards Grid / Empty State */}
      {tiles.length === 0 ? (
        <div className="bg-gradient-to-b from-[#081b38]/90 via-[#06142e]/95 to-[#030a18]/95 border-2 border-cyan-400/50 shadow-[0_0_30px_rgba(0,229,255,0.2)] p-12 rounded-3xl text-center backdrop-blur-xl my-4">
          <div className="w-16 h-16 rounded-2xl bg-cyan-500/15 border border-cyan-400/30 flex items-center justify-center mx-auto mb-4 text-cyan-400 shadow-[0_0_20px_rgba(0,229,255,0.2)]">
            <Layers className="w-8 h-8" />
          </div>
          <h3 className="text-lg font-bold text-white mb-2">No Candidate Tiles Found</h3>
          <p className="text-sm text-slate-300 max-w-md mx-auto mb-6 leading-relaxed">
            Execute a natural language semantic query or upload satellite tiles to retrieve and rank candidate tiles.
          </p>
          <button
            type="button"
            onClick={() => {
              const el = document.getElementById('semantic-search');
              if (el) el.scrollIntoView({ behavior: 'smooth' });
            }}
            className="px-6 py-3 bg-gradient-to-r from-cyan-400 via-sky-400 to-blue-500 hover:from-cyan-300 hover:to-blue-400 text-slate-950 text-xs font-black rounded-xl shadow-[0_0_25px_rgba(0,229,255,0.4)] transition-all cursor-pointer"
          >
            Go to Semantic Search
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {displayedTiles.map((tile, idx) => {
            const isSelected = tile.id === selectedTileId;
            const hasImageError = imageErrorMap[tile.id];
            const tileImageSrc = getTileImageSrc(tile);
            const formattedCoords = tile.coordinates?.formatted || (tile.lat && tile.lng ? `${tile.lat}° N, ${tile.lng}° E` : 'GeoTIFF Extent');
            const scorePercent = tile.similarity || (tile.scoreRaw ? Math.round(tile.scoreRaw * 100) : 85);
            const acquisitionDate = getTileDate(tile);

            return (
              <div
                key={tile.id || idx}
                className={`relative bg-gradient-to-b from-[#081b38]/90 via-[#06142e]/95 to-[#030a18]/95 border-2 border-cyan-400/50 shadow-[0_0_30px_rgba(0,229,255,0.2)] p-4 rounded-2xl flex flex-col justify-between backdrop-blur-xl transition-all duration-300 cursor-pointer group hover:-translate-y-1 ${
                  isSelected
                    ? 'border-2 border-cyan-400 shadow-xl shadow-cyan-500/20 bg-gradient-to-b from-[#081b38]/95 via-[#06142e]/95 to-[#030a18]/95 border-2 border-cyan-400/50 shadow-[0_0_35px_rgba(0,229,255,0.25)]'
                    : 'border border-cyan-500/25 hover:border-cyan-500/40 hover:bg-gradient-to-b from-[#081b38]/90 via-[#06142e]/95 to-[#030a18]/95 border-2 border-cyan-400/50 shadow-[0_0_30px_rgba(0,229,255,0.2)]'
                }`}
                onClick={(e) => openTileModal(tile, e)}
              >
              <div>
                {/* Card Top Header: Tile ID & Badges */}
                <div className="flex items-center justify-between gap-2 pb-3 border-b border-cyan-500/25 mb-3">
                  <div className="flex items-center gap-2 min-w-0">
                    <span className="w-2 h-2 rounded-full bg-cyan-400"></span>
                    <span className="text-white font-semibold text-sm truncate font-mono" title={tile.tileName || tile.id}>
                      {tile.tileName || tile.id}
                    </span>
                  </div>

                  <div className="flex items-center gap-1.5 shrink-0">
                    <span className="px-2.5 py-0.5 bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 text-[10px] font-semibold rounded-full">
                      {tile.status || "Verified"}
                    </span>
                    <span className="px-2.5 py-0.5 bg-cyan-500/15 text-cyan-300 border border-cyan-500/30 text-[11px] font-bold rounded-full">
                      {scorePercent}% Match
                    </span>
                  </div>
                </div>

                {/* Satellite Tile Image Viewport */}
                <div 
                  className="relative w-full h-48 bg-black border border-cyan-500/25 mb-3.5 overflow-hidden rounded-xl flex items-center justify-center group"
                  title="Click to maximize tile preview"
                >
                  {!hasImageError ? (
                    <img
                      src={tileImageSrc}
                      alt={`Satellite Tile ${tile.id}`}
                      className="w-full h-full object-cover filter contrast-105 brightness-100 transition-transform duration-500 group-hover:scale-105"
                      onError={(e) => {
                        if (tile.image && e.currentTarget.src !== tile.image && !e.currentTarget.src.includes('default.jpg')) {
                          e.currentTarget.src = tile.image;
                        } else {
                          handleImageError(tile.id);
                        }
                      }}
                    />
                  ) : (
                    <div className="flex flex-col items-center justify-center text-slate-500 gap-2">
                      <Database className="w-8 h-8 text-cyan-400/40" />
                      <span className="text-xs">Tile Data Archived</span>
                    </div>
                  )}
                </div>

                {/* Metadata Details Card */}
                <div className="space-y-1.5 text-xs text-slate-300 mb-3 bg-black/50 p-3 rounded-xl border border-cyan-500/15 font-mono">
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400 flex items-center gap-1.5 font-sans">
                      <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
                      Similarity:
                    </span>
                    <span className="text-cyan-300 font-bold">{scorePercent}%</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400 flex items-center gap-1.5 font-sans">
                      <Calendar className="w-3.5 h-3.5 text-emerald-400" />
                      Acquired:
                    </span>
                    <span className="text-slate-200 font-medium">{acquisitionDate}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400 flex items-center gap-1.5 font-sans">
                      <Layers className="w-3.5 h-3.5 text-blue-400" />
                      Sensor:
                    </span>
                    <span className="text-slate-200 font-medium">{tile.sensor || "Sentinel-2 MSI"}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400 flex items-center gap-1.5 font-sans">
                      <MapPin className="w-3.5 h-3.5 text-amber-400" />
                      Centroid:
                    </span>
                    <span className="text-slate-200 font-medium truncate max-w-[150px]" title={formattedCoords}>
                      {formattedCoords}
                    </span>
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="pt-2 border-t border-cyan-500/25 flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    setMapTile({
                      ...tile,
                      date: acquisitionDate,
                      image: tileImageSrc
                    });
                  }}
                  className="py-2.5 px-3 bg-[#00e5ff] hover:bg-[#9cf0ff] text-[#070e1b] font-mono text-xs font-bold uppercase rounded-xl flex items-center justify-center gap-1.5 transition-all cursor-pointer shadow-md shadow-cyan-500/25"
                  title="See tile footprint and tactical layers on offline interactive map"
                >
                  <MapPin className="w-3.5 h-3.5" />
                  <span>[ SEE ON MAP ]</span>
                </button>
                <button
                  type="button"
                  onClick={(e) => openTileModal(tile, e)}
                  className="py-2.5 px-3 text-xs font-semibold border border-cyan-500/25 hover:border-cyan-400/40 bg-slate-800/60 hover:bg-slate-800 text-slate-300 hover:text-white rounded-xl transition-all flex items-center justify-center gap-1.5 cursor-pointer"
                  title="Maximize tile in modal"
                >
                  <Maximize2 className="w-3.5 h-3.5" />
                  <span className="hidden sm:inline">Inspect</span>
                </button>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleTemporalClick(tile.id);
                  }}
                  className={`flex-1 py-2.5 px-3 text-xs font-semibold rounded-xl transition-all flex items-center justify-center gap-1.5 cursor-pointer ${
                    isSelected
                      ? 'bg-cyan-400 text-slate-950 shadow-lg shadow-cyan-500/25 font-bold'
                      : 'bg-cyan-500/15 hover:bg-cyan-500 text-cyan-300 hover:text-slate-950 border border-cyan-500/30'
                  }`}
                  title="Open Temporal Analysis and Change Detection for this tile"
                >
                  <Clock className="w-3.5 h-3.5" />
                  <span>Temporal Analysis</span>
                </button>
              </div>
            </div>
          );
        })}
      </div>
      )}

      {/* Show More / Show Less Pagination Controls */}
      {tiles.length > 6 && (
        <div className="mt-8 flex flex-wrap items-center justify-center gap-3 pt-6 border-t border-cyan-500/25">
          {visibleCount < tiles.length ? (
            <>
              <button
                type="button"
                onClick={() => setVisibleCount(prev => Math.min(prev + 6, tiles.length))}
                className="px-6 py-2.5 bg-slate-800/80 hover:bg-cyan-500 text-slate-200 hover:text-slate-950 text-xs font-semibold rounded-xl border border-cyan-500/25 hover:border-cyan-400 shadow-md transition-all flex items-center gap-2 cursor-pointer"
              >
                <ChevronDown className="w-4 h-4" />
                <span>Show More Tiles ({Math.min(6, tiles.length - visibleCount)} remaining)</span>
              </button>
              <button
                type="button"
                onClick={() => setVisibleCount(tiles.length)}
                className="px-4 py-2.5 bg-gradient-to-b from-[#081b38]/90 via-[#06142e]/95 to-[#030a18]/95 border-2 border-cyan-400/50 shadow-[0_0_30px_rgba(0,229,255,0.2)] hover:bg-slate-800 text-slate-400 hover:text-white text-xs font-medium border border-cyan-500/25 rounded-xl transition-all cursor-pointer"
              >
                Show All ({tiles.length})
              </button>
            </>
          ) : (
            <button
              type="button"
              onClick={() => {
                setVisibleCount(6);
                const el = document.getElementById('candidate-tiles');
                if (el) el.scrollIntoView({ behavior: 'smooth' });
              }}
              className="px-6 py-2.5 bg-slate-800/80 hover:bg-slate-800 text-slate-300 hover:text-white text-xs font-medium border border-cyan-500/25 rounded-xl transition-all flex items-center gap-2 cursor-pointer"
            >
              <ChevronUp className="w-4 h-4" />
              <span>Collapse to 6 Tiles</span>
            </button>
          )}
        </div>
      )}

      {/* MAXIMIZED TILE POPUP MODAL (Glassmorphic + Soft Edges) */}
      {maximizedTile && (
        <div 
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-md p-4 sm:p-6 animate-fade-in"
          onClick={() => {
            setMaximizedTile(null);
            setModalZoom(1);
          }}
        >
          <div 
            className="relative w-full max-w-5xl bg-slate-900/95 border border-cyan-500/40 rounded-3xl shadow-2xl shadow-cyan-500/10 flex flex-col max-h-[90vh] overflow-hidden backdrop-blur-2xl animate-scale-in"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="flex items-center justify-between px-6 py-4 bg-[#030814]/90 border-b border-cyan-500/25">
              <div className="flex items-center gap-3">
                <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-pulse"></span>
                <span className="text-base font-bold text-white tracking-wide font-mono">
                  Tile Inspection: {maximizedTile.tileName || maximizedTile.id}
                </span>
                <span className="px-3 py-1 bg-cyan-500/15 text-cyan-300 border border-cyan-500/30 text-xs font-semibold rounded-full">
                  {maximizedTile.similarity || 85}% Match
                </span>
              </div>
              
              <div className="flex items-center gap-3">
                {/* Zoom Controls */}
                <div className="flex items-center gap-1 bg-slate-800/80 border border-cyan-500/25 rounded-xl p-1 text-xs">
                  <button
                    onClick={() => setModalZoom(z => Math.max(1, z - 0.25))}
                    className="p-1.5 hover:bg-slate-700 text-slate-300 hover:text-white rounded-lg transition-colors"
                    title="Zoom Out"
                  >
                    <ZoomOut className="w-4 h-4" />
                  </button>
                  <span className="px-2 text-slate-200 font-bold font-mono">{Math.round(modalZoom * 100)}%</span>
                  <button
                    onClick={() => setModalZoom(z => Math.min(3, z + 0.25))}
                    className="p-1.5 hover:bg-slate-700 text-slate-300 hover:text-white rounded-lg transition-colors"
                    title="Zoom In"
                  >
                    <ZoomIn className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => setModalZoom(1)}
                    className="p-1.5 hover:bg-slate-700 text-slate-300 hover:text-white rounded-lg transition-colors"
                    title="Reset Zoom"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                  </button>
                </div>

                {/* Close Button */}
                <button
                  onClick={() => {
                    setMaximizedTile(null);
                    setModalZoom(1);
                  }}
                  className="p-2 bg-slate-800/80 hover:bg-rose-500/20 text-slate-300 hover:text-rose-400 border border-cyan-500/25 hover:border-rose-500/30 rounded-xl transition-colors cursor-pointer"
                  title="Close (ESC)"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Modal Body */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-0 flex-1 overflow-y-auto min-h-0">
              {/* Full Image Viewport */}
              <div className="lg:col-span-7 xl:col-span-8 relative bg-black overflow-hidden border-b lg:border-b-0 lg:border-r border-cyan-500/25 min-h-[380px] lg:min-h-[500px] flex items-center justify-center">
                <div 
                  className="w-full h-full flex items-center justify-center overflow-hidden transition-transform duration-200"
                  style={{ transform: `scale(${modalZoom})` }}
                >
                  <img
                    src={getTileImageSrc(maximizedTile)}
                    alt={`Satellite Tile ${maximizedTile.tileName || maximizedTile.id}`}
                    className="w-full h-full object-cover object-center filter contrast-105 brightness-100"
                  />
                </div>
              </div>

              {/* Telemetry & Metadata Side Panel */}
              <div className="lg:col-span-5 xl:col-span-4 p-6 flex flex-col justify-between bg-gradient-to-b from-[#081b38]/95 via-[#06142e]/95 to-[#030a18]/95 border-2 border-cyan-400/50 shadow-[0_0_35px_rgba(0,229,255,0.25)] space-y-4">
                <div className="space-y-4">
                  <div>
                    <h3 className="text-xs text-cyan-400 font-bold uppercase tracking-wider flex items-center gap-1.5 mb-3">
                      <Activity className="w-4 h-4" />
                      Geospatial Telemetry
                    </h3>
                  </div>

                  <div className="space-y-2 text-xs font-mono">
                    <div className="flex items-center justify-between p-2.5 bg-[#030814]/90 border border-cyan-500/15 rounded-xl">
                      <span className="text-slate-400 font-sans">Identifier:</span>
                      <span className="text-cyan-300 font-bold">{maximizedTile.tileName || maximizedTile.id}</span>
                    </div>
                    <div className="flex items-center justify-between p-2.5 bg-[#030814]/90 border border-cyan-500/15 rounded-xl">
                      <span className="text-slate-400 font-sans">Vector Score:</span>
                      <span className="text-cyan-300 font-bold">{maximizedTile.similarity || 85}%</span>
                    </div>
                    <div className="flex items-center justify-between p-2.5 bg-[#030814]/90 border border-cyan-500/15 rounded-xl">
                      <span className="text-slate-400 font-sans">Acquisition:</span>
                      <span className="text-white font-bold">{getTileDate(maximizedTile)}</span>
                    </div>
                    <div className="flex items-center justify-between p-2.5 bg-[#030814]/90 border border-cyan-500/15 rounded-xl">
                      <span className="text-slate-400 font-sans">Sensor:</span>
                      <span className="text-slate-200 font-semibold">{maximizedTile.sensor || "Sentinel-2 MSI"}</span>
                    </div>
                    <div className="flex items-center justify-between p-2.5 bg-[#030814]/90 border border-cyan-500/15 rounded-xl">
                      <span className="text-slate-400 font-sans">Latitude:</span>
                      <span className="text-slate-200 font-semibold">{maximizedTile.coordinates?.lat || maximizedTile.lat || "N/A"}</span>
                    </div>
                    <div className="flex items-center justify-between p-2.5 bg-[#030814]/90 border border-cyan-500/15 rounded-xl">
                      <span className="text-slate-400 font-sans">Longitude:</span>
                      <span className="text-slate-200 font-semibold">{maximizedTile.coordinates?.lng || maximizedTile.lng || "N/A"}</span>
                    </div>
                    <div className="flex items-center justify-between p-2.5 bg-[#030814]/90 border border-cyan-500/15 rounded-xl">
                      <span className="text-slate-400 font-sans">Spatial Res:</span>
                      <span className="text-emerald-400 font-bold">{maximizedTile.resolution || "10 m"}</span>
                    </div>
                    <div className="flex items-center justify-between p-2.5 bg-[#030814]/90 border border-cyan-500/15 rounded-xl">
                      <span className="text-slate-400 font-sans">CRS:</span>
                      <span className="text-slate-300">{maximizedTile.crs || "EPSG:32643"}</span>
                    </div>
                  </div>
                </div>

                {/* Modal Action Controls */}
                <div className="pt-4 border-t border-cyan-500/25 space-y-2">
                  <button
                    type="button"
                    onClick={() => setMapTile(maximizedTile)}
                    className="w-full py-3 bg-[#00e5ff] hover:bg-[#9cf0ff] text-[#070e1b] text-xs font-bold rounded-xl flex items-center justify-center gap-2 shadow-lg shadow-cyan-500/25 transition-all cursor-pointer font-mono uppercase"
                  >
                    <MapPin className="w-4 h-4" />
                    <span>[ SEE ON TACTICAL MAP ]</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => handleTemporalClick(maximizedTile.id)}
                    className="w-full py-2.5 bg-gradient-to-r from-cyan-400 to-cyan-500 hover:from-cyan-300 hover:to-cyan-400 text-slate-950 text-xs font-bold rounded-xl flex items-center justify-center gap-2 shadow-lg shadow-cyan-500/25 transition-all cursor-pointer"
                  >
                    <Clock className="w-4 h-4" />
                    <span>Open in Temporal Analysis</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setMaximizedTile(null);
                      setModalZoom(1);
                    }}
                    className="w-full py-2 bg-slate-800/80 hover:bg-slate-800 text-slate-300 hover:text-white text-xs font-medium rounded-xl border border-cyan-500/25 transition-colors cursor-pointer"
                  >
                    Close Preview
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Offline Tactical Map Modal */}
      <TacticalMapModal
        isOpen={!!mapTile}
        onClose={() => setMapTile(null)}
        activeTile={mapTile}
      />
    </section>
  );
}
