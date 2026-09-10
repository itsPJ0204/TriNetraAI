import React, { useState } from 'react';
import { Eye, Layers, Compass, CheckCircle2, Clock } from 'lucide-react';
import { THEATER_PRESETS } from '../data/mockData';

export default function CandidateTilesGrid({ tiles, selectedTileId, onSelectTile, activeQuery }) {
  const [activeTheater, setActiveTheater] = useState("Galwan Sector");

  const handleTheaterClick = (preset) => {
    setActiveTheater(preset.name);
    onSelectTile(preset.tileId);
  };

  const handleInspectClick = (tileId) => {
    onSelectTile(tileId);
    setTimeout(() => {
      const el = document.getElementById('image-viewer');
      if (el) el.scrollIntoView({ behavior: 'smooth' });
    }, 50);
  };

  const handleTemporalClick = (tileId) => {
    onSelectTile(tileId);
    setTimeout(() => {
      const el = document.getElementById('temporal-analysis');
      if (el) el.scrollIntoView({ behavior: 'smooth' });
    }, 50);
  };

  return (
    <section className="w-full py-16 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto border-b border-[#1e293b]/40 animate-in fade-in duration-300" id="candidate-tiles">
      {/* Active Search Query Result Banner */}
      {activeQuery && (
        <div className="mb-6 px-4 py-3 bg-[#0d1726]/90 border border-[#00e5ff]/50 rounded-sm font-mono text-[12px] flex flex-wrap items-center justify-between gap-3 shadow-[0_0_15px_rgba(0,229,255,0.1)]">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[#10b981] animate-pulse"></span>
            <span className="text-[#64748b]">ACTIVE QUERY:</span>
            <span className="text-[#9cf0ff] font-bold">"{activeQuery}"</span>
          </div>
          <div className="flex items-center gap-3 text-[11px]">
            <span className="text-[#00e5ff]">● {tiles.length} CANDIDATE TILES RESOLVED</span>
            <span className="text-[#64748b]">|</span>
            <span className="text-[#10b981]">FAISS HNSW: 42ms</span>
          </div>
        </div>
      )}

      {/* Controls Bar */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 mb-8 pb-4 border-b border-[#1e293b]">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="w-2 h-2 bg-[#00e5ff]"></span>
            <span className="font-mono text-[10px] text-[#00e5ff] uppercase tracking-widest font-semibold">
              MODULE // 02
            </span>
          </div>
          <h2 className="text-[28px] sm:text-[34px] font-bold text-white tracking-tight">
            Ranked Candidate Tiles // Geospatial Grid
          </h2>
        </div>

        {/* Theater Presets Filter */}
        <div className="flex items-center gap-2">
          <span className="font-mono text-[10px] text-[#64748b] uppercase">THEATER:</span>
          <div className="flex items-center gap-1.5 overflow-x-auto">
            {THEATER_PRESETS.map((p, idx) => (
              <button
                key={idx}
                onClick={() => handleTheaterClick(p)}
                className={`px-3 py-1.5 font-mono text-[11px] rounded-sm transition-colors cursor-pointer ${
                  activeTheater === p.name
                    ? 'bg-[#1a2942] border border-[#00e5ff] text-[#00e5ff] font-semibold'
                    : 'bg-[#070e1b] border border-[#1e293b] text-[#94a3b8] hover:text-white'
                }`}
              >
                {p.name}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Candidate Tiles Bento Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {tiles.map((tile) => {
          const isSelected = tile.id === selectedTileId;
          return (
            <div
              key={tile.id}
              className={`hud-bracket-tl hud-bracket-br relative bg-[#0d1726]/80 p-4 rounded-sm flex flex-col justify-between backdrop-blur-md transition-all duration-200 cursor-pointer ${
                isSelected
                  ? 'border-2 border-[#00e5ff] shadow-[0_0_20px_rgba(0,229,255,0.2)] bg-[#131f33]'
                  : 'border border-[#1e293b] hover:border-[#00e5ff]/60'
              }`}
              onClick={() => onSelectTile(tile.id)}
            >
              <div>
                <div className="flex items-center justify-between pb-3 border-b border-[#1e293b] mb-3">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-[#00e5ff] font-bold text-[12px]">
                      TILE ID: {tile.id}
                    </span>
                    <span className="px-1.5 py-0.5 bg-[#10b981]/20 text-[#10b981] border border-[#10b981]/40 font-mono text-[9px] uppercase font-bold">
                      {tile.status}
                    </span>
                  </div>
                  <span className="font-mono text-[12px] text-[#00e5ff] font-bold">
                    {tile.similarity}% SIMILARITY
                  </span>
                </div>

                {/* Synthetic HUD Satellite preview tile graphic */}
                <div className="relative w-full h-40 bg-[#070e1b] border border-[#1e293b] mb-4 overflow-hidden flex items-center justify-center">
                  <div className="absolute inset-0 hud-grid-bg opacity-40"></div>
                  {/* Crosshairs */}
                  <div className="absolute inset-x-0 top-1/2 h-px bg-[#00e5ff]/20"></div>
                  <div className="absolute inset-y-0 left-1/2 w-px bg-[#00e5ff]/20"></div>

                  {/* Synthetic bounding box */}
                  <div className="absolute w-24 h-20 border border-[#00e5ff] bg-[#00e5ff]/10 flex flex-col justify-between p-1">
                    <span className="text-[8px] font-mono text-[#00e5ff]">
                      {tile.detectedObjects[0]?.label || "TARGET"}
                    </span>
                    <span className="text-[8px] font-mono text-[#10b981] self-end">
                      {tile.detectedObjects[0]?.confidence || 90}%
                    </span>
                  </div>

                  <div className="absolute bottom-2 left-2 font-mono text-[10px] text-[#64748b]">
                    {tile.coordinates.formatted}
                  </div>
                  <div className="absolute top-2 right-2 px-1.5 py-0.5 bg-[#0c1320]/90 text-[#00e5ff] font-mono text-[9px] border border-[#00e5ff]/30">
                    {tile.sensor}
                  </div>
                </div>

                {/* Metadata details */}
                <div className="space-y-1.5 font-mono text-[12px] text-[#94a3b8] mb-4">
                  <div className="flex justify-between">
                    <span className="text-[#64748b]">ACQUISITION:</span>
                    <span className="text-white">{tile.date}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#64748b]">DETECTED:</span>
                    <span className="text-[#9cf0ff] font-bold">
                      {tile.detectedObjects.map(d => `${d.count} ${d.label.split('_')[0]}`).slice(0, 2).join(', ')}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#64748b]">WATER PROXIMITY:</span>
                    <span className="text-[#10b981] font-bold">
                      {tile.hydrology.distanceMeters}m ({tile.hydrology.isNearRiver ? 'COMPLIANT' : 'FAR'})
                    </span>
                  </div>
                </div>
              </div>

              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleInspectClick(tile.id);
                  }}
                  className={`flex-1 py-2 font-mono text-[10px] sm:text-[11px] font-bold tracking-wider uppercase border transition-colors flex items-center justify-center gap-1.5 cursor-pointer ${
                    isSelected
                      ? 'bg-[#00e5ff] text-[#070e1b] border-[#00e5ff]'
                      : 'bg-[#131f33] hover:bg-[#00e5ff] hover:text-[#070e1b] text-[#00e5ff] border-[#00e5ff]/40'
                  }`}
                  title="Inspect tile in YOLO Optical Target Inspector"
                >
                  <Eye className="w-3.5 h-3.5" />
                  <span>INSPECT</span>
                </button>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleTemporalClick(tile.id);
                  }}
                  className="flex-1 py-2 font-mono text-[10px] sm:text-[11px] font-bold tracking-wider uppercase bg-[#131f33] hover:bg-[#ef4444] hover:text-white text-[#ef4444] border border-[#ef4444]/50 transition-colors flex items-center justify-center gap-1.5 cursor-pointer shadow-[0_0_8px_rgba(239,68,68,0.2)]"
                  title="Open Temporal Analysis and Change Detection for this tile"
                >
                  <Clock className="w-3.5 h-3.5" />
                  <span>TEMPORAL</span>
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
