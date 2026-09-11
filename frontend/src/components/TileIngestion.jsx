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
  Server,
  ArrowLeft,
  Calendar,
  MapPin,
  Filter,
  SlidersHorizontal,
  ChevronDown,
  Clock,
  Plus,
  X,
  Target,
  Image as ImageIcon,
  Maximize2
} from 'lucide-react';
import { uploadTile, extractMetadata, processTile, getArchive } from '../services/api';
import { DEFAULT_INGESTION_TILE, INITIAL_ARCHIVE, RELATIVE_SECTORS } from '../data/mockData';

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
    tileId: "T028",
    relativeSector: RELATIVE_SECTORS[0].name,
    sensor: "Landsat-8",
    date: new Date().toISOString().slice(0, 10),
    lat: String(RELATIVE_SECTORS[0].lat),
    lng: String(RELATIVE_SECTORS[0].lng),
    bbox: `[${(RELATIVE_SECTORS[0].lat - 0.12).toFixed(2)}, ${(RELATIVE_SECTORS[0].lng - 0.16).toFixed(2)}, ${(RELATIVE_SECTORS[0].lat + 0.13).toFixed(2)}, ${(RELATIVE_SECTORS[0].lng + 0.16).toFixed(2)}]`,
    crs: RELATIVE_SECTORS[0].crs,
    resolution: RELATIVE_SECTORS[0].resolution,
    cloudCover: "4%",
    region: RELATIVE_SECTORS[0].region,
    image: RELATIVE_SECTORS[0].image
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
  const [selectedSensor, setSelectedSensor] = useState('ALL');
  const [selectedDate, setSelectedDate] = useState('ALL');
  const [selectedRegion, setSelectedRegion] = useState('ALL');
  const [selectedDetailTile, setSelectedDetailTile] = useState(null);
  const [archiveSuccessToast, setArchiveSuccessToast] = useState('');

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


  // Open "MODULE // 07 : Add New Satellite Tile // Data Ingestion" directly on page from Archive
  const handleOpenAddTile = () => {
    const existingIds = archiveList
      .map(t => parseInt(t.id?.replace(/\D/g, '') || '0', 10))
      .filter(n => !isNaN(n));
    const nextNum = existingIds.length > 0 ? Math.max(...existingIds) + 1 : archiveList.length + 1;
    const nextId = `T${String(nextNum).padStart(3, '0')}`;
    const baseSector = RELATIVE_SECTORS[0];

    // Clear detail view, reset workbench
    setSelectedDetailTile(null);
    setCurrentStep('upload');
    setFile(null);
    setFileInfo(null);
    setSavedTile(null);
    setProcessProgress(0);
    setActivePipelineStep(0);
    if (fileInputRef.current) fileInputRef.current.value = "";

    setMetadata({
      tileId: nextId,
      relativeSector: baseSector.name,
      sensor: "Landsat-8",
      date: new Date().toISOString().slice(0, 10),
      lat: String(baseSector.lat),
      lng: String(baseSector.lng),
      bbox: `[${(baseSector.lat - 0.12).toFixed(2)}, ${(baseSector.lng - 0.16).toFixed(2)}, ${(baseSector.lat + 0.13).toFixed(2)}, ${(baseSector.lng + 0.16).toFixed(2)}]`,
      crs: baseSector.crs,
      resolution: baseSector.resolution,
      cloudCover: "4%",
      region: baseSector.region,
      image: baseSector.image
    });

    // Scroll smoothly to MODULE // 07
    setTimeout(() => {
      const el = document.getElementById('data-ingestion');
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    }, 60);
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
        const matchedSector = RELATIVE_SECTORS.find(s => s.name === metadata.relativeSector) || RELATIVE_SECTORS[0];
        const enriched = {
          ...result.tileRecord,
          image: metadata.image || matchedSector.image,
          region: metadata.region || matchedSector.region,
          location: metadata.region || matchedSector.region,
          dateIso: metadata.date,
          temporalPass: `${metadata.date?.slice(0, 4) || '2025'} // Newly Ingested Pass (${metadata.region || matchedSector.region})`
        };
        setSavedTile(enriched);
        setArchiveList(prev => [enriched, ...prev.filter(t => t.id !== enriched.id)]);
        try {
          const stored = localStorage.getItem('sat_intel_archive_tiles');
          const list = stored ? JSON.parse(stored) : [];
          localStorage.setItem('sat_intel_archive_tiles', JSON.stringify([enriched, ...list.filter(t => t.id !== enriched.id)]));
        } catch (err) {}
        if (onTileIngested) {
          onTileIngested(enriched);
        }
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
      setArchiveSuccessToast(`✓ Relative Tile ${savedTile.id} successfully ingested into SQLite Archive for ${savedTile.region}!`);
      setTimeout(() => setArchiveSuccessToast(''), 6000);
    }
    setCurrentStep('success');
  };

  const handleAddAnother = () => {
    handleOpenAddTile();
  };

  const filteredArchive = archiveList.filter(item => {
    // Sensor filter
    if (selectedSensor !== 'ALL') {
      const s = (item.sensor || '').toLowerCase();
      if (!s.includes(selectedSensor.toLowerCase())) return false;
    }
    // Date filter
    if (selectedDate !== 'ALL') {
      const d = (item.date || item.dateIso || '');
      if (!d.includes(selectedDate)) return false;
    }
    // Region filter
    if (selectedRegion !== 'ALL') {
      const r = (item.region || item.location || '').toLowerCase();
      if (!r.includes(selectedRegion.toLowerCase())) return false;
    }
    // Text search filter
    if (searchFilter.trim()) {
      const q = searchFilter.toLowerCase();
      return (
        item.id?.toLowerCase().includes(q) ||
        item.sensor?.toLowerCase().includes(q) ||
        item.region?.toLowerCase().includes(q) ||
        item.location?.toLowerCase().includes(q) ||
        item.date?.toLowerCase().includes(q) ||
        item.dateIso?.toLowerCase().includes(q) ||
        item.status?.toLowerCase().includes(q)
      );
    }
    return true;
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

        {/* Status badges & Quick Jump */}
        <div className="flex items-center gap-3 font-mono text-[11px] flex-wrap">
          <div className="flex items-center gap-1.5 px-3 py-1.5 bg-[#0d1726] border border-[#00e5ff]/40 rounded-sm text-[#00e5ff]">
            <HardDrive className="w-3.5 h-3.5" />
            <span>STORAGE: LOCAL AIR-GAP</span>
          </div>
          <div className="flex items-center gap-1.5 px-3 py-1.5 bg-[#0d1726] border border-[#10b981]/40 rounded-sm text-[#10b981]">
            <Server className="w-3.5 h-3.5" />
            <span>SQLITE &amp; FAISS: INCREMENTAL</span>
          </div>
          <button
            type="button"
            onClick={() => {
              const el = document.getElementById('archive-section');
              if (el) el.scrollIntoView({ behavior: 'smooth' });
            }}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-[#131f33] hover:bg-[#1a2942] border border-[#1e293b] hover:border-[#00e5ff]/50 rounded-sm text-[#94a3b8] hover:text-[#00e5ff] transition-colors cursor-pointer"
          >
            <Database className="w-3.5 h-3.5" />
            <span>[ ARCHIVE CATALOG ↓ ]</span>
          </button>
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

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={handleSaveTile}
                  className="py-3 bg-[#00e5ff] hover:bg-[#9cf0ff] text-[#070e1b] font-mono text-[12px] font-bold uppercase tracking-wider rounded-sm transition-all flex items-center justify-center gap-2 shadow-[0_0_15px_rgba(0,229,255,0.25)] cursor-pointer"
                >
                  <Database className="w-4 h-4" />
                  <span>[ SAVE TILE ]</span>
                </button>
                <button
                  type="button"
                  onClick={() => {
                    handleSaveTile();
                    setSelectedDetailTile(savedTile);
                    const el = document.getElementById('archive-section');
                    if (el) el.scrollIntoView({ behavior: 'smooth' });
                  }}
                  className="py-3 bg-[#131f33] hover:bg-[#1a2942] border border-[#00e5ff]/50 text-[#00e5ff] font-mono text-[12px] font-bold uppercase tracking-wider rounded-sm transition-all flex items-center justify-center gap-2 cursor-pointer"
                >
                  <Database className="w-4 h-4" />
                  <span>[ VIEW IN ARCHIVE ↓ ]</span>
                </button>
              </div>
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
              <div className="grid grid-cols-1 sm:grid-cols-4 gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => {
                    setSelectedDetailTile(savedTile);
                    setArchiveSuccessToast(`✓ Relative Tile ${savedTile.id} successfully ingested into SQLite Archive for ${savedTile.region}!`);
                    const el = document.getElementById('archive-section');
                    if (el) el.scrollIntoView({ behavior: 'smooth' });
                    setTimeout(() => setArchiveSuccessToast(''), 6000);
                  }}
                  className="py-2.5 bg-[#00e5ff] hover:bg-[#9cf0ff] text-[#070e1b] font-mono text-[11px] font-bold uppercase rounded-sm transition-colors flex items-center justify-center gap-1.5 cursor-pointer shadow-[0_0_12px_rgba(0,229,255,0.25)]"
                >
                  <Database className="w-3.5 h-3.5" />
                  [ VIEW IN ARCHIVE ]
                </button>
                <button
                  type="button"
                  onClick={() => onViewTile && onViewTile(savedTile.id)}
                  className="py-2.5 bg-[#131f33] hover:bg-[#00e5ff] hover:text-[#070e1b] border border-[#00e5ff]/40 text-[#00e5ff] font-mono text-[11px] font-bold uppercase rounded-sm transition-colors flex items-center justify-center gap-1.5 cursor-pointer"
                >
                  <Clock className="w-3.5 h-3.5" />
                  [ TEMPORAL COMPARE ]
                </button>
                <button
                  type="button"
                  onClick={() => onSearchTile && onSearchTile(savedTile.sensor + " " + savedTile.region)}
                  className="py-2.5 bg-[#131f33] hover:bg-[#1a2942] border border-[#1e293b] text-white font-mono text-[11px] font-bold uppercase rounded-sm transition-colors flex items-center justify-center gap-1.5 cursor-pointer"
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
        {selectedDetailTile ? (
          /* TILE DETAILS VIEW */
          <div className="bg-[#0b1322] border border-[#00e5ff]/30 rounded-sm p-5 shadow-2xl relative overflow-hidden">
            {/* Top Bar: ← BACK TO ARCHIVE ... TILE T027 */}
            <div className="flex items-center justify-between border-b border-[#1e293b] pb-4 mb-6">
              <button
                type="button"
                onClick={() => setSelectedDetailTile(null)}
                className="flex items-center gap-2 px-3 py-1.5 bg-[#070e1b] hover:bg-[#131f33] text-[#00e5ff] hover:text-white border border-[#00e5ff]/30 rounded-sm font-mono text-[12px] font-bold uppercase transition-colors cursor-pointer"
              >
                <ArrowLeft className="w-4 h-4" />
                ← BACK TO ARCHIVE
              </button>
              <div className="flex items-center gap-2 font-mono">
                <span className="w-2 h-2 rounded-full bg-[#10b981] animate-pulse"></span>
                <span className="text-[16px] font-extrabold text-white tracking-wider">
                  TILE {selectedDetailTile.id}
                </span>
              </div>
            </div>

            {/* Main 2-column info & visual grid */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
              {/* Left Col: Satellite Image visual box with relative sector tiles */}
              <div className="lg:col-span-6 bg-[#070e1b] border border-[#1e293b] rounded-sm p-4 relative flex flex-col justify-between overflow-hidden group">
                <div>
                  {/* Header Labels */}
                  <div className="w-full flex items-center justify-between text-[10px] font-mono text-[#64748b] uppercase tracking-wider mb-2 border-b border-[#1e293b]/60 pb-1.5">
                    <span className="text-[#00e5ff] font-bold flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-[#00e5ff]"></span>
                      RELATIVE TILE // {selectedDetailTile.temporalPass || `${selectedDetailTile.dateIso || selectedDetailTile.date} Pass`}
                    </span>
                    <span className="text-white font-medium">{selectedDetailTile.sensor || 'Landsat-8'}</span>
                  </div>

                  <div className="relative w-full aspect-square max-w-[320px] mx-auto rounded-sm overflow-hidden border border-[#00e5ff]/30 shadow-inner my-2 bg-[#030712] flex items-center justify-center">
                    <img 
                      src={selectedDetailTile.image || "/satellite-tiles/T027_2023.jpg"}
                      alt={`Satellite Tile ${selectedDetailTile.id}`}
                      className="w-full h-full object-cover brightness-95 contrast-105 group-hover:scale-105 transition-transform duration-500"
                      onError={(e) => {
                        e.target.onerror = null;
                        e.target.src = "/satellite-tiles/T027_2023.jpg";
                      }}
                    />
                    
                    {/* Overlay Tactical Reticle */}
                    <div className="absolute inset-0 border border-[#00e5ff]/20 pointer-events-none">
                      <div className="absolute top-0 left-0 w-4 h-4 border-t-2 border-l-2 border-[#00e5ff]"></div>
                      <div className="absolute top-0 right-0 w-4 h-4 border-t-2 border-r-2 border-[#00e5ff]"></div>
                      <div className="absolute bottom-0 left-0 w-4 h-4 border-b-2 border-l-2 border-[#00e5ff]"></div>
                      <div className="absolute bottom-0 right-0 w-4 h-4 border-b-2 border-r-2 border-[#00e5ff]"></div>
                      
                      {/* Center reticle */}
                      <div className="absolute inset-0 flex items-center justify-center">
                        <div className="w-12 h-12 border border-[#00e5ff]/40 rounded-full flex items-center justify-center">
                          <div className="w-1.5 h-1.5 bg-[#00e5ff] rounded-full"></div>
                        </div>
                      </div>
                    </div>

                    {/* Bottom telemetry overlay */}
                    <div className="absolute bottom-2 left-2 right-2 bg-[#070e1b]/85 backdrop-blur-sm px-2.5 py-1 rounded border border-[#1e293b] flex items-center justify-between text-[9px] font-mono text-[#94a3b8]">
                      <span>RES: {selectedDetailTile.resolution || '10m'}</span>
                      <span>FOV: 512×512 PX</span>
                      <span className="text-[#10b981]">GEOLINKED</span>
                    </div>
                  </div>
                </div>

                {/* Relative Tiles In Same Sector */}
                {(() => {
                  const currentLoc = (selectedDetailTile.region || selectedDetailTile.location || 'Kolkata').toLowerCase();
                  const relativeSectorTiles = archiveList.filter(t => {
                    if (t.id === selectedDetailTile.id) return false;
                    const r = (t.region || t.location || '').toLowerCase();
                    return r.includes(currentLoc) || currentLoc.includes(r);
                  });

                  return (
                    <div className="w-full mt-3 pt-3 border-t border-[#1e293b]/70">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-[10px] font-mono text-[#00e5ff] uppercase tracking-wider font-bold flex items-center gap-1.5">
                          <Layers className="w-3.5 h-3.5 text-[#00e5ff]" />
                          RELATIVE TILES // SAME GEOGRAPHIC SECTOR ({selectedDetailTile.region || 'Kolkata'})
                        </span>
                        <span className="text-[9px] font-mono text-[#64748b]">
                          {relativeSectorTiles.length} RELATED PASSES
                        </span>
                      </div>
                      {relativeSectorTiles.length > 0 ? (
                        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                          {relativeSectorTiles.slice(0, 6).map((relTile) => (
                            <button
                              key={relTile.id}
                              type="button"
                              onClick={() => setSelectedDetailTile(relTile)}
                              className="p-1.5 bg-[#0d1726] hover:bg-[#131f33] border border-[#1e293b] hover:border-[#00e5ff] rounded-sm text-left transition-all group cursor-pointer flex items-center gap-2"
                            >
                              <img
                                src={relTile.image || "/satellite-tiles/T027_2023.jpg"}
                                alt={relTile.id}
                                className="w-8 h-8 rounded-sm object-cover border border-[#1e293b] shrink-0"
                              />
                              <div className="min-w-0 font-mono">
                                <div className="text-[11px] font-bold text-white group-hover:text-[#00e5ff] truncate">
                                  {relTile.id}
                                </div>
                                <div className="text-[9px] text-[#64748b] truncate">
                                  {relTile.dateIso || relTile.date}
                                </div>
                              </div>
                            </button>
                          ))}
                        </div>
                      ) : (
                        <div className="text-[10px] font-mono text-[#64748b] italic">
                          Baseline pass for this sector. Additional passes will appear here.
                        </div>
                      )}
                    </div>
                  );
                })()}
              </div>

              {/* Right Col: Tile Information */}
              <div className="lg:col-span-6 bg-[#070e1b] border border-[#1e293b] rounded-sm p-5 flex flex-col justify-between">
                <div>
                  <div className="flex items-center gap-2 border-b border-[#1e293b] pb-2.5 mb-4">
                    <Database className="w-4 h-4 text-[#00e5ff]" />
                    <h4 className="font-mono text-[13px] font-bold text-white uppercase tracking-wider">
                      TILE INFORMATION
                    </h4>
                  </div>

                  <div className="space-y-3 font-mono text-[12px]">
                    <div className="flex justify-between py-1 border-b border-[#1e293b]/60">
                      <span className="text-[#64748b]">Tile ID:</span>
                      <span className="text-[#00e5ff] font-bold">{selectedDetailTile.id}</span>
                    </div>
                    <div className="flex justify-between py-1 border-b border-[#1e293b]/60">
                      <span className="text-[#64748b]">Sensor:</span>
                      <span className="text-white font-medium">{selectedDetailTile.sensor || 'Landsat-8'}</span>
                    </div>
                    <div className="flex justify-between py-1 border-b border-[#1e293b]/60">
                      <span className="text-[#64748b]">Date:</span>
                      <span className="text-white">{selectedDetailTile.dateIso || selectedDetailTile.date || '2023-05-18'}</span>
                    </div>
                    <div className="flex justify-between py-1 border-b border-[#1e293b]/60">
                      <span className="text-[#64748b]">Region:</span>
                      <span className="text-[#9cf0ff] font-medium">{selectedDetailTile.region || selectedDetailTile.location || 'Kolkata Urban'}</span>
                    </div>
                    <div className="flex justify-between py-1 border-b border-[#1e293b]/60">
                      <span className="text-[#64748b]">Cloud Cover:</span>
                      <span className="text-white">{selectedDetailTile.cloudCover || '6%'}</span>
                    </div>
                    <div className="flex justify-between py-1 border-b border-[#1e293b]/60">
                      <span className="text-[#64748b]">Resolution:</span>
                      <span className="text-white">{selectedDetailTile.resolution || '10m'}</span>
                    </div>
                    <div className="flex justify-between py-1 border-b border-[#1e293b]/60">
                      <span className="text-[#64748b]">CRS:</span>
                      <span className="text-[#94a3b8]">{selectedDetailTile.crs || 'EPSG:4326'}</span>
                    </div>
                    <div className="flex justify-between py-1">
                      <span className="text-[#64748b]">Coordinates:</span>
                      <span className="text-[#00e5ff]">{selectedDetailTile.coordinates || `${selectedDetailTile.lat || 22.5726}° N, ${selectedDetailTile.lng || 88.3639}° E`}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* PROCESSING STATUS Checklist */}
            <div className="mt-6 border-t border-[#1e293b] pt-5">
              <div className="text-[11px] font-mono text-[#64748b] uppercase tracking-wider mb-3">
                PROCESSING STATUS
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-2.5">
                <div className="flex items-center gap-2 p-2.5 bg-[#070e1b] border border-[#10b981]/30 rounded-sm font-mono text-[11px] text-[#10b981]">
                  <Check className="w-3.5 h-3.5 text-[#10b981] shrink-0" />
                  <span>Metadata Extracted</span>
                </div>
                <div className="flex items-center gap-2 p-2.5 bg-[#070e1b] border border-[#10b981]/30 rounded-sm font-mono text-[11px] text-[#10b981]">
                  <Check className="w-3.5 h-3.5 text-[#10b981] shrink-0" />
                  <span>Tile Generated</span>
                </div>
                <div className="flex items-center gap-2 p-2.5 bg-[#070e1b] border border-[#10b981]/30 rounded-sm font-mono text-[11px] text-[#10b981]">
                  <Check className="w-3.5 h-3.5 text-[#10b981] shrink-0" />
                  <span>Embedding Generated</span>
                </div>
                <div className="flex items-center gap-2 p-2.5 bg-[#070e1b] border border-[#10b981]/30 rounded-sm font-mono text-[11px] text-[#10b981]">
                  <Check className="w-3.5 h-3.5 text-[#10b981] shrink-0" />
                  <span>FAISS Indexed</span>
                </div>
                <div className="flex items-center gap-2 p-2.5 bg-[#070e1b] border border-[#10b981]/30 rounded-sm font-mono text-[11px] text-[#10b981]">
                  <Check className="w-3.5 h-3.5 text-[#10b981] shrink-0" />
                  <span>Available for Search</span>
                </div>
              </div>
            </div>

            {/* Bottom Actions: [ Temporal Compare ] & [ Search Similar ] */}
            <div className="mt-6 pt-5 border-t border-[#1e293b] flex flex-col sm:flex-row items-center justify-between gap-4">
              <button
                type="button"
                onClick={() => {
                  if (onViewTile) onViewTile(selectedDetailTile.id);
                  setTimeout(() => {
                    const el = document.getElementById('temporal-analysis');
                    if (el) el.scrollIntoView({ behavior: 'smooth' });
                  }, 120);
                }}
                className="w-full sm:w-auto px-6 py-2.5 bg-[#00e5ff] hover:bg-[#9cf0ff] text-[#070e1b] font-mono text-[12px] font-bold uppercase rounded-sm transition-all shadow-[0_0_15px_rgba(0,229,255,0.3)] cursor-pointer flex items-center justify-center gap-2"
              >
                <Clock className="w-4 h-4" />
                [ Temporal Compare ]
              </button>

              <button
                type="button"
                onClick={() => onSearchTile && onSearchTile(selectedDetailTile.sensor + " " + (selectedDetailTile.region || selectedDetailTile.location))}
                className="w-full sm:w-auto px-6 py-2.5 bg-[#131f33] hover:bg-[#1a2d4a] text-[#00e5ff] border border-[#00e5ff]/50 font-mono text-[12px] font-bold uppercase rounded-sm transition-all hover:border-[#00e5ff] cursor-pointer flex items-center justify-center gap-2"
              >
                <Search className="w-4 h-4" />
                [ Search Similar ]
              </button>
            </div>
          </div>
        ) : (
          /* ARCHIVE TABLE & FILTER VIEW */
          <div className="bg-[#0b1322] border border-[#1e293b] rounded-sm p-5 shadow-xl">
            {/* Header: Title + Offline Badge + [ + ADD NEW TILE ] Button */}
            <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
              <div className="flex items-center gap-2.5">
                <Database className="w-5 h-5 text-[#00e5ff]" />
                <h3 className="text-[18px] font-bold text-white font-mono uppercase tracking-wider">
                  SATELLITE TILE ARCHIVE
                </h3>
              </div>
              <div className="flex items-center gap-3">
                <div className="text-[11px] font-mono text-[#64748b] hidden sm:block">
                  OFFLINE SQLITE CATALOG // ZERO-CLOUD
                </div>
                <button
                  type="button"
                  onClick={handleOpenAddTile}
                  className="flex items-center gap-1.5 px-3.5 py-1.5 bg-[#00e5ff] hover:bg-[#9cf0ff] text-[#070e1b] font-mono text-[12px] font-bold uppercase rounded-sm transition-all shadow-[0_0_12px_rgba(0,229,255,0.25)] cursor-pointer"
                >
                  <Plus className="w-4 h-4" />
                  + ADD NEW TILE
                </button>
              </div>
            </div>

            {/* Success Notification Banner */}
            {archiveSuccessToast && (
              <div className="mb-4 p-3 bg-[#10b981]/15 border border-[#10b981]/40 rounded-sm font-mono text-[12px] text-[#10b981] flex items-center justify-between animate-in fade-in duration-200">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-[#10b981]" />
                  <span>{archiveSuccessToast}</span>
                </div>
                <button
                  type="button"
                  onClick={() => setArchiveSuccessToast('')}
                  className="text-[#64748b] hover:text-white cursor-pointer"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            )}

            {/* Filter Bar: 🔎 Search tiles... | Sensor ▼ | Date ▼ | Region ▼ */}
            <div className="grid grid-cols-1 md:grid-cols-12 gap-3 mb-4 p-3 bg-[#070e1b] border border-[#1e293b] rounded-sm">
              {/* Search */}
              <div className="md:col-span-5 relative flex items-center">
                <Search className="w-4 h-4 text-[#64748b] absolute left-3 pointer-events-none" />
                <input
                  type="text"
                  value={searchFilter}
                  onChange={(e) => setSearchFilter(e.target.value)}
                  placeholder="🔎 Search tiles..."
                  className="w-full bg-[#0d1726] border border-[#1e293b] text-white font-mono text-[12px] pl-9 pr-3 py-2 rounded-sm focus:border-[#00e5ff] focus:outline-none placeholder-[#64748b]"
                />
              </div>

              {/* Sensor Dropdown */}
              <div className="md:col-span-2 relative">
                <select
                  value={selectedSensor}
                  onChange={(e) => setSelectedSensor(e.target.value)}
                  className="w-full bg-[#0d1726] border border-[#1e293b] text-white font-mono text-[12px] px-3 py-2 rounded-sm focus:border-[#00e5ff] focus:outline-none appearance-none cursor-pointer"
                >
                  <option value="ALL">Sensor ▼ (All)</option>
                  <option value="Landsat">Landsat</option>
                  <option value="Sentinel">Sentinel</option>
                  <option value="Cartosat">Cartosat</option>
                </select>
                <ChevronDown className="w-3.5 h-3.5 text-[#64748b] absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
              </div>

              {/* Date Dropdown */}
              <div className="md:col-span-2 relative">
                <select
                  value={selectedDate}
                  onChange={(e) => setSelectedDate(e.target.value)}
                  className="w-full bg-[#0d1726] border border-[#1e293b] text-white font-mono text-[12px] px-3 py-2 rounded-sm focus:border-[#00e5ff] focus:outline-none appearance-none cursor-pointer"
                >
                  <option value="ALL">Date ▼ (All)</option>
                  <option value="2020">2020</option>
                  <option value="2021">2021</option>
                  <option value="2022">2022</option>
                  <option value="2023">2023</option>
                  <option value="2024">2024</option>
                  <option value="2025">2025</option>
                </select>
                <ChevronDown className="w-3.5 h-3.5 text-[#64748b] absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
              </div>

              {/* Region Dropdown */}
              <div className="md:col-span-3 relative">
                <select
                  value={selectedRegion}
                  onChange={(e) => setSelectedRegion(e.target.value)}
                  className="w-full bg-[#0d1726] border border-[#1e293b] text-white font-mono text-[12px] px-3 py-2 rounded-sm focus:border-[#00e5ff] focus:outline-none appearance-none cursor-pointer"
                >
                  <option value="ALL">Region ▼ (All)</option>
                  <option value="Kolkata">Kolkata</option>
                  <option value="Ladakh">Ladakh</option>
                  <option value="Arunachal">Arunachal</option>
                  <option value="Galwan">Galwan</option>
                </select>
                <ChevronDown className="w-3.5 h-3.5 text-[#64748b] absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
              </div>
            </div>

            {/* Summary Metrics: Total Tiles | Sensors | Date Range | Regions */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4 p-4 bg-[#070e1b] border border-[#1e293b] rounded-sm font-mono text-center">
              <div className="p-2 border-r border-[#1e293b]/60 last:border-r-0">
                <div className="text-[11px] text-[#64748b] uppercase tracking-wider mb-1">Total Tiles</div>
                <div className="text-[20px] font-extrabold text-[#00e5ff]">
                  {248 + (archiveList.length > 6 ? archiveList.length - 6 : 0)}
                </div>
              </div>
              <div className="p-2 border-r border-[#1e293b]/60 last:border-r-0">
                <div className="text-[11px] text-[#64748b] uppercase tracking-wider mb-1">Sensors</div>
                <div className="text-[17px] font-bold text-white">
                  {selectedSensor === 'ALL' ? 'Landsat' : selectedSensor}
                </div>
              </div>
              <div className="p-2 border-r border-[#1e293b]/60 last:border-r-0">
                <div className="text-[11px] text-[#64748b] uppercase tracking-wider mb-1">Date Range</div>
                <div className="text-[17px] font-bold text-[#9cf0ff]">2020 – 2025</div>
              </div>
              <div className="p-2">
                <div className="text-[11px] text-[#64748b] uppercase tracking-wider mb-1">Regions</div>
                <div className="text-[17px] font-bold text-white">
                  {selectedRegion === 'ALL' ? 'Kolkata' : selectedRegion}
                </div>
              </div>
            </div>

            {/* Table: Tile ID | Date | Sensor | Location | Cloud | Status | Action */}
            <div className="overflow-x-auto border border-[#1e293b] rounded-sm bg-[#070e1b]">
              <table className="w-full text-left font-mono text-[12px]">
                <thead className="bg-[#0b1322] border-b border-[#1e293b] text-[#64748b] text-[10px] uppercase">
                  <tr>
                    <th className="py-3 px-4">Tile ID</th>
                    <th className="py-3 px-4">Date</th>
                    <th className="py-3 px-4">Sensor</th>
                    <th className="py-3 px-4">Location</th>
                    <th className="py-3 px-4">Cloud</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4 text-center">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#1e293b]/60 text-white">
                  {filteredArchive.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="py-8 text-center text-[#64748b]">
                        No satellite tiles match current filter criteria.
                      </td>
                    </tr>
                  ) : (
                    filteredArchive.map((item, idx) => {
                      const isNew = item.id === savedTile?.id;
                      return (
                        <tr 
                          key={item.id || idx}
                          className={`hover:bg-[#131f33]/70 transition-colors ${isNew ? 'bg-[#00e5ff]/10' : ''}`}
                        >
                          <td className="py-3 px-4 font-bold text-[#00e5ff]">
                            <div className="flex items-center gap-1.5">
                              <span>{item.id}</span>
                              {isNew && (
                                <span className="px-1.5 py-0.2 bg-[#00e5ff] text-[#070e1b] text-[8px] font-bold rounded-sm">
                                  NEW
                                </span>
                              )}
                            </div>
                          </td>
                          <td className="py-3 px-4 text-[#94a3b8]">
                            {item.dateIso || item.date}
                          </td>
                          <td className="py-3 px-4 text-white font-medium">
                            {item.sensor}
                          </td>
                          <td className="py-3 px-4 text-[#9cf0ff]">
                            {item.location || item.region || "Kolkata"}
                          </td>
                          <td className="py-3 px-4 text-[#94a3b8]">
                            {item.cloudCover || "08%"}
                          </td>
                          <td className="py-3 px-4">
                            <span className="px-2 py-0.5 bg-[#10b981]/15 text-[#10b981] border border-[#10b981]/30 rounded-sm text-[10px] font-bold inline-flex items-center gap-1">
                              <span className="w-1.5 h-1.5 rounded-full bg-[#10b981]"></span>
                              {item.status || "READY"}
                            </span>
                          </td>
                          <td className="py-3 px-4 text-center">
                            <button
                              type="button"
                              onClick={() => setSelectedDetailTile(item)}
                              className="px-3 py-1 bg-[#131f33] hover:bg-[#00e5ff] hover:text-[#070e1b] border border-[#00e5ff]/40 text-[#00e5ff] text-[11px] font-bold rounded-sm transition-all cursor-pointer shadow-sm"
                            >
                              [ Details ]
                            </button>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
