import React, { useState, useEffect, Component } from 'react';
import Navigation from './components/Navigation';
import NavigationDrawer from './components/NavigationDrawer';
import HeroSection from './components/HeroSection';
import SemanticSearch from './components/SemanticSearch';
import ImageToImageSearch from './components/ImageToImageSearch';
import CandidateTilesGrid from './components/CandidateTilesGrid';
import TemporalAnalysis from './components/TemporalAnalysis';
import TileIngestion from './components/TileIngestion';
import TelemetryDock from './components/TelemetryDock';
import AIAssistant from './components/AIAssistant';
import { searchSatelliteImages, getArchive, mapBackendTiles } from './services/api';

class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("Component ErrorBoundary caught:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="my-8 p-6 bg-red-950/40 border border-rose-500/50 rounded-2xl text-center max-w-4xl mx-auto backdrop-blur-xl">
          <h3 className="text-lg font-bold text-rose-300 mb-2">Section Display Error</h3>
          <p className="text-xs text-rose-200/80 mb-4">{String(this.state.error?.message || "An unexpected rendering error occurred")}</p>
          <button
            type="button"
            onClick={() => this.setState({ hasError: false, error: null })}
            className="px-4 py-2 bg-rose-500/20 hover:bg-rose-500/40 text-rose-200 border border-rose-400/40 text-xs font-mono font-bold rounded-xl transition-all"
          >
            Reset Component
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

export default function App() {
  const [tiles, setTiles] = useState([]);
  const [selectedTileId, setSelectedTileId] = useState(null);
  const [customActiveTile, setCustomActiveTile] = useState(null);
  const [isSearching, setIsSearching] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [activeQuery, setActiveQuery] = useState("");
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [activeSection, setActiveSection] = useState("hero");

  const activeTile = (customActiveTile && (!selectedTileId || customActiveTile.id === selectedTileId || customActiveTile.file === selectedTileId))
    ? customActiveTile
    : (tiles.find(t => t.id === selectedTileId || t.file === selectedTileId) || customActiveTile || (tiles.length > 0 ? tiles[0] : null));

  // Auto-populate candidate tiles from SQLite / Qdrant on initial app load
  useEffect(() => {
    let isMounted = true;
    async function loadInitialData() {
      try {
        const res = await getArchive('all');
        if (isMounted && res.success && res.tiles && res.tiles.length > 0) {
          // Sub-tiles for candidate grid
          const subTiles = res.tiles.filter(t => t.imageType !== 'Full');
          const initialTiles = subTiles.length > 0 ? subTiles : res.tiles;
          setTiles(initialTiles);
          setSelectedTileId(initialTiles[0].id || initialTiles[0].file);
          setCustomActiveTile(initialTiles[0]);
          setHasSearched(true);
        }
      } catch (err) {
        console.warn('Initial tile archive load:', err);
      }
    }
    loadInitialData();
    return () => { isMounted = false; };
  }, []);

  const handleTileIngested = (newTile) => {
    setTiles(prev => {
      const exists = prev.some(t => t.id === newTile.id);
      if (exists) {
        return prev.map(t => t.id === newTile.id ? { ...t, ...newTile } : t);
      }
      return [newTile, ...prev];
    });
    setSelectedTileId(newTile.id);
    setCustomActiveTile(newTile);
    setHasSearched(true);
  };

  const handleViewTile = (tileOrId) => {
    const tileObj = typeof tileOrId === 'object' && tileOrId ? tileOrId : tiles.find(t => t.id === tileOrId || t.file === tileOrId);
    const tileId = typeof tileOrId === 'object' && tileOrId ? (tileOrId.id || tileOrId.file) : tileOrId;

    setSelectedTileId(tileId);
    if (tileObj) {
      setCustomActiveTile(tileObj);
      setTiles(prev => {
        const exists = prev.some(t => t.id === tileObj.id || (t.file && t.file === tileObj.file && t.date === tileObj.date));
        if (exists) return prev;
        return [tileObj, ...prev];
      });
    }
    setHasSearched(true);
    setActiveSection('temporal-analysis');
    setTimeout(() => {
      const el = document.getElementById('temporal-analysis');
      if (el) el.scrollIntoView({ behavior: 'smooth' });
    }, 150);
  };

  const handleSearchTile = (query) => {
    handleSearch(query || "");
  };

  const handleSearch = async (query) => {
    setIsSearching(true);
    setActiveQuery(query);
    try {
      const result = await searchSatelliteImages(query);
      console.log('[TRI-APP] handleSearch result:', result?.success, 'tiles:', result?.tiles?.length, 'first:', result?.tiles?.[0]?.id);
      if (result.success && result.tiles) {
        setTiles(result.tiles);
        if (result.tiles.length > 0) {
          setSelectedTileId(result.tiles[0].id);
          setCustomActiveTile(result.tiles[0]);
        }
      }
      setHasSearched(true);
    } catch (err) {
      console.error("Search error:", err);
      setHasSearched(true);
    } finally {
      setIsSearching(false);
      setActiveSection('candidate-tiles');
      setTimeout(() => {
        const el = document.getElementById('candidate-tiles');
        if (el) el.scrollIntoView({ behavior: 'smooth' });
      }, 150);
    }
  };

  const handleSelectTile = (tileOrId) => {
    if (typeof tileOrId === 'object' && tileOrId) {
      setSelectedTileId(tileOrId.id || tileOrId.file);
      setCustomActiveTile(tileOrId);
    } else {
      setSelectedTileId(tileOrId);
      const found = tiles.find(t => t.id === tileOrId || t.file === tileOrId);
      if (found) setCustomActiveTile(found);
    }
    setHasSearched(true);
  };

  const handleNavigate = (sectionId) => {
    setActiveSection(sectionId);
    if (['candidate-tiles', 'temporal-analysis', 'temporal-search', 'change-wiper'].includes(sectionId)) {
      setHasSearched(true);
    }
    setTimeout(() => {
      let targetId = sectionId;
      if (sectionId === 'change-wiper' || sectionId === 'temporal-search') {
        targetId = 'temporal-analysis';
      } else if (sectionId === 'archive' || sectionId === 'archive-section') {
        targetId = 'archive-section';
      }
      const el = document.getElementById(targetId);
      if (el) el.scrollIntoView({ behavior: 'smooth' });
    }, 100);
  };

  const handleAgentAction = (action, payload) => {
    if (action === 'SEARCH_TEXT' || action === 'SEARCH_IMAGE') {
      if (payload?.tiles && payload.tiles.length > 0) {
        const mappedTiles = mapBackendTiles(payload.tiles);
        setTiles(mappedTiles);
        if (mappedTiles.length > 0) {
          setSelectedTileId(mappedTiles[0].id || mappedTiles[0].file);
          setCustomActiveTile(mappedTiles[0]);
        }
        setHasSearched(true);
        setActiveQuery(payload.query || "AI Assistant Query");
        handleNavigate('candidate-tiles');
      } else if (payload?.query) {
        handleSearch(payload.query);
      }
    } else if (action === 'CHANGE_DETECT') {
      if (payload?.tileId) {
        handleSelectTile(payload.tileId);
      }
      setHasSearched(true);
      handleNavigate('temporal-analysis');
    } else if (action === 'LIST_TILES' || action === 'TEMPORAL_QUERY') {
      handleNavigate('archive-section');
    }
  };

  return (
    <div className="bg-black text-slate-100 min-h-screen relative font-sans antialiased selection:bg-cyan-400 selection:text-slate-950">
      {/* Background Ambient Glows */}
      <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden">
        <div className="absolute -top-40 -left-40 w-[600px] h-[600px] rounded-full bg-cyan-500/[0.05] blur-[120px]"></div>
        <div className="absolute top-1/3 -right-40 w-[600px] h-[600px] rounded-full bg-indigo-500/[0.04] blur-[140px]"></div>
        <div className="absolute bottom-10 left-1/4 w-[500px] h-[500px] rounded-full bg-emerald-500/[0.03] blur-[120px]"></div>
      </div>

      {/* Left Sliding Navigation Drawer */}
      <NavigationDrawer 
        isOpen={isDrawerOpen} 
        onClose={() => setIsDrawerOpen(false)} 
        onNavigate={handleNavigate}
        onOpenChat={() => setIsChatOpen(true)}
        activeSection={activeSection}
      />

      {/* Top Header */}
      <Navigation 
        onNavigate={handleNavigate} 
        onOpenDrawer={() => setIsDrawerOpen(true)}
        onOpenChat={() => setIsChatOpen(true)}
      />

      {/* Main Single Page Content */}
      <main className="relative z-10">
        {/* Section 1: Hero Viewport */}
        <HeroSection onEnterCommandCenter={() => {
          handleNavigate('semantic-search');
        }} />

        {/* Section 2: Semantic Search */}
        <SemanticSearch onSearch={handleSearch} isSearching={isSearching} />

        {/* Section 3: Ranked Candidate Tiles Grid */}
        {hasSearched && (
          <ErrorBoundary>
            <CandidateTilesGrid
              tiles={tiles}
              selectedTileId={selectedTileId}
              onSelectTile={handleSelectTile}
              activeQuery={activeQuery}
            />
          </ErrorBoundary>
        )}

        {/* Section 4: Image-to-Image Satellite Reverse Search */}
        <ErrorBoundary>
          <ImageToImageSearch 
            onSelectTile={handleSelectTile}
            onSearchResults={(matchedTiles) => {
              if (matchedTiles && matchedTiles.length > 0) {
                setTiles(matchedTiles);
                setSelectedTileId(matchedTiles[0].id);
                setHasSearched(true);
                setActiveQuery("Visual Satellite Match");
              }
            }}
          />
        </ErrorBoundary>

        {/* Section 5: Dedicated Temporal Search & Change Detection Workbench */}
        <ErrorBoundary>
          <TemporalAnalysis activeTile={activeTile} onSelectTile={handleSelectTile} />
        </ErrorBoundary>

        {/* Section 6: Tile Ingestion & SQLite Archive */}
        <ErrorBoundary>
          <TileIngestion 
            onTileIngested={handleTileIngested}
            onViewTile={handleViewTile}
            onSearchTile={handleSearchTile}
          />
        </ErrorBoundary>
      </main>

      {/* TriNetra AI Intelligent Chatbot Assistant */}
      <AIAssistant 
        isOpen={isChatOpen}
        onOpen={() => setIsChatOpen(true)}
        onClose={() => setIsChatOpen(false)}
        onNavigate={handleNavigate}
        onSearch={handleSearch}
        onSelectTile={handleSelectTile}
        onAgentAction={handleAgentAction}
      />

      {/* Persistent Bottom Telemetry Dock */}
      <TelemetryDock onOpenChat={() => setIsChatOpen(true)} />
    </div>
  );
}
