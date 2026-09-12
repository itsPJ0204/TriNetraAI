import React from 'react';
import { Menu, UploadCloud, ShieldCheck, Sparkles, Bot } from 'lucide-react';

export default function Navigation({ onNavigate, onOpenDrawer, onOpenAssistant }) {
  const handleNavClick = (e, targetId) => {
    if (onNavigate) {
      e.preventDefault();
      onNavigate(targetId);
    }
  };

  return (
    <header className="fixed top-0 left-0 w-full z-40 flex items-center justify-between px-4 sm:px-8 py-3.5 bg-black/80 backdrop-blur-2xl border-b border-cyan-500/20 shadow-[0_4px_30px_rgba(0,0,0,0.8)]">
      <div className="w-full max-w-7xl mx-auto flex items-center justify-between gap-4">
        {/* Left: Sliding Menu Trigger Button + Brand Title */}
        <div className="flex items-center gap-3 sm:gap-4">
          {/* Menu Drawer Toggle Button */}
          <button
            onClick={onOpenDrawer}
            className="flex items-center gap-2.5 px-3.5 py-2 bg-[#061022]/90 hover:bg-cyan-500/20 text-cyan-300 hover:text-white border border-cyan-500/30 hover:border-cyan-400 rounded-2xl transition-all duration-200 shadow-[0_0_15px_rgba(0,229,255,0.15)] cursor-pointer group"
            title="Open Intelligence Navigation Menu"
            aria-label="Open Navigation Menu"
          >
            <Menu className="w-5 h-5 text-cyan-400 group-hover:scale-110 transition-transform" />
            <span className="text-xs font-bold tracking-wide">Menu</span>
          </button>

          {/* Clean Brand Title with Glowing Gradient */}
          <div className="flex items-center gap-2">
            <span className="text-base sm:text-lg font-extrabold tracking-tight text-white flex items-center gap-2">
              <span className="bg-gradient-to-r from-white via-cyan-200 to-cyan-400 bg-clip-text text-transparent drop-shadow-[0_0_12px_rgba(0,229,255,0.4)]">
                TriNetra AI
              </span>
              <span className="text-[11px] px-2.5 py-0.5 bg-cyan-500/15 text-cyan-300 border border-cyan-500/30 rounded-full font-semibold shadow-[0_0_10px_rgba(0,229,255,0.2)]">
                त्रिनेत्र
              </span>
            </span>
          </div>
        </div>

        {/* Right Status & Quick Action (No center top tabs) */}
        <div className="flex items-center gap-3">
          {/* Air-Gap Status Indicator */}
          <div className="hidden sm:flex items-center gap-2 px-3.5 py-1.5 bg-[#04151f]/90 border border-emerald-500/30 rounded-full shadow-[0_0_12px_rgba(16,185,129,0.15)]">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            <span className="text-xs text-emerald-400 font-semibold tracking-wide">
              Offline Active
            </span>
          </div>

          {/* Ask AI Button */}
          <button
            onClick={onOpenAssistant}
            className="flex items-center gap-2 px-3.5 py-2 bg-gradient-to-br from-cyan-500/20 to-indigo-600/20
                       hover:from-cyan-500/30 hover:to-indigo-600/30
                       text-cyan-300 hover:text-white border border-cyan-500/30 hover:border-cyan-400/60
                       font-bold text-xs rounded-xl transition-all duration-200
                       shadow-[0_0_15px_rgba(0,229,255,0.15)] hover:shadow-[0_0_25px_rgba(0,229,255,0.3)]
                       hover:scale-[1.02] active:scale-[0.98] cursor-pointer"
            title="Open TriNetra AI Assistant"
          >
            <Bot className="w-4 h-4" />
            <span className="hidden sm:inline">Ask AI</span>
          </button>

          {/* Quick Ingest Tile CTA */}
          <button 
            onClick={(e) => handleNavClick(e, 'data-ingestion')}
            className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-cyan-400 to-blue-500 hover:from-cyan-300 hover:to-blue-400 text-slate-950 font-bold text-xs rounded-xl transition-all duration-200 shadow-[0_0_20px_rgba(0,229,255,0.35)] hover:scale-[1.02] active:scale-[0.98] cursor-pointer"
            title="Ingest new satellite tile into local archive"
          >
            <UploadCloud className="w-4 h-4" />
            <span>Ingest Tile</span>
          </button>
        </div>
      </div>
    </header>
  );
}
