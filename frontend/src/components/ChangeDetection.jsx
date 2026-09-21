import React, { useState } from 'react';
import { ArrowLeftRight, Waves, CheckCircle2, TrendingUp } from 'lucide-react';

export default function ChangeDetection({ activeTile }) {
  const [sliderPos, setSliderPos] = useState(50);
  const [showMask, setShowMask] = useState(true);

  if (!activeTile) return null;
  const { changeAnalysis, hydrology } = activeTile;

  return (
    <section className="w-full py-16 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto border-b border-[#1e293b]/40" id="change-wiper">
      <div className="flex items-center gap-2 mb-2">
        <span className="w-2 h-2 bg-[#00e5ff]"></span>
        <span className="font-mono text-[10px] text-[#00e5ff] uppercase tracking-widest font-semibold">
          MODULE // 04
        </span>
      </div>
      <h2 className="text-[28px] sm:text-[34px] font-bold text-white tracking-tight mb-2">
        Bitemporal Change Wiper & GIS Proximity Buffer
      </h2>
      <p className="text-[14px] text-[#94a3b8] mb-8">
        Pixel-aligned temporal differential engine demonstrating automated construction delta over 36 months.
      </p>

      {/* Comparison Wiper Interactive Container */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Wiper Interactive Frame (8 cols) */}
        <div className="lg:col-span-8 hud-bracket-tl hud-bracket-br relative bg-[#0d1726] border border-[#00e5ff]/40 p-4 rounded-sm backdrop-blur-md">
          {/* Controls header */}
          <div className="flex flex-wrap items-center justify-between pb-3 mb-3 border-b border-[#1e293b] text-xs font-mono gap-2">
            <div className="flex items-center gap-3">
              <span className="text-white font-bold">DRAGGABLE WIPER:</span>
              <span className="text-[#64748b]">T0 ({changeAnalysis.baselineYear})</span>
              <span className="text-[#00e5ff] font-bold">VS</span>
              <span className="text-[#10b981] font-bold">T1 ({changeAnalysis.currentYear})</span>
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setShowMask(!showMask)}
                className={`px-2.5 py-1 font-mono text-[10px] uppercase font-bold transition-all rounded-sm border ${
                  showMask
                    ? 'bg-[#00e5ff] text-[#070e1b] border-[#00e5ff]'
                    : 'bg-[#131f33] text-[#00e5ff] border-[#00e5ff]/40 hover:bg-[#00e5ff]/20'
                }`}
              >
                {showMask ? "HEATMAP MASK: ON" : "HEATMAP MASK: OFF"}
              </button>
            </div>
          </div>

          {/* Draggable Wiper Container */}
          <div className="relative w-full h-[380px] sm:h-[440px] bg-[#070e1b] border border-[#1e293b] overflow-hidden select-none">
            {/* Right: AFTER Image Simulation (Full Background) */}
            <div className="absolute inset-0 bg-[#141b2b] flex flex-col justify-between p-6">
              <div className="absolute inset-0 hud-grid-bg opacity-30"></div>
              
              {/* Fortified Base Delta Visual Indicators (After) */}
              <div className="relative z-10 space-y-2">
                <div className="inline-block px-2.5 py-1 bg-[#f97316]/20 border border-[#f97316] text-[#f97316] font-mono text-[11px] font-bold">
                  AFTER: {changeAnalysis.currentYear} // FORTIFIED MILITARY BASE DETECTED
                </div>
                <p className="font-mono text-[11px] text-[#94a3b8] max-w-xs">
                  {changeAnalysis.afterDesc}
                </p>
              </div>

              {/* Heatmap delta contour simulation overlay */}
              {showMask && (
                <div className="absolute inset-16 border-2 border-dashed border-[#f97316] bg-[#f97316]/20 rounded-sm flex items-center justify-center p-4">
                  <div className="text-center font-mono">
                    <span className="text-[#f97316] font-bold text-sm block">
                      DELTA FOOTPRINT: +{changeAnalysis.changedAreaM2.toLocaleString()} m²
                    </span>
                    <span className="text-[#94a3b8] text-xs">
                      CONFIDENCE: {changeAnalysis.confidence}% (PASS-MATCH)
                    </span>
                  </div>
                </div>
              )}

              <div className="relative z-10 self-end font-mono text-[11px] text-[#64748b]">
                {activeTile.sensor} // RESOLUTION: {activeTile.resolution}
              </div>
            </div>

            {/* Left: BEFORE Image Simulation (Clipped by slider width) */}
            <div
              style={{ width: `${sliderPos}%` }}
              className="absolute inset-0 bg-[#0b121e] border-r-2 border-[#00e5ff] flex flex-col justify-between p-6 overflow-hidden transition-none"
            >
              <div className="absolute inset-0 hud-grid-bg opacity-20"></div>
              
              {/* Natural Riparian Riverbank (Before) */}
              <div className="relative z-10 space-y-2 min-w-[280px]">
                <div className="inline-block px-2.5 py-1 bg-[#10b981]/20 border border-[#10b981] text-[#10b981] font-mono text-[11px] font-bold">
                  BEFORE: {changeAnalysis.baselineYear} // PRISTINE RIVERBANK
                </div>
                <p className="font-mono text-[11px] text-[#94a3b8] max-w-xs">
                  {changeAnalysis.beforeDesc}
                </p>
              </div>

              <div className="relative z-10 font-mono text-[11px] text-[#64748b]">
                ARCHIVE SATELLITE TILES // T0 BASELINE
              </div>
            </div>

            {/* Slider HUD Reticle Divider Handle Bar */}
            <div
              style={{ left: `${sliderPos}%` }}
              className="absolute top-0 bottom-0 -ml-3.5 w-7 pointer-events-none flex flex-col items-center justify-center"
            >
              <div className="w-7 h-7 bg-[#00e5ff] text-[#070e1b] flex items-center justify-center rounded-[2px] shadow-[0_0_12px_#00e5ff]">
                <ArrowLeftRight className="w-4 h-4 font-bold" />
              </div>
            </div>
          </div>

          {/* Slider Range Controller */}
          <div className="mt-4 px-2">
            <input
              type="range"
              min="0"
              max="100"
              value={sliderPos}
              onChange={(e) => setSliderPos(Number(e.target.value))}
              className="w-full h-1 bg-[#1a2942] rounded-lg appearance-none cursor-ew-resize accent-[#00e5ff]"
            />
            <div className="flex justify-between font-mono text-[10px] text-[#64748b] mt-1.5">
              <span>◄ 100% BASELINE ({changeAnalysis.baselineYear})</span>
              <span className="text-[#00e5ff]">DRAG SLIDER TO REVEAL TEMPORAL CHANGE</span>
              <span>100% CURRENT ({changeAnalysis.currentYear}) ►</span>
            </div>
          </div>
        </div>

        {/* Right GIS Spatial Proximity Verification (4 cols) */}
        <div className="lg:col-span-4 flex flex-col justify-between gap-4">
          {/* GIS Measurement Panel */}
          <div className="bg-[#0d1726] border border-[#1e293b] p-4 rounded-sm">
            <div className="flex items-center justify-between pb-2 mb-3 border-b border-[#1e293b]">
              <span className="font-mono text-[11px] text-[#00e5ff] uppercase tracking-wider font-bold">
                GIS HYDROLOGIC BUFFER
              </span>
              <Waves className="w-4 h-4 text-[#00e5ff]" />
            </div>
            <div className="space-y-3 font-mono text-[11px]">
              <div>
                <span className="text-[#64748b] block text-[10px]">NEAREST WATERBODY:</span>
                <span className="text-white font-bold text-[13px]">{hydrology.nearestRiver}</span>
              </div>
              <div>
                <span className="text-[#64748b] block text-[10px]">MEASURED PROXIMITY DISTANCE:</span>
                <div className="flex items-center justify-between mt-0.5">
                  <span className="text-[#10b981] text-[20px] font-bold">{hydrology.distanceMeters} METERS</span>
                  <span className="text-[#64748b] text-[10px]">RAY-CAST GIS</span>
                </div>
              </div>
              <div>
                <span className="text-[#64748b] block text-[10px]">OPERATIONAL QUERY THRESHOLD:</span>
                <span className="text-[#f59e0b] font-bold text-[11px]">&lt; {hydrology.thresholdMeters} METERS PERIMETER</span>
              </div>
              {/* Pass Condition Box */}
              <div className="p-3 bg-[#10b981]/15 border border-[#10b981]/40 rounded-sm mt-3">
                <div className="flex items-center gap-2 text-[#10b981] font-mono text-[11px] font-bold">
                  <CheckCircle2 className="w-4 h-4" />
                  <span>{hydrology.status}</span>
                </div>
                <p className="text-[11px] text-[#94a3b8] mt-1 font-sans">
                  Target cluster is verified strictly inside the 500m river corridor constraint.
                </p>
              </div>
            </div>
          </div>

          {/* Delta Summary Card */}
          <div className="bg-[#0d1726] border border-[#1e293b] p-4 rounded-sm">
            <div className="flex items-center justify-between pb-2 mb-3 border-b border-[#1e293b]">
              <span className="font-mono text-[11px] text-white uppercase tracking-wider font-bold">
                TEMPORAL FOOTPRINT DELTA
              </span>
              <TrendingUp className="w-4 h-4 text-[#f59e0b]" />
            </div>
            <div className="grid grid-cols-2 gap-2 font-mono text-center">
              <div className="p-2.5 bg-[#070e1b] border border-[#1e293b]">
                <div className="text-[9px] text-[#64748b]">NEW STRUCTURES</div>
                <div className="text-[18px] font-bold text-white mt-0.5">
                  +{changeAnalysis.newStructuresCount}
                </div>
              </div>
              <div className="p-2.5 bg-[#070e1b] border border-[#1e293b]">
                <div className="text-[9px] text-[#64748b]">EXCAVATED AREA</div>
                <div className="text-[18px] font-bold text-[#f97316] mt-0.5">
                  {changeAnalysis.changedAreaM2} m²
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
