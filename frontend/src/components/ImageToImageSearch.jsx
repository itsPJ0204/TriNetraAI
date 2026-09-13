import React, { useState, useRef, useEffect } from 'react';
import { getSearchFilters } from '../services/api';
import { UploadCloud, Image as ImageIcon, CheckCircle2, Trash2, RefreshCw, Eye, SlidersHorizontal, Sparkles, MessageSquare, AlertCircle } from 'lucide-react';
import { searchByImage } from '../services/api';

export default function ImageToImageSearch({ onSelectTile, onSearchResults }) {
  const [imageFile, setImageFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [imageMeta, setImageMeta] = useState(null);
  const [searchPrompt, setSearchPrompt] = useState("");
  const [processingStep, setProcessingStep] = useState(0);
  const [isSearching, setIsSearching] = useState(false);
  const [results, setResults] = useState(null);
  const [errorMessage, setErrorMessage] = useState(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [availableFilters, setAvailableFilters] = useState({ aoi: [], satellites: [], years: [] });
  const [selectedFilters, setSelectedFilters] = useState({ aoi: "", satellite: "", year: "" });
  const fileInputRef = useRef(null);

  useEffect(() => {
    getSearchFilters().then(data => setAvailableFilters(data));
  }, []);

  const handleFile = (file) => {
    if (!file) return;
    const isImageOrTiff = file.type.startsWith('image/') || /\.(tif|tiff|geotiff|png|jpe?g|webp|bmp)$/i.test(file.name);
    if (!isImageOrTiff) {
      setErrorMessage("Please upload a valid satellite image or GeoTIFF file (.tif, .tiff, .png, .jpg).");
      return;
    }

    setErrorMessage(null);
    const isTiff = /\.(tif|tiff|geotiff)$/i.test(file.name) || file.type.includes('tiff');

    if (isTiff) {
      const canvas = document.createElement('canvas');
      canvas.width = 300;
      canvas.height = 300;
      const ctx = canvas.getContext('2d');
      ctx.fillStyle = '#061a38';
      ctx.fillRect(0, 0, 300, 300);

      ctx.strokeStyle = '#00e5ff';
      ctx.lineWidth = 2;
      ctx.strokeRect(20, 20, 260, 260);

      ctx.fillStyle = '#00e5ff';
      ctx.font = 'bold 13px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText('GEOTIFF SATELLITE RASTER', 150, 130);

      ctx.fillStyle = '#94a3b8';
      ctx.font = '11px sans-serif';
      const displayName = file.name.length > 25 ? file.name.substring(0, 22) + '...' : file.name;
      ctx.fillText(displayName, 150, 155);

      ctx.fillStyle = '#10b981';
      ctx.font = '10px monospace';
      ctx.fillText(`Size: ${(file.size / 1024).toFixed(1)} KB (Multiband)`, 150, 180);

      const url = canvas.toDataURL('image/png');
      setImageMeta({
        name: file.name,
        size: (file.size / 1024).toFixed(1) + " KB",
        width: 256,
        height: 256,
        type: file.type || "image/tiff"
      });
      setPreviewUrl(url);
      setImageFile(file);
      setResults(null);
      setProcessingStep(0);
    } else {
      const url = URL.createObjectURL(file);
      const img = new Image();
      img.onload = () => {
        setImageMeta({
          name: file.name,
          size: (file.size / 1024).toFixed(1) + " KB",
          width: img.width,
          height: img.height,
          type: file.type || "image/png"
        });
        setPreviewUrl(url);
        setImageFile(file);
        setResults(null);
        setProcessingStep(0);
      };
      img.onerror = () => {
        setImageMeta({
          name: file.name,
          size: (file.size / 1024).toFixed(1) + " KB",
          width: 256,
          height: 256,
          type: file.type || "image/png"
        });
        setPreviewUrl(url);
        setImageFile(file);
        setResults(null);
        setProcessingStep(0);
      };
      img.src = url;
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const handleSearch = async () => {
    if (!imageFile && !previewUrl && !searchPrompt.trim()) return;

    setIsSearching(true);
    setErrorMessage(null);
    setResults(null);
    setProcessingStep(1);

    const timer2 = setTimeout(() => setProcessingStep(2), 200);
    const timer3 = setTimeout(() => setProcessingStep(3), 450);

    try {
      let fileToSend = imageFile;
      if (!fileToSend && previewUrl && previewUrl.startsWith('data:')) {
        const fetchRes = await fetch(previewUrl);
        const blob = await fetchRes.blob();
        fileToSend = new File([blob], imageMeta?.name || "query_image.png", { type: blob.type || "image/png" });
      }

      if (!fileToSend && previewUrl && previewUrl.startsWith('/')) {
        const fetchRes = await fetch(previewUrl);
        const blob = await fetchRes.blob();
        fileToSend = new File([blob], imageMeta?.name || "query_image.jpg", { type: "image/jpeg" });
      }

      if (!fileToSend && searchPrompt.trim()) {
        const canvas = document.createElement('canvas');
        canvas.width = 256;
        canvas.height = 256;
        const ctx = canvas.getContext('2d');
        ctx.fillStyle = '#061a38';
        ctx.fillRect(0, 0, 256, 256);
        const dataUrl = canvas.toDataURL('image/png');
        const res = await fetch(dataUrl);
        const blob = await res.blob();
        fileToSend = new File([blob], "prompt_seed.png", { type: "image/png" });
      }

      setErrorMessage(null);
      const aoiObj = availableFilters.aoi.find(a => a.id === selectedFilters.aoi);
      const res = await searchByImage(fileToSend, searchPrompt, 8, {
        ...selectedFilters,
        aoi: aoiObj || null
      });

      clearTimeout(timer2);
      clearTimeout(timer3);
      setProcessingStep(4);

      if (res && res.matches && res.matches.length > 0) {
        setResults(res.matches);
        if (onSearchResults) {
          onSearchResults(res.tiles || res.matches);
        }
      } else {
        setResults([]);
        setErrorMessage("No matching satellite tiles found for this visual query.");
      }
    } catch (err) {
      console.error("Image search error:", err);
      clearTimeout(timer2);
      clearTimeout(timer3);
      setProcessingStep(0);
      setErrorMessage(err.message || "Failed to communicate with vector search backend.");
    } finally {
      setIsSearching(false);
    }
  };

  const handleReset = () => {
    setImageFile(null);
    setPreviewUrl(null);
    setImageMeta(null);
    setSearchPrompt("");
    setResults(null);
    setErrorMessage(null);
    setProcessingStep(0);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleViewTile = (tileId) => {
    if (onSelectTile) onSelectTile(tileId);
    const el = document.getElementById('candidate-tiles') || document.getElementById('temporal-analysis');
    if (el) el.scrollIntoView({ behavior: 'smooth' });
  };

  const handleAnalyze = (tileId) => {
    if (onSelectTile) onSelectTile(tileId);
    const el = document.getElementById('temporal-analysis');
    if (el) el.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <section className="w-full py-16 px-4 sm:px-6 lg:px-8 max-w-6xl mx-auto border-b border-cyan-500/30" id="image-search">
      {/* Section Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-8">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-pulse shadow-[0_0_8px_rgba(0,229,255,0.8)]"></span>
            <span className="text-xs font-black text-cyan-300 uppercase tracking-wider">
              Visual Retrieval Engine
            </span>
          </div>
          <h2 className="text-2xl sm:text-3xl font-black text-white tracking-tight">
            Image-to-Image Satellite Search
          </h2>
          <p className="text-sm text-slate-300 mt-1 max-w-2xl">
            Reverse visual search across indexed satellite tiles using multimodal feature embeddings and cosine similarity.
          </p>
        </div>
      </div>

      <div className="space-y-8">
        {/* Upload & Controls Workbench Container */}
        <div className="bg-gradient-to-b from-[#0c2a58]/90 via-[#071a38]/95 to-[#030d1c]/98 border-2 border-cyan-400/60 p-6 sm:p-8 rounded-3xl backdrop-blur-2xl shadow-[0_0_40px_rgba(0,229,255,0.3)]">
          <div className="grid grid-cols-1 md:grid-cols-12 gap-6 items-stretch">
            {/* Left: Drag & Drop Upload Zone */}
            <div className="md:col-span-6 flex flex-col justify-center">
              {!previewUrl ? (
                <div
                  onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
                  onDragLeave={() => setIsDragOver(false)}
                  onDrop={handleDrop}
                  onClick={() => fileInputRef.current?.click()}
                  className={`relative border-2 border-dashed rounded-3xl p-6 sm:p-8 flex flex-col items-center justify-center text-center cursor-pointer transition-all duration-300 min-h-[280px] h-full bg-black/50 ${
                    isDragOver
                      ? 'border-cyan-300 bg-cyan-500/25 shadow-[0_0_35px_rgba(0,229,255,0.4)] scale-[1.01]'
                      : 'border-cyan-400/50 hover:border-cyan-300 hover:bg-black/70'
                  }`}
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*,.tif,.tiff,.geotiff"
                    className="hidden"
                    onChange={(e) => {
                      if (e.target.files && e.target.files[0]) handleFile(e.target.files[0]);
                    }}
                  />
                  <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-cyan-400 to-blue-500 text-slate-950 flex items-center justify-center mb-4 shadow-lg shadow-cyan-500/40">
                    <UploadCloud className="w-7 h-7" />
                  </div>
                  <div className="text-base sm:text-lg font-black text-white mb-2">
                    Upload Query Satellite Tile
                  </div>
                  <p className="text-xs sm:text-sm text-slate-300 max-w-sm mx-auto mb-4 leading-relaxed px-2">
                    Drag &amp; drop GeoTIFF (.tif, .tiff), PNG, or JPG, or click to browse
                  </p>
                  <span className="text-xs font-black text-slate-950 px-4 py-1.5 bg-gradient-to-r from-cyan-400 to-blue-500 rounded-full shadow-[0_0_12px_rgba(0,229,255,0.4)]">
                    GeoTIFF &amp; Multi-band Supported
                  </span>
                </div>
              ) : (
                <div className="bg-black/60 border-2 border-cyan-400/50 p-6 rounded-3xl h-full flex flex-col justify-between">
                  <div>
                    <div className="flex items-center justify-between pb-3 mb-3 border-b border-cyan-400/30 text-xs">
                      <span className="text-cyan-300 font-extrabold text-sm">Query Tile Loaded</span>
                      <span className="text-emerald-400 font-bold flex items-center gap-1.5">
                        <CheckCircle2 className="w-4 h-4" />
                        Ready
                      </span>
                    </div>

                    <div className="relative w-full h-44 bg-black border-2 border-cyan-400/30 rounded-2xl overflow-hidden flex items-center justify-center mb-4">
                      <img
                        src={previewUrl}
                        alt="Query Satellite Preview"
                        className="w-full h-full object-contain filter contrast-105"
                      />
                    </div>

                    <div className="space-y-1.5 text-xs text-slate-200 mb-4 bg-black/80 p-3.5 rounded-2xl border border-cyan-400/20 font-mono">
                      <div className="flex justify-between items-center">
                        <span className="text-slate-400 font-sans">File:</span>
                        <span className="text-white font-bold truncate max-w-[180px]" title={imageMeta?.name}>
                          {imageMeta?.name}
                        </span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-slate-400 font-sans">Dimensions:</span>
                        <span className="text-cyan-300 font-bold">{imageMeta?.width} &times; {imageMeta?.height} px</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-3 pt-3 border-t border-cyan-400/20">
                    <button
                      type="button"
                      onClick={() => fileInputRef.current?.click()}
                      className="flex-1 py-2.5 bg-[#0a2246] hover:bg-cyan-500/20 text-cyan-200 text-xs font-bold rounded-xl border border-cyan-400/40 transition-colors flex items-center justify-center gap-2 cursor-pointer"
                    >
                      <RefreshCw className="w-3.5 h-3.5 text-cyan-400" />
                      <span>Replace Tile</span>
                    </button>
                    <button
                      type="button"
                      onClick={handleReset}
                      className="px-4 py-2.5 bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 border border-rose-500/40 rounded-xl transition-colors flex items-center justify-center cursor-pointer"
                      title="Remove Image"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* Right: Optional Guidance + Search Button */}
            <div className="md:col-span-6 flex flex-col justify-between space-y-4">
              <div className="bg-black/50 border-2 border-cyan-400/40 rounded-3xl p-6 flex flex-col justify-between h-full">
                <div>
                  <div className="flex items-center justify-between pb-3 mb-3 border-b border-cyan-400/20">
                    <label className="text-xs font-extrabold text-white tracking-wide flex items-center gap-2">
                      <MessageSquare className="w-4 h-4 text-cyan-400" />
                      Optional Text Guidance
                    </label>
                    {searchPrompt && (
                      <button
                        type="button"
                        onClick={() => setSearchPrompt("")}
                        className="text-xs font-bold text-rose-400 hover:text-rose-300 transition-colors cursor-pointer"
                      >
                        Clear
                      </button>
                    )}
                  </div>

                  <textarea
                    rows={4}
                    value={searchPrompt}
                    onChange={(e) => setSearchPrompt(e.target.value)}
                    placeholder="Optional prompt guidance (e.g., 'Find riverbanks with armored vehicles')..."
                    className="w-full bg-black/80 border-2 border-cyan-400/30 focus:border-cyan-300 text-white placeholder-slate-400 text-xs sm:text-sm p-3.5 rounded-2xl focus:outline-none resize-none transition-colors leading-relaxed"
                  />
                </div>

                <div className="flex flex-wrap items-center gap-2 mt-4 pt-3 border-t border-cyan-400/20 text-xs">
                  <span className="text-cyan-300 font-bold text-xs mr-1">Presets:</span>
                  {[
                    "Near riverbank",
                    "Armored vehicles",
                    "Mountain outpost",
                    "Runway apron"
                  ].map((chip) => (
                    <button
                      key={chip}
                      type="button"
                      onClick={() => setSearchPrompt(chip)}
                      className="px-3 py-1 bg-cyan-500/20 hover:bg-gradient-to-r hover:from-cyan-400 hover:to-blue-500 text-cyan-200 hover:text-slate-950 border border-cyan-400/40 rounded-full text-xs font-bold transition-all cursor-pointer"
                    >
                      +{chip}
                    </button>
                  ))}
                </div>
              </div>

              {/* Dropdown Filters UI */}
              <div className="flex flex-wrap items-center gap-4 mt-4 mb-2">
                <select 
                  value={selectedFilters.aoi} 
                  onChange={e => setSelectedFilters({...selectedFilters, aoi: e.target.value})}
                  className="px-3 py-2 bg-[#06142e]/95 border border-cyan-500/30 text-slate-300 text-sm rounded-lg focus:outline-none focus:border-cyan-400 w-full sm:w-auto flex-1"
                >
                  <option value="">All Regions</option>
                  {availableFilters.aoi.map(a => (
                    <option key={a.id} value={a.id}>{a.label}</option>
                  ))}
                </select>
                
                <select 
                  value={selectedFilters.satellite} 
                  onChange={e => setSelectedFilters({...selectedFilters, satellite: e.target.value})}
                  className="px-3 py-2 bg-[#06142e]/95 border border-cyan-500/30 text-slate-300 text-sm rounded-lg focus:outline-none focus:border-cyan-400 w-full sm:w-auto flex-1"
                >
                  <option value="">All Satellites</option>
                  {availableFilters.satellites.map(s => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>

                <select 
                  value={selectedFilters.year} 
                  onChange={e => setSelectedFilters({...selectedFilters, year: e.target.value})}
                  className="px-3 py-2 bg-[#06142e]/95 border border-cyan-500/30 text-slate-300 text-sm rounded-lg focus:outline-none focus:border-cyan-400 w-full sm:w-auto flex-1"
                >
                  <option value="">All Years</option>
                  {availableFilters.years.map(y => (
                    <option key={y} value={y}>{y}</option>
                  ))}
                </select>
              </div>

              {/* Primary Search Button (Styled matching Ingest Tile) */}
              <button
                type="button"
                disabled={(!previewUrl && !searchPrompt.trim()) || isSearching}
                onClick={handleSearch}
                className={`w-full py-4 text-sm font-black tracking-wide rounded-2xl flex items-center justify-center gap-2.5 cursor-pointer shadow-xl transition-all ${
                  (previewUrl || searchPrompt.trim()) && !isSearching
                    ? 'bg-gradient-to-r from-cyan-400 via-sky-400 to-blue-500 hover:from-cyan-300 hover:to-blue-400 text-slate-950 shadow-[0_0_35px_rgba(0,229,255,0.5)] hover:scale-[1.01]'
                    : 'bg-slate-900 text-slate-500 border-2 border-cyan-500/20 cursor-not-allowed opacity-60'
                }`}
              >
                <Sparkles className="w-5 h-5" />
                <span>
                  {isSearching
                    ? "Extracting Embeddings..."
                    : previewUrl && searchPrompt.trim()
                    ? "Search with Image + Text Guidance"
                    : previewUrl
                    ? "Search Similar Satellite Tiles"
                    : "Search with Text Guidance"}
                </span>
              </button>

              {errorMessage && (
                <div className="p-3 bg-rose-500/20 border-2 border-rose-500/40 rounded-2xl flex items-center gap-2.5 text-xs text-rose-200">
                  <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
                  <span>{errorMessage}</span>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Results Grid when user searches */}
        {results && results.length > 0 && (
          <div className="space-y-4 pt-2">
            <div className="flex flex-wrap items-center justify-between text-xs text-slate-300 gap-2">
              <span className="font-extrabold text-white text-base">Top Nearest-Neighbor Matches:</span>
              <span className="text-slate-950 font-black px-3.5 py-1 bg-gradient-to-r from-cyan-400 to-blue-500 rounded-full shadow-[0_0_12px_rgba(0,229,255,0.4)]">
                {results.length} Candidates Resolved
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {results.map((tile) => {
                const coordStr = typeof tile.coordinates === 'object' && tile.coordinates !== null
                  ? tile.coordinates.formatted || `${tile.coordinates.lat}° N, ${tile.coordinates.lng}° E`
                  : tile.coordinates || "28.58° N, 77.26° E";
                const displayName = tile.tileName || tile.id;

                return (
                  <div
                    key={tile.id}
                    className="p-4 bg-gradient-to-b from-[#0c2a58]/90 via-[#071a38]/95 to-[#030d1c]/98 hover:from-[#103468] hover:to-[#051326] border-2 border-cyan-400/50 hover:border-cyan-300 rounded-3xl transition-all flex flex-col justify-between gap-3 shadow-[0_0_20px_rgba(0,229,255,0.15)]"
                  >
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-black text-white font-mono">{displayName}</span>
                        <span className="text-xs font-black text-slate-950 px-2.5 py-0.5 bg-gradient-to-r from-cyan-400 to-blue-500 rounded-full">
                          {tile.similarity}% Match
                        </span>
                      </div>

                      <div className="w-full h-40 relative bg-black border-2 border-cyan-400/30 rounded-2xl overflow-hidden mb-3">
                        {tile.image ? (
                          <img
                            src={tile.image}
                            alt={displayName}
                            className="w-full h-full object-cover filter contrast-105"
                            onError={(e) => { e.currentTarget.style.display = 'none'; }}
                          />
                        ) : null}
                      </div>

                      <div className="space-y-1 text-xs">
                        <div className="text-slate-300">
                          <strong className="text-slate-400">Loc:</strong> {coordStr}
                        </div>
                        <div className="text-slate-300">
                          <strong className="text-slate-400">Date:</strong> {tile.date} &bull; <strong className="text-slate-400">Sensor:</strong> {tile.sensor || "Sentinel-2"}
                        </div>
                        <div className="text-emerald-400 font-bold pt-1">
                          {tile.detected || `Similarity Match (${tile.similarity}%)`}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 pt-2 border-t border-cyan-400/20">
                      <button
                        type="button"
                        onClick={() => handleViewTile(tile.id)}
                        className="flex-1 py-2 bg-[#0a2246] hover:bg-cyan-500/20 text-cyan-200 text-xs font-bold rounded-xl border border-cyan-400/40 transition-colors flex items-center justify-center gap-1.5 cursor-pointer"
                      >
                        <Eye className="w-3.5 h-3.5 text-cyan-400" />
                        <span>View</span>
                      </button>
                      <button
                        type="button"
                        onClick={() => handleAnalyze(tile.id)}
                        className="flex-1 py-2 bg-gradient-to-r from-cyan-400 to-blue-500 hover:from-cyan-300 hover:to-blue-400 text-slate-950 text-xs font-black rounded-xl transition-colors flex items-center justify-center gap-1.5 cursor-pointer shadow-md shadow-cyan-500/30"
                      >
                        <SlidersHorizontal className="w-3.5 h-3.5" />
                        <span>Analyze</span>
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
