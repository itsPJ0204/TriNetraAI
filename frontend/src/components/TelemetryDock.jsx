import React, { useState, useEffect } from 'react';
import { WifiOff } from 'lucide-react';
import { SYSTEM_STATUS } from '../data/mockData';

export default function TelemetryDock() {
  const [clock, setClock] = useState("UTC +05:30 IST LIVE");

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      const istOffset = 5.5 * 60 * 60 * 1000;
      const istDate = new Date(now.getTime() + (now.getTimezoneOffset() * 60000) + istOffset);
      const h = String(istDate.getHours()).padStart(2, '0');
      const m = String(istDate.getMinutes()).padStart(2, '0');
      const s = String(istDate.getSeconds()).padStart(2, '0');
      setClock(`${h}:${m}:${s} IST LIVE`);
    };

    updateTime();
    const timer = setInterval(updateTime, 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <footer className="fixed bottom-0 left-0 w-full z-50 flex flex-wrap justify-between items-center px-4 py-1.5 bg-[#070e1b]/95 backdrop-blur-md border-t border-[#1e293b] shadow-[0_-4px_16px_rgba(0,0,0,0.7)] font-mono text-[11px] text-[#64748b] select-none">
      {/* Left Engine State & FAISS Index Count */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-[#10b981] animate-pulse"></span>
          <span className="text-white font-semibold">
            SYSTEM STATUS: AI ENGINE {SYSTEM_STATUS.aiEngine}
          </span>
        </div>
        <span className="hidden md:inline text-[#1e293b]">|</span>
        <div className="hidden md:flex items-center gap-1.5">
          <span>FAISS INDEX:</span>
          <span className="text-[#00e5ff] font-bold">
            {SYSTEM_STATUS.indexedTiles.toLocaleString()} TILES // LOCAL STORAGE
          </span>
        </div>
        <span className="hidden md:inline text-[#1e293b]">|</span>
        <div className="hidden md:block">
          LATENCY: <strong className="text-[#10b981]">{SYSTEM_STATUS.latencyMs}ms</strong>
        </div>
      </div>

      {/* Center Air-Gap Node Declaration */}
      <div className="hidden xl:flex items-center gap-2 text-[11px] text-[#9cf0ff]">
        <WifiOff className="w-3.5 h-3.5 text-[#10b981]" />
        <span>OFFLINE MODE: ACTIVE (AIR-GAPPED HIGH SPEED SECURE NODE)</span>
      </div>

      {/* Right Live UTC/IST & Coordinates Readout */}
      <div className="flex items-center gap-3">
        <span className="hidden sm:inline">{SYSTEM_STATUS.telemetry.lat} {SYSTEM_STATUS.telemetry.lng}</span>
        <span className="hidden sm:inline text-[#1e293b]">|</span>
        <span className="text-white font-bold">{clock}</span>
      </div>
    </footer>
  );
}
