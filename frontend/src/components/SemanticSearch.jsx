import React, { useState, useEffect } from 'react';
import { getSearchFilters } from '../services/api';
import { Search, Sparkles, Cpu, CornerDownLeft, X, Layers } from 'lucide-react';

const SUGGESTIONS = [
  "Large camps and tanks near rivers",
  "Urban expansion and construction sites",
  "Aircraft on runway aprons",
  "Dense industrial facility zones",
  "Deforestation and clearings"
];

export default function SemanticSearch({ onSearch, isSearching }) {
  const [query, setQuery] = useState("");
  const [availableFilters, setAvailableFilters] = useState({ aoi: [], satellites: [], years: [] });
  const [selectedFilters, setSelectedFilters] = useState({ aoi: "", satellite: "", year: "" });

  useEffect(() => {
    getSearchFilters().then(data => setAvailableFilters(data));
  }, []);

  const executeSearch = (targetQuery) => {
    if (!targetQuery || !targetQuery.trim()) return;
    const aoiObj = availableFilters.aoi.find(a => a.id === selectedFilters.aoi);
    onSearch(targetQuery, {
      ...selectedFilters,
      aoi: aoiObj || null
    });
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    executeSearch(query);
  };

  const handleSuggestionClick = (item) => {
    setQuery(item);
    executeSearch(item);
  };

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

        <div className="flex items-center gap-2.5 px-3.5 py-2 bg-gradient-to-b from-[#081b38]/90 via-[#06142e]/95 to-[#030a18]/95 border-2 border-cyan-400/50 shadow-[0_0_30px_rgba(0,229,255,0.2)] border border-cyan-500/25 rounded-2xl backdrop-blur-md self-start md:self-center shadow-sm">
          <Cpu className="w-4 h-4 text-cyan-400" />
          <span className="text-xs text-slate-300 font-medium">RemoteCLIP ViT-B/32 &bull; Qdrant</span>
        </div>
      </div>

      
      {/* Dynamic Filters */}
      <div className="flex flex-wrap items-center gap-4 mb-4">
        <select 
          value={selectedFilters.aoi} 
          onChange={e => setSelectedFilters({...selectedFilters, aoi: e.target.value})}
          className="px-3 py-2 bg-[#06142e]/95 border border-cyan-500/30 text-slate-300 text-sm rounded-lg focus:outline-none focus:border-cyan-400"
        >
          <option value="">All Regions</option>
          {availableFilters.aoi.map(a => (
            <option key={a.id} value={a.id}>{a.label}</option>
          ))}
        </select>
        
        <select 
          value={selectedFilters.satellite} 
          onChange={e => setSelectedFilters({...selectedFilters, satellite: e.target.value})}
          className="px-3 py-2 bg-[#06142e]/95 border border-cyan-500/30 text-slate-300 text-sm rounded-lg focus:outline-none focus:border-cyan-400"
        >
          <option value="">All Satellites</option>
          {availableFilters.satellites.map(s => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>

        <select 
          value={selectedFilters.year} 
          onChange={e => setSelectedFilters({...selectedFilters, year: e.target.value})}
          className="px-3 py-2 bg-[#06142e]/95 border border-cyan-500/30 text-slate-300 text-sm rounded-lg focus:outline-none focus:border-cyan-400"
        >
          <option value="">All Years</option>
          {availableFilters.years.map(y => (
            <option key={y} value={y}>{y}</option>
          ))}
        </select>
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
              placeholder="Search reconnaissance imagery (e.g., 'Find camps and tanks near rivers')..."
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
          Suggested:
        </span>
        {SUGGESTIONS.map((sugg, idx) => (
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
