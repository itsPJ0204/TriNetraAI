import React, { useState } from 'react';
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
import { searchSatelliteImages, mapBackendTiles } from './services/api';

export default function App() {
  const [tiles, setTiles] = useState([]);
  const [selectedTileId, setSelectedTileId] = useState(null);
  const [isSearching, setIsSearching] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [activeQuery, setActiveQuery] = useState("");
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [activeSection, setActiveSection] = useState("hero");
  const [isAssistantOpen, setIsAssistantOpen] = useState(false);

  const activeTile = tiles.find(t => t.id === selectedTileId) || (tiles.length > 0 ? tiles[0] : null);

  const handleTileIngested = (newTile) => {
    setTiles(prev => {
      const exists = prev.some(t => t.id === newTile.id);
      if (exists) {
        return prev.map(t => t.id === newTile.id ? { ...t, ...newTile } : t);
      }
      return [newTile, ...prev];
    });
    setSelectedTileId(newTile.id);
    setHasSearched(true);
  };

  const handleViewTile = (tileId) => {
    setSelectedTileId(tileId);
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
      if (result.success && result.tiles) {
        setTiles(result.tiles);
        if (result.tiles.length > 0) {
          setSelectedTileId(result.tiles[0].id);
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

  const handleSelectTile = (tileId) => {
    setSelectedTileId(tileId);
    setHasSearched(true);
  };

  const handleNavigate = (sectionId) => {
    setActiveSection(sectionId);
    if (['candidate-tiles', 'temporal-analysis', 'change-wiper'].includes(sectionId)) {
      if (tiles.length > 0) {
        setHasSearched(true);
      }
    }
    setTimeout(() => {
      const targetId = sectionId === 'change-wiper' ? 'temporal-analysis' : sectionId;
      const el = document.getElementById(targetId);
      if (el) el.scrollIntoView({ behavior: 'smooth' });
    }, 100);
  };

  const handleAgentAction = (action, payload) => {
    if (action === 'SEARCH_TEXT' || action === 'SEARCH_IMAGE') {
      if (payload.tiles && payload.tiles.length > 0) {
        const mappedTiles = mapBackendTiles(payload.tiles);
        setTiles(mappedTiles);
        setSelectedTileId(mappedTiles[0].id);
        setActiveQuery(payload.query || (action === 'SEARCH_IMAGE' ? 'Image Similarity Search' : 'Agent Search'));
        setHasSearched(true);
        handleNavigate('candidate-tiles');
      }
    } else if (action === 'CHANGE_DETECT') {
      if (payload.tileId) {
        handleViewTile(payload.tileId);
      } else {
        handleNavigate('temporal-analysis');
      }
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
        activeSection={activeSection}
        onOpenAssistant={() => { setIsAssistantOpen(true); setIsDrawerOpen(false); }}
      />

      {/* Top Header */}
      <Navigation
        onNavigate={handleNavigate}
        onOpenDrawer={() => setIsDrawerOpen(true)}
        onOpenAssistant={() => setIsAssistantOpen(true)}
      />

      {/* Main Single Page Content */}
      <main className="relative z-10">
        {/* Section 1: Hero Viewport */}
        <HeroSection
          onEnterCommandCenter={() => { handleNavigate('semantic-search'); }}
          onOpenAssistant={() => setIsAssistantOpen(true)}
        />

        {/* Section 2: Semantic Search */}
        <SemanticSearch onSearch={handleSearch} isSearching={isSearching} />

        {/* Section 3: Ranked Candidate Tiles Grid */}
        {hasSearched && (
          <CandidateTilesGrid
            tiles={tiles}
            selectedTileId={selectedTileId}
            onSelectTile={handleSelectTile}
            activeQuery={activeQuery}
          />
        )}

        {/* Section 4: Image-to-Image Satellite Reverse Search */}
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

        {/* Section 5: Dedicated Temporal Comparison & Change Detection */}
        {hasSearched && (
          <TemporalAnalysis activeTile={activeTile} onSelectTile={handleSelectTile} />
        )}

        {/* Section 6: Tile Ingestion & SQLite Archive */}
        <TileIngestion
          onTileIngested={handleTileIngested}
          onViewTile={handleViewTile}
          onSearchTile={handleSearchTile}
        />
      </main>

      {/* Persistent Bottom Telemetry Dock */}
      <TelemetryDock />

      {/* AI Assistant — floating right-side panel, always mounted */}
      <AIAssistant
        onNavigate={handleNavigate}
        onSearch={handleSearch}
        onSelectTile={handleSelectTile}
        onAgentAction={handleAgentAction}
        isOpen={isAssistantOpen}
        onClose={() => setIsAssistantOpen(false)}
      />
    </div>
  );
}
