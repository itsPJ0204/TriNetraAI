import React from 'react';
import { ShieldCheck, Search, Image as ImageIcon, Sparkles, Activity, Layers, ArrowRight } from 'lucide-react';

export default function HeroSection({ onEnterCommandCenter }) {
  return (
    <section className="relative w-full min-h-[92vh] pt-20 pb-12 flex flex-col justify-between overflow-hidden bg-black border-b border-cyan-500/25" id="hero">
      {/* Photorealistic Earth Horizon & Constellation Image Layer */}
      <div className="absolute inset-0 z-0">
        <img
          src="/images/hero_earth.png"
          alt="Earth Horizon from Orbit with Indian Subcontinent and Satellites"
          className="w-full h-full object-cover object-bottom opacity-85 scale-100 filter brightness-95 contrast-105"
          onError={(e) => {
            e.target.style.display = 'none';
          }}
        />
        {/* Cosmic Ambient Overlays */}
        <div className="absolute inset-0 bg-gradient-to-t from-[#060a12] via-[#060a12]/60 to-transparent"></div>
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_transparent_30%,_rgba(6,10,18,0.75)_80%)]"></div>
      </div>

      {/* Atmospheric Grid Lines */}
      <div className="absolute inset-0 z-10 pointer-events-none hud-grid-bg opacity-25"></div>

      {/* Center Hero Content Container */}
      <div className="relative z-20 max-w-5xl mx-auto w-full px-4 sm:px-6 py-16 my-auto flex flex-col items-center text-center">
        {/* Classification / Defense Space Pill Badge */}
        <div className="inline-flex items-center gap-2.5 px-4 py-1.5 bg-gradient-to-b from-[#081b38]/90 via-[#06142e]/95 to-[#030a18]/95 border-2 border-cyan-400/50 shadow-[0_0_30px_rgba(0,229,255,0.2)] border border-cyan-500/30 rounded-full mb-8 backdrop-blur-xl shadow-lg shadow-cyan-500/10 animate-fade-in">
          <ShieldCheck className="w-4 h-4 text-cyan-400" />
          <span className="text-xs text-cyan-200 tracking-wide font-medium">
            Defense Space Agency // Air-Gapped Intelligence Workstation
          </span>
        </div>

        {/* Main Typography Hierarchy */}
        <h1 className="font-extrabold text-4xl sm:text-6xl md:text-7xl leading-tight tracking-tight text-white mb-4 drop-shadow-2xl">
          <span className="bg-gradient-to-r from-white via-slate-100 to-cyan-200 bg-clip-text text-transparent">
            TriNetra AI
          </span>
        </h1>
        
        <p className="text-base sm:text-xl text-slate-300 max-w-3xl font-medium leading-relaxed mb-10">
          Offline Semantic Vector Search & Multi-Temporal Change Detection for High-Resolution Satellite Reconnaissance
        </p>

        {/* Command CTA Cluster */}
        <div className="flex flex-wrap items-center justify-center gap-4 mb-12">
          <a
            href="#semantic-search"
            onClick={onEnterCommandCenter}
            className="px-8 py-3.5 bg-gradient-to-r from-cyan-400 to-cyan-500 hover:from-cyan-300 hover:to-cyan-400 text-slate-950 font-bold text-sm tracking-wide rounded-2xl transition-all duration-200 shadow-lg shadow-cyan-500/25 flex items-center gap-2.5 cursor-pointer hover:scale-[1.02] active:scale-[0.98]"
          >
            <Search className="w-4 h-4" />
            <span>Launch Command Center</span>
            <ArrowRight className="w-4 h-4 ml-1" />
          </a>
          <a
            href="#image-search"
            className="px-7 py-3.5 bg-gradient-to-b from-[#081b38]/90 via-[#06142e]/95 to-[#030a18]/95 border-2 border-cyan-400/50 shadow-[0_0_30px_rgba(0,229,255,0.2)] hover:bg-slate-800 text-slate-200 hover:text-white border border-cyan-500/30 hover:border-cyan-500/40 font-semibold text-sm rounded-2xl backdrop-blur-xl transition-all duration-200 flex items-center gap-2.5 shadow-md hover:scale-[1.02]"
          >
            <ImageIcon className="w-4 h-4 text-cyan-400" />
            <span>Visual Image Search</span>
          </a>
        </div>

        {/* Hero Telemetry Status Card (Glassmorphic) */}
        <div className="w-full max-w-3xl bg-gradient-to-b from-[#081b38]/90 via-[#06142e]/95 to-[#030a18]/95 border-2 border-cyan-400/50 shadow-[0_0_30px_rgba(0,229,255,0.2)] border border-cyan-500/25 backdrop-blur-xl py-3 px-6 rounded-2xl flex flex-wrap items-center justify-between gap-4 text-xs text-slate-300 shadow-xl">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse"></span>
            <span className="text-slate-400">Indexed Vectors:</span>
            <strong className="text-cyan-300 font-semibold">90+ Sub-Tiles Loaded</strong>
          </div>
          <div className="hidden sm:block text-slate-700">|</div>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
            <span className="text-slate-400">Resolution:</span>
            <strong className="text-slate-200 font-semibold">Sub-0.5m / Multispectral</strong>
          </div>
          <div className="hidden sm:block text-slate-700">|</div>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
            <span className="text-slate-400">Security Mode:</span>
            <strong className="text-emerald-400 font-semibold">Offline Air-Gap</strong>
          </div>
        </div>
      </div>

      {/* Orbital Telemetry Bottom Readouts */}
      <div className="relative z-20 w-full bg-[#030814]/90 backdrop-blur-md border-t border-cyan-500/25 px-6 py-2.5 flex flex-wrap justify-between items-center text-xs text-slate-400 font-mono">
        <div className="flex items-center gap-3">
          <span className="text-slate-300">Constellation: Cartosat-3 &bull; Sentinel-2A &bull; Landsat-8</span>
          <span className="hidden md:inline text-slate-700">&bull;</span>
          <span className="hidden md:inline">Target Center: 18°55'N, 72°50'E</span>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-cyan-400 flex items-center gap-1.5">
            <Activity className="w-3.5 h-3.5" />
            RemoteCLIP ViT-B/32
          </span>
          <span className="text-emerald-400 font-semibold">System Optimal</span>
        </div>
      </div>
    </section>
  );
}
