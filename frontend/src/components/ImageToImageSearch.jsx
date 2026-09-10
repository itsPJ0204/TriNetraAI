import React, { useState, useRef } from 'react';
import { UploadCloud, Image as ImageIcon, CheckCircle2, Trash2, RefreshCw, Eye, SlidersHorizontal, Sparkles } from 'lucide-react';

const SIMILAR_MOCK_RESULTS = [
  {
    id: "T027",
    similarity: 94,
    sensor: "Sentinel-2 MSI",
    resolution: "10 m",
    date: "14 JUN 2023",
    coordinates: "22.57° N, 88.36° E",
    detected: "18 Camps, 4 Tanks",
    previewBg: "from-[#102438] to-[#0a1524]"
  },
  {
    id: "T041",
    similarity: 89,
    sensor: "Cartosat-3 PAN",
    resolution: "0.25 m",
    date: "08 MAY 2023",
    coordinates: "34.15° N, 77.58° E",
    detected: "Fortified Staging, Revetments",
    previewBg: "from-[#1f2937] to-[#111827]"
  },
  {
    id: "T063",
    similarity: 85,
    sensor: "RISAT-2BR1 SAR",
    resolution: "0.35 m",
    date: "22 SEP 2022",
    coordinates: "27.58° N, 91.86° E",
    detected: "Reinforced Apron, Revetment",
    previewBg: "from-[#172554] to-[#0f172a]"
  },
  {
    id: "T091",
    similarity: 81,
    sensor: "Oceansat-3 VNIR",
    resolution: "360 m",
    date: "18 FEB 2023",
    coordinates: "23.75° N, 68.15° E",
    detected: "Riparian Embankment & Jetty",
    previewBg: "from-[#134e4a] to-[#042f2e]"
  }
];

export default function ImageToImageSearch({ onSelectTile }) {
  const [imageFile, setImageFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [imageMeta, setImageMeta] = useState(null);
  const [processingStep, setProcessingStep] = useState(0); // 0: idle, 1..4: steps
  const [isSearching, setIsSearching] = useState(false);
  const [results, setResults] = useState(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef(null);

  const handleFile = (file) => {
    if (!file || !file.type.startsWith('image/')) return;

    const url = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => {
      setImageMeta({
        name: file.name,
        size: (file.size / 1024).toFixed(1) + " KB",
        width: img.width,
        height: img.height,
        type: file.type
      });
      setPreviewUrl(url);
      setImageFile(file);
      setResults(null);
      setProcessingStep(0);
    };
    img.src = url;
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const handleSampleSelect = (sampleType) => {
    // Generate an illustrative synthetic canvas pattern for quick sample selection
    const canvas = document.createElement('canvas');
    canvas.width = 512;
    canvas.height = 512;
    const ctx = canvas.getContext('2d');
    
    // Background terrain
    ctx.fillStyle = sampleType === 'camps' ? '#18293d' : sampleType === 'outpost' ? '#272d38' : '#142233';
    ctx.fillRect(0, 0, 512, 512);

    // River / road
    ctx.strokeStyle = '#00e5ff';
    ctx.lineWidth = 12;
    ctx.beginPath();
    ctx.moveTo(0, 150);
    ctx.bezierCurveTo(180, 220, 320, 100, 512, 300);
    ctx.stroke();

    // Structures
    ctx.fillStyle = '#f59e0b';
    for (let i = 0; i < 8; i++) {
      ctx.fillRect(100 + (i % 4) * 50, 260 + Math.floor(i / 4) * 60, 32, 24);
    }

    const url = canvas.toDataURL('image/png');
    setPreviewUrl(url);
    setImageMeta({
      name: `MIL_RECON_${sampleType.toUpperCase()}_SURV.PNG`,
      size: "184.2 KB",
      width: 512,
      height: 512,
      type: "image/png"
    });
    setImageFile({ name: `MIL_RECON_${sampleType.toUpperCase()}_SURV.PNG` });
    setResults(null);
    setProcessingStep(0);
  };

  const handleSearch = () => {
    if (!previewUrl) return;

    setIsSearching(true);
    setResults(null);
    setProcessingStep(1);

    // Progressive 4-step workflow animation
    setTimeout(() => setProcessingStep(2), 300);
    setTimeout(() => setProcessingStep(3), 650);
    setTimeout(() => {
      setProcessingStep(4);
      setResults(SIMILAR_MOCK_RESULTS);
      setIsSearching(false);
    }, 1000);
  };

  const handleReset = () => {
    setImageFile(null);
    setPreviewUrl(null);
    setImageMeta(null);
    setResults(null);
    setProcessingStep(0);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleViewTile = (tileId) => {
    if (onSelectTile) onSelectTile(tileId);
    const el = document.getElementById('image-viewer');
    if (el) el.scrollIntoView({ behavior: 'smooth' });
  };

  const handleAnalyze = (tileId) => {
    if (onSelectTile) onSelectTile(tileId);
    const el = document.getElementById('change-wiper');
    if (el) el.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <section className="w-full py-16 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto border-b border-[#1e293b]/40" id="image-search">
      {/* Section Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-8 pb-3 border-b border-[#1e293b]">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="w-2 h-2 bg-[#00e5ff]"></span>
            <span className="font-mono text-[10px] text-[#00e5ff] uppercase tracking-widest font-semibold">
              MODULE // 06
            </span>
          </div>
          <h2 className="text-[28px] sm:text-[34px] font-bold text-white tracking-tight">
            Image-to-Image Satellite Search
          </h2>
          <p className="text-[14px] text-[#94a3b8] mt-1">
            Reverse visual search across 68,920 air-gapped satellite tiles using multimodal feature embeddings and FAISS nearest-neighbor matching.
          </p>
        </div>

        {/* Quick Sample Selector */}
        <div className="flex items-center gap-2">
          <span className="font-mono text-[10px] text-[#64748b] uppercase">TEST SAMPLES:</span>
          <button
            type="button"
            onClick={() => handleSampleSelect('camps')}
            className="px-2.5 py-1 bg-[#131f33] hover:bg-[#1a2942] border border-[#1e293b] text-[#94a3b8] hover:text-[#00e5ff] font-mono text-[10px] rounded-sm transition-colors cursor-pointer"
          >
            Encampment
          </button>
          <button
            type="button"
            onClick={() => handleSampleSelect('outpost')}
            className="px-2.5 py-1 bg-[#131f33] hover:bg-[#1a2942] border border-[#1e293b] text-[#94a3b8] hover:text-[#00e5ff] font-mono text-[10px] rounded-sm transition-colors cursor-pointer"
          >
            Mountain Outpost
          </button>
          <button
            type="button"
            onClick={() => handleSampleSelect('runway')}
            className="px-2.5 py-1 bg-[#131f33] hover:bg-[#1a2942] border border-[#1e293b] text-[#94a3b8] hover:text-[#00e5ff] font-mono text-[10px] rounded-sm transition-colors cursor-pointer"
          >
            Runway Apron
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Upload & Preview Zone (Left 5 Cols) */}
        <div className="lg:col-span-5 flex flex-col justify-between">
          {!previewUrl ? (
            /* Drag & Drop Upload Target */
            <div
              onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
              onDragLeave={() => setIsDragOver(false)}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`hud-bracket-tl hud-bracket-br relative border-2 border-dashed rounded-sm p-8 flex flex-col items-center justify-center text-center cursor-pointer transition-all duration-200 min-h-[320px] ${
                isDragOver
                  ? 'border-[#00e5ff] bg-[#00e5ff]/10 shadow-[0_0_24px_rgba(0,229,255,0.2)]'
                  : 'border-[#1e293b] hover:border-[#00e5ff]/50 bg-[#0d1726]/60'
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                className="hidden"
                onChange={(e) => {
                  if (e.target.files && e.target.files[0]) handleFile(e.target.files[0]);
                }}
              />
              <div className="w-14 h-14 rounded-full bg-[#131f33] border border-[#00e5ff]/40 flex items-center justify-center mb-4 text-[#00e5ff]">
                <UploadCloud className="w-7 h-7" />
              </div>
              <div className="font-mono text-[13px] font-bold text-white uppercase tracking-wider mb-1">
                DROP SATELLITE IMAGE
              </div>
              <div className="text-[12px] text-[#00e5ff] font-mono mb-3">
                + UPLOAD IMAGE
              </div>
              <p className="font-mono text-[11px] text-[#64748b] max-w-xs">
                Supports GeoTIFF, PNG, JPG, or multispectral PNG tiles. Air-gapped feature extraction executed locally.
              </p>
            </div>
          ) : (
            /* Uploaded Preview & Metadata Card */
            <div className="hud-bracket-tl hud-bracket-br relative bg-[#0d1726] border border-[#00e5ff]/40 p-4 rounded-sm">
              <div className="flex items-center justify-between pb-2 mb-3 border-b border-[#1e293b] font-mono text-[11px]">
                <span className="text-[#00e5ff] font-bold uppercase">UPLOADED QUERY TILE</span>
                <span className="text-[#10b981] font-semibold">LOADED READY</span>
              </div>

              {/* Preview Box */}
              <div className="relative w-full h-[230px] bg-[#070e1b] border border-[#1e293b] rounded-sm overflow-hidden flex items-center justify-center mb-3">
                <img
                  src={previewUrl}
                  alt="Query Satellite Preview"
                  className="w-full h-full object-contain filter contrast-105"
                />
                <div className="absolute inset-0 hud-grid-bg opacity-30 pointer-events-none"></div>
                <div className="absolute bottom-2 left-2 px-2 py-0.5 bg-[#070e1b]/90 border border-[#1e293b] font-mono text-[10px] text-[#00e5ff]">
                  QUERY VECTOR
                </div>
              </div>

              {/* Metadata Details */}
              <div className="space-y-1.5 font-mono text-[11px] text-[#94a3b8] mb-4">
                <div className="flex justify-between">
                  <span className="text-[#64748b]">FILENAME:</span>
                  <span className="text-white font-semibold truncate max-w-[200px]" title={imageMeta?.name}>
                    {imageMeta?.name}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#64748b]">DIMENSIONS:</span>
                  <span className="text-[#9cf0ff]">{imageMeta?.width} × {imageMeta?.height} PX</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#64748b]">FILE SIZE:</span>
                  <span className="text-white">{imageMeta?.size}</span>
                </div>
              </div>

              {/* Action Buttons: Remove & Replace */}
              <div className="flex items-center gap-2 pt-2 border-t border-[#1e293b]">
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="flex-1 py-1.5 bg-[#131f33] hover:bg-[#1a2942] border border-[#1e293b] text-[#e2e8f0] font-mono text-[11px] font-semibold rounded-sm transition-colors flex items-center justify-center gap-1.5 cursor-pointer"
                >
                  <RefreshCw className="w-3.5 h-3.5 text-[#00e5ff]" />
                  REPLACE IMAGE
                </button>
                <button
                  type="button"
                  onClick={handleReset}
                  className="px-3 py-1.5 bg-[#93000a]/20 hover:bg-[#93000a]/40 border border-[#ef4444] text-[#ffb4ab] font-mono text-[11px] rounded-sm transition-colors flex items-center justify-center gap-1 cursor-pointer"
                  title="Remove Image"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          )}

          {/* Primary Trigger Button */}
          <button
            type="button"
            disabled={!previewUrl || isSearching}
            onClick={handleSearch}
            className={`w-full mt-4 py-3 font-mono text-[12px] font-bold tracking-widest uppercase transition-all rounded-sm flex items-center justify-center gap-2 cursor-pointer shadow-[0_0_15px_rgba(0,229,255,0.2)] ${
              previewUrl && !isSearching
                ? 'bg-[#00e5ff] hover:bg-[#9cf0ff] text-[#070e1b]'
                : 'bg-[#131f33] text-[#64748b] border border-[#1e293b] cursor-not-allowed opacity-60'
            }`}
          >
            <Sparkles className="w-4 h-4" />
            {isSearching ? "[ EXTRACTING EMBEDDINGS... ]" : "[ SEARCH SIMILAR TILES ]"}
          </button>
        </div>

        {/* Processing Stepper & Results Feed (Right 7 Cols) */}
        <div className="lg:col-span-7 flex flex-col justify-between">
          {/* Processing Status Stepper */}
          <div className="bg-[#0d1726] border border-[#1e293b] p-4 rounded-sm mb-6">
            <div className="flex items-center justify-between pb-2 mb-3 border-b border-[#1e293b] font-mono text-[11px]">
              <span className="text-[#64748b] uppercase font-bold">EMBEDDING PIPELINE TELEMETRY</span>
              <span className="text-[#00e5ff]">FAISS INDEX STATUS: ACTIVE</span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 font-mono text-[11px]">
              <div className={`p-2 border rounded-sm transition-colors ${
                processingStep >= 1 ? 'bg-[#00e5ff]/15 border-[#00e5ff] text-[#00e5ff]' : 'bg-[#070e1b] border-[#1e293b] text-[#64748b]'
              }`}>
                <div className="flex items-center justify-between">
                  <span>IMAGE LOADED</span>
                  {processingStep >= 1 && <CheckCircle2 className="w-3.5 h-3.5 text-[#10b981]" />}
                </div>
              </div>

              <div className={`p-2 border rounded-sm transition-colors ${
                processingStep >= 2 ? 'bg-[#00e5ff]/15 border-[#00e5ff] text-[#00e5ff]' : 'bg-[#070e1b] border-[#1e293b] text-[#64748b]'
              }`}>
                <div className="flex items-center justify-between">
                  <span>EMBEDDING</span>
                  {processingStep >= 2 && <CheckCircle2 className="w-3.5 h-3.5 text-[#10b981]" />}
                </div>
              </div>

              <div className={`p-2 border rounded-sm transition-colors ${
                processingStep >= 3 ? 'bg-[#00e5ff]/15 border-[#00e5ff] text-[#00e5ff]' : 'bg-[#070e1b] border-[#1e293b] text-[#64748b]'
              }`}>
                <div className="flex items-center justify-between">
                  <span>VECTOR SEARCH</span>
                  {processingStep >= 3 && <CheckCircle2 className="w-3.5 h-3.5 text-[#10b981]" />}
                </div>
              </div>

              <div className={`p-2 border rounded-sm transition-colors ${
                processingStep >= 4 ? 'bg-[#10b981]/15 border-[#10b981] text-[#10b981]' : 'bg-[#070e1b] border-[#1e293b] text-[#64748b]'
              }`}>
                <div className="flex items-center justify-between">
                  <span>TILES FOUND</span>
                  {processingStep >= 4 && <CheckCircle2 className="w-3.5 h-3.5 text-[#10b981]" />}
                </div>
              </div>
            </div>
          </div>

          {/* Ranked Results Cards */}
          {results ? (
            <div className="space-y-3">
              <div className="flex items-center justify-between font-mono text-[11px] text-[#64748b]">
                <span>TOP RANKED NEAREST-NEIGHBOR TILES (COSINE METRIC):</span>
                <span className="text-[#00e5ff] font-bold">4 CANDIDATES RESOLVED</span>
              </div>

              <div className="space-y-2.5">
                {results.map((tile) => (
                  <div
                    key={tile.id}
                    className="p-3 bg-[#0d1726]/90 hover:bg-[#131f33] border border-[#1e293b] hover:border-[#00e5ff]/50 rounded-sm transition-all flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 font-mono"
                  >
                    {/* Left: Tile Badge & Similarity */}
                    <div className="flex items-center gap-3">
                      <div className="w-12 h-12 bg-gradient-to-br from-[#131f33] to-[#070e1b] border border-[#00e5ff]/40 flex flex-col items-center justify-center text-center rounded-sm">
                        <span className="text-[10px] text-[#64748b]">TILE</span>
                        <span className="text-[12px] font-bold text-[#00e5ff]">{tile.id}</span>
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-[14px] font-bold text-white">{tile.id}</span>
                          <span className="text-[#00e5ff] font-bold text-[13px]">— {tile.similarity}% MATCH</span>
                          <span className="px-1.5 py-0.2 bg-[#1a2942] text-[#9cf0ff] text-[9px] rounded-sm">
                            {tile.sensor}
                          </span>
                        </div>
                        <div className="text-[11px] text-[#94a3b8] mt-0.5">
                          LOC: {tile.coordinates} • DATE: {tile.date}
                        </div>
                        <div className="text-[10px] text-[#10b981] mt-0.5">
                          FEATURES: {tile.detected}
                        </div>
                      </div>
                    </div>

                    {/* Right Action Buttons */}
                    <div className="flex items-center gap-2 self-end sm:self-center">
                      <button
                        type="button"
                        onClick={() => handleViewTile(tile.id)}
                        className="px-3 py-1.5 bg-[#131f33] hover:bg-[#00e5ff] hover:text-[#070e1b] border border-[#00e5ff]/40 text-[#00e5ff] text-[10px] font-bold uppercase rounded-sm transition-colors flex items-center gap-1 cursor-pointer"
                      >
                        <Eye className="w-3 h-3" />
                        [ VIEW TILE ]
                      </button>
                      <button
                        type="button"
                        onClick={() => handleAnalyze(tile.id)}
                        className="px-3 py-1.5 bg-[#00e5ff] hover:bg-[#9cf0ff] text-[#070e1b] text-[10px] font-bold uppercase rounded-sm transition-colors flex items-center gap-1 cursor-pointer"
                      >
                        <SlidersHorizontal className="w-3 h-3" />
                        [ ANALYZE ]
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            /* Empty State Prompt */
            <div className="bg-[#0d1726]/40 border border-[#1e293b] border-dashed rounded-sm p-8 text-center flex flex-col items-center justify-center my-auto min-h-[220px]">
              <ImageIcon className="w-10 h-10 text-[#64748b] mb-2" />
              <div className="font-mono text-[12px] text-white font-bold uppercase mb-1">
                AWAITING SATELLITE IMAGE QUERY
              </div>
              <p className="font-mono text-[11px] text-[#64748b] max-w-sm">
                Upload a reconnaissance tile or select a test sample above, then press [ SEARCH SIMILAR TILES ] to execute offline embedding similarity retrieval.
              </p>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
