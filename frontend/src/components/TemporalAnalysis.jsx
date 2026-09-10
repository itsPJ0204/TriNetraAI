import React, { useState, useEffect, useRef } from 'react';
import { 
  ArrowLeftRight, 
  Calendar, 
  Layers, 
  Maximize2, 
  Minimize2, 
  RotateCcw, 
  ZoomIn, 
  ZoomOut, 
  CheckCircle2, 
  AlertTriangle, 
  Eye, 
  ShieldCheck, 
  MapPin, 
  Sliders, 
  ChevronRight,
  Sparkles,
  Clock,
  Compass,
  Activity
} from 'lucide-react';
import { CANDIDATE_TILES, MARKER_TYPES } from '../data/mockData';
import { getChangeDetection, getTemporalHistory, getAvailableDates } from '../services/api';

export default function TemporalAnalysis({ activeTile, onSelectTile }) {
  // Current tile context (fall back to activeTile or T027)
  const currentTile = activeTile || CANDIDATE_TILES[0];
  const [selectedTileId, setSelectedTileId] = useState(currentTile.id);
  
  // Date range state
  const [startDate, setStartDate] = useState(2020);
  const [endDate, setEndDate] = useState(2023);
  const [activeYearPreview, setActiveYearPreview] = useState(null);

  // Comparison controls
  const [sliderPos, setSliderPos] = useState(50);
  const [isDraggingSlider, setIsDraggingSlider] = useState(false);
  const [viewMode, setViewMode] = useState('slider'); // 'slider' or 'side-by-side'
  const [zoomLevel, setZoomLevel] = useState(1);
  const [isFullscreen, setIsFullscreen] = useState(false);
  
  // Change mask controls
  const [showMask, setShowMask] = useState(true);
  const [maskOpacity, setMaskOpacity] = useState(75);

  // Analysis result state
  const [analysisResult, setAnalysisResult] = useState(null);
  const [isComparing, setIsComparing] = useState(false);
  const [activeMarkerPopover, setActiveMarkerPopover] = useState(null);

  const containerRef = useRef(null);
  const sliderTrackRef = useRef(null);

  // Sync selected tile when activeTile changes from parent
  useEffect(() => {
    if (activeTile && activeTile.id !== selectedTileId) {
      setSelectedTileId(activeTile.id);
      loadAnalysis(activeTile.id, startDate, endDate);
    }
  }, [activeTile]);

  // Initial load
  useEffect(() => {
    loadAnalysis(selectedTileId, startDate, endDate);
  }, [selectedTileId]);

  const loadAnalysis = async (tileId, before, after) => {
    setIsComparing(true);
    try {
      const res = await getChangeDetection(tileId, before, after);
      if (res.success) {
        setAnalysisResult(res);
      }
    } catch (e) {
      console.error("Temporal analysis error:", e);
    } finally {
      setIsComparing(false);
    }
  };

  const handleCompareClick = () => {
    loadAnalysis(selectedTileId, startDate, endDate);
    setActiveYearPreview(null);
  };

  const handleTileChange = (tileId) => {
    setSelectedTileId(tileId);
    if (onSelectTile) onSelectTile(tileId);
    loadAnalysis(tileId, startDate, endDate);
  };

  // Slider drag handling
  const handleSliderMove = (clientX) => {
    if (!sliderTrackRef.current) return;
    const rect = sliderTrackRef.current.getBoundingClientRect();
    const x = Math.max(0, Math.min(clientX - rect.left, rect.width));
    const percent = Math.round((x / rect.width) * 100);
    setSliderPos(percent);
  };

  const handleMouseDown = () => setIsDraggingSlider(true);
  const handleMouseUp = () => setIsDraggingSlider(false);
  const handleMouseMove = (e) => {
    if (isDraggingSlider) handleSliderMove(e.clientX);
  };

  const handleTouchMove = (e) => {
    if (e.touches && e.touches[0]) handleSliderMove(e.touches[0].clientX);
  };

  // Active tile reference object
  const tileData = CANDIDATE_TILES.find(t => t.id === selectedTileId) || currentTile;
  const availableYears = tileData.availableYears || [2020, 2021, 2022, 2023, 2024, 2025];
  const historyList = tileData.temporalHistory || [];

  return (
    <section className="w-full py-16 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto border-b border-[#1e293b]/40" id="temporal-analysis">
      {/* Section Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-8 pb-3 border-b border-[#1e293b]">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="w-2 h-2 bg-[#00e5ff]"></span>
            <span className="font-mono text-[10px] text-[#00e5ff] uppercase tracking-widest font-semibold">
              MODULE // 04
            </span>
          </div>
          <h2 className="text-[28px] sm:text-[34px] font-bold text-white tracking-tight">
            Temporal Comparison // Change Detection
          </h2>
          <p className="text-[14px] text-[#94a3b8] mt-1">
            Compare satellite imagery of the same geographic area across different acquisition dates to detect ground changes over time.
          </p>
        </div>

        {/* System telemetry badges */}
        <div className="flex items-center gap-3 font-mono text-[11px]">
          <div className="flex items-center gap-1.5 px-3 py-1.5 bg-[#0d1726] border border-[#00e5ff]/40 rounded-sm text-[#00e5ff]">
            <Layers className="w-3.5 h-3.5" />
            <span>ARCHIVE: 2020—2025 READY</span>
          </div>
          <div className="flex items-center gap-1.5 px-3 py-1.5 bg-[#0d1726] border border-[#10b981]/40 rounded-sm text-[#10b981]">
            <Activity className="w-3.5 h-3.5" />
            <span>DIFF ENGINE: PIXEL-ALIGNED</span>
          </div>
        </div>
      </div>

      {/* TEMPORAL SEARCH & DATE RANGE BAR */}
      <div className="bg-[#0c1424] border border-[#1e293b] rounded-sm p-4 sm:p-5 mb-8 shadow-[0_4px_24px_rgba(0,0,0,0.4)]">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          {/* Controls: Location, Start Date, End Date */}
          <div className="flex flex-wrap items-center gap-4 sm:gap-6 font-mono text-xs">
            {/* Tile/Location Selector */}
            <div className="flex flex-col gap-1.5">
              <label className="text-[10px] text-[#64748b] tracking-wider uppercase font-bold flex items-center gap-1">
                <MapPin className="w-3 h-3 text-[#00e5ff]" />
                LOCATION / TILE
              </label>
              <div className="flex items-center gap-1 bg-[#131f33] border border-[#1e293b] rounded-sm p-1">
                {CANDIDATE_TILES.map(t => (
                  <button
                    key={t.id}
                    onClick={() => handleTileChange(t.id)}
                    className={`px-3 py-1.5 rounded-sm font-bold tracking-wider transition-all duration-150 ${
                      selectedTileId === t.id
                        ? 'bg-[#00e5ff] text-[#070e1b] shadow-[0_0_10px_rgba(0,229,255,0.4)]'
                        : 'text-[#94a3b8] hover:text-white hover:bg-[#1a2942]'
                    }`}
                  >
                    [{t.id}]
                  </button>
                ))}
              </div>
            </div>

            {/* Start Date */}
            <div className="flex flex-col gap-1.5">
              <label className="text-[10px] text-[#64748b] tracking-wider uppercase font-bold flex items-center gap-1">
                <Calendar className="w-3 h-3 text-[#00e5ff]" />
                START DATE (BEFORE)
              </label>
              <select
                value={startDate}
                onChange={(e) => setStartDate(Number(e.target.value))}
                className="bg-[#131f33] border border-[#1e293b] text-white px-3 py-1.5 rounded-sm focus:border-[#00e5ff] focus:outline-none font-mono"
              >
                {availableYears.map(yr => (
                  <option key={`start-${yr}`} value={yr} disabled={yr >= endDate}>
                    {yr} {yr === 2020 ? '(Baseline)' : ''}
                  </option>
                ))}
              </select>
            </div>

            {/* Arrow Divider */}
            <div className="hidden sm:flex items-center justify-center pt-5 text-[#00e5ff]">
              <ArrowLeftRight className="w-4 h-4" />
            </div>

            {/* End Date */}
            <div className="flex flex-col gap-1.5">
              <label className="text-[10px] text-[#64748b] tracking-wider uppercase font-bold flex items-center gap-1">
                <Calendar className="w-3 h-3 text-[#10b981]" />
                END DATE (AFTER)
              </label>
              <select
                value={endDate}
                onChange={(e) => setEndDate(Number(e.target.value))}
                className="bg-[#131f33] border border-[#1e293b] text-white px-3 py-1.5 rounded-sm focus:border-[#00e5ff] focus:outline-none font-mono"
              >
                {availableYears.map(yr => (
                  <option key={`end-${yr}`} value={yr} disabled={yr <= startDate}>
                    {yr} {yr === 2023 ? '(Current Delta)' : ''}
                  </option>
                ))}
              </select>
            </div>

            {/* Compare Action Button */}
            <div className="flex flex-col justify-end pt-5">
              <button
                onClick={handleCompareClick}
                disabled={isComparing}
                className="px-6 py-2 bg-[#00e5ff] hover:bg-[#00b8cc] text-[#070e1b] font-mono text-xs font-bold uppercase tracking-widest rounded-sm transition-all duration-150 shadow-[0_0_15px_rgba(0,229,255,0.3)] flex items-center gap-2 cursor-pointer disabled:opacity-50"
              >
                <Sparkles className="w-4 h-4" />
                <span>{isComparing ? 'PROCESSING...' : '[ COMPARE ]'}</span>
              </button>
            </div>
          </div>

          {/* Quick Marker Legend Pill */}
          <div className="flex items-center gap-3 pt-2 lg:pt-0 border-t lg:border-t-0 border-[#1e293b]">
            <span className="font-mono text-[10px] text-[#64748b] uppercase tracking-wider">STATUS:</span>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-[#ef4444] animate-pulse"></span>
              <span className="font-mono text-[11px] font-bold text-[#ef4444]">DELTA DETECTED (91.4%)</span>
            </div>
          </div>
        </div>

        {/* INTERACTIVE TIMELINE SELECTOR */}
        <div className="mt-6 pt-5 border-t border-[#1e293b]">
          <div className="flex items-center justify-between text-[11px] font-mono text-[#64748b] mb-2">
            <span className="uppercase tracking-wider">LOCAL ARCHIVE TIMELINE (CLICK ANY YEAR TO INSPECT):</span>
            <span className="text-[#00e5ff]">ACTIVE RANGE: {startDate} ──► {endDate}</span>
          </div>

          {/* Graphical timeline track */}
          <div className="relative flex items-center justify-between py-3">
            {/* Connecting line */}
            <div className="absolute left-4 right-4 top-1/2 -translate-y-1/2 h-0.5 bg-[#1e293b] z-0"></div>
            {/* Highlighted active range line */}
            <div
              className="absolute top-1/2 -translate-y-1/2 h-0.5 bg-gradient-to-r from-[#00e5ff] to-[#10b981] z-0 transition-all duration-300"
              style={{
                left: `${((startDate - 2020) / 5) * 100}%`,
                width: `${((endDate - startDate) / 5) * 100}%`
              }}
            ></div>

            {availableYears.map((yr) => {
              const isStart = yr === startDate;
              const isEnd = yr === endDate;
              const inRange = yr >= startDate && yr <= endDate;
              const isPreview = activeYearPreview === yr;
              const milestone = historyList.find(h => h.year === yr);

              return (
                <div key={yr} className="relative z-10 flex flex-col items-center group">
                  <button
                    onClick={() => {
                      setActiveYearPreview(yr);
                    }}
                    className={`w-8 h-8 rounded-full border-2 flex items-center justify-center font-mono text-[11px] font-bold transition-all duration-150 ${
                      isStart
                        ? 'bg-[#00e5ff] text-[#070e1b] border-[#00e5ff] shadow-[0_0_12px_rgba(0,229,255,0.6)] scale-110'
                        : isEnd
                        ? 'bg-[#10b981] text-[#070e1b] border-[#10b981] shadow-[0_0_12px_rgba(16,185,129,0.6)] scale-110'
                        : isPreview
                        ? 'bg-[#f59e0b] text-[#070e1b] border-[#f59e0b] scale-110'
                        : inRange
                        ? 'bg-[#0e1f36] text-[#00e5ff] border-[#00e5ff]/60 hover:bg-[#00e5ff]/20'
                        : 'bg-[#0d1726] text-[#64748b] border-[#1e293b] hover:border-[#94a3b8] hover:text-white'
                    }`}
                    title={`${yr}: ${milestone?.label || 'Available in archive'}`}
                  >
                    ●
                  </button>
                  <span className={`font-mono text-[11px] mt-1.5 font-bold transition-colors ${
                    isStart ? 'text-[#00e5ff]' : isEnd ? 'text-[#10b981]' : isPreview ? 'text-[#f59e0b]' : inRange ? 'text-white' : 'text-[#64748b]'
                  }`}>
                    {yr}
                  </span>
                  {milestone && (
                    <span className="hidden md:inline-block font-mono text-[9px] text-[#94a3b8] mt-0.5 tracking-tight text-center max-w-[85px] truncate">
                      {milestone.label}
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* TEMPORAL RESULTS SUMMARY BANNER (When change is detected) */}
      {analysisResult && analysisResult.changeDetected === "YES" && (
        <div className="hud-bracket-tl hud-bracket-br relative bg-[#131122]/90 border border-[#ef4444]/40 rounded-sm p-4 sm:p-5 mb-8 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 shadow-[0_0_24px_rgba(239,68,68,0.12)]">
          <div className="flex items-start sm:items-center gap-3.5">
            <div className="w-10 h-10 rounded-full bg-[#ef4444]/15 border border-[#ef4444]/60 flex items-center justify-center text-[#ef4444] shrink-0 animate-pulse">
              <AlertTriangle className="w-5 h-5" />
            </div>
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <span className="px-2 py-0.5 bg-[#ef4444]/20 border border-[#ef4444]/50 font-mono text-[10px] text-[#ef4444] font-bold uppercase tracking-wider rounded-[2px]">
                  CHANGE DETECTED
                </span>
                <span className="font-mono text-xs font-bold text-white tracking-wide">
                  [{tileData.id}] {startDate} ──► {endDate}
                </span>
                <span className="font-mono text-[11px] text-[#00e5ff]">
                  // {analysisResult.changeType}
                </span>
              </div>
              <div className="flex flex-wrap items-center gap-x-4 gap-y-1 font-mono text-xs text-[#94a3b8] mt-1">
                <span>Confidence: <strong className="text-white">{analysisResult.confidencePercent}%</strong></span>
                <span>First observed: <strong className="text-[#f59e0b]">{analysisResult.firstObservedYear}</strong></span>
                <span>Area Delta: <strong className="text-white">+{analysisResult.changedAreaM2.toLocaleString()} m²</strong></span>
                <span>Status: <strong className="text-[#ef4444]">Needs Review</strong></span>
              </div>
            </div>
          </div>

          <a
            href="#comparison-canvas"
            onClick={(e) => {
              e.preventDefault();
              const el = document.getElementById('comparison-canvas');
              if (el) el.scrollIntoView({ behavior: 'smooth' });
            }}
            className="px-4 py-2 bg-[#ef4444]/15 hover:bg-[#ef4444] border border-[#ef4444] text-[#ef4444] hover:text-[#070e1b] font-mono text-xs font-bold uppercase tracking-wider rounded-sm transition-all duration-150 shrink-0 flex items-center gap-1.5"
          >
            <Eye className="w-3.5 h-3.5" />
            <span>[ VIEW COMPARISON ]</span>
          </a>
        </div>
      )}

      {/* MAIN WORKSPACE: 12-COLUMN GRID (8 COLS VIEWPORT + 4 COLS SIDE PANEL) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 mb-12" id="comparison-canvas">
        
        {/* LEFT COLUMN (8 COLS): LARGE BEFORE / AFTER COMPARISON WORKSPACE */}
        <div className="lg:col-span-8 flex flex-col justify-start">
          <div 
            ref={containerRef}
            className={`hud-bracket-tl hud-bracket-br relative bg-[#0c1424] border border-[#00e5ff]/40 rounded-sm p-4 backdrop-blur-md transition-all ${
              isFullscreen ? 'fixed inset-4 z-50 bg-[#070e1b] overflow-auto' : ''
            }`}
          >
            {/* Top Workspace Controls Strip */}
            <div className="flex flex-wrap items-center justify-between pb-3 mb-3 border-b border-[#1e293b] font-mono text-xs gap-3">
              {/* Date comparison labels */}
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-[#00e5ff]"></span>
                  <span className="text-white font-bold">BEFORE: {startDate}</span>
                </div>
                <span className="text-[#64748b] font-bold">VS</span>
                <div className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-[#10b981]"></span>
                  <span className="text-white font-bold">AFTER: {endDate}</span>
                </div>
              </div>

              {/* View Mode & Zoom/Pan Tools */}
              <div className="flex items-center gap-2">
                {/* View Mode Toggle */}
                <div className="flex items-center bg-[#131f33] border border-[#1e293b] rounded-sm p-0.5">
                  <button
                    onClick={() => setViewMode('slider')}
                    className={`px-2.5 py-1 text-[10px] font-bold uppercase transition-colors rounded-sm ${
                      viewMode === 'slider' ? 'bg-[#00e5ff] text-[#070e1b]' : 'text-[#94a3b8] hover:text-white'
                    }`}
                  >
                    SLIDER
                  </button>
                  <button
                    onClick={() => setViewMode('side-by-side')}
                    className={`px-2.5 py-1 text-[10px] font-bold uppercase transition-colors rounded-sm ${
                      viewMode === 'side-by-side' ? 'bg-[#00e5ff] text-[#070e1b]' : 'text-[#94a3b8] hover:text-white'
                    }`}
                  >
                    SIDE BY SIDE
                  </button>
                </div>

                {/* Zoom buttons */}
                <button
                  onClick={() => setZoomLevel(prev => Math.min(prev + 0.25, 2.5))}
                  className="p-1.5 bg-[#131f33] hover:bg-[#1a2942] border border-[#1e293b] text-[#94a3b8] hover:text-[#00e5ff] rounded-sm transition-colors"
                  title="Zoom In"
                >
                  <ZoomIn className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={() => setZoomLevel(prev => Math.max(prev - 0.25, 0.75))}
                  className="p-1.5 bg-[#131f33] hover:bg-[#1a2942] border border-[#1e293b] text-[#94a3b8] hover:text-[#00e5ff] rounded-sm transition-colors"
                  title="Zoom Out"
                >
                  <ZoomOut className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={() => setZoomLevel(1)}
                  className="p-1.5 bg-[#131f33] hover:bg-[#1a2942] border border-[#1e293b] text-[#94a3b8] hover:text-[#00e5ff] rounded-sm transition-colors"
                  title="Reset Zoom"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                </button>

                {/* Fullscreen Toggle */}
                <button
                  onClick={() => setIsFullscreen(!isFullscreen)}
                  className="p-1.5 bg-[#131f33] hover:bg-[#1a2942] border border-[#1e293b] text-[#94a3b8] hover:text-[#00e5ff] rounded-sm transition-colors"
                  title={isFullscreen ? "Exit Fullscreen" : "Fullscreen"}
                >
                  {isFullscreen ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
                </button>
              </div>
            </div>

            {/* CHANGE MASK CONTROL BAR */}
            <div className="flex flex-wrap items-center justify-between bg-[#08101d] border border-[#1e293b] px-3.5 py-2 mb-3 rounded-sm font-mono text-xs gap-3">
              <div className="flex items-center gap-3">
                <span className="text-[#94a3b8] font-bold text-[11px] uppercase">CHANGE MASK:</span>
                <button
                  onClick={() => setShowMask(!showMask)}
                  className={`px-2.5 py-1 text-[10px] font-bold uppercase rounded-sm border transition-all ${
                    showMask
                      ? 'bg-[#00e5ff] text-[#070e1b] border-[#00e5ff] shadow-[0_0_10px_rgba(0,229,255,0.4)]'
                      : 'bg-[#131f33] text-[#94a3b8] border-[#1e293b] hover:text-white'
                  }`}
                >
                  {showMask ? 'MASK: [ ON ]' : 'MASK: [ OFF ]'}
                </button>
              </div>

              {/* Opacity Slider */}
              <div className="flex items-center gap-3">
                <span className="text-[10px] text-[#64748b] uppercase tracking-wider">
                  MASK OPACITY: <strong className="text-white">{maskOpacity}%</strong>
                </span>
                <input
                  type="range"
                  min="10"
                  max="100"
                  value={maskOpacity}
                  onChange={(e) => setMaskOpacity(Number(e.target.value))}
                  disabled={!showMask}
                  className="w-28 sm:w-36 h-1.5 bg-[#1e293b] rounded-lg appearance-none cursor-pointer accent-[#00e5ff] disabled:opacity-40"
                />
              </div>
            </div>

            {/* VIEWPORT CANVAS (SLIDER OR SIDE-BY-SIDE) */}
            {viewMode === 'slider' ? (
              /* DRAGGABLE COMPARISON SLIDER VIEW */
              <div
                ref={sliderTrackRef}
                onMouseMove={handleMouseMove}
                onMouseUp={handleMouseUp}
                onTouchMove={handleTouchMove}
                className="relative w-full h-[440px] sm:h-[500px] bg-[#070e1b] border border-[#1e293b] overflow-hidden select-none cursor-ew-resize group"
              >
                {/* 1. Base Layer: AFTER Image (Visible underneath on the right) */}
                <div 
                  className="absolute inset-0 w-full h-full"
                  style={{ transform: `scale(${zoomLevel})`, transformOrigin: 'center center' }}
                >
                  {/* High-res military base & terrain synthetic simulation */}
                  <div className="absolute inset-0 bg-gradient-to-br from-[#121c2e] via-[#0b1320] to-[#070e1b]"></div>
                  <div className="absolute inset-0 hud-grid-bg opacity-30"></div>

                  {/* River channel */}
                  <div className="absolute -left-10 top-1/4 w-[120%] h-14 bg-cyan-950/40 border-y border-cyan-500/25 -rotate-12 blur-[0.5px] flex items-center justify-center">
                    <span className="font-mono text-[10px] text-[#00e5ff] tracking-widest opacity-60">
                      {tileData.hydrology?.nearestRiver?.toUpperCase() || "RIPARIAN CHANNEL"} // BUFFER ZONE
                    </span>
                  </div>

                  {/* AFTER (2023): Expanded military encampment & infrastructure */}
                  <div className="absolute top-[28%] left-[30%] w-[38%] h-[32%] border border-[#ef4444]/60 bg-[#ef4444]/10 rounded-sm p-2">
                    <div className="grid grid-cols-4 gap-2 h-full">
                      <div className="bg-[#1e293b] border border-cyan-400/40 rounded-sm flex items-center justify-center font-mono text-[9px] text-[#00e5ff]">HQ</div>
                      <div className="bg-[#1e293b] border border-cyan-400/40 rounded-sm flex items-center justify-center font-mono text-[9px] text-[#00e5ff]">BARRACK</div>
                      <div className="bg-[#1e293b] border border-cyan-400/40 rounded-sm flex items-center justify-center font-mono text-[9px] text-[#00e5ff]">BARRACK</div>
                      <div className="bg-[#1e293b] border border-amber-400/50 rounded-sm flex items-center justify-center font-mono text-[9px] text-[#f59e0b]">RADAR</div>
                      <div className="bg-[#1e293b] border border-emerald-400/50 rounded-sm flex items-center justify-center font-mono text-[9px] text-[#10b981]">SAM</div>
                      <div className="bg-[#1e293b] border border-emerald-400/50 rounded-sm flex items-center justify-center font-mono text-[9px] text-[#10b981]">ARMOR</div>
                      <div className="bg-[#1e293b] border border-emerald-400/50 rounded-sm flex items-center justify-center font-mono text-[9px] text-[#10b981]">ARMOR</div>
                      <div className="bg-[#1e293b] border border-cyan-400/40 rounded-sm flex items-center justify-center font-mono text-[9px] text-[#00e5ff]">DEPOT</div>
                    </div>
                  </div>

                  {/* After label indicator */}
                  <div className="absolute bottom-4 right-4 bg-[#070e1b]/90 border border-[#10b981]/60 px-3 py-1.5 rounded-sm font-mono text-xs">
                    <span className="text-[#10b981] font-bold">AFTER: {endDate}</span>
                    <span className="text-[#94a3b8] text-[10px] ml-2">FORTIFIED BASE DETECTED</span>
                  </div>
                </div>

                {/* 2. Mask Layer: Highlighted change detection heat overlay */}
                {showMask && (
                  <div
                    className="absolute inset-0 pointer-events-none transition-opacity duration-150"
                    style={{
                      opacity: maskOpacity / 100,
                      transform: `scale(${zoomLevel})`,
                      transformOrigin: 'center center'
                    }}
                  >
                    {/* Glowing contour highlighting new structures */}
                    <div className="absolute top-[26%] left-[28%] w-[42%] h-[36%] border-2 border-dashed border-[#ef4444] rounded-sm bg-[#ef4444]/20 shadow-[0_0_30px_rgba(239,68,68,0.5)] animate-pulse flex items-start justify-end p-2">
                      <span className="font-mono text-[10px] bg-[#ef4444] text-white px-2 py-0.5 rounded-[2px] font-bold tracking-wider">
                        DELTA: +4,280 m²
                      </span>
                    </div>
                  </div>
                )}

                {/* 3. Top Layer: BEFORE Image (Clipped by the draggable slider) */}
                <div
                  className="absolute inset-y-0 left-0 overflow-hidden border-r-2 border-[#00e5ff] shadow-[0_0_20px_rgba(0,229,255,0.8)]"
                  style={{ width: `${sliderPos}%` }}
                >
                  <div
                    className="absolute inset-0 w-[1000px] sm:w-[1200px] h-full"
                    style={{ transform: `scale(${zoomLevel})`, transformOrigin: 'center center' }}
                  >
                    {/* Natural undeveloped riverbank in 2020 */}
                    <div className="absolute inset-0 bg-gradient-to-br from-[#0c1a2e] via-[#091424] to-[#070d18]"></div>
                    <div className="absolute inset-0 hud-grid-bg opacity-30"></div>

                    {/* River channel in 2020 */}
                    <div className="absolute -left-10 top-1/4 w-[120%] h-14 bg-cyan-950/40 border-y border-cyan-500/25 -rotate-12 blur-[0.5px]"></div>

                    {/* Pristine natural vegetation / zero structure footprint */}
                    <div className="absolute top-[32%] left-[34%] w-[30%] h-[24%] border border-dashed border-[#64748b]/40 rounded-sm flex items-center justify-center p-3 text-center">
                      <span className="font-mono text-[10px] text-[#64748b] tracking-wider uppercase">
                        UNDEVELOPED ALLUVIAL PLAIN // ZERO MILITARY FOOTPRINT
                      </span>
                    </div>

                    {/* Before label indicator */}
                    <div className="absolute bottom-4 left-4 bg-[#070e1b]/90 border border-[#00e5ff]/60 px-3 py-1.5 rounded-sm font-mono text-xs">
                      <span className="text-[#00e5ff] font-bold">BEFORE: {startDate}</span>
                      <span className="text-[#94a3b8] text-[10px] ml-2">PRISTINE RIVERBANK</span>
                    </div>
                  </div>
                </div>

                {/* 4. Draggable Slider Handle */}
                <div
                  onMouseDown={handleMouseDown}
                  className="absolute top-0 bottom-0 -translate-x-1/2 z-30 cursor-ew-resize flex flex-col items-center justify-center"
                  style={{ left: `${sliderPos}%` }}
                >
                  <div className="w-8 h-8 rounded-full bg-[#00e5ff] border-2 border-white flex items-center justify-center text-[#070e1b] shadow-[0_0_16px_rgba(0,229,255,0.9)] cursor-grab active:cursor-grabbing hover:scale-110 transition-transform">
                    <ArrowLeftRight className="w-4 h-4" />
                  </div>
                  <div className="px-2 py-0.5 bg-[#070e1b] border border-[#00e5ff] rounded font-mono text-[9px] text-[#00e5ff] font-bold uppercase mt-2 tracking-wider">
                    {sliderPos}%
                  </div>
                </div>
              </div>
            ) : (
              /* SIDE BY SIDE COMPARISON VIEW */
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Before Frame */}
                <div className="relative h-[360px] sm:h-[440px] bg-[#0c1424] border border-[#00e5ff]/40 rounded-sm overflow-hidden p-3">
                  <div className="font-mono text-xs font-bold text-[#00e5ff] pb-2 mb-2 border-b border-[#1e293b] flex items-center justify-between">
                    <span>BEFORE: {startDate} (BASELINE)</span>
                    <span className="text-[#64748b]">PRISTINE</span>
                  </div>
                  <div className="relative w-full h-[calc(100%-36px)] bg-[#070d18] flex items-center justify-center border border-[#1e293b]">
                    <div className="absolute inset-0 hud-grid-bg opacity-30"></div>
                    <div className="w-3/4 h-12 bg-cyan-950/40 border-y border-cyan-500/20 -rotate-12 blur-[0.5px]"></div>
                    <div className="font-mono text-[11px] text-[#64748b] text-center p-4">
                      NATURAL ALLUVIAL RIVERBANK<br />ZERO DETECTED STRUCTURES
                    </div>
                  </div>
                </div>

                {/* After Frame */}
                <div className="relative h-[360px] sm:h-[440px] bg-[#0c1424] border border-[#10b981]/40 rounded-sm overflow-hidden p-3">
                  <div className="font-mono text-xs font-bold text-[#10b981] pb-2 mb-2 border-b border-[#1e293b] flex items-center justify-between">
                    <span>AFTER: {endDate} (CURRENT)</span>
                    <span className="text-[#ef4444]">NEW STRUCTURES</span>
                  </div>
                  <div className="relative w-full h-[calc(100%-36px)] bg-[#09111e] flex items-center justify-center border border-[#1e293b]">
                    <div className="absolute inset-0 hud-grid-bg opacity-30"></div>
                    {/* Structure bounding highlight */}
                    <div className="w-3/5 h-2/5 border-2 border-[#ef4444] bg-[#ef4444]/20 rounded-sm p-2 flex flex-col justify-between">
                      <span className="font-mono text-[9px] text-[#ef4444] font-bold">MILITARY FORTIFICATION</span>
                      <span className="font-mono text-[10px] text-white font-bold text-right">+4,280 m²</span>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Bottom Wiper Status Footer */}
            <div className="flex flex-wrap items-center justify-between pt-3 mt-3 border-t border-[#1e293b] font-mono text-[11px] text-[#94a3b8] gap-2">
              <div className="flex items-center gap-2">
                <Compass className="w-3.5 h-3.5 text-[#00e5ff]" />
                <span>GSD: 10 m/pixel</span>
                <span>•</span>
                <span>REGISTRATION: 0.12 px RMS</span>
              </div>
              <div className="flex items-center gap-2 text-[#00e5ff]">
                <span>DRAG SLIDER LEFT/RIGHT TO INSPECT HISTORICAL TRANSITION</span>
              </div>
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN (4 COLS): CHANGE ANALYSIS SIDE PANEL */}
        <div className="lg:col-span-4 flex flex-col gap-6">
          {/* Main Analysis Card */}
          <div className="hud-bracket-tl hud-bracket-br relative bg-[#0c1424] border border-[#1e293b] rounded-sm p-5 shadow-lg">
            <div className="flex items-center justify-between pb-3 mb-4 border-b border-[#1e293b]">
              <h3 className="font-mono text-[13px] font-bold text-white uppercase tracking-wider flex items-center gap-2">
                <Activity className="w-4 h-4 text-[#00e5ff]" />
                TEMPORAL ANALYSIS
              </h3>
              <span className="font-mono text-[10px] px-2 py-0.5 bg-[#10b981]/20 border border-[#10b981]/40 text-[#10b981] font-bold rounded-[2px]">
                {analysisResult?.qaStatus || "✓ VALID CHANGE"}
              </span>
            </div>

            {/* Analysis Metrics Grid */}
            <div className="space-y-3 font-mono text-xs">
              <div className="flex items-center justify-between py-1.5 border-b border-[#1e293b]/60">
                <span className="text-[#64748b]">Location:</span>
                <span className="text-white font-bold">{tileData.id} ({tileData.coordinates.formatted})</span>
              </div>

              <div className="flex items-center justify-between py-1.5 border-b border-[#1e293b]/60">
                <span className="text-[#64748b]">Before:</span>
                <span className="text-[#00e5ff] font-bold">{startDate}</span>
              </div>

              <div className="flex items-center justify-between py-1.5 border-b border-[#1e293b]/60">
                <span className="text-[#64748b]">After:</span>
                <span className="text-[#10b981] font-bold">{endDate}</span>
              </div>

              <div className="flex items-center justify-between py-1.5 border-b border-[#1e293b]/60">
                <span className="text-[#64748b]">Change Detected:</span>
                <span className={`font-bold px-2 py-0.5 rounded text-[11px] ${
                  analysisResult?.changeDetected === 'YES' ? 'bg-[#ef4444]/20 text-[#ef4444]' : 'bg-[#10b981]/20 text-[#10b981]'
                }`}>
                  {analysisResult?.changeDetected || "YES"}
                </span>
              </div>

              <div className="flex items-center justify-between py-1.5 border-b border-[#1e293b]/60">
                <span className="text-[#64748b]">Change Type:</span>
                <span className="text-[#f59e0b] font-bold text-right">
                  {analysisResult?.changeType || "NEW STRUCTURE"}
                </span>
              </div>

              <div className="flex items-center justify-between py-1.5 border-b border-[#1e293b]/60">
                <span className="text-[#64748b]">Confidence:</span>
                <span className="text-white font-bold text-sm">
                  {analysisResult?.confidencePercent || 91.4}%
                </span>
              </div>

              <div className="flex items-center justify-between py-1.5 border-b border-[#1e293b]/60">
                <span className="text-[#64748b]">Changed Area:</span>
                <span className="text-white font-bold">
                  {(analysisResult?.changedAreaM2 || 4280).toLocaleString()} m²
                </span>
              </div>

              <div className="flex items-center justify-between py-1.5">
                <span className="text-[#64748b]">QA Status:</span>
                <span className="text-[#10b981] font-bold flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  {analysisResult?.qaStatus || "✓ VALID CHANGE"}
                </span>
              </div>
            </div>

            {/* Quick Context Summary */}
            <div className="mt-5 p-3 bg-[#131f33] border border-[#1e293b] rounded-sm font-sans text-xs text-[#94a3b8] leading-relaxed">
              <p className="font-mono text-[10px] text-[#00e5ff] uppercase font-bold mb-1">
                TACTICAL ASSESSMENT:
              </p>
              Automated pixel subtraction identifies a confirmed conversion from undeveloped riverbank in <strong>{startDate}</strong> into a fortified base facility by <strong>{endDate}</strong> within 350 meters of the riparian boundary.
            </div>
          </div>

          {/* GEOSPATIAL MARKER STATES & MAP LEGEND CARD */}
          <div className="bg-[#0c1424] border border-[#1e293b] rounded-sm p-5 shadow-lg">
            <h4 className="font-mono text-xs font-bold text-white uppercase tracking-wider mb-3 pb-2 border-b border-[#1e293b] flex items-center gap-2">
              <MapPin className="w-3.5 h-3.5 text-[#00e5ff]" />
              GEOSPATIAL MARKER STATES
            </h4>

            {/* Marker State Legend */}
            <div className="space-y-2.5 font-mono text-xs mb-4">
              {MARKER_TYPES.map(m => (
                <div key={m.id} className="flex items-center justify-between text-[#94a3b8]">
                  <div className="flex items-center gap-2">
                    <span className={`w-2.5 h-2.5 rounded-full ${m.dotClass}`}></span>
                    <span>{m.label}</span>
                  </div>
                  <span className="text-[10px] text-[#64748b]">{m.id.toUpperCase()}</span>
                </div>
              ))}
            </div>

            {/* Interactive Change Marker Simulator */}
            <div className="bg-[#131f33] border border-[#1e293b] p-3 rounded-sm">
              <div className="flex items-center justify-between mb-2">
                <span className="font-mono text-[10px] text-[#64748b] uppercase">CLICK TO INSPECT MARKER:</span>
                <span className="font-mono text-[10px] text-[#ef4444] font-bold">● ACTIVE</span>
              </div>
              <div 
                onClick={() => setActiveMarkerPopover(activeMarkerPopover ? null : tileData)}
                className="cursor-pointer bg-[#0d1726] border border-[#ef4444]/60 hover:border-[#ef4444] p-2.5 rounded-sm transition-all flex items-center justify-between group"
              >
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-[#ef4444] animate-pulse"></span>
                  <span className="font-mono text-xs font-bold text-white group-hover:text-[#00e5ff]">
                    [{tileData.id}] HIGH-CONFIDENCE CHANGE
                  </span>
                </div>
                <ChevronRight className="w-4 h-4 text-[#64748b] group-hover:text-[#00e5ff] transition-colors" />
              </div>

              {/* Marker Popover Dialog */}
              {activeMarkerPopover && (
                <div className="mt-3 p-3 bg-[#070e1b] border border-[#00e5ff]/50 rounded-sm font-mono text-xs space-y-2 shadow-xl animate-in fade-in duration-200">
                  <div className="text-white font-bold">{tileData.id}</div>
                  <div className="text-[#ef4444] font-bold text-[11px]">CHANGE DETECTED</div>
                  <div className="text-[#94a3b8] text-[11px]">{startDate} ──► {endDate}</div>
                  <div className="text-white font-bold">Confidence: {analysisResult?.confidencePercent || 91.4}%</div>
                  <button
                    onClick={() => {
                      const el = document.getElementById('comparison-canvas');
                      if (el) el.scrollIntoView({ behavior: 'smooth' });
                    }}
                    className="w-full mt-2 py-1.5 bg-[#00e5ff] text-[#070e1b] font-bold text-[10px] uppercase rounded-sm text-center shadow-[0_0_10px_rgba(0,229,255,0.4)]"
                  >
                    [ OPEN TEMPORAL ANALYSIS ]
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* MULTI-YEAR COMPARISON & PROGRESSION TIMELINE */}
      <div className="bg-[#0c1424] border border-[#1e293b] rounded-sm p-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 mb-6 border-b border-[#1e293b] gap-2">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Clock className="w-4 h-4 text-[#00e5ff]" />
              <h3 className="font-mono text-[14px] font-bold text-white uppercase tracking-wider">
                MULTI-YEAR PROGRESSION TIMELINE // 2020 ──► 2025
              </h3>
            </div>
            <p className="text-[12px] text-[#94a3b8] font-sans">
              Sequential satellite timeline revealing exactly when ground alterations first emerged and expanded.
            </p>
          </div>
          <div className="font-mono text-xs text-[#00e5ff] px-3 py-1 bg-[#131f33] border border-[#00e5ff]/30 rounded-sm">
            FIRST OBSERVED: {analysisResult?.firstObservedYear || 2022}
          </div>
        </div>

        {/* Multi-Year Cards Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          {historyList.map((item, idx) => {
            const isSelected = (item.year === startDate || item.year === endDate || activeYearPreview === item.year);
            const isChangeDetected = item.detectedChange;

            return (
              <div
                key={item.year}
                onClick={() => {
                  setActiveYearPreview(item.year);
                  setEndDate(item.year);
                  loadAnalysis(selectedTileId, startDate, item.year);
                }}
                className={`cursor-pointer rounded-sm p-3.5 border transition-all duration-200 flex flex-col justify-between min-h-[170px] ${
                  isSelected
                    ? 'bg-[#131f33] border-[#00e5ff] shadow-[0_0_15px_rgba(0,229,255,0.25)]'
                    : isChangeDetected
                    ? 'bg-[#0d1726] border-[#ef4444]/40 hover:border-[#ef4444]'
                    : 'bg-[#0d1726] border-[#1e293b] hover:border-[#64748b]'
                }`}
              >
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-mono text-[15px] font-bold text-white">{item.year}</span>
                    <span className={`w-2 h-2 rounded-full ${
                      isChangeDetected ? 'bg-[#ef4444] animate-pulse' : 'bg-[#64748b]'
                    }`}></span>
                  </div>
                  
                  <div className={`font-mono text-[10px] font-bold uppercase mb-1.5 ${
                    isChangeDetected ? 'text-[#ef4444]' : 'text-[#64748b]'
                  }`}>
                    {item.label}
                  </div>

                  <p className="text-[11px] text-[#94a3b8] leading-tight line-clamp-3">
                    {item.description}
                  </p>
                </div>

                <div className="pt-3 mt-3 border-t border-[#1e293b] flex items-center justify-between font-mono text-[9px]">
                  <span className="text-[#64748b]">Structures:</span>
                  <span className={item.structuresCount > 0 ? "text-white font-bold" : "text-[#64748b]"}>
                    {item.structuresCount}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
