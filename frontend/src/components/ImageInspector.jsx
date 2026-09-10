import React from 'react';
import { Satellite, Brain, CheckCircle, ShieldCheck } from 'lucide-react';

export default function ImageInspector({ activeTile }) {
  if (!activeTile) return null;

  return (
    <section className="w-full py-16 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto border-b border-[#1e293b]/40" id="image-viewer">
      <div className="flex items-center gap-2 mb-2">
        <span className="w-2 h-2 bg-[#00e5ff]"></span>
        <span className="font-mono text-[10px] text-[#00e5ff] uppercase tracking-widest font-semibold">
          MODULE // 03
        </span>
      </div>
      <h2 className="text-[28px] sm:text-[34px] font-bold text-white tracking-tight mb-2">
        High-Resolution Target Inspector & Optical Detection
      </h2>
      <p className="text-[14px] text-[#94a3b8] mb-8">
        Air-gapped sub-pixel convolutional segmentation with automated bounding boxes and military telemetry feed.
      </p>

      {/* Split View: Canvas Reticle Display (65%) & Metadata Inspector (35%) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Inspector Canvas Container */}
        <div className="lg:col-span-8 hud-bracket-tl hud-bracket-br relative bg-[#0d1726] border border-[#00e5ff]/30 rounded-sm p-4 backdrop-blur-md">
          {/* Viewer Top Controls Strip */}
          <div className="flex flex-wrap items-center justify-between pb-3 mb-3 border-b border-[#1e293b] text-xs font-mono text-[#94a3b8] gap-2">
            <div className="flex items-center gap-2">
              <span className="text-[#00e5ff] font-bold">FOV: 1.2 KM × 1.2 KM</span>
              <span>•</span>
              <span>BAND: B04 (RED) / B03 (GREEN) / B02 (BLUE)</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="px-2 py-0.5 bg-[#131f33] border border-[#1e293b] text-[#10b981]">
                YOLOv8x ACTIVE
              </span>
              <span className="text-[#00e5ff]">ZOOM: 16.0×</span>
            </div>
          </div>

          {/* Satellite Image Viewer with Bounding Boxes */}
          <div className="relative w-full h-[420px] sm:h-[480px] bg-[#0c1424] border border-[#1e293b] overflow-hidden flex items-center justify-center select-none">
            {/* Synthetic Reconnaissance Ground Pattern */}
            <div className="absolute inset-0 bg-gradient-to-br from-[#121c2e] via-[#09111e] to-[#070d18] opacity-95"></div>
            <div className="absolute inset-0 hud-grid-bg opacity-35"></div>

            {/* River channel simulation line */}
            <div className="absolute -left-10 top-1/3 w-[120%] h-14 bg-cyan-950/40 border-y border-cyan-500/20 -rotate-12 blur-[1px] flex items-center justify-center">
              <span className="font-mono text-[11px] text-[#9cf0ff] tracking-widest opacity-60">
                {activeTile.hydrology.nearestRiver.toUpperCase()} // BUFFER ZONE
              </span>
            </div>

            {/* Render Target Bounding Boxes */}
            {activeTile.boundingBoxes?.map((box) => (
              <div
                key={box.id}
                style={{
                  top: `${box.y}%`,
                  left: `${box.x}%`,
                  width: `${box.width}%`,
                  height: `${box.height}%`,
                  borderColor: box.color
                }}
                className="absolute border-2 bg-black/20 p-1.5 shadow-[0_0_15px_rgba(0,229,255,0.3)] transition-all hover:scale-105"
              >
                <div
                  style={{ backgroundColor: box.color }}
                  className="flex items-center justify-between px-1 py-0.5 text-[#070e1b] font-mono text-[9px] font-bold"
                >
                  <span>{box.label}</span>
                  <span>{box.confidence}%</span>
                </div>
                <div className="text-[9px] font-mono text-white mt-1">
                  LAT: {activeTile.coordinates.lat}° / LNG: {activeTile.coordinates.lng}°
                </div>
                <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                  <span className="w-1.5 h-1.5 bg-[#00e5ff] rounded-full"></span>
                </div>
              </div>
            ))}

            {/* Canvas Reticle Coordinate Overlays */}
            <div className="absolute top-4 left-4 font-mono text-[11px] text-[#00e5ff] bg-[#070e1b]/90 px-2.5 py-1 border border-[#1e293b]">
              LOC: {activeTile.coordinates.formatted}
            </div>
            <div className="absolute bottom-4 left-4 font-mono text-[10px] text-[#94a3b8] bg-[#070e1b]/90 px-2.5 py-1 border border-[#1e293b]">
              ALT: 4,820M AMSL // SENSOR: {activeTile.sensor.toUpperCase()}
            </div>

            {/* HUD Compass Heading */}
            <div className="absolute top-4 right-4 w-12 h-12 rounded-full border border-[#00e5ff]/40 flex items-center justify-center font-mono text-[10px] text-[#00e5ff]">
              <span className="absolute top-1 font-bold">N</span>
              <span className="w-1.5 h-1.5 rounded-full bg-[#00e5ff]"></span>
            </div>
          </div>

          {/* Viewer Bottom Bar */}
          <div className="flex flex-wrap items-center justify-between pt-3 mt-3 border-t border-[#1e293b] text-xs font-mono text-[#94a3b8]">
            <span>AIR-GAP INTEGRITY: UNCOMPROMISED LOCAL CACHE</span>
            <span className="text-[#10b981] font-semibold">ALL SENSOR CHECKS NOMINAL</span>
          </div>
        </div>

        {/* Right Metadata & Intelligence Panel (35%) */}
        <div className="lg:col-span-4 flex flex-col justify-between gap-4">
          {/* Sensor Meta Card */}
          <div className="bg-[#0d1726] border border-[#1e293b] p-4 rounded-sm">
            <div className="flex items-center justify-between pb-2 mb-3 border-b border-[#1e293b]">
              <span className="font-mono text-[11px] text-[#00e5ff] uppercase tracking-wider font-bold">
                SENSOR TELEMETRY METADATA
              </span>
              <Satellite className="w-4 h-4 text-[#00e5ff]" />
            </div>
            <div className="space-y-2.5 font-mono text-[11px]">
              <div className="flex justify-between">
                <span className="text-[#64748b]">PRIMARY SENSOR:</span>
                <span className="text-white font-semibold">{activeTile.sensor}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#64748b]">GROUND SAMPLE DIST:</span>
                <span className="text-[#00e5ff] font-semibold">{activeTile.resolution}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#64748b]">PROJECTION / CRS:</span>
                <span className="text-white">{activeTile.crs}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#64748b]">ACQUISITION TIMESTAMP:</span>
                <span className="text-white">{activeTile.timestamp}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#64748b]">CLOUD COVER:</span>
                <span className="text-[#10b981] font-bold">{activeTile.qa.cloudOcclusion}</span>
              </div>
            </div>
          </div>

          {/* AI Confidence & Inference Gauges Card */}
          <div className="bg-[#0d1726] border border-[#1e293b] p-4 rounded-sm flex-1 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between pb-2 mb-3 border-b border-[#1e293b]">
                <span className="font-mono text-[11px] text-[#10b981] uppercase tracking-wider font-bold">
                  AI INFERENCE GAUGES
                </span>
                <Brain className="w-4 h-4 text-[#10b981]" />
              </div>

              {/* Progress bars */}
              <div className="space-y-3 mb-4">
                {activeTile.detectedObjects?.map((obj, i) => (
                  <div key={i}>
                    <div className="flex justify-between font-mono text-[11px] mb-1">
                      <span className="text-[#94a3b8]">{obj.label} ({obj.count} UNITS)</span>
                      <span className="text-[#00e5ff] font-bold">{obj.confidence}%</span>
                    </div>
                    <div className="w-full bg-[#131f33] h-1.5 rounded-sm overflow-hidden">
                      <div
                        className="bg-[#00e5ff] h-full transition-all duration-500"
                        style={{ width: `${obj.confidence}%` }}
                      ></div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Quality Badges */}
            <div className="pt-3 border-t border-[#1e293b] flex items-center justify-between gap-2">
              <span className="px-2.5 py-1 bg-[#10b981]/20 border border-[#10b981]/40 text-[#10b981] font-mono text-[10px] font-bold uppercase flex items-center gap-1">
                <CheckCircle className="w-3.5 h-3.5" />
                QA: {activeTile.qa.status}
              </span>
              <span className="px-2.5 py-1 bg-[#1a2942] border border-[#1e293b] text-[#9cf0ff] font-mono text-[10px] font-bold uppercase flex items-center gap-1">
                <ShieldCheck className="w-3.5 h-3.5 text-[#00e5ff]" />
                AIR-GAP CERTIFIED
              </span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
