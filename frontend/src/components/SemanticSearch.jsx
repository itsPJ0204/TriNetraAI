import React, { useState } from 'react';
import { Search, Sparkles, Cpu, CornerDownLeft, X, Layers } from 'lucide-react';

const S2_SUGGESTIONS = [
  "Urban expansion and construction sites",
  "Large camps and tanks near rivers",
  "Aircraft on runway aprons",
  "Dense industrial facility zones",
  "Deforestation and clearings"
];

const S1_SUGGESTIONS = [
  "Structural Radar Backscatter Shift",
  "Water & Flood Inundation Extent",
  "High-Reflectance Metal Infrastructure",
  "Industrial Facilities & Grid Targets",
  "Coastal & Port Radar Signatures"
];

export default function SemanticSearch({ onSearch, isSearching }) {
  const [query, setQuery] = useState("");
  const [selectedSensor, setSelectedSensor] = useState("sentinel2");

  const executeSearch = (targetQuery, sensorToUse = selectedSensor) => {
    if (!targetQuery || !targetQuery.trim()) return;
    onSearch(targetQuery, sensorToUse);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    executeSearch(query, selectedSensor);
  };

  const handleSuggestionClick = (item) => {
    setQuery(item);
    executeSearch(item, selectedSensor);
  };

  const suggestions = selectedSensor === 'sentinel1' ? S1_SUGGESTIONS : S2_SUGGESTIONS;

  return (
    <section className="w-full py-16 px-4 sm:px-6 lg:px-8 max-w-6xl mx-auto border-b border-cyan-500/25" id="semantic-search">
      {/* Section Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-8">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="w-2 h-2 rounded-full bg-cyan-400"></span>
            <span className="text-xs text-cyan-400 font-semibold tracking-wider uppercase">
              Semantic Query Engine
            </span>
          </div>
          <h2 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
            Natural Language Vector Search
          </h2>
          <p className="text-sm text-slate-400 mt-1 max-w-2xl">
            Query across multi-band satellite archives using natural language prompts matched against 512-D RemoteCLIP embeddings in real-time.
          </p>
        </div>

        {/* Sensor Toggle */}
        <div className="flex items-center bg-black/80 p-1 rounded-2xl border border-cyan-400/40 shadow-inner">
          <button
            type="button"
            onClick={() => setSelectedSensor('sentinel2')}
            className={`px-4 py-1.5 rounded-xl font-mono text-xs font-bold transition-all cursor-pointer ${
              selectedSensor === 'sentinel2'
                ? 'bg-gradient-to-r from-emerald-400 to-teal-500 text-slate-950 shadow-[0_0_15px_rgba(16,185,129,0.4)]'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            🛰️ Sentinel-2 (Optical)
          </button>
          <button
            type="button"
            onClick={() => setSelectedSensor('sentinel1')}
            className={`px-4 py-1.5 rounded-xl font-mono text-xs font-bold transition-all cursor-pointer ${
              selectedSensor === 'sentinel1'
                ? 'bg-gradient-to-r from-cyan-400 to-blue-500 text-slate-950 shadow-[0_0_15px_rgba(0,229,255,0.4)]'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            📡 Sentinel-1 (Radar SAR)
          </button>
        </div>
      </div>

      {/* Redesigned Floating Glass Search Bar */}
      <form onSubmit={handleSubmit} className="relative mb-6">
        <div className="relative flex flex-col sm:flex-row items-center gap-2 p-2 sm:p-2.5 bg-gradient-to-b from-[#081b38]/90 via-[#06142e]/95 to-[#030a18]/95 border-2 border-cyan-400/50 shadow-[0_0_30px_rgba(0,229,255,0.2)] border border-cyan-500/30 focus-within:border-cyan-400/60 rounded-2xl sm:rounded-3xl backdrop-blur-2xl shadow-xl shadow-black/40 transition-all duration-200">
          
          {/* Search Icon */}
          <div className="hidden sm:flex items-center pl-3.5 pr-1 text-slate-400">
            <Search className="w-5 h-5 text-cyan-400" />
          </div>

          {/* Input field */}
          <div className="flex-1 w-full flex items-center px-2 py-1">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={selectedSensor === 'sentinel1' ? "Search Sentinel-1 radar features (e.g. 'industrial metal structures', 'water bodies')..." : "Search Sentinel-2 optical features (e.g., 'urban construction', 'river basin', 'airports')..."}
              className="w-full bg-transparent border-0 text-white placeholder-slate-400 text-sm sm:text-base font-normal focus:outline-none focus:ring-0 px-2 py-1.5"
            />
            {query && (
              <button
                type="button"
                onClick={() => setQuery("")}
                className="p-1 text-slate-400 hover:text-white rounded-full hover:bg-slate-800 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>

          {/* Execute Vector Search Button */}
          <button
            type="submit"
            disabled={isSearching}
            className="w-full sm:w-auto px-6 py-3 bg-gradient-to-r from-cyan-400 to-cyan-500 hover:from-cyan-300 hover:to-cyan-400 text-slate-950 text-sm font-bold rounded-xl sm:rounded-2xl transition-all duration-200 flex items-center justify-center gap-2 shadow-lg shadow-cyan-500/20 cursor-pointer disabled:opacity-50 hover:scale-[1.02] active:scale-[0.98]"
          >
            <Sparkles className="w-4 h-4" />
            <span>{isSearching ? "Searching..." : "Vector Search"}</span>
          </button>
        </div>
      </form>

      {/* Suggestion Chips */}
      <div className="flex flex-wrap items-center gap-2 pt-1">
        <span className="text-xs text-slate-400 font-medium mr-1 flex items-center gap-1">
          <Layers className="w-3.5 h-3.5 text-cyan-400" />
          Suggested ({selectedSensor === 'sentinel1' ? 'Radar' : 'Optical'}):
        </span>
        {suggestions.map((sugg, idx) => (
          <button
            key={idx}
            type="button"
            onClick={() => handleSuggestionClick(sugg)}
            className="px-3 py-1.5 bg-gradient-to-b from-[#081b38]/90 via-[#06142e]/95 to-[#030a18]/95 border-2 border-cyan-400/50 shadow-[0_0_30px_rgba(0,229,255,0.2)] hover:bg-slate-800 text-slate-300 hover:text-cyan-300 border border-cyan-500/25 hover:border-cyan-500/30 rounded-full text-xs transition-all duration-150 cursor-pointer"
          >
            {sugg}
          </button>
        ))}
      </div>
    </section>
  );
}
