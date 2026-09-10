import React, { useState } from 'react';
import Navigation from './components/Navigation';
import HeroSection from './components/HeroSection';
import SemanticSearch from './components/SemanticSearch';
import ImageToImageSearch from './components/ImageToImageSearch';
import CandidateTilesGrid from './components/CandidateTilesGrid';
import ImageInspector from './components/ImageInspector';
import TemporalAnalysis from './components/TemporalAnalysis';
import AnalystReview from './components/AnalystReview';
import TileIngestion from './components/TileIngestion';
import TelemetryDock from './components/TelemetryDock';
import { CANDIDATE_TILES } from './data/mockData';
import { searchSatelliteImages } from './services/api';

export default function App() {
  const [tiles, setTiles] = useState(CANDIDATE_TILES);
  const [selectedTileId, setSelectedTileId] = useState(CANDIDATE_TILES[0].id);
  const [isSearching, setIsSearching] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [activeQuery, setActiveQuery] = useState("");

  const activeTile = tiles.find(t => t.id === selectedTileId) || tiles[0];

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
    setTimeout(() => {
      const el = document.getElementById('image-viewer');
      if (el) el.scrollIntoView({ behavior: 'smooth' });
    }, 150);
  };

  const handleSearchTile = (query) => {
    handleSearch(query || "T027 Kolkata Landsat 8");
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
    if (['candidate-tiles', 'image-viewer', 'temporal-analysis', 'change-wiper', 'audit-log'].includes(sectionId)) {
      if (!hasSearched) {
        setHasSearched(true);
        if (!activeQuery) {
          setActiveQuery("Find large camps and tanks near rivers from 2020 to 2023");
        }
      }
    }
    setTimeout(() => {
      const targetId = sectionId === 'change-wiper' ? 'temporal-analysis' : sectionId;
      const el = document.getElementById(targetId);
      if (el) el.scrollIntoView({ behavior: 'smooth' });
    }, 100);
  };

  return (
    <div className="bg-[#070e1b] text-[#e2e8f0] min-h-screen relative font-sans">
      {/* Top Header */}
      <Navigation onNavigate={handleNavigate} />

      {/* Main Single Page Scrollable Experience */}
      <main>
        {/* Section 1: Hero Viewport (Cinematic Orbital Insight Architecture) */}
        <HeroSection onEnterCommandCenter={() => {
          const el = document.getElementById('semantic-search');
          if (el) el.scrollIntoView({ behavior: 'smooth' });
        }} />

        {/* Section 2: Semantic Search & 8-Stage Autonomous Pipeline */}
        <SemanticSearch onSearch={handleSearch} isSearching={isSearching} />

        {/* Section 3: Ranked Candidate Tiles // Geospatial Grid - Displayed when user search query (Comes BEFORE Image Search) */}
        {hasSearched && (
          <CandidateTilesGrid
            tiles={tiles}
            selectedTileId={selectedTileId}
            onSelectTile={handleSelectTile}
            activeQuery={activeQuery}
          />
        )}

        {/* Section 4: Image-to-Image Satellite Reverse Search */}
        <ImageToImageSearch onSelectTile={handleSelectTile} />

        {/* Deep Target Analysis & Audit Suite */}
        {hasSearched && (
          <>
            {/* Section 5: High-Resolution Target Inspector & Optical AI Detection */}
            <ImageInspector activeTile={activeTile} />

            {/* Section 6: Dedicated Temporal Comparison & Multi-Year Change Detection */}
            <TemporalAnalysis activeTile={activeTile} onSelectTile={handleSelectTile} />

            {/* Section 7: Analyst Mission Review & Offline Audit Log */}
            <AnalystReview activeTile={activeTile} />
          </>
        )}

        {/* Section 8: Add New Satellite Tile // Data Ingestion & Live SQLite Archive */}
        <TileIngestion 
          onTileIngested={handleTileIngested}
          onViewTile={handleViewTile}
          onSearchTile={handleSearchTile}
        />
      </main>

      {/* Persistent Bottom HUD Dock */}
      <TelemetryDock />
    </div>
  );
}
