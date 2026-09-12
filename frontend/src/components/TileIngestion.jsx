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
  ChevronLeft,
  ChevronRight,
  Clock, 
  Plus, 
  X, 
  Target, 
  Image as ImageIcon, 
  Maximize2 
} from 'lucide-react';
import { uploadTile, extractMetadata, processTile, getArchive, API_BASE_URL, ingestStac } from '../services/api';

export default function TileIngestion({ onTileIngested, onViewTile, onSearchTile }) {
  // Wizard steps: 'upload' -> 'metadata' -> 'processing' -> 'record' -> 'success'
  const [currentStep, setCurrentStep] = useState('upload');
  
  // File state
  const [ingestionSource, setIngestionSource] = useState('local'); // 'local' | 'stac'
  const [stacForm, setStacForm] = useState({
    minx: "77.15",
    miny: "28.57",
    maxx: "77.28",
    maxy: "28.67",
    startDate: "2026-01-01",
    endDate: "2026-06-27",
    isDownloading: false
  });
  
  // File state
  const [file, setFile] = useState(null);
  const [fileInfo, setFileInfo] = useState(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef(null);

  // Dynamic metadata form state
  const [metadata, setMetadata] = useState({
    tileId: "sentinel2_tile_new.tif",
    relativeSector: "Northern AOI",
    sensor: "Sentinel-2 MSI",
    date: new Date().toISOString().slice(0, 10),
    lat: "28.6139",
    lng: "77.2090",
    bbox: "[77.15, 28.57, 77.28, 28.67]",
    crs: "EPSG:32643",
    resolution: "10 m",
    cloudCover: "0.0%",
    region: "Northern AOI",
    image: "/satellite-tiles/default.jpg"
  });
  const [isExtracting, setIsExtracting] = useState(false);
  const [ingestError, setIngestError] = useState(null);

  // Processing pipeline states
  const [processProgress, setProcessProgress] = useState(0);
  const [activePipelineStep, setActivePipelineStep] = useState(0);
  const [currentStepName, setCurrentStepName] = useState("Initializing file...");

  // Final saved record & dynamic archive state
  const [savedTile, setSavedTile] = useState(null);
  const [ingestionReport, setIngestionReport] = useState(null);
  const [generatedTilesList, setGeneratedTilesList] = useState([]);
  const [archiveList, setArchiveList] = useState([]);
  const [isLoadingArchive, setIsLoadingArchive] = useState(true);
  
  // Archive filter states
  const [searchFilter, setSearchFilter] = useState("");
  const [selectedSensor, setSelectedSensor] = useState('ALL');
  const [selectedDate, setSelectedDate] = useState('ALL');
  const [selectedRegion, setSelectedRegion] = useState('ALL');
  const [selectedType, setSelectedType] = useState('ALL'); // 'ALL' | 'Full' | 'Tile'
  
  // Archive pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 10;

  const [selectedDetailTile, setSelectedDetailTile] = useState(null);
  const [archiveSuccessToast, setArchiveSuccessToast] = useState('');

  const PIPELINE_STAGES = [
    { id: 1, label: "VALIDATE GEOTIFF HEADERS" },
    { id: 2, label: "EXTRACT SPATIAL METADATA & CRS" },
    { id: 3, label: "GENERATE 256x256 TILES & PYRAMIDS" },
    { id: 4, label: "COMPUTE 512-D VISION EMBEDDING VECTOR" },
    { id: 5, label: "UPDATE QDRANT VECTOR INDEX" },
    { id: 6, label: "INSERT ROW INTO SQLITE REGISTRY" },
    { id: 7, label: "TILE READY FOR SEARCH & DELTA" }
  ];

  // Load real archive on mount
  useEffect(() => {
    loadArchive();
  }, []);

  const loadArchive = async () => {
    setIsLoadingArchive(true);
    try {
      const res = await getArchive();
      if (res.success && res.tiles) {
        setArchiveList(res.tiles);
      }
    } catch (err) {
      console.warn("Failed to load archive:", err);
    } finally {
      setIsLoadingArchive(false);
    }
  };

  // Reset page to 1 when any filter changes
  useEffect(() => {
    setCurrentPage(1);
  }, [searchFilter, selectedSensor, selectedDate, selectedRegion, selectedType]);

  // Reset form to Add New Tile
  const handleOpenAddTile = () => {
    setSelectedDetailTile(null);
    setCurrentStep('upload');
    setFile(null);
    setFileInfo(null);
    setSavedTile(null);
    setProcessProgress(0);
    setActivePipelineStep(0);
    if (fileInputRef.current) fileInputRef.current.value = "";

    const todayStr = new Date().toISOString().slice(0, 10);
    setMetadata({
      tileId: `sentinel2_tile_${archiveList.length + 1}.tif`,
      relativeSector: "Northern AOI",
      sensor: "Sentinel-2 MSI",
      date: todayStr,
      lat: "28.6139",
      lng: "77.2090",
      bbox: "[77.15, 28.57, 77.28, 28.67]",
      crs: "EPSG:32643",
      resolution: "10 m",
      cloudCover: "0.0%",
      region: "Northern AOI",
      image: ""
    });

    setTimeout(() => {
      const el = document.getElementById('data-ingestion');
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 60);
  };

  // Handle file selection and auto-extract metadata from real GeoTIFF
  const handleSelectFile = async (selectedFile) => {
    if (!selectedFile) return;
    setFile(selectedFile);
    
    const sizeStr = selectedFile.size > 1024 * 1024 
      ? `${(selectedFile.size / (1024 * 1024)).toFixed(1)} MB` 
      : `${(selectedFile.size / 1024).toFixed(1)} KB`;
    
    const formatStr = selectedFile.name?.toLowerCase().endsWith('.tif') || selectedFile.name?.toLowerCase().endsWith('.tiff')
      ? 'GeoTIFF'
      : selectedFile.name?.split('.').pop().toUpperCase() || 'GeoTIFF';

    setFileInfo({
      name: selectedFile.name,
      size: sizeStr,
      format: formatStr,
      status: "✓ FILE READY FOR INGESTION"
    });

    // Auto-extract metadata from file via backend POST /metadata/extract
    setIsExtracting(true);
    try {
      const metaRes = await extractMetadata(selectedFile);
      if (metaRes.success && metaRes.metadata) {
        setMetadata(prev => ({
          ...prev,
          ...metaRes.metadata
        }));
      }
    } catch (e) {
      console.warn("Auto metadata extraction warning:", e);
    } finally {
      setIsExtracting(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleSelectFile(e.dataTransfer.files[0]);
    }
  };

  // Quick sample tile selector with real Sentinel-2 tiles fetching real GeoTIFF binary
  const handleLoadSample = async (sampleType = 'summer') => {
    const filename = sampleType === 'summer' ? "sentinel2_tile_1.tif" : "sentinel2_tile_2.tif";
    const date = sampleType === 'summer' ? "2026-06-27" : "2026-01-18";
    const previewUrl = `${API_BASE_URL}/tile-preview?path=${encodeURIComponent(`data/tiles/sentinel2/${date}/${filename}`)}`;

    setIsExtracting(true);
    setIngestError(null);

    try {
      const resp = await fetch(previewUrl);
      if (resp.ok) {
        const blob = await resp.blob();
        const realFile = new File([blob], filename, { type: "image/tiff" });
        await handleSelectFile(realFile);
        return;
      }
    } catch (e) {
      console.warn("Could not fetch binary sample blob, creating fallback:", e);
    }

    const sample = {
      name: filename,
      size: 196608,
      type: "image/tiff"
    };
    
    setFile(sample);
    setFileInfo({
      name: sample.name,
      size: "192 KB (256x256 GeoTIFF)",
      format: "GeoTIFF",
      status: "✓ SAMPLE READY FOR INGESTION"
    });

    setMetadata({
      tileId: sample.name,
      relativeSector: "Northern AOI",
      sensor: "Sentinel-2 MSI",
      date: date,
      lat: "28.6139",
      lng: "77.2090",
      bbox: "[77.15, 28.57, 77.28, 28.67]",
      crs: "EPSG:32643",
      resolution: "10 m",
      cloudCover: "0.0%",
      region: "Northern AOI",
      image: previewUrl
    });
    setIsExtracting(false);
  };

  const handleRemoveFile = () => {
    setFile(null);
    setFileInfo(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
    setCurrentStep('upload');
  };

  // Re-run Auto extract metadata
  const handleAutoExtract = async () => {
    if (!file) return;
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

  const simulatePipelineProcessing = () => {
    setProcessProgress(15);
    setActivePipelineStep(1);
    setCurrentStepName("Fetching STAC metadata and downloading GeoTIFF rasters...");
    setTimeout(() => {
      setProcessProgress(35);
      setActivePipelineStep(2);
      setCurrentStepName("Inspecting GeoTIFF headers, bands, and bounding box CRS...");
    }, 400);
    setTimeout(() => {
      setProcessProgress(55);
      setActivePipelineStep(3);
      setCurrentStepName("Generating 256x256 sub-tiles and spatial pyramids...");
    }, 900);
    setTimeout(() => {
      setProcessProgress(75);
      setActivePipelineStep(4);
      setCurrentStepName("Computing 512-D multimodal vision embeddings with RemoteCLIP...");
    }, 1400);
  };

  // Start processing tile through 7-step incremental ingestion calling POST /ingest/upload
  const handleStacSubmit = async (e) => {
    e.preventDefault();
    const { minx, miny, maxx, maxy, startDate, endDate } = stacForm;
    const bbox = [parseFloat(minx), parseFloat(miny), parseFloat(maxx), parseFloat(maxy)];
    const datetimeRange = `${startDate}/${endDate}`;
    
    setStacForm(prev => ({ ...prev, isDownloading: true }));
    setIngestError(null);
    
    // Simulate steps in UI
    setFileInfo({ name: `Fetching STAC data for ${datetimeRange}`, size: "Remote", format: "Landsat C2 L2" });
    setCurrentStep('processing');
    simulatePipelineProcessing();
    
    const uploadRes = await ingestStac(bbox, datetimeRange, 256, false);
    
    if (uploadRes.success) {
      setStacForm(prev => ({ ...prev, isDownloading: false }));
      
      const backendData = uploadRes.data || {};
      const summary = backendData.summary || {};
      const returnedTiles = backendData.tiles || [];
      const primaryTile = returnedTiles.length > 0 ? returnedTiles[0] : null;
      const tileId = primaryTile?.id || "STAC_Tile";
      
      const tileRecord = {
        id: tileId,
        file: uploadRes.fileInfo.name,
        sensor: "Landsat 8/9 C2 L2",
        date: backendData.date || endDate,
        dateIso: backendData.date || endDate,
        lat: parseFloat(miny) + (parseFloat(maxy) - parseFloat(miny))/2,
        lng: parseFloat(minx) + (parseFloat(maxx) - parseFloat(minx))/2,
        bbox: `[${minx}, ${miny}, ${maxx}, ${maxy}]`,
        resolution: "30 m",
        crs: "EPSG:4326",
        cloudCover: "0.0%",
        region: "Custom STAC AOI",
        image: primaryTile ? `${API_BASE_URL}/tile-preview-jpg?path=${encodeURIComponent(primaryTile.filepath)}` : '/satellite-tiles/default.jpg',
        imageType: 'Full',
        status: "ACTIVE",
        similarity: 98,
        backendSummary: summary
      };
      
      setSavedTile(tileRecord);
      setIngestionReport({
        extracted: summary.tiles_new || 1,
        indexed: summary.qdrant_points_added || 1,
        timeMs: 2540
      });
      setGeneratedTilesList(returnedTiles);
      setCurrentStep('success');
      setArchiveList(prev => [tileRecord, ...prev]);
      if (onTileIngested) onTileIngested(tileRecord);
    } else {
      setStacForm(prev => ({ ...prev, isDownloading: false }));
      setIngestError(uploadRes.error || "STAC Ingestion Failed.");
      setCurrentStep('upload');
    }
  };

  const processUploadedFile = async () => {
    setCurrentStep('processing');
    setIngestError(null);

    setCurrentStep('processing');
    setProcessProgress(15);
    setActivePipelineStep(1);
    setCurrentStepName("Uploading GeoTIFF rasters to POST /ingest/upload...");

    const t1 = setTimeout(() => {
      setProcessProgress(35);
      setActivePipelineStep(2);
      setCurrentStepName("Inspecting GeoTIFF headers, bands, and bounding box CRS...");
    }, 400);

    const t2 = setTimeout(() => {
      setProcessProgress(55);
      setActivePipelineStep(3);
      setCurrentStepName("Generating 256x256 sub-tiles and spatial pyramids...");
    }, 900);

    const t3 = setTimeout(() => {
      setProcessProgress(75);
      setActivePipelineStep(4);
      setCurrentStepName("Computing 512-D multimodal vision embeddings with RemoteCLIP...");
    }, 1400);

    try {
      // Ingest via backend /ingest/upload API
      const result = await processTile(file, metadata);
      clearTimeout(t1);
      clearTimeout(t2);
      clearTimeout(t3);

      if (!result.success) {
        setIngestError(result.error || "Backend /ingest/upload request failed.");
        setCurrentStepName(`Error: ${result.error || "Ingestion failed"}`);
        return;
      }

      setProcessProgress(90);
      setActivePipelineStep(5);
      setCurrentStepName("Adding vectors to Qdrant vector index and SQLite registry...");

      setTimeout(async () => {
        setProcessProgress(100);
        setActivePipelineStep(7);
        setCurrentStepName("Ingestion & indexing complete ✓");

        if (result.tileRecord) {
          const rep = result.summary || {};
          const tiles = result.allTiles || [];
          setIngestionReport(rep);
          setGeneratedTilesList(tiles);

          const enriched = {
            ...result.tileRecord,
            image: result.tileRecord.image || metadata.image || `${API_BASE_URL}/tile-preview?path=${encodeURIComponent(`data/tiles/sentinel2/${metadata.date}/${metadata.tileId}`)}`,
            region: metadata.region || "Northern AOI",
            location: metadata.region || "Northern AOI",
            dateIso: metadata.date,
            temporalPass: `${metadata.date} // Ingested Pass (${metadata.region || 'AOI'})`,
            tilesGenerated: rep.tiles_discovered || (tiles.length > 0 ? tiles.length : 1),
            embeddingsCount: rep.embeddings_generated || (tiles.length > 0 ? tiles.length : 1),
            qdrantCount: rep.qdrant_points_added || (tiles.length > 0 ? tiles.length : 1)
          };
          setSavedTile(enriched);
          
          // Refresh full archive from backend
          await loadArchive();

          if (onTileIngested) {
            onTileIngested(enriched);
          }
          setTimeout(() => {
            setCurrentStep('record');
          }, 500);
        }
      }, 500);
    } catch (err) {
      clearTimeout(t1);
      clearTimeout(t2);
      clearTimeout(t3);
      console.error("Ingestion failed:", err);
      setIngestError(err.message || "Failed to communicate with backend /ingest/upload");
      setCurrentStepName(`Error: ${err.message}`);
    }
  };

  const handleStartProcessing = async () => {
    if (!file) return;
    await processUploadedFile();
  };

  const handleSaveTile = async () => {
    // 1. Refresh full live archive from SQLite database
    await loadArchive();

    // 2. Reset filters so the newly ingested tiles are immediately visible at the top of Page 1
    setSelectedSensor('ALL');
    setSelectedDate('ALL');
    setSelectedRegion('ALL');
    setSelectedType('ALL');
    setSearchFilter('');
    setCurrentPage(1);

    if (savedTile) {
      if (onTileIngested) {
        onTileIngested(savedTile);
      }
      setArchiveSuccessToast(`✓ Tiles for ${savedTile.date} successfully registered in SQLite Archive!`);
      setTimeout(() => setArchiveSuccessToast(''), 6000);
    }
    setCurrentStep('success');
  };

  // Helper to identify if an item is a Full image or a Sub-tile
  const getItemType = (item) => {
    if (item.imageType) return item.imageType;
    const name = (item.file || item.id || '').toLowerCase();
    if (name.includes('full') || name.includes('scene') || name.includes('mosaic') || (item.width && item.width > 512)) {
      return 'Full';
    }
    return 'Tile';
  };

  // Dynamic filter options derived from real archiveList
  const uniqueSensors = ['ALL', ...new Set(archiveList.map(t => t.sensor).filter(Boolean))];
  const uniqueDates = ['ALL', ...new Set(archiveList.map(t => (t.date || t.dateIso || '').slice(0, 4)).filter(Boolean))].sort();
  const uniqueRegions = ['ALL', ...new Set(archiveList.map(t => t.region || t.location).filter(Boolean))].sort();

  // Dynamic summary metrics
  const totalArchiveCount = archiveList.length;
  const datesArray = archiveList.map(t => t.date || t.dateIso).filter(Boolean).sort();
  const earliestYear = datesArray.length > 0 ? datesArray[0].slice(0, 4) : "2025";
  const latestYear = datesArray.length > 0 ? datesArray[datesArray.length - 1].slice(0, 4) : "2026";
  const dateRangeStr = earliestYear === latestYear ? earliestYear : `${earliestYear} – ${latestYear}`;

  // Filtered Archive List
  const filteredArchive = archiveList.filter(item => {
    if (selectedSensor !== 'ALL') {
      const s = (item.sensor || '').toLowerCase();
      if (!s.includes(selectedSensor.toLowerCase())) return false;
    }
    if (selectedDate !== 'ALL') {
      const d = (item.date || item.dateIso || '');
      if (!d.includes(selectedDate)) return false;
    }
    if (selectedRegion !== 'ALL') {
      const r = (item.region || item.location || '').toLowerCase();
      if (!r.includes(selectedRegion.toLowerCase())) return false;
    }
    if (selectedType !== 'ALL') {
      const type = getItemType(item);
      if (type !== selectedType) return false;
    }
    if (searchFilter.trim()) {
      const q = searchFilter.toLowerCase();
      const typeStr = getItemType(item).toLowerCase();
      return (
        item.id?.toLowerCase().includes(q) ||
        item.file?.toLowerCase().includes(q) ||
        item.sensor?.toLowerCase().includes(q) ||
        item.region?.toLowerCase().includes(q) ||
        item.location?.toLowerCase().includes(q) ||
        item.date?.toLowerCase().includes(q) ||
        item.dateIso?.toLowerCase().includes(q) ||
        item.status?.toLowerCase().includes(q) ||
        typeStr.includes(q)
      );
    }
    return true;
  });

  // Pagination calculation
  const totalPages = Math.ceil(filteredArchive.length / itemsPerPage) || 1;
  const safeCurrentPage = Math.min(Math.max(currentPage, 1), totalPages);
  const startIndex = (safeCurrentPage - 1) * itemsPerPage;
  const paginatedArchive = filteredArchive.slice(startIndex, startIndex + itemsPerPage);

  // Generate page numbers array (sliding window of 5 pages)
  const getPageNumbers = () => {
    const pages = [];
    const maxButtons = 5;
    let start = Math.max(1, safeCurrentPage - Math.floor(maxButtons / 2));
    let end = Math.min(totalPages, start + maxButtons - 1);
    if (end - start + 1 < maxButtons) {
      start = Math.max(1, end - maxButtons + 1);
    }
    for (let i = start; i <= end; i++) {
      pages.push(i);
    }
    return pages;
  };

  return (
    <section className="w-full py-16 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto border-b border-cyan-500/25/40" id="data-ingestion">
      {/* Section Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-8 pb-3 border-b border-cyan-500/25">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-pulse shadow-[0_0_8px_rgba(0,229,255,0.8)]"></span>
            <span className="text-xs font-bold uppercase tracking-wider text-cyan-300">
              Module: Ingestion &amp; Archive
            </span>
          </div>
          <h2 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            Add New Satellite Tile
          </h2>
          <p className="text-[14px] text-[#94a3b8] mt-1">
            Offline ingestion pipeline: Extract genuine GeoTIFF metadata, generate multimodal vision embeddings, and incrementally append vectors to Qdrant &amp; SQLite catalog.
          </p>
        </div>

        {/* Status badges & Quick Jump */}
        <div className="flex items-center gap-3 font-mono text-[11px] flex-wrap">
          <div className="flex items-center gap-1.5 px-3 py-1.5 bg-[#061024]/90 backdrop-blur-xl border border-cyan-500/30 rounded-xl text-[#00e5ff]">
            <HardDrive className="w-3.5 h-3.5" />
            <span>STORAGE: LOCAL AIR-GAP</span>
          </div>
          <div className="flex items-center gap-1.5 px-3 py-1.5 bg-[#061024]/90 backdrop-blur-xl border border-[#10b981]/40 rounded-xl text-[#10b981]">
            <Server className="w-3.5 h-3.5" />
            <span>SQLITE &amp; QDRANT: INCREMENTAL</span>
          </div>
          <button
            type="button"
            onClick={() => {
              const el = document.getElementById('archive-section');
              if (el) el.scrollIntoView({ behavior: 'smooth' });
            }}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800/80 hover:bg-[#1a2942] border border-cyan-500/25 hover:border-[#00e5ff]/50 rounded-xl text-[#94a3b8] hover:text-[#00e5ff] transition-colors cursor-pointer"
          >
            <Database className="w-3.5 h-3.5" />
            <span>Archive Catalog ({totalArchiveCount}) ↓</span>
          </button>
        </div>
      </div>

      {/* Main Ingestion Workbench */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-16 items-stretch">
        {/* Left Side: Upload & Workflow Cards */}
        <div className="flex flex-col justify-stretch h-full">

          {/* STEP 1: UPLOAD TILE */}
          {currentStep === 'upload' && (
            <div className="space-y-4 h-full flex flex-col">
              <div className="flex gap-2 mb-2 p-1 bg-[#061024]/50 backdrop-blur-xl border border-cyan-500/30 rounded-xl">
                <button 
                  onClick={() => setIngestionSource('local')}
                  className={`flex-1 py-2 px-4 rounded-lg text-sm font-semibold transition-all ${ingestionSource === 'local' ? 'bg-cyan-500/20 text-[#00e5ff] border border-cyan-500/50' : 'text-[#94a3b8] hover:text-white'}`}
                >
                  Local File Upload
                </button>
                <button 
                  onClick={() => setIngestionSource('stac')}
                  className={`flex-1 py-2 px-4 rounded-lg text-sm font-semibold transition-all ${ingestionSource === 'stac' ? 'bg-cyan-500/20 text-[#00e5ff] border border-cyan-500/50' : 'text-[#94a3b8] hover:text-white'}`}
                >
                  Landsat STAC API
                </button>
              </div>

              {!fileInfo && ingestionSource === 'local' && (
                /* Drag & Drop Area */
                <div
                  onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
                  onDragLeave={() => setIsDragOver(false)}
                  onDrop={handleDrop}
                  onClick={() => fileInputRef.current?.click()}
                  className={`border-2 border-dashed rounded-xl p-8 flex flex-col items-center justify-center text-center cursor-pointer transition-all duration-200 h-full min-h-[340px] ${
                    isDragOver
                      ? 'border-[#00e5ff] bg-[#00e5ff]/10 shadow-[0_0_24px_rgba(0,229,255,0.2)]'
                      : 'border-cyan-500/25 hover:border-[#00e5ff]/50 bg-[#061024]/90 backdrop-blur-xl'
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
                  <div className="w-16 h-16 rounded-full bg-slate-800/80 border border-cyan-500/30 flex items-center justify-center mb-4 text-[#00e5ff] shadow-[0_0_15px_rgba(0,229,255,0.15)]">
                    <UploadCloud className="w-8 h-8" />
                  </div>
                  <div className="font-mono text-[14px] font-bold text-white uppercase tracking-wider mb-2">
                    DROP SATELLITE TILE HERE
                  </div>
                  <div className="text-[12px] text-[#00e5ff] font-mono mb-3 font-semibold">
                    Browse GeoTIFF or Image
                  </div>
                  <p className="font-mono text-[11px] text-[#64748b]">
                    GeoTIFF / TIFF / PNG / JPG • Automatic Metadata Extraction &amp; Embedding via /ingest/upload
                  

                  {/* Sample pills */}
                  <div className="mt-6 pt-4 border-t border-cyan-500/25 flex items-center gap-2 flex-wrap justify-center">
                    <span className="font-mono text-[10px] text-[#64748b] uppercase">SAMPLE RECON TILES:</span>
                    <button
                      type="button"
                      onClick={(e) => { e.stopPropagation(); handleLoadSample('summer'); }}
                      className="px-2.5 py-1 bg-slate-800/80 hover:bg-[#1a2942] border border-cyan-500/30 text-[#9cf0ff] font-mono text-[10px] rounded-xl transition-colors cursor-pointer"
                    >
                      Sentinel-2 Summer Pass (2026-06-27)
                    </button>
                    <button
                      type="button"
                      onClick={(e) => { e.stopPropagation(); handleLoadSample('winter'); }}
                      className="px-2.5 py-1 bg-slate-800/80 hover:bg-[#1a2942] border border-cyan-500/25 text-[#94a3b8] hover:text-[#00e5ff] font-mono text-[10px] rounded-xl transition-colors cursor-pointer"
                    >
                      Sentinel-2 Winter Pass (2026-01-18)
                    </button>
                  </div>
                           </p>
                </div>
              )}

              {!fileInfo && ingestionSource === 'stac' && (
                <div className="bg-[#061024]/90 backdrop-blur-xl border border-cyan-500/25 rounded-xl p-6 h-full min-h-[340px] flex flex-col">
                  <h3 className="text-lg font-bold text-white mb-1">Microsoft Planetary Computer</h3>
                  <p className="text-xs text-[#94a3b8] mb-6">Download Landsat 8/9 C2 L2 Surface Reflectance via STAC API</p>
                  
                  <form onSubmit={handleStacSubmit} className="space-y-4 flex-1">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-xs font-medium text-[#94a3b8] mb-1">Min Longitude (X)</label>
                        <input type="text" value={stacForm.minx} onChange={e => setStacForm({...stacForm, minx: e.target.value})} required className="w-full bg-slate-900/80 border border-cyan-500/30 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-[#00e5ff]" />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-[#94a3b8] mb-1">Min Latitude (Y)</label>
                        <input type="text" value={stacForm.miny} onChange={e => setStacForm({...stacForm, miny: e.target.value})} required className="w-full bg-slate-900/80 border border-cyan-500/30 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-[#00e5ff]" />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-[#94a3b8] mb-1">Max Longitude (X)</label>
                        <input type="text" value={stacForm.maxx} onChange={e => setStacForm({...stacForm, maxx: e.target.value})} required className="w-full bg-slate-900/80 border border-cyan-500/30 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-[#00e5ff]" />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-[#94a3b8] mb-1">Max Latitude (Y)</label>
                        <input type="text" value={stacForm.maxy} onChange={e => setStacForm({...stacForm, maxy: e.target.value})} required className="w-full bg-slate-900/80 border border-cyan-500/30 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-[#00e5ff]" />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-[#94a3b8] mb-1">Start Date</label>
                        <input type="date" value={stacForm.startDate} onChange={e => setStacForm({...stacForm, startDate: e.target.value})} required className="w-full bg-slate-900/80 border border-cyan-500/30 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-[#00e5ff]" />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-[#94a3b8] mb-1">End Date</label>
                        <input type="date" value={stacForm.endDate} onChange={e => setStacForm({...stacForm, endDate: e.target.value})} required className="w-full bg-slate-900/80 border border-cyan-500/30 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-[#00e5ff]" />
                      </div>
                    </div>
                    
                    <button
                      type="submit"
                      disabled={stacForm.isDownloading}
                      className="mt-6 w-full flex items-center justify-center gap-2 py-3 bg-[#00e5ff] text-slate-900 font-bold rounded-xl hover:bg-[#00c4d9] transition-all"
                    >
                      {stacForm.isDownloading ? (
                        <><RefreshCw className="w-5 h-5 animate-spin" /> Fetching & Ingesting...</>
                      ) : (
                        <><UploadCloud className="w-5 h-5" /> Download & Ingest STAC Data</>
                      )}
                    </button>
                  </form>
                </div>
              )}

              {fileInfo && (
                <div className="bg-[#061024]/90 backdrop-blur-xl border border-cyan-500/30 p-6 rounded-xl space-y-4">
                  <div className="flex items-center justify-between pb-3 border-b border-cyan-500/25 font-mono text-[12px]">
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

                  <div className="flex items-center gap-3 pt-3 border-t border-cyan-500/25">
                    <button
                      type="button"
                      onClick={handleRemoveFile}
                      className="px-4 py-2 bg-[#93000a]/20 hover:bg-[#93000a]/40 border border-[#ef4444] text-[#ffb4ab] font-mono text-[11px] font-bold uppercase rounded-xl transition-colors flex items-center gap-1.5 cursor-pointer"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                      [ REMOVE ]
                    </button>
                    <button
                      type="button"
                      onClick={() => setCurrentStep('metadata')}
                      className="flex-1 py-2.5 bg-[#00e5ff] hover:bg-[#9cf0ff] text-[#070e1b] font-mono text-[12px] font-bold uppercase tracking-wider rounded-xl transition-all flex items-center justify-center gap-2 shadow-[0_0_12px_rgba(0,229,255,0.25)] cursor-pointer"
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
            <div className="bg-[#061024]/90 backdrop-blur-xl border border-cyan-500/30 p-6 rounded-xl">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 pb-3 mb-4 border-b border-cyan-500/25">
                <div>
                  <h3 className="font-mono text-[14px] text-white font-bold uppercase">
                    TILE INFORMATION &amp; SPATIAL INDEXING
                  </h3>
                  <p className="font-mono text-[11px] text-[#64748b]">
                    Extracted directly from GeoTIFF headers and radiometric tags.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={handleAutoExtract}
                  disabled={isExtracting}
                  className="px-3 py-1.5 bg-slate-800/80 hover:bg-[#1a2942] border border-[#00e5ff]/50 text-[#00e5ff] font-mono text-[11px] font-bold rounded-xl transition-colors flex items-center gap-1.5 self-start sm:self-center cursor-pointer"
                >
                  <Sparkles className="w-3.5 h-3.5 text-[#00e5ff]" />
                  {isExtracting ? "EXTRACTING..." : "[ RE-EXTRACT METADATA ]"}
                </button>
              </div>

              {/* Form Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 font-mono text-[12px]">
                <div>
                  <label className="text-[#64748b] text-[10px] uppercase block mb-1">Tile ID / Filename</label>
                  <input
                    type="text"
                    value={metadata.tileId}
                    onChange={(e) => setMetadata({ ...metadata, tileId: e.target.value })}
                    className="w-full bg-[#030814]/90 border border-cyan-500/25 text-white px-3 py-2 rounded-xl focus:border-[#00e5ff] focus:outline-none"
                  />
                </div>

                <div>
                  <label className="text-[#64748b] text-[10px] uppercase block mb-1">Satellite / Sensor</label>
                  <input
                    type="text"
                    value={metadata.sensor}
                    onChange={(e) => setMetadata({ ...metadata, sensor: e.target.value })}
                    className="w-full bg-[#030814]/90 border border-cyan-500/25 text-white px-3 py-2 rounded-xl focus:border-[#00e5ff] focus:outline-none"
                  />
                </div>

                <div>
                  <label className="text-[#64748b] text-[10px] uppercase block mb-1">Acquisition Date</label>
                  <input
                    type="date"
                    value={metadata.date}
                    onChange={(e) => setMetadata({ ...metadata, date: e.target.value })}
                    className="w-full bg-[#030814]/90 border border-cyan-500/25 text-white px-3 py-2 rounded-xl focus:border-[#00e5ff] focus:outline-none"
                  />
                </div>

                <div>
                  <label className="text-[#64748b] text-[10px] uppercase block mb-1">Region / Sector</label>
                  <input
                    type="text"
                    value={metadata.region}
                    onChange={(e) => setMetadata({ ...metadata, region: e.target.value })}
                    className="w-full bg-[#030814]/90 border border-cyan-500/25 text-white px-3 py-2 rounded-xl focus:border-[#00e5ff] focus:outline-none"
                  />
                </div>

                <div>
                  <label className="text-[#64748b] text-[10px] uppercase block mb-1">Center Latitude</label>
                  <input
                    type="text"
                    value={metadata.lat}
                    onChange={(e) => setMetadata({ ...metadata, lat: e.target.value })}
                    className="w-full bg-[#030814]/90 border border-cyan-500/25 text-white px-3 py-2 rounded-xl focus:border-[#00e5ff] focus:outline-none"
                  />
                </div>

                <div>
                  <label className="text-[#64748b] text-[10px] uppercase block mb-1">Center Longitude</label>
                  <input
                    type="text"
                    value={metadata.lng}
                    onChange={(e) => setMetadata({ ...metadata, lng: e.target.value })}
                    className="w-full bg-[#030814]/90 border border-cyan-500/25 text-white px-3 py-2 rounded-xl focus:border-[#00e5ff] focus:outline-none"
                  />
                </div>

                <div>
                  <label className="text-[#64748b] text-[10px] uppercase block mb-1">Resolution</label>
                  <input
                    type="text"
                    value={metadata.resolution}
                    onChange={(e) => setMetadata({ ...metadata, resolution: e.target.value })}
                    className="w-full bg-[#030814]/90 border border-cyan-500/25 text-white px-3 py-2 rounded-xl focus:border-[#00e5ff] focus:outline-none"
                  />
                </div>

                <div>
                  <label className="text-[#64748b] text-[10px] uppercase block mb-1">CRS Projection</label>
                  <input
                    type="text"
                    value={metadata.crs}
                    onChange={(e) => setMetadata({ ...metadata, crs: e.target.value })}
                    className="w-full bg-[#030814]/90 border border-cyan-500/25 text-white px-3 py-2 rounded-xl focus:border-[#00e5ff] focus:outline-none"
                  />
                </div>

                <div>
                  <label className="text-[#64748b] text-[10px] uppercase block mb-1">Cloud Cover</label>
                  <input
                    type="text"
                    value={metadata.cloudCover}
                    onChange={(e) => setMetadata({ ...metadata, cloudCover: e.target.value })}
                    className="w-full bg-[#030814]/90 border border-cyan-500/25 text-white px-3 py-2 rounded-xl focus:border-[#00e5ff] focus:outline-none"
                  />
                </div>

                <div>
                  <label className="text-[#64748b] text-[10px] uppercase block mb-1">Bounding Box</label>
                  <input
                    type="text"
                    value={metadata.bbox}
                    onChange={(e) => setMetadata({ ...metadata, bbox: e.target.value })}
                    className="w-full bg-[#030814]/90 border border-cyan-500/25 text-white px-3 py-2 rounded-xl focus:border-[#00e5ff] focus:outline-none"
                  />
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center justify-between gap-3 mt-6 pt-4 border-t border-cyan-500/25">
                <button
                  type="button"
                  onClick={() => setCurrentStep('upload')}
                  className="px-4 py-2 bg-slate-800/80 hover:bg-[#1a2942] border border-cyan-500/25 text-[#94a3b8] hover:text-white font-mono text-[11px] font-semibold rounded-xl transition-colors cursor-pointer"
                >
                  ← BACK TO FILE
                </button>
                <button
                  type="button"
                  onClick={handleStartProcessing}
                  className="px-6 py-2.5 bg-[#00e5ff] hover:bg-[#9cf0ff] text-[#070e1b] font-mono text-[12px] font-bold uppercase tracking-wider rounded-xl transition-all flex items-center gap-2 shadow-[0_0_15px_rgba(0,229,255,0.25)] cursor-pointer"
                >
                  <Cpu className="w-4 h-4" />
                  <span>[ PROCESS &amp; INDEX TILE ]</span>
                </button>
              </div>
            </div>
          )}

          {/* STEP 3: TILE PROCESSING PROGRESS */}
          {currentStep === 'processing' && (
            <div className="bg-[#061024]/90 backdrop-blur-xl border border-[#00e5ff]/50 p-6 rounded-xl space-y-6 shadow-[0_0_24px_rgba(0,229,255,0.1)]">
              <div>
                <div className="flex items-center justify-between font-mono text-[12px] mb-2">
                  <span className="text-white font-bold uppercase tracking-wider">PROCESSING NEW TILE</span>
                  <span className="text-[#00e5ff] font-bold">{processProgress}%</span>
                </div>
                              {/* Ingest Error Alert */}
              {ingestError && (
                <div className="bg-[#ef4444]/10 border border-[#ef4444]/50 p-4 rounded-xl space-y-3 font-mono">
                  <div className="flex items-center gap-2 text-[#ef4444] font-bold text-[12px]">
                    <AlertCircle className="w-4 h-4" />
                    <span>INGESTION PIPELINE ERROR (/ingest/upload)</span>
                  </div>
                  <div className="text-[#fca5a5] text-[11px] bg-[#030814]/90 p-3 border border-[#ef4444]/30 rounded-xl">
                    {ingestError}
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => { setIngestError(null); setCurrentStep('metadata'); }}
                      className="px-3 py-1.5 bg-[#ef4444]/20 hover:bg-[#ef4444]/30 text-[#fca5a5] border border-[#ef4444]/50 rounded-xl text-[11px] font-bold"
                    >
                      ← Back to Metadata / Fix Details
                    </button>
                    <button
                      onClick={handleStartProcessing}
                      className="px-3 py-1.5 bg-[#00e5ff] hover:bg-[#00c8e0] text-[#070e1b] rounded-xl text-[11px] font-bold"
                    >
                      ⟳ Retry Ingestion
                    </button>
                  </div>
                </div>
              )}

              {/* Error Message */}
                <div className="w-full h-3 bg-[#030814]/90 border border-cyan-500/25 rounded-xl overflow-hidden p-0.5">
                  <div 
                    className="h-full bg-gradient-to-r from-[#00e5ff] to-[#10b981] transition-all duration-300 rounded-lg"
                    style={{ width: `${processProgress}%` }}
                  ></div>
                </div>
                <div className="font-mono text-[11px] text-[#9cf0ff] mt-2 flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-[#00e5ff] animate-pulse"></span>
                  <span>Current step: {currentStepName}</span>
                </div>
              </div>

              {/* 7-Step Vertical Flow Pipeline */}
              <div className="border border-cyan-500/25 bg-[#030814]/90 p-4 rounded-xl space-y-2">
                <div className="font-mono text-[10px] text-[#64748b] uppercase pb-2 border-b border-cyan-500/25">
                  INGESTION PIPELINE EXECUTION
                </div>
                <div className="space-y-1.5 font-mono text-[11px]">
                  <div className="p-1.5 text-[#64748b]">IMAGE TARGET: {fileInfo?.name || metadata.tileId}</div>
                  {PIPELINE_STAGES.map((st, idx) => {
                    const isDone = activePipelineStep > idx;
                    const isCurrent = activePipelineStep === idx + 1;
                    return (
                      <div
                        key={st.id}
                        className={`p-2 rounded-xl border flex items-center justify-between transition-all ${
                          isCurrent
                            ? 'bg-slate-800/80 border-[#00e5ff] text-[#00e5ff]'
                            : isDone
                            ? 'bg-[#061024]/90 backdrop-blur-xl border-cyan-500/25 text-white'
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

          {/* STEP 4: DATABASE RECORD PREVIEW & INGESTION TELEMETRY */}
          {currentStep === 'record' && savedTile && (
            <div className="bg-[#061024]/90 backdrop-blur-xl border border-[#00e5ff]/50 p-6 rounded-xl space-y-5">
              <div className="flex items-center justify-between pb-3 border-b border-cyan-500/25 font-mono text-[12px]">
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 bg-[#10b981] rounded-full animate-pulse"></span>
                  <span className="text-white font-bold uppercase tracking-wider">INGESTION &amp; INDEXING TELEMETRY</span>
                </div>
                <span className="px-2.5 py-0.5 bg-[#10b981]/20 text-[#10b981] border border-[#10b981]/40 text-[10px] font-bold uppercase">
                  ● PIPELINE COMPLETE ✓
                </span>
              </div>

              {/* 4 Pipeline Stat Metrics */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 font-mono text-center">
                <div className="bg-[#030814]/90 border border-cyan-500/25 p-3 rounded-xl">
                  <div className="text-[10px] text-[#64748b] uppercase">Tiles Generated</div>
                  <div className="text-[18px] font-extrabold text-[#00e5ff] mt-0.5">
                    {ingestionReport?.tiles_discovered || generatedTilesList.length || 1}
                  </div>
                  <div className="text-[9px] text-[#94a3b8] mt-0.5">256x256 GeoTIFFs</div>
                </div>
                <div className="bg-[#030814]/90 border border-cyan-500/25 p-3 rounded-xl">
                  <div className="text-[10px] text-[#64748b] uppercase">Vision Embeddings</div>
                  <div className="text-[18px] font-extrabold text-[#10b981] mt-0.5">
                    {ingestionReport?.embeddings_generated || (ingestionReport?.tiles_discovered ? ingestionReport.tiles_discovered : generatedTilesList.length) || 1}
                  </div>
                  <div className="text-[9px] text-[#94a3b8] mt-0.5">512-D RemoteCLIP</div>
                </div>
                <div className="bg-[#030814]/90 border border-cyan-500/25 p-3 rounded-xl">
                  <div className="text-[10px] text-[#64748b] uppercase">Qdrant Points</div>
                  <div className="text-[18px] font-extrabold text-[#c084fc] mt-0.5">
                    {ingestionReport?.qdrant_points_added || (ingestionReport?.tiles_discovered ? ingestionReport.tiles_discovered : generatedTilesList.length) || 1}
                  </div>
                  <div className="text-[9px] text-[#94a3b8] mt-0.5">collection: satellite_tiles</div>
                </div>
                <div className="bg-[#030814]/90 border border-cyan-500/25 p-3 rounded-xl">
                  <div className="text-[10px] text-[#64748b] uppercase">SQLite Rows</div>
                  <div className="text-[18px] font-extrabold text-[#38bdf8] mt-0.5">
                    {generatedTilesList.length || (ingestionReport?.tiles_discovered ? ingestionReport.tiles_discovered + 1 : 2)}
                  </div>
                  <div className="text-[9px] text-[#94a3b8] mt-0.5">tiles &amp; images tables</div>
                </div>
              </div>

              {/* Generated Sub-Tiles Preview Grid */}
              {generatedTilesList.length > 0 && (
                <div className="bg-[#030814]/90 border border-cyan-500/25 p-4 rounded-xl space-y-3 font-mono">
                  <div className="flex items-center justify-between text-[11px] text-[#64748b] uppercase pb-2 border-b border-cyan-500/25">
                    <span>GENERATED SUB-TILES &amp; COMPOSITE ({generatedTilesList.length} TOTAL)</span>
                    <span className="text-[#00e5ff]">QDRANT &amp; SQLITE SYNCED ✓</span>
                  </div>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 max-h-48 overflow-y-auto pr-1">
                    {generatedTilesList.map((t, idx) => {
                      const isFull = t.imageType === 'Full';
                      const previewUrl = `${API_BASE_URL}/tile-preview?path=${encodeURIComponent(t.filepath)}`;
                      return (
                        <div key={t.id || idx} className="bg-[#061024]/90 backdrop-blur-xl border border-cyan-500/25 p-2 rounded-xl space-y-1">
                          <div className="relative aspect-square bg-[#030814]/90 rounded-xl overflow-hidden border border-cyan-500/25/60">
                            <img src={previewUrl} alt={t.file} className="w-full h-full object-cover" />
                            <span className={`absolute top-1 right-1 px-1 py-0.2 text-[8px] font-bold rounded-xl ${isFull ? 'bg-[#8b5cf6] text-white' : 'bg-[#00e5ff] text-[#070e1b]'}`}>
                              {isFull ? 'FULL' : 'TILE'}
                            </span>
                          </div>
                          <div className="text-[10px] text-white font-bold truncate">{t.file}</div>
                          <div className="text-[9px] text-[#64748b]">{t.width}x{t.height}px • {t.crs}</div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Database Table Card */}
              <div className="bg-[#030814]/90 border border-cyan-500/25 p-4 rounded-xl space-y-2 font-mono text-[12px]">
                <div className="flex justify-between py-1 border-b border-cyan-500/25/50">
                  <span className="text-[#64748b]">Primary Target</span>
                  <span className="text-[#00e5ff] font-bold">{savedTile.id}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-cyan-500/25/50">
                  <span className="text-[#64748b]">Source File</span>
                  <span className="text-white break-all">{savedTile.file}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-cyan-500/25/50">
                  <span className="text-[#64748b]">Sensor</span>
                  <span className="text-white">{savedTile.sensor}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-cyan-500/25/50">
                  <span className="text-[#64748b]">Acquisition Date</span>
                  <span className="text-white">{savedTile.date}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-cyan-500/25/50">
                  <span className="text-[#64748b]">Location</span>
                  <span className="text-[#9cf0ff]">{savedTile.lat}° N, {savedTile.lng}° E ({savedTile.region})</span>
                </div>
                <div className="flex justify-between py-1 border-b border-cyan-500/25/50">
                  <span className="text-[#64748b]">CRS</span>
                  <span className="text-white">{savedTile.crs}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-cyan-500/25/50">
                  <span className="text-[#64748b]">Vision Embedding</span>
                  <span className="text-[#10b981] font-bold">✓ 512-D RemoteCLIP ViT-B-32</span>
                </div>
                <div className="flex justify-between py-1 border-b border-cyan-500/25/50">
                  <span className="text-[#64748b]">Qdrant Vector Index</span>
                  <span className="text-[#10b981] font-bold">✓ UPSERTED (satellite_tiles)</span>
                </div>
                <div className="flex justify-between py-1 border-b border-cyan-500/25/50">
                  <span className="text-[#64748b]">SQLite Registry</span>
                  <span className="text-[#10b981] font-bold">✓ SYNCED (tile_registry.sqlite)</span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-[#64748b]">Status</span>
                  <span className="text-[#10b981] font-bold">● ACTIVE &amp; SEARCHABLE</span>
                </div>
              </div>

              {/* Storage Directories Card */}
              <div className="bg-[#030814]/90 border border-cyan-500/25 p-4 rounded-xl space-y-2 font-mono text-[11px]">
                <div className="text-[#00e5ff] text-[10px] font-bold uppercase pb-1 border-b border-cyan-500/25 flex items-center gap-1.5">
                  <Database className="w-3.5 h-3.5 text-[#00e5ff]" />
                  <span>PERSISTENT STORAGE LOCATIONS ON DISK:</span>
                </div>
                <div className="space-y-1.5 text-[#94a3b8]">
                  <div className="flex flex-col sm:flex-row sm:justify-between py-1 border-b border-cyan-500/25/40">
                    <span className="text-[#64748b]">1. Raw Input GeoTIFFs:</span>
                    <span className="text-white font-mono text-[10px] select-all">data/raw/sentinel2/{savedTile.date}/</span>
                  </div>
                  <div className="flex flex-col sm:flex-row sm:justify-between py-1 border-b border-cyan-500/25/40">
                    <span className="text-[#64748b]">2. Sliced Sub-Tiles (256x256) &amp; Composite:</span>
                    <span className="text-[#10b981] font-mono text-[10px] select-all">data/tiles/sentinel2/{savedTile.date}/</span>
                  </div>
                  <div className="flex flex-col sm:flex-row sm:justify-between py-1 border-b border-cyan-500/25/40">
                    <span className="text-[#64748b]">3. 512-D Vision Embeddings Cache &amp; Manifest:</span>
                    <span className="text-[#c084fc] font-mono text-[10px] select-all">data/embeddings/indexing_manifest.json</span>
                  </div>
                  <div className="flex flex-col sm:flex-row sm:justify-between py-1">
                    <span className="text-[#64748b]">4. SQLite Spatial Metadata Registry:</span>
                    <span className="text-[#38bdf8] font-mono text-[10px] select-all">database/tile_registry.sqlite</span>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={handleSaveTile}
                  className="py-3 bg-[#00e5ff] hover:bg-[#9cf0ff] text-[#070e1b] font-mono text-[12px] font-bold uppercase tracking-wider rounded-xl transition-all flex items-center justify-center gap-2 shadow-[0_0_15px_rgba(0,229,255,0.25)] cursor-pointer"
                >
                  <Database className="w-4 h-4" />
                  <span>[ SAVE TO ARCHIVE ]</span>
                </button>
                <button
                  type="button"
                  onClick={() => {
                    handleSaveTile();
                    setSelectedDetailTile(savedTile);
                    const el = document.getElementById('archive-section');
                    if (el) el.scrollIntoView({ behavior: 'smooth' });
                  }}
                  className="py-3 bg-slate-800/80 hover:bg-[#1a2942] border border-[#00e5ff]/50 text-[#00e5ff] font-mono text-[12px] font-bold uppercase tracking-wider rounded-xl transition-all flex items-center justify-center gap-2 cursor-pointer"
                >
                  <Database className="w-4 h-4" />
                  <span>[ VIEW IN CATALOG ↓ ]</span>
                </button>
              </div>
            </div>
          )}

          {/* STEP 5: SUCCESS SCREEN */}
          {currentStep === 'success' && savedTile && (
            <div className="bg-[#061024]/90 backdrop-blur-xl border border-[#10b981]/60 p-6 rounded-xl space-y-5">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-[#10b981]/20 border border-[#10b981] flex items-center justify-center text-[#10b981]">
                  <Check className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="font-mono text-[16px] text-white font-bold">
                    ✓ TILE SUCCESSFULLY ADDED
                  </h3>
                  <p className="font-mono text-[12px] text-[#94a3b8] mt-0.5">
                    Tile <span className="text-[#00e5ff] font-bold">{savedTile.id}</span> has been indexed in Qdrant and registered in SQLite via <code className="text-[#00e5ff]">/ingest/upload</code>.
                  </p>
                </div>
              </div>

              {/* Updated Checklist */}
              <div className="bg-[#030814]/90 border border-cyan-500/25 p-4 rounded-xl space-y-2 font-mono text-[12px]">
                <div className="text-[#64748b] text-[10px] uppercase pb-1 border-b border-cyan-500/25">
                  UPDATED SUBSYSTEMS:
                </div>
                <div className="flex justify-between text-white">
                  <span>IMAGE ARCHIVE (TILES DIR)</span>
                  <span className="text-[#10b981] font-bold">✓</span>
                </div>
                <div className="flex justify-between text-white">
                  <span>METADATA DATABASE (SQLITE)</span>
                  <span className="text-[#10b981] font-bold">✓</span>
                </div>
                <div className="flex justify-between text-white">
                  <span>VECTOR INDEX (QDRANT)</span>
                  <span className="text-[#10b981] font-bold">✓</span>
                </div>
                <div className="flex justify-between text-white">
                  <span>SEMANTIC &amp; TEMPORAL SEARCH</span>
                  <span className="text-[#10b981] font-bold">✓</span>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="grid grid-cols-1 sm:grid-cols-4 gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => {
                    setSelectedDetailTile(savedTile);
                    setArchiveSuccessToast(`✓ Tile ${savedTile.id} successfully ingested into SQLite Archive for ${savedTile.region}!`);
                    const el = document.getElementById('archive-section');
                    if (el) el.scrollIntoView({ behavior: 'smooth' });
                    setTimeout(() => setArchiveSuccessToast(''), 6000);
                  }}
                  className="py-2.5 bg-[#00e5ff] hover:bg-[#9cf0ff] text-[#070e1b] font-mono text-[11px] font-bold uppercase rounded-xl transition-colors flex items-center justify-center gap-1.5 cursor-pointer shadow-[0_0_12px_rgba(0,229,255,0.25)]"
                >
                  <Database className="w-3.5 h-3.5" />
                  View in Archive
                </button>
                <button
                  type="button"
                  onClick={() => onViewTile && onViewTile(savedTile.id)}
                  className="py-2.5 bg-slate-800/80 hover:bg-[#00e5ff] hover:text-[#070e1b] border border-cyan-500/30 text-[#00e5ff] font-mono text-[11px] font-bold uppercase rounded-xl transition-colors flex items-center justify-center gap-1.5 cursor-pointer"
                >
                  <Clock className="w-3.5 h-3.5" />
                  Temporal Compare
                </button>
                <button
                  type="button"
                  onClick={() => onSearchTile && onSearchTile(savedTile.sensor + " " + savedTile.region)}
                  className="py-2.5 bg-slate-800/80 hover:bg-[#1a2942] border border-cyan-500/25 text-white font-mono text-[11px] font-bold uppercase rounded-xl transition-colors flex items-center justify-center gap-1.5 cursor-pointer"
                >
                  <Search className="w-3.5 h-3.5" />
                  Search This Tile
                </button>
                <button
                  type="button"
                  onClick={handleOpenAddTile}
                  className="py-2.5 bg-slate-800/80 hover:bg-[#1a2942] border border-cyan-500/25 text-white font-mono text-[11px] font-bold uppercase rounded-xl transition-colors flex items-center justify-center gap-1.5 cursor-pointer"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  Add Another Tile
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Right Side: Ingestion Pipeline Horizontal Flow */}
        <div className="flex flex-col justify-stretch h-full">
          <div className="relative bg-gradient-to-b from-[#081b38]/90 via-[#06142e]/95 to-[#030a18]/95 border-2 border-cyan-400/50 shadow-[0_0_30px_rgba(0,229,255,0.2)] rounded-3xl p-6 sm:p-8 backdrop-blur-2xl overflow-hidden h-full flex flex-col justify-between">
            {/* Subtle grid pattern background */}
            <div
              className="absolute inset-0 pointer-events-none opacity-30"
              style={{
                backgroundImage: 'linear-gradient(#142229 1px, transparent 1px), linear-gradient(90deg, #142229 1px, transparent 1px)',
                backgroundSize: '24px 24px'
              }}
            ></div>

            {/* Header */}
            <div className="relative flex items-center justify-between pb-4 mb-4 border-b border-[#24404a]">
              <h3 className="text-base font-bold text-white tracking-wide">
                Ingestion Pipeline
              </h3>
              <div className="font-mono text-xs text-[#5fe6cf] border border-[#2f6b63] bg-[#5fe6cf]/10 px-2.5 py-0.5 rounded">
                ●
              </div>
            </div>

            {/* Horizontal Flow Stages (Fitted without horizontal scrollbar) */}
            <div className="relative flex items-start justify-between w-full py-4 gap-2">
              {/* Stage 1 */}
              <div className="relative flex flex-col items-center flex-1 min-w-0 px-1">
                <div className="absolute top-[32px] left-[50%] w-full h-[1px] bg-gradient-to-r from-[#2f6b63] via-[#2f6b63] to-transparent z-0"></div>
                <div className="absolute top-[28px] -right-[2px] w-0 h-0 border-t-[4px] border-t-transparent border-b-[4px] border-b-transparent border-l-[6px] border-l-[#2f6b63] z-0"></div>
                <div className="relative z-10 w-[60px] h-[60px] sm:w-[68px] sm:h-[68px] rounded-2xl bg-[#0c161c] border border-[#24404a] flex items-center justify-center shadow-lg group-hover:border-cyan-400 transition-colors">
                  <div className="absolute -top-2 -left-2 w-[20px] h-[20px] rounded-full bg-[#060d12] border border-[#5fe6cf] text-[#5fe6cf] font-mono text-[10px] flex items-center justify-center font-bold z-20">
                    1
                  </div>
                  <svg viewBox="0 0 48 48" fill="none" className="w-7 h-7 sm:w-8 sm:h-8">
                    <rect x="20" y="20" width="8" height="8" rx="1" stroke="#5fe6cf" strokeWidth="1.6"/>
                    <line x1="24" y1="20" x2="24" y2="10" stroke="#5fe6cf" strokeWidth="1.6"/>
                    <line x1="10" y1="24" x2="20" y2="24" stroke="#5fe6cf" strokeWidth="1.6"/>
                    <g stroke="#5fe6cf" strokeWidth="1.6" strokeLinecap="round">
                      <line x1="6" y1="6" x2="12" y2="12"/>
                      <line x1="4" y1="10" x2="10" y2="16"/>
                      <line x1="10" y1="4" x2="16" y2="10"/>
                    </g>
                    <circle cx="35" cy="14" r="1.6" fill="#5fe6cf"/>
                    <circle cx="30" cy="34" r="1.6" fill="#5fe6cf"/>
                    <path d="M24 10 C 26 6, 34 6, 35 14" stroke="#5fe6cf" strokeWidth="1" strokeDasharray="2 2" opacity="0.6"/>
                  </svg>
                </div>
                <div className="mt-3 text-center">
                  <h4 className="text-[11px] sm:text-[12px] font-semibold text-white mb-1 leading-snug">GeoTIFF Source Ingest</h4>
                  <span className="font-mono text-[9.5px] sm:text-[10px] text-[#5fe6cf] tracking-tight block">GDAL / RasterIO</span>
                </div>
              </div>

              {/* Stage 2 */}
              <div className="relative flex flex-col items-center flex-1 min-w-0 px-1">
                <div className="absolute top-[32px] left-[50%] w-full h-[1px] bg-gradient-to-r from-[#2f6b63] via-[#2f6b63] to-transparent z-0"></div>
                <div className="absolute top-[28px] -right-[2px] w-0 h-0 border-t-[4px] border-t-transparent border-b-[4px] border-b-transparent border-l-[6px] border-l-[#2f6b63] z-0"></div>
                <div className="relative z-10 w-[60px] h-[60px] sm:w-[68px] sm:h-[68px] rounded-2xl bg-[#0c161c] border border-[#24404a] flex items-center justify-center shadow-lg">
                  <div className="absolute -top-2 -left-2 w-[20px] h-[20px] rounded-full bg-[#060d12] border border-[#5fe6cf] text-[#5fe6cf] font-mono text-[10px] flex items-center justify-center font-bold z-20">
                    2
                  </div>
                  <svg viewBox="0 0 48 48" fill="none" className="w-7 h-7 sm:w-8 sm:h-8">
                    <rect x="8" y="8" width="32" height="32" rx="2" stroke="#5fe6cf" strokeWidth="1.6"/>
                    <line x1="8" y1="19" x2="40" y2="19" stroke="#5fe6cf" strokeWidth="1.2"/>
                    <line x1="8" y1="29" x2="40" y2="29" stroke="#5fe6cf" strokeWidth="1.2"/>
                    <line x1="19" y1="8" x2="19" y2="40" stroke="#5fe6cf" strokeWidth="1.2"/>
                    <line x1="29" y1="8" x2="29" y2="40" stroke="#5fe6cf" strokeWidth="1.2"/>
                    <rect x="19" y="8" width="10" height="11" fill="#5fe6cf" opacity="0.22"/>
                  </svg>
                </div>
                <div className="mt-3 text-center">
                  <h4 className="text-[11px] sm:text-[12px] font-semibold text-white mb-1 leading-snug">Tiling &amp; Grid Slicing</h4>
                  <span className="font-mono text-[9.5px] sm:text-[10px] text-[#5fe6cf] tracking-tight block">256×256 sub-tiles</span>
                </div>
              </div>

              {/* Stage 3 */}
              <div className="relative flex flex-col items-center flex-1 min-w-0 px-1">
                <div className="absolute top-[32px] left-[50%] w-full h-[1px] bg-gradient-to-r from-[#2f6b63] via-[#2f6b63] to-transparent z-0"></div>
                <div className="absolute top-[28px] -right-[2px] w-0 h-0 border-t-[4px] border-t-transparent border-b-[4px] border-b-transparent border-l-[6px] border-l-[#2f6b63] z-0"></div>
                <div className="relative z-10 w-[60px] h-[60px] sm:w-[68px] sm:h-[68px] rounded-2xl bg-[#0c161c] border border-[#24404a] flex items-center justify-center shadow-lg">
                  <div className="absolute -top-2 -left-2 w-[20px] h-[20px] rounded-full bg-[#060d12] border border-[#5fe6cf] text-[#5fe6cf] font-mono text-[10px] flex items-center justify-center font-bold z-20">
                    3
                  </div>
                  <svg viewBox="0 0 48 48" fill="none" className="w-7 h-7 sm:w-8 sm:h-8">
                    <g stroke="#5fe6cf" strokeWidth="1.1" opacity="0.75">
                      <line x1="10" y1="12" x2="24" y2="9"/>
                      <line x1="10" y1="12" x2="24" y2="24"/>
                      <line x1="10" y1="24" x2="24" y2="9"/>
                      <line x1="10" y1="24" x2="24" y2="24"/>
                      <line x1="10" y1="36" x2="24" y2="24"/>
                      <line x1="10" y1="36" x2="24" y2="39"/>
                      <line x1="24" y1="9" x2="38" y2="18"/>
                      <line x1="24" y1="24" x2="38" y2="18"/>
                      <line x1="24" y1="24" x2="38" y2="30"/>
                      <line x1="24" y1="39" x2="38" y2="30"/>
                    </g>
                    <g fill="#060d12" stroke="#5fe6cf" strokeWidth="1.4">
                      <circle cx="10" cy="12" r="2.6"/>
                      <circle cx="10" cy="24" r="2.6"/>
                      <circle cx="10" cy="36" r="2.6"/>
                      <circle cx="24" cy="9" r="2.6"/>
                      <circle cx="24" cy="24" r="2.6"/>
                      <circle cx="24" cy="39" r="2.6"/>
                      <circle cx="38" cy="18" r="2.6"/>
                      <circle cx="38" cy="30" r="2.6"/>
                    </g>
                  </svg>
                </div>
                <div className="mt-3 text-center">
                  <h4 className="text-[11px] sm:text-[12px] font-semibold text-white mb-1 leading-snug">RemoteCLIP Embedding</h4>
                  <span className="font-mono text-[9.5px] sm:text-[10px] text-[#5fe6cf] tracking-tight block">512-D vision vector</span>
                </div>
              </div>

              {/* Stage 4 */}
              <div className="relative flex flex-col items-center flex-1 min-w-0 px-1">
                <div className="relative z-10 w-[60px] h-[60px] sm:w-[68px] sm:h-[68px] rounded-2xl bg-[#0c161c] border border-[#6b5326] flex items-center justify-center shadow-lg">
                  <div className="absolute -top-2 -left-2 w-[20px] h-[20px] rounded-full bg-[#060d12] border border-[#e8a33d] text-[#e8a33d] font-mono text-[10px] flex items-center justify-center font-bold z-20">
                    4
                  </div>
                  <svg viewBox="0 0 48 48" fill="none" className="w-7 h-7 sm:w-8 sm:h-8">
                    <g stroke="#e8a33d" strokeWidth="1.6">
                      <ellipse cx="16" cy="12" rx="9" ry="3.4"/>
                      <path d="M7 12 L7 30 C7 32 11 33.6 16 33.6 C21 33.6 25 32 25 30 L25 12"/>
                      <path d="M7 21 C7 23 11 24.6 16 24.6 C21 24.6 25 23 25 21" opacity="0.7"/>
                    </g>
                    <g stroke="#e8a33d" strokeWidth="1.4">
                      <circle cx="35" cy="15" r="2.2"/>
                      <circle cx="41" cy="24" r="2.2"/>
                      <circle cx="33" cy="30" r="2.2"/>
                      <circle cx="41" cy="34" r="2.2"/>
                      <line x1="35" y1="15" x2="41" y2="24"/>
                      <line x1="41" y1="24" x2="33" y2="30"/>
                      <line x1="33" y1="30" x2="41" y2="34"/>
                      <line x1="41" y1="24" x2="41" y2="34" opacity="0.5"/>
                    </g>
                  </svg>
                </div>
                <div className="mt-3 text-center">
                  <h4 className="text-[11px] sm:text-[12px] font-semibold text-white mb-1 leading-snug">Dual-Store Indexing</h4>
                  <span className="font-mono text-[9.5px] sm:text-[10px] text-[#e8a33d] tracking-tight block">Qdrant + SQLite</span>
                </div>
              </div>
            </div>

            {/* Bottom spacer */}
            <div className="pb-1"></div>
          </div>
        </div>

      </div>

      {/* DATABASE / ARCHIVE VIEW */}
      <div className="mt-8 pt-8 border-t border-cyan-500/25" id="archive-section">
        {selectedDetailTile ? (
          /* TILE DETAILS VIEW */
          <div className="bg-[#061024]/95 backdrop-blur-2xl border border-cyan-500/25 rounded-xl p-5 shadow-2xl relative overflow-hidden">
            {/* Top Bar: ← BACK TO ARCHIVE ... TILE */}
            <div className="flex items-center justify-between border-b border-cyan-500/25 pb-4 mb-6">
              <button
                type="button"
                onClick={() => setSelectedDetailTile(null)}
                className="flex items-center gap-2 px-3 py-1.5 bg-[#030814]/90 hover:bg-slate-800/80 text-[#00e5ff] hover:text-white border border-cyan-500/25 rounded-xl font-mono text-[12px] font-bold uppercase transition-colors cursor-pointer"
              >
                <ArrowLeft className="w-4 h-4" />
                ← BACK TO ARCHIVE
              </button>
              <div className="flex items-center gap-2 font-mono">
                <span className="w-2 h-2 rounded-full bg-[#10b981] animate-pulse"></span>
                <span className="text-[16px] font-extrabold text-white tracking-wider">
                  TILE {selectedDetailTile.id}
                </span>
                <span className={`ml-2 px-2 py-0.5 font-bold rounded-lg text-[10px] ${
                  getItemType(selectedDetailTile) === 'Full' 
                    ? 'bg-[#8b5cf6]/20 border border-[#8b5cf6]/50 text-[#c084fc]' 
                    : 'bg-[#00e5ff]/15 border border-cyan-500/30 text-[#00e5ff]'
                }`}>
                  {getItemType(selectedDetailTile).toUpperCase()}
                </span>
              </div>
            </div>

            {/* Main 2-column info & visual grid */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
              {/* Left Col: Satellite Image visual box */}
              <div className="lg:col-span-6 bg-[#030814]/90 border border-cyan-500/25 rounded-xl p-4 relative flex flex-col justify-between overflow-hidden group">
                <div>
                  {/* Header Labels */}
                  <div className="w-full flex items-center justify-between text-[10px] font-mono text-[#64748b] uppercase tracking-wider mb-2 border-b border-cyan-500/25/60 pb-1.5">
                    <span className="text-[#00e5ff] font-bold flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-[#00e5ff]"></span>
                      ACQUISITION // {selectedDetailTile.dateIso || selectedDetailTile.date}
                    </span>
                    <span className="text-white font-medium">{selectedDetailTile.sensor || 'Sentinel-2 MSI'}</span>
                  </div>

                  <div className="relative w-full aspect-square max-w-[320px] mx-auto rounded-xl overflow-hidden border border-cyan-500/25 shadow-inner my-2 bg-[#030712] flex items-center justify-center">
                    <img 
                      src={selectedDetailTile.image || "/satellite-tiles/default.jpg"}
                      onError={(e) => { e.target.onerror = null; e.target.src = "/satellite-tiles/default.jpg"; }}
                      alt={`Satellite Tile ${selectedDetailTile.id}`}
                      className="w-full h-full object-cover brightness-95 contrast-105 group-hover:scale-105 transition-transform duration-500"
                    />
                    
                    {/* Overlay Tactical Reticle */}
                    <div className="absolute inset-0 border border-[#00e5ff]/20 pointer-events-none">
                      <div className="absolute top-0 left-0 w-4 h-4 border-t-2 border-l-2 border-[#00e5ff]"></div>
                      <div className="absolute top-0 right-0 w-4 h-4 border-t-2 border-r-2 border-[#00e5ff]"></div>
                      <div className="absolute bottom-0 left-0 w-4 h-4 border-b-2 border-l-2 border-[#00e5ff]"></div>
                      <div className="absolute bottom-0 right-0 w-4 h-4 border-b-2 border-r-2 border-[#00e5ff]"></div>
                      
                      <div className="absolute inset-0 flex items-center justify-center">
                        <div className="w-12 h-12 border border-cyan-500/30 rounded-full flex items-center justify-center">
                          <div className="w-1.5 h-1.5 bg-[#00e5ff] rounded-full"></div>
                        </div>
                      </div>
                    </div>

                    <div className="absolute bottom-2 left-2 right-2 bg-[#030814]/90/85 backdrop-blur-sm px-2.5 py-1 rounded border border-cyan-500/25 flex items-center justify-between text-[9px] font-mono text-[#94a3b8]">
                      <span>RES: {selectedDetailTile.resolution || '10m'}</span>
                      <span>FOV: {getItemType(selectedDetailTile) === 'Full' ? 'FULL SCENE' : '256×256 PX'}</span>
                      <span className="text-[#10b981]">GEOLINKED</span>
                    </div>
                  </div>
                </div>

                {/* Related Multi-Temporal Passes */}
                {(() => {
                  const currentFileName = selectedDetailTile.file || (selectedDetailTile.id.includes("sentinel2_tile_") ? selectedDetailTile.id.match(/sentinel2_tile_\\d+\\.tif/i)?.[0] : null);
                  const relatedPasses = currentFileName ? archiveList.filter(t => {
                    if (t.id === selectedDetailTile.id) return false;
                    return t.file === currentFileName || (t.id && t.id.includes(currentFileName));
                  }) : [];

                  return (
                    <div className="w-full mt-3 pt-3 border-t border-cyan-500/25/70">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-[10px] font-mono text-[#00e5ff] uppercase tracking-wider font-bold flex items-center gap-1.5">
                          <Layers className="w-3.5 h-3.5 text-[#00e5ff]" />
                          CO-REGISTERED PASSES ACROSS TIME ({selectedDetailTile.file})
                        </span>
                        <span className="text-[9px] font-mono text-[#64748b]">
                          {relatedPasses.length} COMPATIBLE PASSES
                        </span>
                      </div>
                      {relatedPasses.length > 0 ? (
                        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                          {relatedPasses.slice(0, 6).map((relTile) => (
                            <button
                              key={relTile.id}
                              type="button"
                              onClick={() => setSelectedDetailTile(relTile)}
                              className="p-1.5 bg-[#061024]/90 backdrop-blur-xl hover:bg-slate-800/80 border border-cyan-500/25 hover:border-[#00e5ff] rounded-xl text-left transition-all group cursor-pointer flex items-center gap-2"
                            >
                              <img
                                src={relTile.image || "/satellite-tiles/default.jpg"}
                                alt={relTile.id}
                                className="w-8 h-8 rounded-xl object-cover border border-cyan-500/25 shrink-0"
                              />
                              <div className="min-w-0 font-mono">
                                <div className="text-[11px] font-bold text-white group-hover:text-[#00e5ff] truncate">
                                  {relTile.dateIso || relTile.date}
                                </div>
                                <div className="text-[9px] text-[#64748b] truncate">
                                  {relTile.id}
                                </div>
                              </div>
                            </button>
                          ))}
                        </div>
                      ) : (
                        <div className="text-[10px] font-mono text-[#64748b] italic">
                          Baseline pass recorded. Additional temporal passes will show here.
                        </div>
                      )}
                    </div>
                  );
                })()}
              </div>

              {/* Right Col: Tile Information */}
              <div className="lg:col-span-6 bg-[#030814]/90 border border-cyan-500/25 rounded-xl p-5 flex flex-col justify-between">
                <div>
                  <div className="flex items-center gap-2 border-b border-cyan-500/25 pb-2.5 mb-4">
                    <Database className="w-4 h-4 text-[#00e5ff]" />
                    <h4 className="font-mono text-[13px] font-bold text-white uppercase tracking-wider">
                      TILE INFORMATION
                    </h4>
                  </div>

                  <div className="space-y-3 font-mono text-[12px]">
                    <div className="flex justify-between py-1 border-b border-cyan-500/25/60">
                      <span className="text-[#64748b]">Tile ID:</span>
                      <span className="text-[#00e5ff] font-bold">{selectedDetailTile.id}</span>
                    </div>
                    <div className="flex justify-between py-1 border-b border-cyan-500/25/60">
                      <span className="text-[#64748b]">File Type:</span>
                      <span className="text-white font-bold">{getItemType(selectedDetailTile) === 'Full' ? 'Full Scene Image' : '256x256 Spatial Tile'}</span>
                    </div>
                    <div className="flex justify-between py-1 border-b border-cyan-500/25/60">
                      <span className="text-[#64748b]">File:</span>
                      <span className="text-white font-medium break-all">{selectedDetailTile.file}</span>
                    </div>
                    <div className="flex justify-between py-1 border-b border-cyan-500/25/60">
                      <span className="text-[#64748b]">Sensor:</span>
                      <span className="text-white font-medium">{selectedDetailTile.sensor || 'Sentinel-2 MSI'}</span>
                    </div>
                    <div className="flex justify-between py-1 border-b border-cyan-500/25/60">
                      <span className="text-[#64748b]">Date:</span>
                      <span className="text-white">{selectedDetailTile.dateIso || selectedDetailTile.date}</span>
                    </div>
                    <div className="flex justify-between py-1 border-b border-cyan-500/25/60">
                      <span className="text-[#64748b]">Region:</span>
                      <span className="text-[#9cf0ff] font-medium">{selectedDetailTile.region || selectedDetailTile.location || 'Northern AOI'}</span>
                    </div>
                    <div className="flex justify-between py-1 border-b border-cyan-500/25/60">
                      <span className="text-[#64748b]">Resolution:</span>
                      <span className="text-white">{selectedDetailTile.resolution || '10m'}</span>
                    </div>
                    <div className="flex justify-between py-1 border-b border-cyan-500/25/60">
                      <span className="text-[#64748b]">CRS:</span>
                      <span className="text-[#94a3b8]">{selectedDetailTile.crs || 'EPSG:32643'}</span>
                    </div>
                    <div className="flex justify-between py-1">
                      <span className="text-[#64748b]">Coordinates:</span>
                      <span className="text-[#00e5ff]">{selectedDetailTile.coordinates || `${selectedDetailTile.lat}° N, ${selectedDetailTile.lng}° E`}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* PROCESSING STATUS Checklist */}
            <div className="mt-6 border-t border-cyan-500/25 pt-5">
              <div className="text-[11px] font-mono text-[#64748b] uppercase tracking-wider mb-3">
                PROCESSING STATUS
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-2.5">
                <div className="flex items-center gap-2 p-2.5 bg-[#030814]/90 border border-[#10b981]/30 rounded-xl font-mono text-[11px] text-[#10b981]">
                  <Check className="w-3.5 h-3.5 text-[#10b981] shrink-0" />
                  <span>Metadata Extracted</span>
                </div>
                <div className="flex items-center gap-2 p-2.5 bg-[#030814]/90 border border-[#10b981]/30 rounded-xl font-mono text-[11px] text-[#10b981]">
                  <Check className="w-3.5 h-3.5 text-[#10b981] shrink-0" />
                  <span>Tile Generated</span>
                </div>
                <div className="flex items-center gap-2 p-2.5 bg-[#030814]/90 border border-[#10b981]/30 rounded-xl font-mono text-[11px] text-[#10b981]">
                  <Check className="w-3.5 h-3.5 text-[#10b981] shrink-0" />
                  <span>Embedding Generated</span>
                </div>
                <div className="flex items-center gap-2 p-2.5 bg-[#030814]/90 border border-[#10b981]/30 rounded-xl font-mono text-[11px] text-[#10b981]">
                  <Check className="w-3.5 h-3.5 text-[#10b981] shrink-0" />
                  <span>Qdrant Indexed</span>
                </div>
                <div className="flex items-center gap-2 p-2.5 bg-[#030814]/90 border border-[#10b981]/30 rounded-xl font-mono text-[11px] text-[#10b981]">
                  <Check className="w-3.5 h-3.5 text-[#10b981] shrink-0" />
                  <span>Available for Search</span>
                </div>
              </div>
            </div>

            {/* Bottom Actions: [ Temporal Compare ] & [ Search Similar ] */}
            <div className="mt-6 pt-5 border-t border-cyan-500/25 flex flex-col sm:flex-row items-center justify-between gap-4">
              <button
                type="button"
                onClick={() => {
                  if (onViewTile) onViewTile(selectedDetailTile.id);
                  setTimeout(() => {
                    const el = document.getElementById('temporal-analysis');
                    if (el) el.scrollIntoView({ behavior: 'smooth' });
                  }, 120);
                }}
                className="w-full sm:w-auto px-6 py-2.5 bg-[#00e5ff] hover:bg-[#9cf0ff] text-[#070e1b] font-mono text-[12px] font-bold uppercase rounded-xl transition-all shadow-[0_0_15px_rgba(0,229,255,0.3)] cursor-pointer flex items-center justify-center gap-2"
              >
                <Clock className="w-4 h-4" />
                [ Temporal Compare ]
              </button>

              <button
                type="button"
                onClick={() => onSearchTile && onSearchTile(selectedDetailTile.sensor + " " + (selectedDetailTile.region || selectedDetailTile.location))}
                className="w-full sm:w-auto px-6 py-2.5 bg-slate-800/80 hover:bg-[#1a2d4a] text-[#00e5ff] border border-[#00e5ff]/50 font-mono text-[12px] font-bold uppercase rounded-xl transition-all hover:border-[#00e5ff] cursor-pointer flex items-center justify-center gap-2"
              >
                <Search className="w-4 h-4" />
                [ Search Similar ]
              </button>
            </div>
          </div>
        ) : (
          /* ARCHIVE TABLE & FILTER VIEW */
          <div className="bg-[#061024]/95 backdrop-blur-2xl border border-cyan-500/25 rounded-xl p-5 shadow-xl">
            {/* Header: Title + Offline Badge + [ + ADD NEW TILE ] Button */}
            <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
              <div className="flex items-center gap-2.5">
                <Database className="w-5 h-5 text-[#00e5ff]" />
                <h3 className="text-[18px] font-bold text-white font-mono uppercase tracking-wider">
                  SATELLITE TILE ARCHIVE ({totalArchiveCount} TILES)
                </h3>
              </div>
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={handleOpenAddTile}
                  className="px-4 py-2 bg-[#00e5ff] hover:bg-[#9cf0ff] text-[#070e1b] font-mono text-[12px] font-bold uppercase rounded-xl transition-all shadow-[0_0_12px_rgba(0,229,255,0.25)] cursor-pointer"
                >
                  ADD NEW TILE
                </button>
              </div>
            </div>

            {/* Success Notification Banner */}
            {archiveSuccessToast && (
              <div className="mb-4 p-3 bg-[#10b981]/15 border border-[#10b981]/40 rounded-xl font-mono text-[12px] text-[#10b981] flex items-center justify-between animate-in fade-in duration-200">
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

            {/* Filter Bar */}
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-12 gap-3 mb-4 p-3 bg-[#030814]/90 border border-cyan-500/25 rounded-xl">
              {/* Search */}
              <div className="sm:col-span-2 md:col-span-4 relative flex items-center">
                <Search className="w-4 h-4 text-[#64748b] absolute left-3 pointer-events-none" />
                <input
                  type="text"
                  value={searchFilter}
                  onChange={(e) => setSearchFilter(e.target.value)}
                  placeholder="🔎 Search tiles by name, ID, or coords..."
                  className="w-full bg-[#061024]/90 backdrop-blur-xl border border-cyan-500/25 text-white font-mono text-[12px] pl-9 pr-3 py-2 rounded-xl focus:border-[#00e5ff] focus:outline-none placeholder-[#64748b]"
                />
              </div>

              {/* Full/Tile Type Dropdown */}
              <div className="md:col-span-2 relative">
                <select
                  value={selectedType}
                  onChange={(e) => setSelectedType(e.target.value)}
                  className="w-full bg-[#061024]/90 backdrop-blur-xl border border-cyan-500/25 text-white font-mono text-[12px] px-3 py-2 rounded-xl focus:border-[#00e5ff] focus:outline-none appearance-none cursor-pointer"
                >
                  <option value="ALL">Type ▼ (All)</option>
                  <option value="Full">Full Images</option>
                  <option value="Tile">Tiles (256x256)</option>
                </select>
                <ChevronDown className="w-3.5 h-3.5 text-[#64748b] absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
              </div>

              {/* Sensor Dropdown */}
              <div className="md:col-span-2 relative">
                <select
                  value={selectedSensor}
                  onChange={(e) => setSelectedSensor(e.target.value)}
                  className="w-full bg-[#061024]/90 backdrop-blur-xl border border-cyan-500/25 text-white font-mono text-[12px] px-3 py-2 rounded-xl focus:border-[#00e5ff] focus:outline-none appearance-none cursor-pointer"
                >
                  {uniqueSensors.map(s => (
                    <option key={s} value={s}>{s === 'ALL' ? 'Sensor ▼ (All)' : s}</option>
                  ))}
                </select>
                <ChevronDown className="w-3.5 h-3.5 text-[#64748b] absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
              </div>

              {/* Date Dropdown */}
              <div className="md:col-span-2 relative">
                <select
                  value={selectedDate}
                  onChange={(e) => setSelectedDate(e.target.value)}
                  className="w-full bg-[#061024]/90 backdrop-blur-xl border border-cyan-500/25 text-white font-mono text-[12px] px-3 py-2 rounded-xl focus:border-[#00e5ff] focus:outline-none appearance-none cursor-pointer"
                >
                  {uniqueDates.map(d => (
                    <option key={d} value={d}>{d === 'ALL' ? 'Year ▼ (All)' : d}</option>
                  ))}
                </select>
                <ChevronDown className="w-3.5 h-3.5 text-[#64748b] absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
              </div>

              {/* Region Dropdown */}
              <div className="md:col-span-2 relative">
                <select
                  value={selectedRegion}
                  onChange={(e) => setSelectedRegion(e.target.value)}
                  className="w-full bg-[#061024]/90 backdrop-blur-xl border border-cyan-500/25 text-white font-mono text-[12px] px-3 py-2 rounded-xl focus:border-[#00e5ff] focus:outline-none appearance-none cursor-pointer"
                >
                  {uniqueRegions.map(r => (
                    <option key={r} value={r}>{r === 'ALL' ? 'Region ▼ (All)' : r}</option>
                  ))}
                </select>
                <ChevronDown className="w-3.5 h-3.5 text-[#64748b] absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
              </div>
            </div>

            {/* Summary Metrics: Total Tiles | Type Breakdown | Date Range | Active Theaters */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4 p-4 bg-[#030814]/90 border border-cyan-500/25 rounded-xl font-mono text-center">
              <div className="p-2 border-r border-cyan-500/25/60 last:border-r-0">
                <div className="text-[11px] text-[#64748b] uppercase tracking-wider mb-1">Matching Results</div>
                <div className="text-[20px] font-extrabold text-[#00e5ff]">
                  {filteredArchive.length}
                </div>
              </div>
              <div className="p-2 border-r border-cyan-500/25/60 last:border-r-0">
                <div className="text-[11px] text-[#64748b] uppercase tracking-wider mb-1">Catalog Types</div>
                <div className="text-[14px] font-bold text-white flex items-center justify-center gap-2">
                  <span className="text-[#c084fc]">Full: {archiveList.filter(t => getItemType(t) === 'Full').length}</span>
                  <span className="text-[#64748b]">|</span>
                  <span className="text-[#00e5ff]">Tiles: {archiveList.filter(t => getItemType(t) === 'Tile').length}</span>
                </div>
              </div>
              <div className="p-2 border-r border-cyan-500/25/60 last:border-r-0">
                <div className="text-[11px] text-[#64748b] uppercase tracking-wider mb-1">Date Range</div>
                <div className="text-[17px] font-bold text-[#9cf0ff]">{dateRangeStr}</div>
              </div>
              <div className="p-2">
                <div className="text-[11px] text-[#64748b] uppercase tracking-wider mb-1">Active Theaters</div>
                <div className="text-[17px] font-bold text-white">
                  {uniqueRegions.filter(r => r !== 'ALL').join(', ') || 'Northern AOI'}
                </div>
              </div>
            </div>

            {/* Table: Tile ID | Date | Sensor | Location | Full/Tile | Cloud | Status | Action */}
            <div className="overflow-x-auto border border-cyan-500/25 rounded-xl bg-[#030814]/90">
              <table className="w-full text-left font-mono text-[12px]">
                <thead className="bg-[#061024]/95 backdrop-blur-2xl border-b border-cyan-500/25 text-[#64748b] text-[10px] uppercase">
                  <tr>
                    <th className="py-3 px-4">Tile ID</th>
                    <th className="py-3 px-4">Date</th>
                    <th className="py-3 px-4">Sensor</th>
                    <th className="py-3 px-4">Location</th>
                    <th className="py-3 px-4 text-center">Full/Tile</th>
                    <th className="py-3 px-4">Cloud</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4 text-center">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#1e293b]/60 text-white">
                  {paginatedArchive.length === 0 ? (
                    <tr>
                      <td colSpan={8} className="py-8 text-center text-[#64748b]">
                        {isLoadingArchive ? "Loading satellite tile catalog..." : "No satellite tiles match current filter criteria."}
                      </td>
                    </tr>
                  ) : (
                    paginatedArchive.map((item, idx) => {
                      const isNew = item.id === savedTile?.id || (savedTile?.date && (item.date === savedTile.date || item.dateIso === savedTile.date)) || (generatedTilesList && generatedTilesList.some(gt => gt.id === item.id || gt.file === item.file));
                      const itemType = getItemType(item);
                      
                      return (
                        <tr 
                          key={item.id || idx}
                          className={`hover:bg-slate-800/80/70 transition-colors ${isNew ? 'bg-[#00e5ff]/10' : ''}`}
                        >
                          <td className="py-3 px-4 font-bold text-[#00e5ff]">
                            <div className="flex items-center gap-1.5">
                              <span>{item.id}</span>
                              {isNew && (
                                <span className="px-1.5 py-0.2 bg-[#00e5ff] text-[#070e1b] text-[8px] font-bold rounded-xl">
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
                            {item.location || item.region || "Northern AOI"}
                          </td>
                          <td className="py-3 px-4 text-center">
                            {itemType === 'Full' ? (
                              <span className="px-2 py-0.5 bg-[#8b5cf6]/20 border border-[#8b5cf6]/50 text-[#c084fc] font-bold rounded-lg text-[10px] inline-flex items-center gap-1">
                                <span className="w-1.5 h-1.5 rounded-full bg-[#8b5cf6]"></span>
                                Full
                              </span>
                            ) : (
                              <span className="px-2 py-0.5 bg-[#00e5ff]/15 border border-cyan-500/30 text-[#00e5ff] font-bold rounded-lg text-[10px] inline-flex items-center gap-1">
                                <span className="w-1.5 h-1.5 rounded-full bg-[#00e5ff]"></span>
                                Tile
                              </span>
                            )}
                          </td>
                          <td className="py-3 px-4 text-[#94a3b8]">
                            {item.cloudCover || "0.0%"}
                          </td>
                          <td className="py-3 px-4">
                            <span className="px-2 py-0.5 bg-[#10b981]/15 text-[#10b981] border border-[#10b981]/30 rounded-xl text-[10px] font-bold inline-flex items-center gap-1">
                              <span className="w-1.5 h-1.5 rounded-full bg-[#10b981]"></span>
                              {item.status || "READY"}
                            </span>
                          </td>
                          <td className="py-3 px-4 text-center">
                            <button
                              type="button"
                              onClick={() => setSelectedDetailTile(item)}
                              className="px-3 py-1 bg-slate-800/80 hover:bg-[#00e5ff] hover:text-[#070e1b] border border-cyan-500/30 text-[#00e5ff] text-[11px] font-bold rounded-xl transition-all cursor-pointer shadow-sm"
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

            {/* Pagination Bar (Max 10 rows per page) */}
            {filteredArchive.length > itemsPerPage && (
              <div className="flex flex-col sm:flex-row items-center justify-between gap-3 p-4 bg-[#030814]/90 border-t border-cyan-500/25 font-mono text-[12px] mt-0.5">
                <div className="text-[#64748b]">
                  Showing <strong className="text-white">{startIndex + 1}</strong>–<strong className="text-white">{Math.min(startIndex + itemsPerPage, filteredArchive.length)}</strong> of <strong className="text-[#00e5ff]">{filteredArchive.length}</strong> items (Page {safeCurrentPage} of {totalPages})
                </div>

                <div className="flex items-center gap-1.5">
                  <button
                    type="button"
                    onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                    disabled={safeCurrentPage === 1}
                    className="px-3 py-1.5 bg-[#061024]/90 backdrop-blur-xl hover:bg-slate-800/80 border border-cyan-500/25 hover:border-[#00e5ff]/50 disabled:opacity-30 disabled:pointer-events-none text-[#94a3b8] hover:text-white rounded-xl transition-colors cursor-pointer flex items-center gap-1"
                  >
                    <ChevronLeft className="w-3.5 h-3.5" />
                    <span>PREV</span>
                  </button>
                  
                  {getPageNumbers().map(pageNum => (
                    <button
                      key={pageNum}
                      type="button"
                      onClick={() => setCurrentPage(pageNum)}
                      className={`w-7 h-7 rounded-xl font-bold text-[11px] transition-all cursor-pointer flex items-center justify-center ${
                        safeCurrentPage === pageNum
                          ? 'bg-[#00e5ff] text-[#070e1b] shadow-[0_0_10px_rgba(0,229,255,0.4)]'
                          : 'bg-[#061024]/90 backdrop-blur-xl border border-cyan-500/25 text-[#94a3b8] hover:text-white hover:border-[#64748b]'
                      }`}
                    >
                      {pageNum}
                    </button>
                  ))}

                  <button
                    type="button"
                    onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                    disabled={safeCurrentPage === totalPages}
                    className="px-3 py-1.5 bg-[#061024]/90 backdrop-blur-xl hover:bg-slate-800/80 border border-cyan-500/25 hover:border-[#00e5ff]/50 disabled:opacity-30 disabled:pointer-events-none text-[#94a3b8] hover:text-white rounded-xl transition-colors cursor-pointer flex items-center gap-1"
                  >
                    <span>NEXT</span>
                    <ChevronRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </section>
  );
}
