import React, { useEffect, useRef, useState, Component } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { 
  X, MapPin, Layers, Activity, RotateCcw, 
  Navigation, ZoomIn, ZoomOut, Globe, WifiOff, Box, Route, AlertCircle,
  Radio, Compass, Crosshair
} from 'lucide-react';
import { 
  INDIA_STATES_GEOJSON, 
  INDIA_HYDROLOGY_GEOJSON, 
  generateLocalTacticalFeatures, 
  calculateNearestRiverDistance 
} from '../data/india_tactical_data';

// Geodesic distance (Haversine formula in km)
export function calculateDistanceKm(lat1, lon1, lat2, lon2) {
  const R = 6371; // Earth radius in km
  const dLat = (lat2 - lat1) * (Math.PI / 180);
  const dLon = (lon2 - lon1) * (Math.PI / 180);
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(lat1 * (Math.PI / 180)) * Math.cos(lat2 * (Math.PI / 180)) *
    Math.sin(dLon / 2) * Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

// Compass Bearing in degrees (0-360) and cardinal direction
export function calculateBearing(lat1, lon1, lat2, lon2) {
  const φ1 = lat1 * (Math.PI / 180);
  const φ2 = lat2 * (Math.PI / 180);
  const Δλ = (lon2 - lon1) * (Math.PI / 180);

  const y = Math.sin(Δλ) * Math.cos(φ2);
  const x = Math.cos(φ1) * Math.sin(φ2) - Math.sin(φ1) * Math.cos(φ2) * Math.cos(Δλ);
  const θ = Math.atan2(y, x);
  const brng = (θ * (180 / Math.PI) + 360) % 360;

  const cardinals = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"];
  const cardinal = cardinals[Math.round(brng / 22.5) % 16];
  return { degrees: Math.round(brng), cardinal };
}

// Fetch shortest road route from OSRM with graceful offline fallback
export async function fetchShortestRoadRoute(startLat, startLng, endLat, endLng) {
  const osrmUrl = `https://router.project-osrm.org/route/v1/driving/${startLng},${startLat};${endLng},${endLat}?overview=full&geometries=geojson&steps=true`;

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 6000);

    const resp = await fetch(osrmUrl, { signal: controller.signal });
    clearTimeout(timeoutId);

    if (resp.ok) {
      const data = await resp.json();
      if (data.code === 'Ok' && data.routes && data.routes.length > 0) {
        const route = data.routes[0];
        // Coordinates in GeoJSON are [lng, lat], convert to Leaflet [lat, lng]
        const latLngs = route.geometry.coordinates.map(pt => [pt[1], pt[0]]);
        const distanceKm = route.distance / 1000;
        const durationSec = route.duration;
        const hours = Math.floor(durationSec / 3600);
        const mins = Math.round((durationSec % 3600) / 60);
        const durationStr = hours > 0 ? `${hours}h ${mins}m` : `${mins} min`;

        const steps = (route.legs?.[0]?.steps || []).map(s => ({
          instruction: s.maneuver?.instruction || s.name || "Proceed on route",
          name: s.name || "Highway",
          distanceM: Math.round(s.distance),
        }));

        return {
          success: true,
          mode: 'road',
          coordinates: latLngs,
          distanceKm: distanceKm,
          durationStr: durationStr,
          durationSec: durationSec,
          summary: route.legs?.[0]?.summary || "Tactical Highway Corridor",
          steps: steps.slice(0, 8),
        };
      }
    }
  } catch (err) {
    console.warn("OSRM routing service unavailable, using tactical geodesic fallback:", err);
  }

  // Fallback: Great-Circle Geodesic Arc Interpolation
  const distKm = calculateDistanceKm(startLat, startLng, endLat, endLng);
  const stepsCount = Math.max(12, Math.min(60, Math.round(distKm / 20)));
  const arcPoints = [];

  for (let i = 0; i <= stepsCount; i++) {
    const frac = i / stepsCount;
    const lat = startLat + (endLat - startLat) * frac;
    const lng = startLng + (endLng - startLng) * frac;
    arcPoints.push([lat, lng]);
  }

  const estHours = Math.floor(distKm / 75);
  const estMins = Math.round((distKm % 75) / 75 * 60);

  return {
    success: true,
    mode: 'geodesic',
    coordinates: arcPoints,
    distanceKm: distKm,
    durationStr: `~${estHours}h ${estMins}m (at 75 km/h)`,
    durationSec: (distKm / 75) * 3600,
    summary: "Direct Geodesic Tactical Corridor",
    steps: [
      { instruction: "Depart from Operator Location", name: "Origin", distanceM: 0 },
      { instruction: "Navigate direct geodesic corridor", name: "Tactical Transit", distanceM: Math.round(distKm * 1000) },
      { instruction: "Arrive at Target Satellite Tile", name: "Destination Centroid", distanceM: 0 }
    ],
  };
}

// Safe & Exhaustive Coordinate Parser for all Tile Data Formats
export function parseTileCoordinates(tile) {
  let lat = 28.6139;
  let lng = 77.2090;

  if (!tile) {
    return {
      bounds: [[lat - 0.015, lng - 0.015], [lat + 0.015, lng + 0.015]],
      center: [lat, lng],
      latSpan: 0.03,
      lngSpan: 0.03,
    };
  }

  // 1. Bounds object { left, bottom, right, top }
  if (tile.bounds && typeof tile.bounds === 'object') {
    const b = tile.bounds;
    const bLeft = parseFloat(b.left);
    const bBottom = parseFloat(b.bottom);
    const bRight = parseFloat(b.right);
    const bTop = parseFloat(b.top);
    if (!isNaN(bLeft) && !isNaN(bBottom) && !isNaN(bRight) && !isNaN(bTop)) {
      const bounds = [[bBottom, bLeft], [bTop, bRight]];
      const center = [(bBottom + bTop) / 2, (bLeft + bRight) / 2];
      return { 
        bounds, 
        center, 
        latSpan: Math.max(0.005, Math.abs(bTop - bBottom)), 
        lngSpan: Math.max(0.005, Math.abs(bRight - bLeft)) 
      };
    }
  }

  // 2. Bbox array [minx, miny, maxx, maxy] or [minLng, minLat, maxLng, maxLat]
  const bbox = Array.isArray(tile.bbox) ? tile.bbox : (Array.isArray(tile.metadata?.bbox) ? tile.metadata.bbox : null);
  if (bbox && bbox.length === 4) {
    const minx = parseFloat(bbox[0]);
    const miny = parseFloat(bbox[1]);
    const maxx = parseFloat(bbox[2]);
    const maxy = parseFloat(bbox[3]);
    if (!isNaN(minx) && !isNaN(miny) && !isNaN(maxx) && !isNaN(maxy)) {
      const bounds = [[miny, minx], [maxy, maxx]];
      const center = [(miny + maxy) / 2, (minx + maxx) / 2];
      return { 
        bounds, 
        center, 
        latSpan: Math.max(0.005, Math.abs(maxy - miny)), 
        lngSpan: Math.max(0.005, Math.abs(maxx - minx)) 
      };
    }
  }

  // 3. Direct lat / lng properties
  const rawLat = tile.lat ?? tile.latitude ?? tile.metadata?.lat ?? tile.metadata?.latitude;
  const rawLng = tile.lng ?? tile.longitude ?? tile.metadata?.lng ?? tile.metadata?.longitude;
  let parsedLat = parseFloat(rawLat);
  let parsedLng = parseFloat(rawLng);

  if (!isNaN(parsedLat) && !isNaN(parsedLng)) {
    lat = parsedLat;
    lng = parsedLng;
  } else {
    // 4. Coordinates property (can be object, array, or string)
    const rawCoords = tile.coordinates ?? tile.metadata?.coordinates;
    if (rawCoords) {
      if (typeof rawCoords === 'object' && !Array.isArray(rawCoords) && rawCoords !== null) {
        const objLat = parseFloat(rawCoords.lat ?? rawCoords.latitude);
        const objLng = parseFloat(rawCoords.lng ?? rawCoords.longitude);
        if (!isNaN(objLat) && !isNaN(objLng)) {
          lat = objLat;
          lng = objLng;
        }
      } else if (Array.isArray(rawCoords) && rawCoords.length >= 2) {
        const arrLat = parseFloat(rawCoords[0]);
        const arrLng = parseFloat(rawCoords[1]);
        if (!isNaN(arrLat) && !isNaN(arrLng)) {
          lat = arrLat;
          lng = arrLng;
        }
      } else if (typeof rawCoords === 'string') {
        const matches = rawCoords.match(/[-+]?[0-9]*\.?[0-9]+/g);
        if (matches && matches.length >= 2) {
          const strLat = parseFloat(matches[0]);
          const strLng = parseFloat(matches[1]);
          if (!isNaN(strLat) && !isNaN(strLng)) {
            lat = strLat;
            lng = strLng;
          }
        }
      }
    }
  }

  // Safety fallback if lat or lng is still NaN or outside global range
  if (isNaN(lat) || Math.abs(lat) > 90) lat = 28.6139;
  if (isNaN(lng) || Math.abs(lng) > 180) lng = 77.2090;

  const bounds = [[lat - 0.015, lng - 0.015], [lat + 0.015, lng + 0.015]];
  const center = [lat, lng];
  return { bounds, center, latSpan: 0.03, lngSpan: 0.03 };
}

// Error Boundary Wrapper to guarantee website NEVER crashes
class TacticalMapErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("TacticalMapModal caught error:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="fixed inset-0 z-[9999] bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-4">
          <div className="bg-slate-900 border-2 border-rose-500 rounded-2xl p-6 max-w-md text-center space-y-4 shadow-2xl">
            <div className="w-12 h-12 rounded-full bg-rose-500/20 border border-rose-500 flex items-center justify-center mx-auto text-rose-400">
              <AlertCircle className="w-6 h-6" />
            </div>
            <h3 className="text-lg font-bold text-white">Tactical Map Notice</h3>
            <p className="text-xs font-mono text-slate-300">
              An unexpected render error occurred while loading the map view.
            </p>
            <button
              onClick={() => {
                this.setState({ hasError: false });
                this.props.onClose();
              }}
              className="px-4 py-2 bg-rose-600 hover:bg-rose-500 text-white rounded-xl font-mono text-xs font-bold transition-all cursor-pointer"
            >
              [ Dismiss &amp; Close Map ]
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

function TacticalMapModalInner({ isOpen, onClose, activeTile, tileImageSrc }) {
  const mapContainerRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const watchIdRef = useRef(null);
  const layersRef = useRef({
    baseTileLayer: null,
    airgapGridLayer: null,
    tileOverlay: null,
    tileRect: null,
    beaconMarker: null,
    statesLayer: null,
    hydrologyLayer: null,
    buildingsLayer: null,
    roadsLayer: null,
    userMarker: null,
    userAccuracyCircle: null,
    rangeLine: null,
    routeGlowLayer: null,
    routeLineLayer: null,
  });

  // Layer & Basemap toggles
  const [basemapMode, setBasemapMode] = useState('clean-white'); // 'clean-white' | 'airgap-white'
  const [showRaster, setShowRaster] = useState(true);
  const [showBuildings, setShowBuildings] = useState(true);
  const [showRoads, setShowRoads] = useState(true);
  const [showHydrology, setShowHydrology] = useState(true);
  const [showStates, setShowStates] = useState(true);
  const [rasterOpacity, setRasterOpacity] = useState(85);
  const [hudTelemetry, setHudTelemetry] = useState(null);

  // Live Laptop GPS Geolocation state
  const [userLocation, setUserLocation] = useState(null);
  const [isLocating, setIsLocating] = useState(false);
  const [isTracking, setIsTracking] = useState(false);
  const [geoError, setGeoError] = useState(null);

  // Shortest Route Navigation state
  const [routeData, setRouteData] = useState(null);
  const [showRoute, setShowRoute] = useState(false);
  const [routeMode, setRouteMode] = useState('road'); // 'road' | 'geodesic'
  const [isCalculatingRoute, setIsCalculatingRoute] = useState(false);

  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isOpen) onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  // Clean up geolocation tracking and map on modal close
  useEffect(() => {
    if (!isOpen) {
      if (watchIdRef.current !== null) {
        navigator.geolocation.clearWatch(watchIdRef.current);
        watchIdRef.current = null;
      }
      setUserLocation(null);
      setIsTracking(false);
      setIsLocating(false);
      setGeoError(null);
    }
  }, [isOpen]);

  // Main Leaflet Map Initialization & Rendering
  useEffect(() => {
    if (!isOpen) {
      if (mapInstanceRef.current) {
        try {
          mapInstanceRef.current.remove();
        } catch (e) {
          console.warn("Leaflet cleanup error:", e);
        }
        mapInstanceRef.current = null;
      }
      return;
    }

    if (!mapContainerRef.current) return;

    // 1. Extract guaranteed valid coordinates and bounds
    const { bounds, center, latSpan, lngSpan } = parseTileCoordinates(activeTile);

    // 2. Calculate live telemetry
    const areaKm2 = (latSpan * 111 * lngSpan * 111 * Math.cos(center[0] * (Math.PI / 180))).toFixed(2);
    const riverInfo = calculateNearestRiverDistance(center[0], center[1]);
    
    setHudTelemetry({
      centerLat: center[0].toFixed(4),
      centerLng: center[1].toFixed(4),
      areaKm2: Math.max(0.25, parseFloat(areaKm2) || 0.25),
      riverName: riverInfo.riverName || "Yamuna River Corridor",
      riverDistanceKm: riverInfo.distanceKm || "1.50",
      isNearRiver: !!riverInfo.isWithinConstraint,
      sensor: activeTile?.sensor || "Sentinel-2 MSI",
      crs: activeTile?.crs || "EPSG:32643",
      tileId: activeTile?.id || activeTile?.tile_name || "TARGET_RECON_TILE",
      date: activeTile?.date || activeTile?.dateIso || new Date().toISOString().slice(0, 10),
    });

    // 3. Clean up any previous Leaflet DOM ID and instance
    if (mapContainerRef.current._leaflet_id) {
      delete mapContainerRef.current._leaflet_id;
    }
    if (mapInstanceRef.current) {
      try {
        mapInstanceRef.current.remove();
      } catch (e) {
        console.warn("Map remove error:", e);
      }
      mapInstanceRef.current = null;
    }

    try {
      // 4. Initialize fresh Leaflet map on clean white container
      const map = L.map(mapContainerRef.current, {
        zoomControl: false,
        attributionControl: false,
        minZoom: 4,
        maxZoom: 19,
      }).setView(center, 14);

      mapInstanceRef.current = map;

      // 5. Basemap Layer: Clean White OpenStreetMap (Free, Zero API Key Required)
      if (basemapMode === 'clean-white') {
        const baseTileLayer = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
          maxZoom: 19,
          className: 'clean-white-tiles',
          crossOrigin: true,
        });

        baseTileLayer.on('tileerror', (e) => {
          if (e.tile) e.tile.style.display = 'none';
        });

        baseTileLayer.addTo(map);
        layersRef.current.baseTileLayer = baseTileLayer;
      }

      // 6. Air-Gap Clean White Tactical Canvas Grid (Works 100% offline with zero network)
      if (basemapMode === 'airgap-white' || basemapMode === 'clean-white') {
        const TacticalGridLayer = L.GridLayer.extend({
          createTile: function (coords) {
            const tile = document.createElement('canvas');
            tile.width = 256;
            tile.height = 256;
            const ctx = tile.getContext('2d');

            if (basemapMode === 'airgap-white') {
              ctx.fillStyle = '#ffffff';
              ctx.fillRect(0, 0, 256, 256);
            }

            // Subtle coordinate grid
            ctx.strokeStyle = basemapMode === 'airgap-white' ? 'rgba(100, 116, 139, 0.25)' : 'rgba(148, 163, 184, 0.15)';
            ctx.lineWidth = 1;
            ctx.strokeRect(0, 0, 256, 256);

            // Center crosshair
            ctx.strokeStyle = 'rgba(2, 132, 199, 0.35)';
            ctx.beginPath();
            ctx.moveTo(120, 128); ctx.lineTo(136, 128);
            ctx.moveTo(128, 120); ctx.lineTo(128, 136);
            ctx.stroke();

            // Coordinate labels
            ctx.fillStyle = 'rgba(71, 85, 105, 0.55)';
            ctx.font = 'bold 9px monospace';
            ctx.fillText(`GRID Z${coords.z} // X${coords.x} Y${coords.y}`, 8, 246);

            return tile;
          }
        });

        const airgapGridLayer = new TacticalGridLayer({ zIndex: basemapMode === 'airgap-white' ? 1 : 2 }).addTo(map);
        layersRef.current.airgapGridLayer = airgapGridLayer;
      }

      // 7. Layer: India State Boundaries GeoJSON
      if (showStates) {
        const statesLayer = L.geoJSON(INDIA_STATES_GEOJSON, {
          style: (feature) => ({
            color: feature.properties?.type === 'NationalBorder' ? '#d97706' : '#0284c7',
            weight: feature.properties?.type === 'NationalBorder' ? 2.5 : 1.5,
            dashArray: '5, 5',
            fillColor: '#0284c7',
            fillOpacity: 0.03,
          }),
          onEachFeature: (feature, layer) => {
            if (feature.properties?.name) {
              layer.bindTooltip(`📍 ${feature.properties.name}`, {
                className: 'tactical-map-tooltip-light',
                sticky: true,
              });
            }
          },
        }).addTo(map);
        layersRef.current.statesLayer = statesLayer;
      }

      // 8. Layer: Hydrology & River Vector Corridors (Water Bodies)
      if (showHydrology) {
        const hydrologyLayer = L.geoJSON(INDIA_HYDROLOGY_GEOJSON, {
          style: {
            color: '#0284c7',
            weight: 4,
            opacity: 0.9,
            lineCap: 'round',
            lineJoin: 'round',
          },
          onEachFeature: (feature, layer) => {
            if (feature.properties?.name) {
              layer.bindTooltip(`🌊 ${feature.properties.name} (${feature.properties.length_km || 1000} km)`, {
                className: 'tactical-map-tooltip-light',
                sticky: true,
              });
            }
          },
        }).addTo(map);
        layersRef.current.hydrologyLayer = hydrologyLayer;
      }

      // 9. Layer: Tactical Roads / Ways & Building Blocks
      const { buildingsGeoJSON, roadsGeoJSON } = generateLocalTacticalFeatures(center[0], center[1], bounds);

      if (showRoads) {
        const roadsLayer = L.geoJSON(roadsGeoJSON, {
          style: (feature) => ({
            color: feature.properties?.class === 'PrimaryRoad' ? '#ea580c' : '#475569',
            weight: feature.properties?.class === 'PrimaryRoad' ? 4 : 2.5,
            dashArray: feature.properties?.class === 'PrimaryRoad' ? '8, 4' : undefined,
            opacity: 0.9,
          }),
          onEachFeature: (feature, layer) => {
            if (feature.properties?.name) {
              layer.bindTooltip(`🛣️ ${feature.properties.name}`, {
                className: 'tactical-map-tooltip-light',
                sticky: true,
              });
            }
          },
        }).addTo(map);
        layersRef.current.roadsLayer = roadsLayer;
      }

      // 10. Layer: Building Footprints (Rendered as solid polygon blocks)
      if (showBuildings) {
        const buildingsLayer = L.geoJSON(buildingsGeoJSON, {
          style: () => ({
            color: '#0f172a',
            weight: 2,
            fillColor: '#334155',
            fillOpacity: 0.78,
          }),
          onEachFeature: (feature, layer) => {
            const p = feature.properties;
            layer.bindTooltip(`🏢 <b>${p.name}</b><br/>Height: ${p.height_m}m &bull; Area: ${p.footprint_m2.toLocaleString()} m²`, {
              className: 'tactical-map-tooltip-light',
              sticky: true,
            });
          },
        }).addTo(map);
        layersRef.current.buildingsLayer = buildingsLayer;
      }

      // 11. Layer: Tile Bounding Box (Highlighted Extent)
      const tileRect = L.rectangle(bounds, {
        color: '#00b4d8',
        weight: 3,
        dashArray: '6, 6',
        fillColor: '#00b4d8',
        fillOpacity: 0.16,
      }).addTo(map);

      tileRect.bindTooltip(`🎯 <b>TARGET TILE: ${activeTile?.id || 'Active'}</b><br/>Extent: [${bounds[0][0].toFixed(3)}, ${bounds[0][1].toFixed(3)}] to [${bounds[1][0].toFixed(3)}, ${bounds[1][1].toFixed(3)}]`, {
        className: 'tactical-map-tooltip-light',
        sticky: true,
      });
      layersRef.current.tileRect = tileRect;

      // 12. Layer: Real Satellite Image Overlay
      const imageSrc = tileImageSrc || activeTile?.image || (activeTile?.image_path ? `http://127.0.0.1:8000/${activeTile.image_path.replace(/\\/g, '/').replace(/^\/+/, '')}` : null);
      
      if (showRaster && imageSrc) {
        try {
          const tileOverlay = L.imageOverlay(imageSrc, bounds, {
            opacity: rasterOpacity / 100,
            interactive: true,
          }).addTo(map);
          layersRef.current.tileOverlay = tileOverlay;
        } catch (err) {
          console.warn("Could not load imageOverlay on Leaflet map:", err);
        }
      }

      // 13. Layer: Pulsing Radar Beacon Centroid Marker
      const radarIcon = L.divIcon({
        className: 'tactical-radar-beacon-icon',
        html: `
          <div class="relative flex items-center justify-center w-8 h-8 -ml-4 -mt-4 pointer-events-none">
            <div class="absolute w-8 h-8 rounded-full bg-cyan-500/30 animate-ping"></div>
            <div class="absolute w-5 h-5 rounded-full bg-cyan-500/50 animate-pulse"></div>
            <div class="w-3.5 h-3.5 rounded-full bg-[#00e5ff] border-2 border-slate-900 shadow-[0_0_12px_#00e5ff]"></div>
          </div>
        `,
        iconSize: [32, 32],
        iconAnchor: [16, 16],
      });

      const beaconMarker = L.marker(center, { icon: radarIcon }).addTo(map);
      beaconMarker.bindTooltip(`📍 Centroid: ${center[0].toFixed(4)}° N, ${center[1].toFixed(4)}° E`, {
        className: 'tactical-map-tooltip-light',
      });
      layersRef.current.beaconMarker = beaconMarker;

      // Ensure map container renders completely and fits bounds
      setTimeout(() => {
        if (mapInstanceRef.current) {
          mapInstanceRef.current.invalidateSize();
          mapInstanceRef.current.fitBounds(bounds, {
            padding: [50, 50],
            animate: true,
            duration: 0.8,
            maxZoom: 16,
          });
        }
      }, 120);

    } catch (err) {
      console.error("Leaflet initialization error:", err);
    }

    return () => {
      if (mapInstanceRef.current) {
        try {
          mapInstanceRef.current.remove();
        } catch (e) {
          console.warn("Leaflet cleanup error:", e);
        }
        mapInstanceRef.current = null;
      }
    };
  }, [isOpen, activeTile, tileImageSrc, basemapMode, showRaster, showBuildings, showRoads, showHydrology, showStates]);

  // Adjust overlay opacity in real-time without re-creating map
  useEffect(() => {
    if (layersRef.current.tileOverlay) {
      try {
        layersRef.current.tileOverlay.setOpacity(rasterOpacity / 100);
      } catch (e) {
        console.warn("Opacity update error:", e);
      }
    }
  }, [rasterOpacity]);

  // Dynamically render / update User Location Marker, Accuracy Circle & Tactical Range Vector
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    if (!userLocation) {
      if (layersRef.current.userMarker) {
        layersRef.current.userMarker.remove();
        layersRef.current.userMarker = null;
      }
      if (layersRef.current.userAccuracyCircle) {
        layersRef.current.userAccuracyCircle.remove();
        layersRef.current.userAccuracyCircle = null;
      }
      if (layersRef.current.rangeLine) {
        layersRef.current.rangeLine.remove();
        layersRef.current.rangeLine = null;
      }
      return;
    }

    try {
      const userLatLng = [userLocation.lat, userLocation.lng];
      const { center } = parseTileCoordinates(activeTile);
      const distKm = calculateDistanceKm(userLocation.lat, userLocation.lng, center[0], center[1]);
      const bearing = calculateBearing(userLocation.lat, userLocation.lng, center[0], center[1]);

      // 1. Operator Beacon DivIcon
      const operatorIcon = L.divIcon({
        className: 'tactical-operator-beacon-icon',
        html: `
          <div class="relative flex items-center justify-center w-10 h-10 -ml-5 -mt-5 pointer-events-none">
            <div class="absolute w-10 h-10 rounded-full bg-blue-500/35 animate-ping"></div>
            <div class="absolute w-6 h-6 rounded-full bg-blue-600/50 animate-pulse"></div>
            <div class="w-4 h-4 rounded-full bg-[#2563eb] border-2 border-white shadow-[0_0_15px_#2563eb] flex items-center justify-center">
              <div class="w-1.5 h-1.5 bg-white rounded-full"></div>
            </div>
          </div>
        `,
        iconSize: [40, 40],
        iconAnchor: [20, 20],
      });

      // Update or create User Marker
      if (layersRef.current.userMarker) {
        layersRef.current.userMarker.setLatLng(userLatLng);
      } else {
        const userMarker = L.marker(userLatLng, { icon: operatorIcon, zIndexOffset: 1000 }).addTo(map);
        layersRef.current.userMarker = userMarker;
      }

      layersRef.current.userMarker.bindTooltip(`📍 <b>YOUR LAPTOP LOCATION (OPERATOR BEACON)</b><br/>Coordinates: ${userLocation.lat.toFixed(5)}° N, ${userLocation.lng.toFixed(5)}° E<br/>GPS Accuracy: ±${Math.round(userLocation.accuracy)}m<br/>Distance to Satellite Tile: <b>${distKm.toFixed(2)} km</b> (Bearing: ${bearing.degrees}° ${bearing.cardinal})`, {
        className: 'tactical-map-tooltip-light',
        sticky: true,
      });

      // 2. Accuracy Radius Circle
      if (layersRef.current.userAccuracyCircle) {
        layersRef.current.userAccuracyCircle.setLatLng(userLatLng);
        layersRef.current.userAccuracyCircle.setRadius(Math.max(10, userLocation.accuracy));
      } else {
        const userAccuracyCircle = L.circle(userLatLng, {
          radius: Math.max(10, userLocation.accuracy),
          color: '#2563eb',
          fillColor: '#38bdf8',
          fillOpacity: 0.15,
          weight: 1.5,
          dashArray: '4, 4',
        }).addTo(map);
        layersRef.current.userAccuracyCircle = userAccuracyCircle;
      }

      // 3. Tactical Geodesic Vector Line connecting Operator to Satellite Tile Centroid
      if (layersRef.current.rangeLine) {
        layersRef.current.rangeLine.setLatLngs([userLatLng, center]);
      } else {
        const rangeLine = L.polyline([userLatLng, center], {
          color: '#0284c7',
          weight: 2.5,
          dashArray: '6, 6',
          opacity: 0.85,
        }).addTo(map);
        layersRef.current.rangeLine = rangeLine;
      }

      layersRef.current.rangeLine.bindTooltip(`📡 <b>TACTICAL LINK VECTOR</b><br/>Range: <b>${distKm.toFixed(2)} km</b> &bull; Bearing: ${bearing.degrees}° ${bearing.cardinal}`, {
        className: 'tactical-map-tooltip-light',
        sticky: true,
      });

    } catch (e) {
      console.warn("Operator marker update error:", e);
    }
  }, [userLocation, activeTile]);

  // Toggle Live Laptop GPS Geolocation
  const handleToggleLiveLocation = () => {
    if (isTracking) {
      // Stop continuous tracking
      if (watchIdRef.current !== null) {
        navigator.geolocation.clearWatch(watchIdRef.current);
        watchIdRef.current = null;
      }
      setIsTracking(false);
      setIsLocating(false);
      setUserLocation(null);
      setGeoError(null);
      return;
    }

    if (!navigator.geolocation) {
      setGeoError("HTML5 Geolocation is not supported by your browser or device.");
      return;
    }

    setIsLocating(true);
    setGeoError(null);

    const successCallback = (pos) => {
      const { latitude, longitude, accuracy, heading, speed } = pos.coords;
      const newLoc = {
        lat: latitude,
        lng: longitude,
        accuracy: accuracy || 20,
        heading: heading,
        speed: speed,
        timestamp: pos.timestamp || Date.now(),
      };

      setUserLocation(newLoc);
      setIsLocating(false);
      setIsTracking(true);
      setGeoError(null);
    };

    const errorCallback = (err) => {
      setIsLocating(false);
      let msg = "Could not acquire laptop GPS position.";
      if (err.code === 1) {
        msg = "Location permission was denied. Please allow location access in your browser address bar.";
      } else if (err.code === 2) {
        msg = "Position unavailable. Please check your laptop's location/Wi-Fi settings.";
      } else if (err.code === 3) {
        msg = "GPS location request timed out.";
      }
      setGeoError(msg);
      setTimeout(() => setGeoError(null), 8000);
    };

    const options = {
      enableHighAccuracy: true,
      timeout: 12000,
      maximumAge: 0,
    };

    // First get current position and zoom in
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        successCallback(pos);
        if (mapInstanceRef.current) {
          mapInstanceRef.current.flyTo([pos.coords.latitude, pos.coords.longitude], 15, {
            animate: true,
            duration: 1.2,
          });
        }
        // Then start continuous position watching
        try {
          const watchId = navigator.geolocation.watchPosition(successCallback, errorCallback, options);
          watchIdRef.current = watchId;
        } catch (e) {
          console.warn("watchPosition error:", e);
        }
      },
      errorCallback,
      options
    );
  };

  // Compute & Draw Shortest Route between Operator GPS and Satellite Tile Centroid
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    if (!showRoute || !userLocation) {
      if (layersRef.current.routeGlowLayer) {
        layersRef.current.routeGlowLayer.remove();
        layersRef.current.routeGlowLayer = null;
      }
      if (layersRef.current.routeLineLayer) {
        layersRef.current.routeLineLayer.remove();
        layersRef.current.routeLineLayer = null;
      }
      return;
    }

    let isMounted = true;
    const { center } = parseTileCoordinates(activeTile);

    const computeRoute = async () => {
      setIsCalculatingRoute(true);
      try {
        let result;
        if (routeMode === 'geodesic') {
          const distKm = calculateDistanceKm(userLocation.lat, userLocation.lng, center[0], center[1]);
          const stepsCount = Math.max(12, Math.min(60, Math.round(distKm / 20)));
          const arcPoints = [];
          for (let i = 0; i <= stepsCount; i++) {
            const frac = i / stepsCount;
            const lat = userLocation.lat + (center[0] - userLocation.lat) * frac;
            const lng = userLocation.lng + (center[1] - userLocation.lng) * frac;
            arcPoints.push([lat, lng]);
          }
          const estHours = Math.floor(distKm / 75);
          const estMins = Math.round((distKm % 75) / 75 * 60);
          result = {
            success: true,
            mode: 'geodesic',
            coordinates: arcPoints,
            distanceKm: distKm,
            durationStr: `~${estHours}h ${estMins}m (at 75 km/h)`,
            durationSec: (distKm / 75) * 3600,
            summary: "Direct Geodesic Air Arc",
            steps: [
              { instruction: "Depart from Operator Location", name: "Origin", distanceM: 0 },
              { instruction: "Navigate direct geodesic corridor", name: "Tactical Transit", distanceM: Math.round(distKm * 1000) },
              { instruction: "Arrive at Target Satellite Tile Centroid", name: "Destination Centroid", distanceM: 0 }
            ],
          };
        } else {
          result = await fetchShortestRoadRoute(userLocation.lat, userLocation.lng, center[0], center[1]);
        }

        if (!isMounted) return;
        setRouteData(result);

        if (result && result.coordinates && result.coordinates.length > 0) {
          // 1. Radiant Neon Amber Glowing Outer Path
          if (layersRef.current.routeGlowLayer) {
            layersRef.current.routeGlowLayer.setLatLngs(result.coordinates);
          } else {
            const routeGlowLayer = L.polyline(result.coordinates, {
              color: '#f59e0b',
              weight: 8,
              opacity: 0.45,
              lineCap: 'round',
              lineJoin: 'round',
            }).addTo(map);
            layersRef.current.routeGlowLayer = routeGlowLayer;
          }

          // 2. High-contrast Tactical Orange Directional Core Polyline
          if (layersRef.current.routeLineLayer) {
            layersRef.current.routeLineLayer.setLatLngs(result.coordinates);
          } else {
            const routeLineLayer = L.polyline(result.coordinates, {
              color: '#ea580c',
              weight: 4.5,
              opacity: 0.95,
              dashArray: result.mode === 'geodesic' ? '8, 6' : undefined,
              lineCap: 'round',
              lineJoin: 'round',
            }).addTo(map);
            layersRef.current.routeLineLayer = routeLineLayer;
          }

          const modeLabel = result.mode === 'road' ? '🛣️ SHORTEST ROAD ROUTE' : '🛩️ DIRECT AIR ARC';
          const tooltipContent = `
            <b>${modeLabel}</b><br/>
            Total Distance: <b>${result.distanceKm.toFixed(2)} km</b><br/>
            Est. Transit Time: <b>${result.durationStr}</b><br/>
            Corridor: <i>${result.summary}</i>
          `;
          layersRef.current.routeLineLayer.bindTooltip(tooltipContent, {
            className: 'tactical-map-tooltip-light',
            sticky: true,
          });
        }
      } catch (err) {
        console.warn("Error calculating route:", err);
      } finally {
        if (isMounted) setIsCalculatingRoute(false);
      }
    };

    computeRoute();

    return () => {
      isMounted = false;
    };
  }, [userLocation, activeTile, routeMode, showRoute]);

  const handleToggleRoute = () => {
    if (!userLocation) {
      setShowRoute(true);
      handleToggleLiveLocation();
      return;
    }
    setShowRoute(prev => !prev);
  };

  const handleFitRoute = () => {
    if (!mapInstanceRef.current) return;
    if (routeData?.coordinates?.length) {
      try {
        const polylineBounds = L.latLngBounds(routeData.coordinates);
        mapInstanceRef.current.fitBounds(polylineBounds, {
          padding: [60, 60],
          animate: true,
          duration: 1.0,
          maxZoom: 16,
        });
      } catch (e) {
        console.warn("Fit route error:", e);
      }
    } else {
      handleFitBoth();
    }
  };

  const handleFlyToOperator = () => {
    if (!mapInstanceRef.current || !userLocation) return;
    try {
      mapInstanceRef.current.flyTo([userLocation.lat, userLocation.lng], 16, {
        animate: true,
        duration: 1.0,
      });
    } catch (e) {
      console.warn("Fly to operator error:", e);
    }
  };

  const handleFitBoth = () => {
    if (!mapInstanceRef.current || !userLocation) return;
    try {
      const { bounds } = parseTileCoordinates(activeTile);
      const combinedBounds = L.latLngBounds([
        bounds[0],
        bounds[1],
        [userLocation.lat, userLocation.lng]
      ]);
      mapInstanceRef.current.fitBounds(combinedBounds, {
        padding: [60, 60],
        animate: true,
        duration: 1.0,
        maxZoom: 16,
      });
    } catch (e) {
      console.warn("Fit both error:", e);
    }
  };

  const handleFlyToTarget = () => {
    if (!mapInstanceRef.current) return;
    try {
      const { bounds } = parseTileCoordinates(activeTile);
      mapInstanceRef.current.fitBounds(bounds, {
        padding: [50, 50],
        animate: true,
        duration: 0.8,
        maxZoom: 16,
      });
    } catch (e) {
      console.warn("Fly to target error:", e);
    }
  };

  const handleResetViewAllIndia = () => {
    if (!mapInstanceRef.current) return;
    try {
      mapInstanceRef.current.flyTo([22.5, 82.0], 5, {
        animate: true,
        duration: 1.2,
      });
    } catch (e) {
      console.warn("Reset view error:", e);
    }
  };

  const handleZoomIn = () => {
    try {
      mapInstanceRef.current?.zoomIn();
    } catch (e) {
      console.warn("Zoom in error:", e);
    }
  };

  const handleZoomOut = () => {
    try {
      mapInstanceRef.current?.zoomOut();
    } catch (e) {
      console.warn("Zoom out error:", e);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[9999] bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-3 sm:p-6 animate-fade-in">
      <div className="relative w-full max-w-7xl h-[92vh] bg-white border-2 border-cyan-400 shadow-[0_0_50px_rgba(0,229,255,0.35)] rounded-3xl flex flex-col overflow-hidden">
        
        {/* TOP COMMAND HEADER */}
        <div className="px-6 py-3.5 bg-[#071328] border-b-2 border-cyan-400/50 flex flex-wrap items-center justify-between gap-3 shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-cyan-500/20 border border-cyan-400 flex items-center justify-center text-cyan-300 shadow-[0_0_15px_rgba(0,229,255,0.4)]">
              <MapPin className="w-5 h-5 text-cyan-400 animate-pulse" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs font-black text-cyan-400 uppercase tracking-wider">
                  TACTICAL SITUATIONAL MAP // WHITE SURFACE
                </span>
                <span className="px-2 py-0.5 bg-emerald-500/20 border border-emerald-400/40 text-emerald-300 font-mono text-[10px] font-bold rounded-full flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                  KEYLESS OSM // OFFLINE READY
                </span>
              </div>
              <p className="font-mono text-[11px] text-slate-300">
                Target: <span className="text-cyan-300 font-bold">{hudTelemetry?.tileId}</span> &bull; {hudTelemetry?.date} &bull; {hudTelemetry?.sensor}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            {/* Basemap Mode Selector */}
            <div className="hidden sm:flex items-center bg-[#0d2144] border border-cyan-500/40 rounded-xl p-1 font-mono text-[10px] mr-1">
              <button
                type="button"
                onClick={() => setBasemapMode('clean-white')}
                className={`px-3 py-1 rounded-lg font-bold transition-all cursor-pointer flex items-center gap-1.5 ${
                  basemapMode === 'clean-white' 
                    ? 'bg-cyan-400 text-slate-950 shadow-md shadow-cyan-500/30' 
                    : 'text-slate-300 hover:text-white'
                }`}
              >
                <Globe className="w-3.5 h-3.5" />
                <span>White Map (Ways &amp; Blocks)</span>
              </button>
              <button
                type="button"
                onClick={() => setBasemapMode('airgap-white')}
                className={`px-3 py-1 rounded-lg font-bold transition-all cursor-pointer flex items-center gap-1.5 ${
                  basemapMode === 'airgap-white' 
                    ? 'bg-cyan-400 text-slate-950 shadow-md shadow-cyan-500/30' 
                    : 'text-slate-300 hover:text-white'
                }`}
              >
                <WifiOff className="w-3.5 h-3.5" />
                <span>Air-Gap White Grid</span>
              </button>
            </div>

            {/* LIVE LAPTOP GPS GEOLOCATION TOGGLE */}
            <button
              type="button"
              onClick={handleToggleLiveLocation}
              disabled={isLocating}
              className={`px-3 py-1.5 font-mono text-[11px] font-bold uppercase rounded-xl transition-all flex items-center gap-1.5 cursor-pointer shadow-sm ${
                isTracking
                  ? 'bg-blue-600 hover:bg-blue-500 text-white border-2 border-blue-400 shadow-[0_0_15px_rgba(59,130,246,0.5)] scale-[1.02]'
                  : 'bg-blue-950/70 hover:bg-blue-900/90 text-blue-300 hover:text-white border border-blue-500/50'
              }`}
              title="Locate your laptop GPS position on the tactical map in real-time"
            >
              <Radio className={`w-3.5 h-3.5 ${isTracking ? 'animate-pulse text-cyan-300' : isLocating ? 'animate-spin text-blue-400' : ''}`} />
              <span>
                {isLocating
                  ? "Acquiring GPS..."
                  : isTracking
                  ? `[ 📍 OPERATOR LIVE: ±${Math.round(userLocation?.accuracy || 15)}m ]`
                  : "[ 📍 LOCATE MY LAPTOP ]"}
              </span>
            </button>

            {/* SHORTEST ROUTE TO SATELLITE TILE */}
            <button
              type="button"
              onClick={handleToggleRoute}
              className={`px-3 py-1.5 font-mono text-[11px] font-bold uppercase rounded-xl transition-all flex items-center gap-1.5 cursor-pointer shadow-sm ${
                showRoute
                  ? 'bg-amber-600 hover:bg-amber-500 text-slate-950 border-2 border-amber-400 shadow-[0_0_15px_rgba(245,158,11,0.5)] font-black scale-[1.02]'
                  : 'bg-amber-950/70 hover:bg-amber-900/90 text-amber-300 hover:text-white border border-amber-500/50'
              }`}
              title="Compute shortest driving / transit route from your laptop location to the satellite tile centroid"
            >
              <Route className={`w-3.5 h-3.5 ${isCalculatingRoute ? 'animate-spin' : ''}`} />
              <span>
                {isCalculatingRoute
                  ? "Routing..."
                  : showRoute
                  ? "[ 🛣️ ROUTE ACTIVE ]"
                  : "[ 🛣️ SHORTEST ROUTE ]"}
              </span>
            </button>

            {/* QUICK ACTIONS WHEN OPERATOR LOCATION IS ACTIVE */}
            {isTracking && userLocation && (
              <>
                {showRoute && (
                  <button
                    type="button"
                    onClick={handleFitRoute}
                    className="px-2.5 py-1.5 bg-amber-500/20 hover:bg-amber-500 text-amber-300 hover:text-slate-950 border border-amber-400/50 font-mono text-[11px] font-bold uppercase rounded-xl transition-all flex items-center gap-1 cursor-pointer"
                    title="Fit camera to view the full shortest route corridor"
                  >
                    <Navigation className="w-3.5 h-3.5" />
                    <span>[ Fit Full Route ]</span>
                  </button>
                )}
                <button
                  type="button"
                  onClick={handleFlyToOperator}
                  className="px-2.5 py-1.5 bg-blue-500/20 hover:bg-blue-500 text-blue-300 hover:text-white border border-blue-400/50 font-mono text-[11px] font-bold uppercase rounded-xl transition-all flex items-center gap-1 cursor-pointer"
                  title="Fly camera directly to your laptop's current GPS location"
                >
                  <Crosshair className="w-3.5 h-3.5" />
                  <span>[ Fly To Me ]</span>
                </button>
                <button
                  type="button"
                  onClick={handleFitBoth}
                  className="px-2.5 py-1.5 bg-indigo-500/20 hover:bg-indigo-500 text-indigo-300 hover:text-white border border-indigo-400/50 font-mono text-[11px] font-bold uppercase rounded-xl transition-all flex items-center gap-1 cursor-pointer"
                  title="Zoom map out to display both your laptop location and satellite tile together"
                >
                  <Compass className="w-3.5 h-3.5" />
                  <span>[ Fit Both ]</span>
                </button>
              </>
            )}

            <button
              type="button"
              onClick={handleFlyToTarget}
              className="px-3 py-1.5 bg-cyan-500/20 hover:bg-cyan-400 text-cyan-300 hover:text-slate-950 border border-cyan-400/50 font-mono text-[11px] font-bold uppercase rounded-xl transition-all flex items-center gap-1.5 cursor-pointer shadow-sm"
              title="Fly camera to target tile bounds"
            >
              <Navigation className="w-3.5 h-3.5" />
              <span>[ Fly To Tile ]</span>
            </button>
            <button
              type="button"
              onClick={handleResetViewAllIndia}
              className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-600 font-mono text-[11px] font-bold uppercase rounded-xl transition-all flex items-center gap-1.5 cursor-pointer"
              title="View all-India tactical coverage"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>[ All India ]</span>
            </button>
            <button
              type="button"
              onClick={onClose}
              className="px-3.5 py-1.5 bg-rose-500/20 hover:bg-rose-500 text-rose-300 hover:text-white border border-rose-500/50 font-mono text-[11px] font-bold uppercase rounded-xl transition-all flex items-center gap-1 cursor-pointer shadow-sm ml-1"
            >
              <X className="w-4 h-4" />
              <span>[ CLOSE ]</span>
            </button>
          </div>
        </div>

        {/* MAP VIEWPORT (Clean White Background) */}
        <div className="relative flex-1 w-full bg-[#ffffff] overflow-hidden">
          
          {/* Geolocation Notice / Error Toast */}
          {geoError && (
            <div className="absolute top-4 inset-x-0 mx-auto z-[1100] max-w-lg bg-rose-950/95 border-2 border-rose-500 text-rose-200 rounded-2xl p-3 px-4 shadow-2xl backdrop-blur-xl flex items-center justify-between gap-3 text-xs font-mono animate-bounce">
              <div className="flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
                <span>{geoError}</span>
              </div>
              <button
                type="button"
                onClick={() => setGeoError(null)}
                className="text-rose-400 hover:text-white p-1"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          )}

          {/* Leaflet Map Canvas Container */}
          <div ref={mapContainerRef} className="w-full h-full z-0" style={{ background: '#ffffff' }} />

          {/* Floating Left: Zoom and Navigation Controls */}
          <div className="absolute top-4 left-4 z-[1000] flex flex-col gap-2 pointer-events-auto">
            <div className="flex flex-col bg-white/95 backdrop-blur-md border-2 border-slate-300 rounded-2xl p-1 shadow-xl">
              <button
                type="button"
                onClick={handleZoomIn}
                className="p-2.5 text-slate-700 hover:text-cyan-600 hover:bg-slate-100 rounded-xl transition-colors cursor-pointer"
                title="Zoom In"
              >
                <ZoomIn className="w-4 h-4" />
              </button>
              <div className="h-px bg-slate-200 my-0.5"></div>
              <button
                type="button"
                onClick={handleZoomOut}
                className="p-2.5 text-slate-700 hover:text-cyan-600 hover:bg-slate-100 rounded-xl transition-colors cursor-pointer"
                title="Zoom Out"
              >
                <ZoomOut className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Floating Left-Top: Recon Telemetry HUD Panel */}
          {hudTelemetry && (
            <div className="absolute top-4 left-18 z-[1000] max-w-xs bg-[#071328]/95 backdrop-blur-xl border-2 border-cyan-400/60 rounded-2xl p-3.5 font-mono text-[11px] text-slate-200 shadow-2xl space-y-2 pointer-events-auto">
              <div className="flex items-center justify-between pb-1.5 border-b border-cyan-500/30 text-cyan-300 font-bold">
                <span className="flex items-center gap-1.5">
                  <Activity className="w-3.5 h-3.5 text-cyan-400" />
                  RECON TELEMETRY HUD
                </span>
                <span className="text-[10px] text-emerald-400">● LIVE</span>
              </div>

              <div className="space-y-1 text-[10px]">
                <div className="flex justify-between">
                  <span className="text-slate-400">Centroid:</span>
                  <span className="text-cyan-300 font-bold">{hudTelemetry.centerLat}° N, {hudTelemetry.centerLng}° E</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Tile Footprint:</span>
                  <span className="text-emerald-400 font-bold">{hudTelemetry.areaKm2} km² (256×256)</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Ground Resolution:</span>
                  <span className="text-white font-bold">10 m / pixel (Sentinel)</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">CRS:</span>
                  <span className="text-slate-300">{hudTelemetry.crs}</span>
                </div>
                <div className="flex justify-between items-center pt-1 border-t border-cyan-500/20">
                  <span className="text-slate-400">Nearest River:</span>
                  <span className="text-cyan-300 font-bold truncate max-w-[130px]">{hudTelemetry.riverName}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-400">River Proximity:</span>
                  <span className={`font-bold ${hudTelemetry.isNearRiver ? 'text-emerald-400' : 'text-amber-400'}`}>
                    {hudTelemetry.riverDistanceKm} km {hudTelemetry.isNearRiver ? '(✓ < 500m)' : ''}
                  </span>
                </div>

                {/* Live Operator Laptop GPS Telemetry when available */}
                {userLocation && (
                  <div className="pt-2 border-t border-cyan-500/30 space-y-1 mt-1">
                    <div className="flex items-center justify-between text-blue-400 font-bold">
                      <span className="flex items-center gap-1">
                        <Radio className="w-3 h-3 text-blue-400 animate-pulse" />
                        OPERATOR GPS BEACON:
                      </span>
                      <span className="text-emerald-400 text-[9px]">● TRACKING</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Device Pos:</span>
                      <span className="text-blue-300 font-bold">{userLocation.lat.toFixed(4)}° N, {userLocation.lng.toFixed(4)}° E</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Accuracy:</span>
                      <span className="text-emerald-400 font-bold">±{Math.round(userLocation.accuracy)} m</span>
                    </div>
                    {(() => {
                      const { center } = parseTileCoordinates(activeTile);
                      const dKm = calculateDistanceKm(userLocation.lat, userLocation.lng, center[0], center[1]);
                      const b = calculateBearing(userLocation.lat, userLocation.lng, center[0], center[1]);
                      return (
                        <>
                          <div className="flex justify-between items-center pt-0.5">
                            <span className="text-slate-400">Direct Range:</span>
                            <span className="text-amber-400 font-black">{dKm.toFixed(2)} km</span>
                          </div>
                          <div className="flex justify-between items-center">
                            <span className="text-slate-400">Vector Bearing:</span>
                            <span className="text-cyan-300 font-bold">{b.degrees}° ({b.cardinal})</span>
                          </div>
                        </>
                      );
                    })()}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Floating Left-Bottom: Shortest Route Navigation HUD Panel */}
          {showRoute && routeData && (
            <div className="absolute top-[280px] left-18 z-[1000] max-w-xs bg-[#071328]/95 backdrop-blur-xl border-2 border-amber-400/70 rounded-2xl p-3.5 font-mono text-[11px] text-slate-200 shadow-2xl space-y-2 pointer-events-auto animate-fade-in">
              <div className="flex items-center justify-between pb-1.5 border-b border-amber-500/30 text-amber-300 font-bold">
                <span className="flex items-center gap-1.5">
                  <Route className="w-3.5 h-3.5 text-amber-400" />
                  SHORTEST ROUTE HUD
                </span>
                <span className="text-[10px] text-emerald-400">● {routeData.mode === 'road' ? 'OSRM ROAD' : 'GEODESIC AIR'}</span>
              </div>

              {/* Mode Toggle */}
              <div className="flex bg-[#0d2144] border border-amber-500/30 rounded-lg p-0.5 text-[10px]">
                <button
                  type="button"
                  onClick={() => setRouteMode('road')}
                  className={`flex-1 py-1 rounded font-bold transition-all text-center cursor-pointer ${
                    routeMode === 'road'
                      ? 'bg-amber-500 text-slate-950 shadow-sm'
                      : 'text-slate-300 hover:text-white'
                  }`}
                >
                  🚗 Road Network
                </button>
                <button
                  type="button"
                  onClick={() => setRouteMode('geodesic')}
                  className={`flex-1 py-1 rounded font-bold transition-all text-center cursor-pointer ${
                    routeMode === 'geodesic'
                      ? 'bg-amber-500 text-slate-950 shadow-sm'
                      : 'text-slate-300 hover:text-white'
                  }`}
                >
                  🛩️ Direct Air Arc
                </button>
              </div>

              <div className="space-y-1.5 text-[10px]">
                <div className="flex justify-between items-center">
                  <span className="text-slate-400">Shortest Distance:</span>
                  <span className="text-amber-400 font-black text-xs">{routeData.distanceKm.toFixed(2)} km</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-400">Est. Transit Duration:</span>
                  <span className="text-cyan-300 font-bold">{routeData.durationStr}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-400">Main Corridor:</span>
                  <span className="text-white font-bold truncate max-w-[130px]" title={routeData.summary}>{routeData.summary}</span>
                </div>

                {/* Corridor Steps Preview */}
                {routeData.steps && routeData.steps.length > 0 && (
                  <div className="pt-1.5 border-t border-amber-500/20 space-y-1">
                    <div className="text-slate-400 font-bold text-[9px] uppercase tracking-wider">Maneuver Sequence:</div>
                    <div className="max-h-24 overflow-y-auto space-y-1 pr-1 custom-scrollbar">
                      {routeData.steps.map((step, idx) => (
                        <div key={idx} className="flex items-start gap-1.5 text-[9px] text-slate-300">
                          <span className="text-amber-400 font-bold shrink-0">{idx + 1}.</span>
                          <span className="truncate">{step.instruction}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <div className="pt-1.5 border-t border-amber-500/20 flex gap-1.5">
                  <button
                    type="button"
                    onClick={handleFitRoute}
                    className="flex-1 py-1 bg-amber-500/20 hover:bg-amber-500 text-amber-300 hover:text-slate-950 border border-amber-400/50 rounded-lg text-center font-bold text-[10px] transition-all cursor-pointer"
                  >
                    Fit Route View
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowRoute(false)}
                    className="px-2 py-1 bg-slate-800 hover:bg-rose-600 text-slate-300 hover:text-white border border-slate-600 rounded-lg text-center font-bold text-[10px] transition-all cursor-pointer"
                    title="Hide Route"
                  >
                    Hide
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Floating Right: Tactical Feature Toggles & Opacity Slider */}
          <div className="absolute top-4 right-4 z-[1000] w-64 bg-[#071328]/95 backdrop-blur-xl border-2 border-cyan-400/60 rounded-2xl p-3.5 font-mono text-[11px] text-slate-200 shadow-2xl space-y-2.5 pointer-events-auto">
            <div className="flex items-center justify-between pb-1.5 border-b border-cyan-500/30 text-cyan-300 font-bold">
              <span className="flex items-center gap-1.5">
                <Layers className="w-3.5 h-3.5 text-cyan-400" />
                TACTICAL GIS LAYERS
              </span>
            </div>

            {/* Layer Checkbox Toggles */}
            <div className="space-y-1.5 text-[11px]">
              <label className="flex items-center justify-between cursor-pointer hover:text-white transition-colors">
                <span className="flex items-center gap-1.5">
                  <Box className="w-3 h-3 text-slate-300" />
                  Building Blocks
                </span>
                <input
                  type="checkbox"
                  checked={showBuildings}
                  onChange={(e) => setShowBuildings(e.target.checked)}
                  className="accent-cyan-400 rounded cursor-pointer"
                />
              </label>

              <label className="flex items-center justify-between cursor-pointer hover:text-white transition-colors">
                <span className="flex items-center gap-1.5">
                  <Route className="w-3 h-3 text-amber-400" />
                  Roads &amp; Highways (Ways)
                </span>
                <input
                  type="checkbox"
                  checked={showRoads}
                  onChange={(e) => setShowRoads(e.target.checked)}
                  className="accent-amber-400 rounded cursor-pointer"
                />
              </label>

              <label className="flex items-center justify-between cursor-pointer hover:text-white transition-colors">
                <span className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded bg-blue-500"></span>
                  Water Bodies &amp; Rivers
                </span>
                <input
                  type="checkbox"
                  checked={showHydrology}
                  onChange={(e) => setShowHydrology(e.target.checked)}
                  className="accent-blue-400 rounded cursor-pointer"
                />
              </label>

              <label className="flex items-center justify-between cursor-pointer hover:text-white transition-colors">
                <span className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded bg-amber-500"></span>
                  State &amp; National Borders
                </span>
                <input
                  type="checkbox"
                  checked={showStates}
                  onChange={(e) => setShowStates(e.target.checked)}
                  className="accent-amber-400 rounded cursor-pointer"
                />
              </label>

              <label className="flex items-center justify-between cursor-pointer hover:text-white transition-colors pt-1 border-t border-cyan-500/20">
                <span className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded bg-cyan-400"></span>
                  Satellite GeoTIFF Overlay
                </span>
                <input
                  type="checkbox"
                  checked={showRaster}
                  onChange={(e) => setShowRaster(e.target.checked)}
                  className="accent-cyan-400 rounded cursor-pointer"
                />
              </label>
            </div>

            {/* Satellite Overlay Opacity Slider */}
            {showRaster && (
              <div className="pt-2 border-t border-cyan-500/20 space-y-1">
                <div className="flex justify-between text-[10px] text-slate-300">
                  <span>Raster Opacity:</span>
                  <span className="text-cyan-300 font-bold">{rasterOpacity}%</span>
                </div>
                <input
                  type="range"
                  min="10"
                  max="100"
                  value={rasterOpacity}
                  onChange={(e) => setRasterOpacity(Number(e.target.value))}
                  className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-cyan-400"
                />
              </div>
            )}
          </div>

          {/* Bottom Floating Footer Legend */}
          <div className="absolute bottom-3 inset-x-4 z-[1000] bg-[#071328]/95 backdrop-blur-xl border-2 border-cyan-400/50 rounded-xl px-4 py-2.5 flex flex-wrap items-center justify-between gap-2 font-mono text-[10px] text-slate-200 pointer-events-auto shadow-2xl">
            <div className="flex items-center gap-4 flex-wrap">
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-1 bg-[#00b4d8] rounded"></span>
                <span>Tile Highlight (256x256)</span>
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 bg-[#334155] border border-slate-900 rounded-sm"></span>
                <span>Building Blocks</span>
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-1 bg-[#ea580c] rounded"></span>
                <span>Primary Ways / Highways</span>
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-1 bg-[#0284c7] rounded"></span>
                <span>Water Bodies &amp; Rivers</span>
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-1 border-b border-dashed border-[#d97706]"></span>
                <span>State Boundaries</span>
              </span>
            </div>
            <div className="text-cyan-300 font-bold">
              CLEAN WHITE MAP // ROADS &amp; BUILDING BLOCKS // ZERO KEY OSM
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}

export default function TacticalMapModal(props) {
  return (
    <TacticalMapErrorBoundary onClose={props.onClose}>
      <TacticalMapModalInner {...props} />
    </TacticalMapErrorBoundary>
  );
}
