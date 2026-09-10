import React from 'react';
import { Lock, FileCheck, Image as ImageIcon } from 'lucide-react';

export default function HeroSection({ onEnterCommandCenter }) {
  return (
    <section className="relative w-full min-h-screen pt-16 flex flex-col justify-between overflow-hidden bg-[#070e1b] border-b border-[#1e293b]/50" id="hero">
      {/* Photorealistic Earth Horizon & Constellation Image Layer */}
      <div className="absolute inset-0 z-0">
        <img
          src="/images/hero_earth.png"
          alt="Cinematic Earth Horizon from Orbit with Indian Subcontinent and Reconnaissance Satellites"
          className="w-full h-full object-cover object-bottom opacity-90 scale-100 filter brightness-100 contrast-110"
          onError={(e) => {
            // Fallback gradient if image not found
            e.target.style.display = 'none';
          }}
        />
        {/* Deep space cosmic overlay */}
        <div className="absolute inset-0 bg-gradient-to-t from-[#070e1b] via-transparent to-[#070e1b]/80"></div>
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_transparent_40%,_rgba(7,14,27,0.6)_85%)]"></div>
      </div>

      {/* Atmospheric Grid Reticle Canvas HUD Lines */}
      <div className="absolute inset-0 z-10 pointer-events-none hud-grid-bg opacity-30"></div>

      {/* Center Hero Content Container */}
      <div className="relative z-20 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-20 my-auto flex flex-col items-center text-center">
        {/* Classification Banner */}
        <div className="inline-flex items-center gap-2 px-3 py-1 bg-[#070e1b]/90 border border-[#00e5ff]/40 rounded-sm mb-6 backdrop-blur-md shadow-[0_0_15px_rgba(0,229,255,0.15)]">
          <Lock className="w-3.5 h-3.5 text-[#00e5ff]" />
          <span className="font-mono text-[11px] text-[#9cf0ff] uppercase tracking-widest font-semibold">
            RESTRICTED C4ISR // DEFENCE SPACE AGENCY AIR-GAPPED WORKSTATION
          </span>
        </div>

        {/* Main Typography Hierarchy */}
        <h1 className="font-bold text-[48px] sm:text-[68px] md:text-[84px] leading-tight tracking-tight text-white mb-2 drop-shadow-[0_4px_24px_rgba(0,0,0,0.9)]">
          TriNetra AI
        </h1>
        <p className="font-mono text-[13px] sm:text-[16px] tracking-[0.15em] sm:tracking-[0.2em] text-[#00e5ff] uppercase font-semibold mb-10">
          Semantic Retrieval and Multi-Temporal Change Analysis of Satellite Imagery
        </p>

        {/* Command CTA Cluster */}
        <div className="flex flex-wrap items-center justify-center gap-4 mb-12">
          <a
            href="#semantic-search"
            onClick={onEnterCommandCenter}
            className="hud-bracket-tl hud-bracket-br relative px-8 py-3.5 bg-[#00e5ff]/15 hover:bg-[#00e5ff] text-[#00e5ff] hover:text-[#070e1b] border border-[#00e5ff] font-mono text-[12px] font-bold tracking-widest uppercase transition-all duration-200 shadow-[0_0_20px_rgba(0,229,255,0.25)] flex items-center gap-2 group cursor-pointer"
          >
            <FileCheck className="w-4 h-4 group-hover:rotate-45 transition-transform duration-300" />
            [ ENTER COMMAND CENTER ]
          </a>
          <a
            href="#image-search"
            className="px-8 py-3.5 bg-[#131f33]/70 hover:bg-[#1a2942] border border-[#00e5ff]/40 text-[#e2e8f0] hover:text-[#00e5ff] font-mono text-[12px] font-semibold tracking-wider uppercase backdrop-blur-md transition-all duration-150 flex items-center gap-2"
          >
            <ImageIcon className="w-4 h-4 text-[#00e5ff]" />
            [ IMAGE SEARCH ]
          </a>
        </div>

        {/* Hero Telemetry Status Strip */}
        <div className="w-full max-w-4xl bg-[#070e1b]/80 border border-[#1e293b] backdrop-blur-md py-2.5 px-6 rounded-sm flex flex-wrap items-center justify-between gap-4 font-mono text-[12px] text-[#94a3b8]">
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-[#00e5ff]"></span>
            <span>FAISS VECTORS: <strong className="text-[#00e5ff]">68,920 TILES INDEXED</strong></span>
          </div>
          <div className="hidden sm:block text-[#1e293b]">|</div>
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-[#10b981]"></span>
            <span>RES: <strong className="text-[#e2e8f0]">SUB-0.25M / 10M MSI</strong></span>
          </div>
          <div className="hidden sm:block text-[#1e293b]">|</div>
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-[#10b981]"></span>
            <span>AIR-GAP STATE: <strong className="text-[#10b981]">ISOLATED ENCLAVE</strong></span>
          </div>
        </div>
      </div>

      {/* Orbital Telemetry Bottom Readouts */}
      <div className="relative z-20 w-full bg-[#0c1320]/90 border-t border-[#1e293b]/60 px-6 py-2 flex flex-wrap justify-between items-center font-mono text-[11px] text-[#64748b]">
        <div className="flex items-center gap-4">
          <span>CONSTELLATION: CARTOSAT-3 / RISAT-2BR1 / SENTINEL-2A</span>
          <span className="hidden md:inline text-[#1e293b]">•</span>
          <span className="hidden md:inline">SUB-SATELLITE POINT: 18°55'N 72°50'E</span>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-[#00e5ff]">SAR ACTIVE // POLAR X-BAND</span>
          <span className="text-[#10b981]">ORBIT VELOCITY: 7.62 KM/S</span>
        </div>
      </div>
    </section>
  );
}
