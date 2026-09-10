import React, { useState, useEffect, useRef } from 'react';
import { 
  UploadCloud, 
  FileCheck, 
  Database, 
  Layers, 
  Cpu, 
  CheckCircle2, 
  Trash2, 
  ArrowRight, 
  Sparkles, 
  Search, 
  Eye, 
  RefreshCw,
  HardDrive,
  Check,
  Server
} from 'lucide-react';
import { uploadTile, extractMetadata, processTile, getArchive } from '../services/api';
import { DEFAULT_INGESTION_TILE, INITIAL_ARCHIVE } from '../data/mockData';

export default function TileIngestion({ onTileIngested, onViewTile, onSearchTile }) {
  // Wizard steps: 'upload' -> 'metadata' -> 'processing' -> 'record' -> 'success'
  const [currentStep, setCurrentStep] = useState('upload');
  
  // File state
  const [file, setFile] = useState(null);
  const [fileInfo, setFileInfo] = useState(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef(null);

  // Metadata form state
  const [metadata, setMetadata] = useState({
    tileId: "T027",
    sensor: "Landsat 8",
    date: "2025-05-07",
    lat: "22.57",
    lng: "88.36",
    bbox: "[22.45, 88.20, 22.70, 88.52]",
    crs: "EPSG:4326",
    resolution: "30 m",
    cloudCover: "12%",
    region: "Kolkata"
  });
  const [isExtracting, setIsExtracting] = useState(false);

  // Processing pipeline states
  const [processProgress, setProcessProgress] = useState(0);
  const [activePipelineStep, setActivePipelineStep] = useState(0);
  const [currentStepName, setCurrentStepName] = useState("Initializing file...");

  // Final saved record & archive state
  const [savedTile, setSavedTile] = useState(null);
  const [archiveList, setArchiveList] = useState([]);
  const [searchFilter, setSearchFilter] = useState("");

  const PIPELINE_STAGES = [
    { id: 1, label: "VALIDATE FILE" },
    { id: 2, label: "EXTRACT METADATA" },
    { id: 3, label: "GENERATE TILES" },
    { id: 4, label: "GENERATE IMAGE EMBEDDING" },
    { id: 5, label: "UPDATE VECTOR INDEX" },
    { id: 6, label: "UPDATE DATABASE" },
    { id: 7, label: "TILE READY" }
  ];

  // Load archive on mount
  useEffect(() => {
    loadArchive();
  }, []);

  const loadArchive = async () => {
    const res = await getArchive();
    if (res.success && res.tiles) {
      setArchiveList(res.tiles);
    }
  };

  // Handle file selection
  const handleSelectFile = async (selectedFile) => {
    if (!selectedFile) return;
    setFile(selectedFile);
    const res = await uploadTile(selectedFile);
    if (res.success) {
      setFileInfo(res.fileInfo);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleSelectFile(e.dataTransfer.files[0]);
    }
  };

  // Quick sample tile selector
  const handleLoadSample = (sampleType = 'landsat') => {
    const sample = sampleType === 'landsat' 
      ? {
          name: "LC08_L2SP_145044_20250507.tif",
          size: 24.6 * 1024 * 1024,
          type: "image/tiff"
        }
      : {
          name: "S2A_MSIL2A_20250509_T43R.tif",
          size: 48.2 * 1024 * 1024,
          type: "image/tiff"
        };
    
    setFile(sample);
    setFileInfo({
      name: sample.name,
      size: sampleType === 'landsat' ? "24.6 MB" : "48.2 MB",
      format: "GeoTIFF",
      status: "✓ FILE READY"
    });
  };

  const handleRemoveFile = () => {
    setFile(null);
    setFileInfo(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
    setCurrentStep('upload');
  };

  // Auto extract metadata handler
  const handleAutoExtract = async () => {
    setIsExtracting(true);
    const res = await extractMetadata(file);
    if (res.success && res.metadata) {
      setMetadata(prev => ({
        ...prev,
        ...res.metadata
      }));
    }
    setIsExtracting(false);
  };

  // Start processing tile through 7-step incremental ingestion
  const handleStartProcessing = () => {
    setCurrentStep('processing');
    setProcessProgress(10);
    setActivePipelineStep(1);
    setCurrentStepName("Validating GeoTIFF headers and CRS...");

    // Step 2
    setTimeout(() => {
      setProcessProgress(28);
      setActivePipelineStep(2);
      setCurrentStepName("Extracting radiometric metadata & bounding coordinates...");
    }, 400);

    // Step 3
    setTimeout(() => {
      setProcessProgress(45);
      setActivePipelineStep(3);
      setCurrentStepName("Generating 512x512 sub-tiles and spatial pyramids...");
    }, 850);

    // Step 4
    setTimeout(() => {
      setProcessProgress(64);
      setActivePipelineStep(4);
      setCurrentStepName("Computing 768-D multimodal vision embedding vector...");
    }, 1300);

    // Step 5: Incremental FAISS update
    setTimeout(() => {
      setProcessProgress(82);
      setActivePipelineStep(5);
      setCurrentStepName("Incrementally adding vectors to FAISS HNSW graph index...");
    }, 1750);

    // Step 6: SQLite row insert
    setTimeout(() => {
      setProcessProgress(95);
      setActivePipelineStep(6);
      setCurrentStepName("Inserting metadata into local SQLite satellite catalog...");
    }, 2150);

    // Step 7: Completed
    setTimeout(async () => {
      setProcessProgress(100);
      setActivePipelineStep(7);
      setCurrentStepName("Tile processing complete ✓");
      
      const result = await processTile(file, metadata);
      if (result.success && result.tileRecord) {
        setSavedTile(result.tileRecord);
        // Transition to database record preview
        setTimeout(() => {
          setCurrentStep('record');
        }, 500);
      }
    }, 2600);
  };

  // Save Tile to local archive & emit to parent
  const handleSaveTile = () => {
    if (savedTile) {
      // Prepend to archive
      setArchiveList(prev => [savedTile, ...prev.filter(t => t.id !== savedTile.id)]);
      
      if (onTileIngested) {
        onTileIngested(savedTile);
      }
    }
    setCurrentStep('success');
  };

  const handleAddAnother = () => {
    setFile(null);
    setFileInfo(null);
    setSavedTile(null);
    setCurrentStep('upload');
    setProcessProgress(0);
    setActivePipelineStep(0);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const filteredArchive = archiveList.filter(item => {
    if (!searchFilter.trim()) return true;
    const q = searchFilter.toLowerCase();
    return (
      item.id?.toLowerCase().includes(q) ||
      item.sensor?.toLowerCase().includes(q) ||
      item.region?.toLowerCase().includes(q) ||
      item.date?.includes(q) ||
      item.status?.toLowerCase().includes(q)
    );
  });

  return (
    <section className="w-full py-16 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto border-b border-[#1e293b]/40" id="data-ingestion">
      {/* Section Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-8 pb-3 border-b border-[#1e293b]">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="w-2 h-2 bg-[#00e5ff]"></span>
            <span className="font-mono text-[10px] text-[#00e5ff] uppercase tracking-widest font-semibold">
              MODULE // 07
            </span>
          </div>
          <h2 className="text-[28px] sm:text-[34px] font-bold text-white tracking-tight">
            Add New Satellite Tile // Data Ingestion
          </h2>
          <p className="text-[14px] text-[#94a3b8] mt-1">
            Offline ingestion pipeline: Extract metadata, generate ViT embeddings, and incrementally append vectors to the local FAISS index &amp; SQLite database.
          </p>
        </div>

        {/* Status badges */}
        <div className="flex items-center gap-3 font-mono text-[11px]">
          <div className="flex items-center gap-1.5 px-3 py-1.5 bg-[#0d1726] border border-[#00e5ff]/40 rounded-sm text-[#00e5ff]">
            <HardDrive className="w-3.5 h-3.5" />
            <span>STORAGE: LOCAL AIR-GAP</span>
          </div>
          <div className="flex items-center gap-1.5 px-3 py-1.5 bg-[#0d1726] border border-[#10b981]/40 rounded-sm text-[#10b981]">
            <Server className="w-3.5 h-3.5" />
            <span>SQLITE &amp; FAISS: INCREMENTAL</span>
          </div>
        </div>
      </div>

      {/* Main Ingestion Workbench */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 mb-16">
        {/* Left Side: Upload & Workflow Cards (7 Cols) */}
        <div className="lg:col-span-7 flex flex-col justify-start">

          {/* STEP 1: UPLOAD TILE */}
          {currentStep === 'upload' && (
            <div className="space-y-4">
              {!fileInfo ? (
                /* Drag & Drop Area */
                <div
                  onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
                  onDragLeave={() => setIsDragOver(false)}
                  onDrop={handleDrop}
                  onClick={() => fileInputRef.current?.click()}
                  className={`hud-bracket-tl hud-bracket-br relative border-2 border-dashed rounded-sm p-10 flex flex-col items-center justify-center text-center cursor-pointer transition-all duration-200 min-h-[340px] ${
                    isDragOver
                      ? 'border-[#00e5ff] bg-[#00e5ff]/10 shadow-[0_0_24px_rgba(0,229,255,0.2)]'
                      : 'border-[#1e293b] hover:border-[#00e5ff]/50 bg-[#0d1726]/80'
                  }`}
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".tif,.tiff,.png,.jpg,.jpeg,.geotiff"
                    className="hidden"
                    onChange={(e) => {
                      if (e.target.files && e.target.files[0]) handleSelectFile(e.target.files[0]);
                    }}
                  />
                  <div className="w-16 h-16 rounded-full bg-[#131f33] border border-[#00e5ff]/40 flex items-center justify-center mb-4 text-[#00e5ff] shadow-[0_0_15px_rgba(0,229,255,0.15)]">
                    <UploadCloud className="w-8 h-8" />
                  </div>
                  <div className="font-mono text-[14px] font-bold text-white uppercase tracking-wider mb-2">
                    DROP SATELLITE TILE HERE
                  </div>
                  <div className="text-[12px] text-[#00e5ff] font-mono mb-3 font-semibold">
                    + [ UPLOAD TILE ]
                  </div>
                  <p className="font-mono text-[11px] text-[#64748b]">
                    GeoTIFF / TIFF / PNG / JPG • Air-gapped local ingestion
                  </p>

                  {/* Sample pills */}
                  <div className="mt-6 pt-4 border-t border-[#1e293b] flex items-center gap-2 flex-wrap justify-center">
                    <span className="font-mono text-[10px] text-[#64748b] uppercase">SAMPLE RECON TILES:</span>
                    <button
                      type="button"
                      onClick={(e) => { e.stopPropagation(); handleLoadSample('landsat'); }}
                      className="px-2.5 py-1 bg-[#131f33] hover:bg-[#1a2942] border border-[#00e5ff]/40 text-[#9cf0ff] font-mono text-[10px] rounded-sm transition-colors cursor-pointer"
                    >
                      Landsat-8 (24.6 MB)
                    </button>
                    <button
                      type="button"
                      onClick={(e) => { e.stopPropagation(); handleLoadSample('sentinel'); }}
                      className="px-2.5 py-1 bg-[#131f33] hover:bg-[#1a2942] border border-[#1e293b] text-[#94a3b8] hover:text-[#00e5ff] font-mono text-[10px] rounded-sm transition-colors cursor-pointer"
                    >
                      Sentinel-2 MSI (48.2 MB)
                    </button>
                  </div>
                </div>
              ) : (
                /* Selected File Card */
                <div className="hud-bracket-tl hud-bracket-br relative bg-[#0d1726] border border-[#00e5ff]/40 p-6 rounded-sm space-y-4">
                  <div className="flex items-center justify-between pb-3 border-b border-[#1e293b] font-mono text-[12px]">
                    <span className="text-[#00e5ff] font-bold uppercase">FILE SELECTION</span>
                    <span className="text-[#10b981] font-semibold">{fileInfo.status}</span>
                  </div>

                  <div className="grid grid-cols-2 gap-4 font-mono text-[12px]">
                    <div>
                      <span className="text-[#64748b] block text-[10px] uppercase">File:</span>
                      <span className="text-white font-bold break-all">{fileInfo.name}</span>
                    </div>
                    <div>
                      <span className="text-[#64748b] block text-[10px] uppercase">Size:</span>
                      <span className="text-[#9cf0ff] font-bold">{fileInfo.size}</span>
                    </div>
                    <div>
                      <span className="text-[#64748b] block text-[10px] uppercase">Format:</span>
                      <span className="text-white font-bold">{fileInfo.format}</span>
                    </div>
                    <div>
                      <span className="text-[#64748b] block text-[10px] uppercase">Status:</span>
                      <span className="text-[#10b981] font-bold">{fileInfo.status}</span>
                    </div>
                  </div>

                  <div className="flex items-center gap-3 pt-3 border-t border-[#1e293b]">
                    <button
                      type="button"
                      onClick={handleRemoveFile}
                      className="px-4 py-2 bg-[#93000a]/20 hover:bg-[#93000a]/40 border border-[#ef4444] text-[#ffb4ab] font-mono text-[11px] font-bold uppercase rounded-sm transition-colors flex items-center gap-1.5 cursor-pointer"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                      [ REMOVE ]
                    </button>
                    <button
                      type="button"
                      onClick={() => setCurrentStep('metadata')}
                      className="flex-1 py-2.5 bg-[#00e5ff] hover:bg-[#9cf0ff] text-[#070e1b] font-mono text-[12px] font-bold uppercase tracking-wider rounded-sm transition-all flex items-center justify-center gap-2 shadow-[0_0_12px_rgba(0,229,255,0.25)] cursor-pointer"
                    >
                      <span>[ REVIEW METADATA ]</span>
                      <ArrowRight className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* STEP 2: TILE METADATA FORM */}
          {currentStep === 'metadata' && (
            <div className="hud-bracket-tl hud-bracket-br relative bg-[#0d1726] border border-[#00e5ff]/40 p-6 rounded-sm">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 pb-3 mb-4 border-b border-[#1e293b]">
                <div>
                  <h3 className="font-mono text-[14px] text-white font-bold uppercase">
                    TILE INFORMATION &amp; SPATIAL INDEXING
                  </h3>
                  <p className="font-mono text-[11px] text-[#64748b]">
                    Verify or edit satellite metadata before generating vector embeddings.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={handleAutoExtract}
                  disabled={isExtracting}
                  className="px-3 py-1.5 bg-[#131f33] hover:bg-[#1a2942] border border-[#00e5ff]/50 text-[#00e5ff] font-mono text-[11px] font-bold rounded-sm transition-colors flex items-center gap-1.5 self-start sm:self-center cursor-pointer"
                >
                  <Sparkles className="w-3.5 h-3.5 text-[#00e5ff]" />
                  {isExtracting ? "EXTRACTING..." : "[ AUTO EXTRACT METADATA ]"}
                </button>
              </div>

              {/* Form Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 font-mono text-[12px]">
                <div>
                  <label className="text-[#64748b] text-[10px] uppercase block mb-1">Tile ID</label>
                  <input
                    type="text"
                    value={metadata.tileId}
                    onChange={(e) => setMetadata({ ...metadata, tileId: e.target.value })}
                    className="w-full bg-[#070e1b] border border-[#1e293b] text-white px-3 py-2 rounded-sm focus:border-[#00e5ff] focus:outline-none"
                  />
                </div>

                <div>
                  <label className="text-[#64748b] text-[10px] uppercase block mb-1">Satellite / Sensor</label>
                  <input
                    type="text"
                    value={metadata.sensor}
                    onChange={(e) => setMetadata({ ...metadata, sensor: e.target.value })}
                    className="w-full bg-[#070e1b] border border-[#1e293b] text-white px-3 py-2 rounded-sm focus:border-[#00e5ff] focus:outline-none"
                  />
                </div>

                <div>
                  <label className="text-[#64748b] text-[10px] uppercase block mb-1">Acquisition Date</label>
                  <input
                    type="date"
                    value={metadata.date}
                    onChange={(e) => setMetadata({ ...metadata, date: e.target.value })}
                    className="w-full bg-[#070e1b] border border-[#1e293b] text-white px-3 py-2 rounded-sm focus:border-[#00e5ff] focus:outline-none"
                  />
                </div>

                <div>
                  <label className="text-[#64748b] text-[10px] uppercase block mb-1">Region / Theater</label>
                  <input
                    type="text"
                    value={metadata.region}
                    onChange={(e) => setMetadata({ ...metadata, region: e.target.value })}
                    className="w-full bg-[#070e1b] border border-[#1e293b] text-white px-3 py-2 rounded-sm focus:border-[#00e5ff] focus:outline-none"
                  />
                </div>

                <div>
                  <label className="text-[#64748b] text-[10px] uppercase block mb-1">Latitude</label>
                  <input
                    type="text"
                    value={metadata.lat}
                    onChange={(e) => setMetadata({ ...metadata, lat: e.target.value })}
                    className="w-full bg-[#070e1b] border border-[#1e293b] text-white px-3 py-2 rounded-sm focus:border-[#00e5ff] focus:outline-none"
                  />
                </div>

                <div>
                  <label className="text-[#64748b] text-[10px] uppercase block mb-1">Longitude</label>
                  <input
                    type="text"
                    value={metadata.lng}
                    onChange={(e) => setMetadata({ ...metadata, lng: e.target.value })}
                    className="w-full bg-[#070e1b] border border-[#1e293b] text-white px-3 py-2 rounded-sm focus:border-[#00e5ff] focus:outline-none"
                  />
                </div>

                <div>
                  <label className="text-[#64748b] text-[10px] uppercase block mb-1">Resolution</label>
                  <input
                    type="text"
                    value={metadata.resolution}
                    onChange={(e) => setMetadata({ ...metadata, resolution: e.target.value })}
                    className="w-full bg-[#070e1b] border border-[#1e293b] text-white px-3 py-2 rounded-sm focus:border-[#00e5ff] focus:outline-none"
                  />
                </div>

                <div>
                  <label className="text-[#64748b] text-[10px] uppercase block mb-1">CRS Projection</label>
                  <input
                    type="text"
                    value={metadata.crs}
                    onChange={(e) => setMetadata({ ...metadata, crs: e.target.value })}
                    className="w-full bg-[#070e1b] border border-[#1e293b] text-white px-3 py-2 rounded-sm focus:border-[#00e5ff] focus:outline-none"
                  />
                </div>

                <div>
                  <label className="text-[#64748b] text-[10px] uppercase block mb-1">Cloud Cover</label>
                  <input
                    type="text"
                    value={metadata.cloudCover}
                    onChange={(e) => setMetadata({ ...metadata, cloudCover: e.target.value })}
                    className="w-full bg-[#070e1b] border border-[#1e293b] text-white px-3 py-2 rounded-sm focus:border-[#00e5ff] focus:outline-none"
                  />
                </div>

                <div>
                  <label className="text-[#64748b] text-[10px] uppercase block mb-1">Bounding Box</label>
                  <input
                    type="text"
                    value={metadata.bbox}
                    onChange={(e) => setMetadata({ ...metadata, bbox: e.target.value })}
                    className="w-full bg-[#070e1b] border border-[#1e293b] text-white px-3 py-2 rounded-sm focus:border-[#00e5ff] focus:outline-none"
                  />
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center justify-between gap-3 mt-6 pt-4 border-t border-[#1e293b]">
                <button
                  type="button"
                  onClick={() => setCurrentStep('upload')}
                  className="px-4 py-2 bg-[#131f33] hover:bg-[#1a2942] border border-[#1e293b] text-[#94a3b8] hover:text-white font-mono text-[11px] font-semibold rounded-sm transition-colors cursor-pointer"
                >
                  ← BACK TO FILE
                </button>
                <button
                  type="button"
                  onClick={handleStartProcessing}
                  className="px-6 py-2.5 bg-[#00e5ff] hover:bg-[#9cf0ff] text-[#070e1b] font-mono text-[12px] font-bold uppercase tracking-wider rounded-sm transition-all flex items-center gap-2 shadow-[0_0_15px_rgba(0,229,255,0.25)] cursor-pointer"
                >
                  <Cpu className="w-4 h-4" />
                  <span>[ PROCESS TILE ]</span>
                </button>
              </div>
            </div>
          )}

          {/* STEP 3: TILE PROCESSING PROGRESS */}
          {currentStep === 'processing' && (
            <div className="hud-bracket-tl hud-bracket-br relative bg-[#0d1726] border border-[#00e5ff]/50 p-6 rounded-sm space-y-6 shadow-[0_0_24px_rgba(0,229,255,0.1)]">
              <div>
                <div className="flex items-center justify-between font-mono text-[12px] mb-2">
                  <span className="text-white font-bold uppercase tracking-wider">PROCESSING NEW TILE</span>
                  <span className="text-[#00e5ff] font-bold">{processProgress}%</span>
                </div>
                {/* Progress Bar */}
                <div className="w-full h-3 bg-[#070e1b] border border-[#1e293b] rounded-sm overflow-hidden p-0.5">
                  <div 
                    className="h-full bg-gradient-to-r from-[#00e5ff] to-[#10b981] transition-all duration-300 rounded-[1px]"
                    style={{ width: `${processProgress}%` }}
                  ></div>
                </div>
                <div className="font-mono text-[11px] text-[#9cf0ff] mt-2 flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-[#00e5ff] animate-pulse"></span>
                  <span>Current step: {currentStepName}</span>
                </div>
              </div>

              {/* 7-Step Vertical Flow Pipeline */}
              <div className="border border-[#1e293b] bg-[#070e1b] p-4 rounded-sm space-y-2">
                <div className="font-mono text-[10px] text-[#64748b] uppercase pb-2 border-b border-[#1e293b]">
                  INGESTION PIPELINE EXECUTION
                </div>
                <div className="space-y-1.5 font-mono text-[11px]">
                  <div className="p-1.5 text-[#64748b]">NEW IMAGE: {fileInfo?.name || "LC08_L2SP_145044_20250507.tif"}</div>
                  {PIPELINE_STAGES.map((st, idx) => {
                    const isDone = activePipelineStep > idx;
                    const isCurrent = activePipelineStep === idx + 1;
                    return (
                      <div
                        key={st.id}
                        className={`p-2 rounded-sm border flex items-center justify-between transition-all ${
                          isCurrent
                            ? 'bg-[#131f33] border-[#00e5ff] text-[#00e5ff]'
                            : isDone
                            ? 'bg-[#0d1726] border-[#1e293b] text-white'
                            : 'bg-transparent border-transparent text-[#64748b]'
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] text-[#64748b]">0{st.id}</span>
                          <span className="font-bold">{st.label}</span>
                        </div>
                        {isDone ? (
                          <CheckCircle2 className="w-4 h-4 text-[#10b981]" />
                        ) : isCurrent ? (
                          <span className="w-2 h-2 rounded-full bg-[#00e5ff] animate-ping"></span>
                        ) : (
                          <span className="w-2 h-2 rounded-full border border-[#64748b]"></span>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          )}

          {/* STEP 4: DATABASE RECORD PREVIEW */}
          {currentStep === 'record' && savedTile && (
            <div className="hud-bracket-tl hud-bracket-br relative bg-[#0d1726] border border-[#00e5ff]/50 p-6 rounded-sm space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-[#1e293b] font-mono text-[12px]">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 bg-[#10b981] rounded-full"></span>
                  <span className="text-white font-bold uppercase">NEW TILE RECORD</span>
                </div>
                <span className="px-2 py-0.5 bg-[#10b981]/20 text-[#10b981] border border-[#10b981]/40 text-[10px] font-bold uppercase">
                  ● ACTIVE
                </span>
              </div>

              {/* Database Table Card */}
              <div className="bg-[#070e1b] border border-[#1e293b] p-4 rounded-sm space-y-2 font-mono text-[12px]">
                <div className="flex justify-between py-1 border-b border-[#1e293b]/50">
                  <span className="text-[#64748b]">Tile ID</span>
                  <span className="text-[#00e5ff] font-bold">{savedTile.id}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-[#1e293b]/50">
                  <span className="text-[#64748b]">File</span>
                  <span className="text-white break-all">{savedTile.file}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-[#1e293b]/50">
                  <span className="text-[#64748b]">Sensor</span>
                  <span className="text-white">{savedTile.sensor}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-[#1e293b]/50">
                  <span className="text-[#64748b]">Date</span>
                  <span className="text-white">{savedTile.date}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-[#1e293b]/50">
                  <span className="text-[#64748b]">Location</span>
                  <span className="text-[#9cf0ff]">{savedTile.lat}° N, {savedTile.lng}° E ({savedTile.region})</span>
                </div>
                <div className="flex justify-between py-1 border-b border-[#1e293b]/50">
                  <span className="text-[#64748b]">Resolution</span>
                  <span className="text-white">{savedTile.resolution}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-[#1e293b]/50">
                  <span className="text-[#64748b]">CRS</span>
                  <span className="text-white">{savedTile.crs}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-[#1e293b]/50">
                  <span className="text-[#64748b]">Embedding</span>
                  <span className="text-[#10b981] font-bold">✓ GENERATED</span>
                </div>
                <div className="flex justify-between py-1 border-b border-[#1e293b]/50">
                  <span className="text-[#64748b]">Vector Index</span>
                  <span className="text-[#10b981] font-bold">✓ UPDATED</span>
                </div>
                <div className="flex justify-between py-1 border-b border-[#1e293b]/50">
                  <span className="text-[#64748b]">Database</span>
                  <span className="text-[#10b981] font-bold">✓ UPDATED</span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-[#64748b]">Status</span>
                  <span className="text-[#10b981] font-bold">● ACTIVE</span>
                </div>
              </div>

              <button
                type="button"
                onClick={handleSaveTile}
                className="w-full py-3 bg-[#00e5ff] hover:bg-[#9cf0ff] text-[#070e1b] font-mono text-[12px] font-bold uppercase tracking-wider rounded-sm transition-all flex items-center justify-center gap-2 shadow-[0_0_15px_rgba(0,229,255,0.25)] cursor-pointer"
              >
                <Database className="w-4 h-4" />
                <span>[ SAVE TILE ]</span>
              </button>
            </div>
          )}

          {/* STEP 5: SUCCESS SCREEN */}
          {currentStep === 'success' && savedTile && (
            <div className="hud-bracket-tl hud-bracket-br relative bg-[#0d1726] border border-[#10b981]/60 p-6 rounded-sm space-y-5">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-[#10b981]/20 border border-[#10b981] flex items-center justify-center text-[#10b981]">
                  <Check className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="font-mono text-[16px] text-white font-bold">
                    ✓ TILE SUCCESSFULLY ADDED
                  </h3>
                  <p className="font-mono text-[12px] text-[#94a3b8] mt-0.5">
                    Tile <span className="text-[#00e5ff] font-bold">{savedTile.id}</span> has been added to the local satellite archive.
                  </p>
                </div>
              </div>

              {/* Updated Checklist */}
              <div className="bg-[#070e1b] border border-[#1e293b] p-4 rounded-sm space-y-2 font-mono text-[12px]">
                <div className="text-[#64748b] text-[10px] uppercase pb-1 border-b border-[#1e293b]">
                  UPDATED SUBSYSTEMS:
                </div>
                <div className="flex justify-between text-white">
                  <span>IMAGE ARCHIVE</span>
                  <span className="text-[#10b981] font-bold">✓</span>
                </div>
                <div className="flex justify-between text-white">
                  <span>METADATA DATABASE</span>
                  <span className="text-[#10b981] font-bold">✓</span>
                </div>
                <div className="flex justify-between text-white">
                  <span>VECTOR INDEX</span>
                  <span className="text-[#10b981] font-bold">✓</span>
                </div>
                <div className="flex justify-between text-white">
                  <span>SEARCH INDEX</span>
                  <span className="text-[#10b981] font-bold">✓</span>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => onViewTile && onViewTile(savedTile.id)}
                  className="py-2.5 bg-[#131f33] hover:bg-[#00e5ff] hover:text-[#070e1b] border border-[#00e5ff]/40 text-[#00e5ff] font-mono text-[11px] font-bold uppercase rounded-sm transition-colors flex items-center justify-center gap-1.5 cursor-pointer"
                >
                  <Eye className="w-3.5 h-3.5" />
                  [ VIEW TILE ]
                </button>
                <button
                  type="button"
                  onClick={() => onSearchTile && onSearchTile(savedTile.sensor + " " + savedTile.region)}
                  className="py-2.5 bg-[#00e5ff] hover:bg-[#9cf0ff] text-[#070e1b] font-mono text-[11px] font-bold uppercase rounded-sm transition-colors flex items-center justify-center gap-1.5 cursor-pointer"
                >
                  <Search className="w-3.5 h-3.5" />
                  [ SEARCH THIS TILE ]
                </button>
                <button
                  type="button"
                  onClick={handleAddAnother}
                  className="py-2.5 bg-[#131f33] hover:bg-[#1a2942] border border-[#1e293b] text-white font-mono text-[11px] font-bold uppercase rounded-sm transition-colors flex items-center justify-center gap-1.5 cursor-pointer"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  [ ADD ANOTHER TILE ]
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Right Side: Architecture & Incremental Telemetry (5 Cols) */}
        <div className="lg:col-span-5 flex flex-col justify-between">
          <div className="bg-[#0d1726] border border-[#1e293b] p-5 rounded-sm space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-[#1e293b]">
              <span className="font-mono text-[11px] text-[#64748b] uppercase font-bold">
                INCREMENTAL INGESTION WORKFLOW
              </span>
              <span className="font-mono text-[10px] text-[#10b981]">NO FULL RE-INDEX</span>
            </div>

            <p className="font-mono text-[12px] text-[#94a3b8]">
              Existing tiles (<code className="text-[#00e5ff]">T001 ... T026</code>) remain unchanged in the FAISS graph. The new satellite image is tokenized, tiled, and appended to the vector database in under 3 seconds.
            </p>

            {/* Architecture Diagram */}
            <div className="p-3 bg-[#070e1b] border border-[#1e293b] rounded-sm font-mono text-[11px] space-y-1.5">
              <div className="text-[#00e5ff] font-bold">New Satellite Image</div>
              <div className="text-[#64748b]">  ↓ Metadata Extraction</div>
              <div className="text-white">  ↓ Tiling &amp; Multi-Band Alignment</div>
              <div className="text-[#f59e0b]">  ↓ CLIP-ViT Embedding Generation</div>
              <div className="text-white">  ↓ Add New Vectors (Incremental)</div>
              <div className="text-[#10b981]">  ↓ Update Local FAISS Index</div>
              <div className="text-white">  ↓ Insert Metadata into SQLite</div>
              <div className="text-[#00e5ff] font-bold">  ✓ Tile Immediately Searchable</div>
            </div>

            <div className="p-3 bg-[#131f33]/60 border border-[#00e5ff]/20 rounded-sm font-mono text-[11px] space-y-1">
              <div className="text-[#64748b] text-[10px] uppercase">FAISS HNSW GRAPH STATUS:</div>
              <div className="text-[#9cf0ff] font-bold">68,920 + {archiveList.length > 4 ? archiveList.length - 4 : 1} VECTORS LOADED</div>
              <div className="text-[#10b981] text-[10px]">INCREMENTAL ADD LATENCY: 28ms</div>
            </div>
          </div>
        </div>
      </div>

      {/* DATABASE / ARCHIVE VIEW */}
      <div className="mt-8 pt-8 border-t border-[#1e293b]" id="archive-section">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-[#00e5ff]"></span>
              <h3 className="text-[20px] font-bold text-white font-mono">
                Satellite Tile Archive &amp; SQLite Catalog
              </h3>
            </div>
            <p className="text-[13px] text-[#94a3b8] font-mono mt-0.5">
              Current local storage archive showing ingested tiles ready for semantic retrieval.
            </p>
          </div>

          {/* Search filter */}
          <div className="flex items-center gap-2">
            <div className="relative">
              <input
                type="text"
                value={searchFilter}
                onChange={(e) => setSearchFilter(e.target.value)}
                placeholder="Filter archive (e.g. Landsat, T027)..."
                className="bg-[#070e1b] border border-[#1e293b] text-white font-mono text-[12px] px-3 py-1.5 rounded-sm focus:border-[#00e5ff] focus:outline-none w-64"
              />
            </div>
          </div>
        </div>

        {/* Database Table */}
        <div className="overflow-x-auto border border-[#1e293b] rounded-sm bg-[#0d1726]">
          <table className="w-full text-left font-mono text-[12px]">
            <thead className="bg-[#070e1b] border-b border-[#1e293b] text-[#64748b] text-[10px] uppercase">
              <tr>
                <th className="py-3 px-4">TILE ID</th>
                <th className="py-3 px-4">SENSOR</th>
                <th className="py-3 px-4">ACQUISITION DATE</th>
                <th className="py-3 px-4">REGION / COORDS</th>
                <th className="py-3 px-4">RESOLUTION</th>
                <th className="py-3 px-4">STATUS</th>
                <th className="py-3 px-4 text-right">ACTIONS</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1e293b]/60 text-white">
              {filteredArchive.map((item, idx) => {
                const isNew = item.id === savedTile?.id;
                return (
                  <tr 
                    key={item.id || idx}
                    className={`hover:bg-[#131f33] transition-colors ${isNew ? 'bg-[#00e5ff]/10' : ''}`}
                  >
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-[#00e5ff]">{item.id}</span>
                        {isNew && (
                          <span className="px-1.5 py-0.2 bg-[#00e5ff] text-[#070e1b] text-[9px] font-bold rounded-sm">
                            NEW
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="py-3 px-4 text-white font-medium">{item.sensor}</td>
                    <td className="py-3 px-4 text-[#94a3b8]">{item.date}</td>
                    <td className="py-3 px-4 text-[#9cf0ff]">{item.region || "Sector"} ({item.lat}°N, {item.lng}°E)</td>
                    <td className="py-3 px-4 text-[#64748b]">{item.resolution}</td>
                    <td className="py-3 px-4">
                      <span className="px-2 py-0.5 bg-[#10b981]/20 text-[#10b981] border border-[#10b981]/40 rounded-sm text-[10px] font-bold">
                        ● {item.status || "ACTIVE"}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          type="button"
                          onClick={() => onViewTile && onViewTile(item.id)}
                          className="px-2.5 py-1 bg-[#131f33] hover:bg-[#00e5ff] hover:text-[#070e1b] border border-[#00e5ff]/40 text-[#00e5ff] text-[10px] font-bold uppercase rounded-sm transition-colors cursor-pointer"
                        >
                          INSPECT
                        </button>
                        <button
                          type="button"
                          onClick={() => onSearchTile && onSearchTile(`${item.sensor} ${item.region || ''}`)}
                          className="px-2.5 py-1 bg-[#00e5ff] hover:bg-[#9cf0ff] text-[#070e1b] text-[10px] font-bold uppercase rounded-sm transition-colors cursor-pointer"
                        >
                          SEARCH
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
