import React, { useState } from 'react';
import { Terminal, Search, CheckCircle2, Cpu } from 'lucide-react';
import { PIPELINE_STAGES, SAMPLE_QUERIES } from '../data/mockData';

export default function SemanticSearch({ onSearch, isSearching }) {
  const [query, setQuery] = useState("Find large camps and tanks near rivers from 2020 to 2023");
  const [activeStage, setActiveStage] = useState(8);

  const executeSearch = (targetQuery) => {
    if (!targetQuery || !targetQuery.trim()) return;
    
    // Animate stages
    setActiveStage(0);
    const interval = setInterval(() => {
      setActiveStage(prev => {
        if (prev >= 8) {
          clearInterval(interval);
          return 8;
        }
        return prev + 1;
      });
    }, 70);

    onSearch(targetQuery);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    executeSearch(query);
  };

  const handlePresetClick = (sq) => {
    setQuery(sq);
    executeSearch(sq);
  };

  return (
    <section className="w-full py-16 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto border-b border-[#1e293b]/40" id="semantic-search">
      {/* Section Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-8 pb-3 border-b border-[#1e293b]">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="w-2 h-2 bg-[#00e5ff]"></span>
            <span className="font-mono text-[10px] text-[#00e5ff] uppercase tracking-widest font-semibold">
              MODULE // 01
            </span>
          </div>
          <h2 className="text-[28px] sm:text-[34px] font-bold text-white tracking-tight">
            Natural Language Semantic Vector Search
          </h2>
          <p className="text-[14px] text-[#94a3b8] mt-1">
            Translate complex military reconnaissance queries into sub-second FAISS geospatial vector searches entirely offline.
          </p>
        </div>
        <div className="flex items-center gap-3 font-mono text-[11px] text-[#9cf0ff] bg-[#1a2942]/40 px-3 py-1.5 border border-[#1e293b] rounded-sm self-start md:self-center">
          <Cpu className="w-4 h-4 text-[#00e5ff]" />
          <span>EMBEDDING MODEL: CLIP-ViT-L/14 MIL-GEOINT</span>
        </div>
      </div>

      {/* Interactive Terminal Search Bar */}
      <form onSubmit={handleSubmit} className="hud-bracket-tl hud-bracket-br relative bg-[#0d1726]/90 border border-[#00e5ff]/40 p-3 sm:p-4 rounded-sm mb-4 backdrop-blur-xl shadow-[0_0_24px_rgba(0,229,255,0.08)]">
        <div className="flex flex-col md:flex-row items-stretch md:items-center gap-3">
          {/* Terminal Prompt Glyph */}
          <div className="flex items-center gap-2 text-[#00e5ff] font-mono text-[13px] px-2">
            <Terminal className="w-5 h-5" />
            <span className="font-bold">QUERY_MGRS&gt;</span>
          </div>

          {/* Input field */}
          <div className="flex-1 bg-[#070e1b]/90 border border-[#1e293b] px-4 py-2.5 rounded-sm flex items-center">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Enter surveillance query (e.g., 'Find camps near rivers...')"
              className="bg-transparent border-0 text-white font-mono text-[13px] sm:text-[14px] w-full focus:ring-0 focus:outline-none p-0 tracking-wide"
            />
            <span className="terminal-cursor"></span>
          </div>

          {/* Execute Vector Search Button */}
          <button
            type="submit"
            disabled={isSearching}
            className="px-6 py-2.5 bg-[#00e5ff] hover:bg-[#9cf0ff] text-[#070e1b] font-mono text-[12px] font-bold tracking-widest uppercase transition-all flex items-center justify-center gap-2 shadow-[0_0_12px_rgba(0,229,255,0.3)] cursor-pointer disabled:opacity-50"
          >
            <Search className="w-4 h-4" />
            {isSearching ? "[ SCANNING... ]" : "[ VECTOR EXECUTE ]"}
          </button>
        </div>
      </form>

      {/* Preset Query Badges */}
      <div className="flex flex-wrap items-center gap-2 mb-8">
        <span className="font-mono text-[10px] text-[#64748b] uppercase">PRESETS:</span>
        {SAMPLE_QUERIES.map((sq, idx) => (
          <button
            key={idx}
            type="button"
            onClick={() => handlePresetClick(sq)}
            className="px-2.5 py-1 bg-[#131f33]/60 hover:bg-[#1a2942] border border-[#1e293b] text-[#94a3b8] hover:text-[#00e5ff] font-mono text-[10px] rounded-sm transition-colors text-left cursor-pointer"
          >
            "{sq}"
          </button>
        ))}
      </div>

      {/* Visual Query Understanding Decomposition Breakdown */}
      <div className="bg-[#070e1b] border border-[#1e293b] p-4 rounded-sm mb-12">
        <div className="flex items-center justify-between mb-3">
          <span className="font-mono text-[10px] text-[#64748b] uppercase tracking-wider font-semibold">
            AI QUERY INTENT EXTRACTION & TOKENIZED CONSTRAINTS
          </span>
          <span className="font-mono text-[10px] text-[#10b981]">4 SLOTS RESOLVED</span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {/* Chip 1 */}
          <div className="p-3 bg-[#0d1726] border-l-2 border-[#00e5ff] border-t border-r border-b border-[#1e293b]">
            <div className="font-mono text-[10px] text-[#64748b] uppercase">Target Class</div>
            <div className="font-mono text-[12px] text-[#9cf0ff] mt-1 font-bold">[Camp, Armor / Tank]</div>
          </div>
          {/* Chip 2 */}
          <div className="p-3 bg-[#0d1726] border-l-2 border-[#00e5ff] border-t border-r border-b border-[#1e293b]">
            <div className="font-mono text-[10px] text-[#64748b] uppercase">Formation Scale</div>
            <div className="font-mono text-[12px] text-[#9cf0ff] mt-1 font-bold">[Large Formations &gt; 12 Bldgs]</div>
          </div>
          {/* Chip 3 */}
          <div className="p-3 bg-[#0d1726] border-l-2 border-[#10b981] border-t border-r border-b border-[#1e293b]">
            <div className="font-mono text-[10px] text-[#64748b] uppercase">Temporal Epoch</div>
            <div className="font-mono text-[12px] text-[#10b981] mt-1 font-bold">[2020-01-01 to 2023-12-31]</div>
          </div>
          {/* Chip 4 */}
          <div className="p-3 bg-[#0d1726] border-l-2 border-[#f59e0b] border-t border-r border-b border-[#1e293b]">
            <div className="font-mono text-[10px] text-[#64748b] uppercase">GIS Riparian Buffer</div>
            <div className="font-mono text-[12px] text-[#f59e0b] mt-1 font-bold">[River Channel &lt; 500m]</div>
          </div>
        </div>
      </div>

      {/* 8-Stage Processing Pipeline Horizontal Stepper Grid */}
      <div>
        <div className="flex items-center gap-2 mb-4">
          <span className="w-1.5 h-1.5 rounded-full bg-[#00e5ff]"></span>
          <h3 className="text-[18px] font-semibold text-white font-mono">
            8-Stage Autonomous Pipeline Architecture
          </h3>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {PIPELINE_STAGES.map((stage, idx) => {
            const isDone = idx < activeStage;
            const isCurrent = idx === activeStage - 1;
            return (
              <div
                key={stage.id}
                className={`p-3 rounded-sm border transition-all duration-200 ${
                  isCurrent
                    ? "bg-[#1a2942] border-[#00e5ff] shadow-[0_0_12px_rgba(0,229,255,0.2)]"
                    : isDone
                    ? "bg-[#0d1726]/80 border-[#1e293b]"
                    : "bg-[#070e1b] border-[#1e293b]/50 opacity-60"
                }`}
              >
                <div className="flex items-center justify-between mb-1.5">
                  <span className={`font-mono text-[10px] font-bold ${isDone ? "text-[#00e5ff]" : "text-[#64748b]"}`}>
                    {stage.code}
                  </span>
                  {isDone ? (
                    <CheckCircle2 className="w-3.5 h-3.5 text-[#10b981]" />
                  ) : (
                    <span className="w-2 h-2 rounded-full border border-[#64748b]"></span>
                  )}
                </div>
                <h4 className="font-mono text-[12px] text-white font-bold">{stage.name}</h4>
                <p className="text-[11px] text-[#94a3b8] mt-1">{stage.desc}</p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
