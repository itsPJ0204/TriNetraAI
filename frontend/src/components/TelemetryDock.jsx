import React, { useState, useEffect } from 'react';
import { WifiOff, Activity, Clock, ShieldCheck, Database, Cpu } from 'lucide-react';
import { SYSTEM_STATUS } from '../data/mockData';

export default function TelemetryDock({ onOpenChat }) {
  const [clock, setClock] = useState("00:00:00 IST");

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      const istOffset = 5.5 * 60 * 60 * 1000;
      const istDate = new Date(now.getTime() + (now.getTimezoneOffset() * 60000) + istOffset);
      const h = String(istDate.getHours()).padStart(2, '0');
      const m = String(istDate.getMinutes()).padStart(2, '0');
      const s = String(istDate.getSeconds()).padStart(2, '0');
      setClock(`${h}:${m}:${s} IST`);
    };

    updateTime();
    const timer = setInterval(updateTime, 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <footer className="fixed bottom-0 left-0 w-full z-40 flex flex-wrap justify-between items-center px-4 sm:px-6 py-2 bg-[#030814]/95 backdrop-blur-xl border-t border-cyan-500/25 shadow-lg shadow-black/40 text-xs text-slate-400 select-none">
      {/* Left Engine State & Vector Index Count */}
      <div className="flex items-center gap-3 font-mono">
        <button
          type="button"
          onClick={onOpenChat}
          className="flex items-center gap-2 px-2.5 py-1 -my-1 rounded-lg bg-cyan-950/40 hover:bg-cyan-500/20 border border-cyan-500/30 hover:border-cyan-400 text-left transition-all duration-150 cursor-pointer group shadow-[0_0_12px_rgba(0,229,255,0.15)] hover:shadow-[0_0_20px_rgba(0,229,255,0.35)]"
          title="Open TriNetra AI Assistant"
        >
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse group-hover:scale-125 transition-transform"></span>
          <span className="text-slate-200 font-semibold font-sans group-hover:text-cyan-200 transition-colors">
            AI Engine: <strong className="text-white font-mono group-hover:text-cyan-300">{SYSTEM_STATUS.aiEngine}</strong>
          </span>
        </button>
        <span className="hidden md:inline text-slate-700">&bull;</span>
        <div className="hidden md:flex items-center gap-1.5 font-sans">
          <Database className="w-3.5 h-3.5 text-cyan-400" />
          <span>Vector Index:</span>
          <span className="text-cyan-300 font-bold font-mono">
            {SYSTEM_STATUS.indexedTiles.toLocaleString()} Tiles (Local SQLite + Qdrant)
          </span>
        </div>
        <span className="hidden md:inline text-slate-700">&bull;</span>
        <div className="hidden md:block font-sans">
          Latency: <strong className="text-emerald-400 font-mono">{SYSTEM_STATUS.latencyMs}ms</strong>
        </div>
      </div>

      {/* Center Air-Gap Node Declaration */}
      <div className="hidden xl:flex items-center gap-2 text-xs text-slate-300">
        <WifiOff className="w-3.5 h-3.5 text-emerald-400" />
        <span className="font-medium">Offline Air-Gapped Secure Workstation Active</span>
      </div>

      {/* Right Live Coordinates & IST Clock */}
      <div className="flex items-center gap-3 font-mono text-xs">
        <span className="hidden sm:inline text-slate-400">{SYSTEM_STATUS.telemetry.lat} {SYSTEM_STATUS.telemetry.lng}</span>
        <span className="hidden sm:inline text-slate-700">&bull;</span>
        <div className="flex items-center gap-1.5 px-2.5 py-0.5 bg-gradient-to-b from-[#081b38]/90 via-[#06142e]/95 to-[#030a18]/95 border-2 border-cyan-400/50 shadow-[0_0_30px_rgba(0,229,255,0.2)] border border-cyan-500/25 rounded-full">
          <Clock className="w-3 h-3 text-cyan-400" />
          <span className="text-white font-bold">{clock}</span>
        </div>
      </div>
    </footer>
  );
}
