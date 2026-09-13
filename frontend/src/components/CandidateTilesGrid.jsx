import React, { useState, useEffect } from 'react';
import { 
  Eye, Layers, Compass, CheckCircle2, Clock, Calendar, 
  Target, MapPin, Sparkles, Activity, Maximize2, X, 
  ZoomIn, ZoomOut, RotateCcw, ShieldCheck, Database,
  ChevronDown, ChevronUp, ArrowRight
} from 'lucide-react';

export default function CandidateTilesGrid({ tiles, selectedTileId, onSelectTile, activeQuery }) {
  const [imageErrorMap, setImageErrorMap] = useState({});
  const [maximizedTile, setMaximizedTile] = useState(null);
  const [modalZoom, setModalZoom] = useState(1);
  const [visibleCount, setVisibleCount] = useState(6);

  useEffect(() => {
    setVisibleCount(6);
  }, [activeQuery, tiles.length]);

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

  const displayedTiles = tiles.slice(0, visibleCount);

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
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-8">
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

        {/* Tiles Count Indicator */}
        <div className="flex items-center gap-2 text-xs text-slate-300 bg-gradient-to-b from-[#081b38]/90 via-[#06142e]/95 to-[#030a18]/95 border-2 border-cyan-400/50 shadow-[0_0_30px_rgba(0,229,255,0.2)] border border-cyan-500/25 px-4 py-2 rounded-2xl self-start md:self-center backdrop-blur-md shadow-sm">
          <Layers className="w-4 h-4 text-cyan-400" />
          <span>Showing <strong className="text-white">{Math.min(visibleCount, tiles.length)}</strong> of <strong className="text-cyan-300">{tiles.length}</strong> Tiles</span>
        </div>
      </div>

      {/* Candidate Tiles Bento Cards Grid / Empty State */}
      {tiles.length === 0 ? (
        <div className="bg-gradient-to-b from-[#081b38]/90 via-[#06142e]/95 to-[#030a18]/95 border-2 border-cyan-400/50 shadow-[0_0_30px_rgba(0,229,255,0.2)] p-12 rounded-3xl text-center backdrop-blur-xl my-4">
          <div className="w-16 h-16 rounded-2xl bg-cyan-500/15 border border-cyan-400/30 flex items-center justify-center mx-auto mb-4 text-cyan-400 shadow-[0_0_20px_rgba(0,229,255,0.2)]">
            <Layers className="w-8 h-8" />
          </div>
          <h3 className="text-lg font-bold text-white mb-2">No Candidate Tiles Found</h3>
          <p className="text-sm text-slate-300 max-w-md mx-auto mb-6 leading-relaxed">
            Nothing matches with the set filter. Please adjust your search query or clear the filters.
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
            const tileImageSrc = tile.image || "/satellite-tiles/default.jpg";
            const formattedCoords = tile.coordinates?.formatted || (tile.lat && tile.lng ? `${tile.lat}° N, ${tile.lng}° E` : 'GeoTIFF Extent');
            const scorePercent = tile.similarity || (tile.scoreRaw ? Math.round(tile.scoreRaw * 100) : 85);
            const acquisitionDate = tile.date || tile.dateIso || "Recent Acquisition";

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
                      onError={() => handleImageError(tile.id)}
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
              <div className="pt-2 border-t border-cyan-500/25 flex gap-2">
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
                    src={maximizedTile.image || "/satellite-tiles/default.jpg"}
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
                      <span className="text-white font-bold">{maximizedTile.date || maximizedTile.dateIso || "Recent Acquisition"}</span>
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
                    onClick={() => handleTemporalClick(maximizedTile.id)}
                    className="w-full py-3 bg-gradient-to-r from-cyan-400 to-cyan-500 hover:from-cyan-300 hover:to-cyan-400 text-slate-950 text-xs font-bold rounded-xl flex items-center justify-center gap-2 shadow-lg shadow-cyan-500/25 transition-all cursor-pointer"
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
    </section>
  );
}
