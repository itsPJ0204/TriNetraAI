import React from 'react';
import { 
  X, 
  Satellite, 
  Search, 
  Layers, 
  Image as ImageIcon, 
  Clock, 
  Database, 
  UploadCloud, 
  ShieldCheck, 
  ChevronRight,
  Sparkles,
  Bot
} from 'lucide-react';

export default function NavigationDrawer({ isOpen, onClose, onNavigate, activeSection, onOpenAssistant }) {
  const navItems = [
    { id: 'ai-assistant', label: 'AI Assistant', icon: Bot, isAI: true },
    { id: 'hero', label: 'Mission Overview', icon: Satellite },
    { id: 'semantic-search', label: 'Vector Search', icon: Search },
    { id: 'candidate-tiles', label: 'Candidate Tiles', icon: Layers },
    { id: 'image-search', label: 'Visual Search', icon: ImageIcon },
    { id: 'temporal-analysis', label: 'Temporal Analysis', icon: Clock },
    { id: 'data-ingestion', label: 'Ingestion & Archive', icon: Database },
  ];

  const handleItemClick = (item) => {
    if (item.id === 'ai-assistant') {
      if (onOpenAssistant) onOpenAssistant();
      if (onClose) onClose();
      return;
    }
    if (onNavigate) onNavigate(item.id);
    if (onClose) onClose();
  };

  return (
    <>
      {/* Backdrop Overlay with smooth blur */}
      <div 
        className={`fixed inset-0 z-50 bg-black/85 backdrop-blur-md transition-opacity duration-300 ${
          isOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'
        }`}
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Sliding Left Navigation Panel */}
      <aside 
        className={`fixed top-0 left-0 bottom-0 z-50 w-80 sm:w-96 bg-black/95 backdrop-blur-3xl border-r-2 border-cyan-400/50 shadow-[0_0_60px_rgba(0,229,255,0.3)] flex flex-col justify-between transform transition-transform duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Top Section: Header & Brand */}
        <div className="p-6 border-b-2 border-cyan-400/30 bg-gradient-to-b from-[#0e2a56]/90 to-black">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-pulse shadow-[0_0_10px_rgba(0,229,255,0.9)]"></span>
              <span className="text-xs font-extrabold uppercase tracking-wider text-cyan-300">
                Satellite Intelligence
              </span>
            </div>

            {/* Close Button */}
            <button 
              onClick={onClose}
              className="p-2 text-slate-400 hover:text-white bg-[#061022] hover:bg-cyan-500/20 border border-cyan-400/40 hover:border-cyan-300 rounded-xl transition-all duration-150 cursor-pointer"
              aria-label="Close Navigation"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          <div>
            <h2 className="text-2xl font-black text-white tracking-tight flex items-center gap-2">
              <span className="bg-gradient-to-r from-white via-cyan-200 to-cyan-400 bg-clip-text text-transparent drop-shadow-[0_0_15px_rgba(0,229,255,0.5)]">
                TriNetra AI
              </span>
              <span className="text-xs px-2.5 py-0.5 bg-cyan-400/20 text-cyan-300 border border-cyan-400/50 rounded-full font-bold">
                त्रिनेत्र
              </span>
            </h2>
            <p className="text-xs text-slate-400 mt-1">
              Offline Geospatial Intelligence &amp; Change Analysis
            </p>
          </div>
        </div>

        {/* Middle Section: Solid Cyan Buttons matching Ingest Tile */}
        <div className="flex-1 overflow-y-auto p-5 space-y-3 custom-scrollbar">
          <div className="px-2 py-1 text-xs font-black uppercase tracking-wider text-cyan-300">
            Intelligence Modules
          </div>

          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = !item.isAI && activeSection === item.id;
            const isAIItem = item.isAI;
            return (
              <button
                key={item.id}
                onClick={() => handleItemClick(item)}
                className={`w-full flex items-center justify-between px-4 py-3.5 rounded-2xl transition-all duration-200 text-left cursor-pointer group ${
                  isAIItem
                    ? 'bg-gradient-to-r from-indigo-500/20 via-cyan-500/15 to-blue-600/10 hover:from-cyan-400 hover:via-sky-400 hover:to-blue-500 text-cyan-200 hover:text-slate-950 border-2 border-cyan-400/50 hover:border-cyan-300 shadow-[0_0_20px_rgba(0,229,255,0.2)] hover:shadow-[0_0_25px_rgba(0,229,255,0.4)]'
                  : isActive 
                    ? 'bg-gradient-to-r from-cyan-400 via-sky-400 to-blue-500 text-slate-950 font-black shadow-[0_0_30px_rgba(0,229,255,0.5)] scale-[1.02]' 
                    : 'bg-gradient-to-r from-cyan-500/20 via-sky-500/15 to-blue-600/10 hover:from-cyan-400 hover:via-sky-400 hover:to-blue-500 text-cyan-200 hover:text-slate-950 border-2 border-cyan-400/40 hover:border-cyan-300 shadow-[0_0_15px_rgba(0,229,255,0.15)] hover:shadow-[0_0_25px_rgba(0,229,255,0.4)]'
                }`}
              >
                <div className="flex items-center gap-3.5">
                  <div className={`p-2 rounded-xl transition-colors ${
                    isActive 
                      ? 'bg-slate-950 text-cyan-400 shadow-md' 
                      : 'bg-cyan-500/20 text-cyan-300 group-hover:bg-slate-950 group-hover:text-cyan-400 border border-cyan-400/30'
                  }`}>
                    <Icon className="w-4 h-4" />
                  </div>
                  <div className="flex flex-col">
                    <span className={`text-sm tracking-wide ${isActive ? 'font-black' : 'font-bold group-hover:font-black'}`}>
                      {item.label}
                    </span>
                    {isAIItem && (
                      <span className="text-[10px] text-cyan-400/70 group-hover:text-slate-950/70 font-medium">CPU · Offline VLM</span>
                    )}
                  </div>
                </div>

                <ChevronRight className={`w-4 h-4 transition-transform group-hover:translate-x-1 ${
                  isActive ? 'text-slate-950' : 'text-cyan-400 group-hover:text-slate-950'
                }`} />
              </button>
            );
          })}

          <div className="pt-3 pb-1 px-2 text-xs font-black uppercase tracking-wider text-cyan-300">
            Quick Ingest
          </div>

          {/* Direct Ingest Tile Button */}
          <button
            onClick={() => handleItemClick('data-ingestion')}
            className="w-full flex items-center justify-between px-4 py-3.5 bg-gradient-to-r from-cyan-400 via-sky-400 to-blue-500 hover:from-cyan-300 hover:to-blue-400 text-slate-950 font-black rounded-2xl transition-all duration-200 text-left cursor-pointer shadow-[0_0_30px_rgba(0,229,255,0.45)] hover:scale-[1.02]"
          >
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-xl bg-slate-950 text-cyan-400">
                <UploadCloud className="w-4 h-4" />
              </div>
              <span className="text-sm font-black">
                + Add Satellite Tile
              </span>
            </div>
            <ChevronRight className="w-4 h-4 text-slate-950" />
          </button>
        </div>

        {/* Bottom Section: Air-Gapped Security */}
        <div className="p-5 border-t-2 border-cyan-400/30 bg-black">
          <div className="flex items-center justify-between p-3.5 bg-[#041520] border-2 border-emerald-400/50 rounded-2xl shadow-[0_0_20px_rgba(16,185,129,0.2)]">
            <div className="flex items-center gap-2.5">
              <div className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse shadow-sm shadow-emerald-400"></div>
              <div>
                <div className="text-xs font-black text-emerald-400">
                  Secure Air-Gapped Node
                </div>
                <div className="text-[10px] text-slate-300">
                  Offline Workstation Active
                </div>
              </div>
            </div>
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
          </div>
        </div>
      </aside>
    </>
  );
}
