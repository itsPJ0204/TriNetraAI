import React from 'react';
import { Shield, Satellite, Terminal } from 'lucide-react';

export default function Navigation({ onNavigate }) {
  const handleNavClick = (e, targetId) => {
    if (onNavigate) {
      e.preventDefault();
      onNavigate(targetId);
    }
  };

  return (
    <header className="fixed top-0 left-0 w-full z-50 flex flex-col justify-between items-center px-4 py-2 bg-[#0c1320]/90 backdrop-blur-md border-b border-[#1e293b]/80 shadow-[0_4px_24px_rgba(0,229,255,0.06)]">
      <div className="w-full flex items-center justify-between gap-4">
        {/* Brand & Indian Tricolour Badge */}
        <div className="flex items-center gap-3">
          <div className="flex items-center space-x-0.5 px-2 py-1 bg-[#070e1b] border border-[#1e293b] rounded-sm">
            <div className="w-1.5 h-4 bg-[#FF9933] rounded-[1px]"></div>
            <div className="w-1.5 h-4 bg-[#FFFFFF] flex items-center justify-center">
              <span className="w-1 h-1 rounded-full bg-[#000080]"></span>
            </div>
            <div className="w-1.5 h-4 bg-[#128807] rounded-[1px]"></div>
            <span className="font-mono text-[10px] text-[#9cf0ff] ml-2 tracking-widest uppercase font-bold">
              BHARAT SAT-INTEL
            </span>
          </div>
          <div className="h-4 w-px bg-[#1e293b] hidden sm:block"></div>
          <span className="text-[14px] font-bold tracking-wider text-[#00e5ff] uppercase hidden md:inline font-mono">
            TRINETRA AI // त्रिनेत्र AI
          </span>
        </div>

        {/* Center Desktop Navigation Cluster */}
        <nav className="hidden xl:flex items-center gap-6 font-mono text-[11px] tracking-wide">
          <a className="border-b-2 border-[#00e5ff] text-[#00e5ff] font-semibold py-1" href="#hero" onClick={(e) => handleNavClick(e, 'hero')}>
            Mission Overview
          </a>
          <a className="text-[#94a3b8] hover:text-[#00e5ff] font-medium py-1 transition-colors duration-150" href="#semantic-search" onClick={(e) => handleNavClick(e, 'semantic-search')}>
            Vector Search
          </a>
          <a className="text-[#94a3b8] hover:text-[#00e5ff] font-medium py-1 transition-colors duration-150" href="#candidate-tiles" onClick={(e) => handleNavClick(e, 'candidate-tiles')}>
            Candidate Tiles
          </a>
          <a className="text-[#94a3b8] hover:text-[#00e5ff] font-medium py-1 transition-colors duration-150" href="#image-search" onClick={(e) => handleNavClick(e, 'image-search')}>
            Image Search
          </a>
          <a className="text-[#94a3b8] hover:text-[#00e5ff] font-medium py-1 transition-colors duration-150" href="#temporal-analysis" onClick={(e) => handleNavClick(e, 'temporal-analysis')}>
            Temporal Analysis
          </a>
          <a className="text-[#94a3b8] hover:text-[#00e5ff] font-medium py-1 transition-colors duration-150" href="#data-ingestion" onClick={(e) => handleNavClick(e, 'data-ingestion')}>
            Data Ingestion
          </a>
        </nav>

        {/* Trailing Status Badges & Quick Action */}
        <div className="flex items-center gap-2 sm:gap-3">
          {/* Air-Gap Status Indicator */}
          <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 bg-[#1a2942]/60 border border-[#00a572]/40 rounded-sm">
            <span className="w-2 h-2 rounded-full bg-[#10b981] animate-pulse"></span>
            <span className="font-mono text-[10px] text-[#10b981] tracking-wider font-semibold">
              ● OFFLINE SYSTEM ACTIVE
            </span>
          </div>

          {/* DEFCON Status Pill */}
          <div className="px-2.5 py-1 bg-[#070e1b] border border-[#00e5ff]/40 rounded-sm">
            <span className="font-mono text-[10px] text-[#00e5ff] tracking-widest font-semibold">
              DEFCON 2 // ENGAGE
            </span>
          </div>

          {/* Quick Ingest Tile CTA */}
          <button 
            onClick={(e) => handleNavClick(e, 'data-ingestion')}
            className="flex items-center gap-1.5 px-3 py-1 bg-[#00e5ff]/10 hover:bg-[#00e5ff]/20 border border-[#00e5ff]/60 hover:border-[#00e5ff] text-[#00e5ff] rounded-sm font-mono text-[10px] uppercase font-bold tracking-wider transition-all duration-150 shadow-[0_0_12px_rgba(0,229,255,0.15)]"
            title="Ingest new satellite tile into local archive"
          >
            <span>+ INGEST TILE</span>
          </button>

          {/* Trailing System Icon Actions */}
          <div className="flex items-center gap-1 text-[#94a3b8]">
            <button className="p-1.5 hover:bg-[#1a2942] hover:text-[#00e5ff] rounded-sm transition-colors" title="Security Enclave">
              <Shield className="w-4 h-4" />
            </button>
            <button className="p-1.5 hover:bg-[#1a2942] hover:text-[#00e5ff] rounded-sm transition-colors" title="Satellite Link">
              <Satellite className="w-4 h-4" />
            </button>
            <button className="p-1.5 hover:bg-[#1a2942] hover:text-[#00e5ff] rounded-sm transition-colors" title="Terminal">
              <Terminal className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}
