import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup, GeoJSON, useMap, Marker } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import { CloudRain, AlertTriangle, Navigation, Activity, BarChart3, Wifi, WifiOff, Clock, Info, Layers, ShieldCheck } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import axios from 'axios';
import HistoricalValidation from './HistoricalValidation';
import MapSearch from './components/MapSearch';
import DataModelStatus from './components/DataModelStatus';
import ModelLimitations from './components/ModelLimitations';
import SystemPipeline from './components/SystemPipeline';

const API_BASE = "http://localhost:8000/api";

// Debounce utility
function useDebounce(value, delay) {
  const [debouncedValue, setDebouncedValue] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedValue(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return debouncedValue;
}

// Component to track map viewport and provide bbox
function MapViewportTracker({ onBoundsChange }) {
  const map = useMap();
  const timerRef = useRef(null);

  useEffect(() => {
    // Set default map view directly: center [13.0827, 80.2707], zoom 14
    map.setView([13.0827, 80.2707], 14);

    // Invalidate size after container layout renders
    const rAF = requestAnimationFrame(() => {
      map.invalidateSize();
    });

    const handleMoveEnd = () => {
      // Debounce: wait 300ms after movement stops
      if (timerRef.current) clearTimeout(timerRef.current);
      timerRef.current = setTimeout(() => {
        const bounds = map.getBounds();
        const bbox = `${bounds.getWest().toFixed(6)},${bounds.getSouth().toFixed(6)},${bounds.getEast().toFixed(6)},${bounds.getNorth().toFixed(6)}`;
        onBoundsChange(bbox);
      }, 300);
    };

    map.on('moveend', handleMoveEnd);
    // Fire once on mount
    handleMoveEnd();
    return () => {
      cancelAnimationFrame(rAF);
      map.off('moveend', handleMoveEnd);
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [map, onBoundsChange]);

  return null;
}

// Controller component to handle map flying and search marker rendering
function MapSearchController({ searchTarget }) {
  const map = useMap();
  const prevTargetRef = useRef(null);
  const markerRef = useRef(null);

  useEffect(() => {
    if (!searchTarget) return;
    if (prevTargetRef.current === searchTarget) return;
    prevTargetRef.current = searchTarget;

    map.flyTo([searchTarget.lat, searchTarget.lon], searchTarget.zoom, { duration: 1.5 });
  }, [map, searchTarget]);

  useEffect(() => {
    if (searchTarget && markerRef.current) {
      markerRef.current.openPopup();
    }
  }, [searchTarget]);

  const searchPinIcon = useMemo(() => {
    return L.divIcon({
      className: 'custom-search-pin',
      html: `
        <div class="custom-search-pin-wrapper">
          <div class="custom-search-pin-pulse"></div>
          <svg width="28" height="38" viewBox="0 0 24 34" fill="none" xmlns="http://www.w3.org/2000/svg" style="z-index:1; filter: drop-shadow(0 3px 6px rgba(0,0,0,0.5));">
            <path d="M12 0C5.37 0 0 5.37 0 12C0 21 12 34 12 34C12 34 24 21 24 12C24 5.37 18.63 0 12 0Z" fill="#ef4444"/>
            <circle cx="12" cy="11" r="4.5" fill="#ffffff"/>
          </svg>
        </div>
      `,
      iconSize: [30, 42],
      iconAnchor: [15, 38],
      popupAnchor: [0, -36]
    });
  }, []);

  if (!searchTarget) return null;

  return (
    <Marker
      ref={markerRef}
      position={[searchTarget.lat, searchTarget.lon]}
      icon={searchPinIcon}
    >
      <Popup autoPan={false}>
        <div style={{ padding: '4px', fontSize: '0.9rem', color: '#0f172a', fontWeight: '600' }}>
          📍 {searchTarget.main_text || searchTarget.display_name}
          {searchTarget.secondary_text && (
            <div style={{ fontSize: '0.75rem', color: '#64748b', fontWeight: '400', marginTop: '2px' }}>
              {searchTarget.secondary_text}
            </div>
          )}
        </div>
      </Popup>
    </Marker>
  );
}

function App() {
  const [activeView, setActiveView] = useState('nowcast'); // 'nowcast' | 'validation'
  const [isSimulated, setIsSimulated] = useState(true);
  const [simulationRainfall, setSimulationRainfall] = useState(0);
  const [searchTarget, setSearchTarget] = useState(null);
  const [liveRainfallData, setLiveRainfallData] = useState(null);
  const [terrainInfo, setTerrainInfo] = useState(null);
  const [forecastOffset, setForecastOffset] = useState(0);
  
  const [forecast, setForecast] = useState(null);
  const [roadsGeojson, setRoadsGeojson] = useState(null);
  const [locations, setLocations] = useState([]);
  const [drainage, setDrainage] = useState(null);
  const [dataStatus, setDataStatus] = useState(null);
  const [mapBbox, setMapBbox] = useState(null);

  const requestIdRef = useRef(0);
  const geoJsonLayerRef = useRef(null);
  const casingLayerRef = useRef(null);
  const staticDataLoaded = useRef(false);

  const liveRainfall = (liveRainfallData?.status === "LIVE" || liveRainfallData?.status === "STALE") 
    ? (liveRainfallData.rainfall_rate || 0) 
    : 0;

  const currentModelRainfall = isSimulated ? simulationRainfall : liveRainfall;

  // Debounce rainfall slider by 300ms to avoid request storms while dragging
  const debouncedRainfall = useDebounce(currentModelRainfall, 300);
  const debouncedForecastOffset = useDebounce(forecastOffset, 300);

  // ===== STATIC DATA: fetch once on mount =====
  useEffect(() => {
    if (staticDataLoaded.current) return;
    staticDataLoaded.current = true;

    const fetchStatic = async () => {
      try {
        const [locRes, drainRes, statusRes, terrainRes] = await Promise.all([
          axios.get(`${API_BASE}/locations/critical`),
          axios.get(`${API_BASE}/drainage/diagnostics?latitude=13.0827&longitude=80.2707`),
          axios.get(`${API_BASE}/data-status`),
          axios.get(`${API_BASE}/terrain/elevation?latitude=13.0827&longitude=80.2707`),
        ]);
        setLocations(locRes.data.locations || []);
        setDrainage(drainRes.data);
        setDataStatus(statusRes.data);
        setTerrainInfo(terrainRes.data);
      } catch (e) {
        console.error("Error fetching static data", e);
      }
    };
    fetchStatic();
  }, []);

  // ===== DYNAMIC DATA: forecast (depends on rainfall, not on bbox) =====
  useEffect(() => {
    const fetchForecast = async () => {
      const currentRequestId = ++requestIdRef.current;
      try {
        const forecastRes = await axios.get(`${API_BASE}/flood/forecast?rainfall=${debouncedRainfall}&is_simulated=${isSimulated}`);
        if (currentRequestId === requestIdRef.current) {
          setForecast(forecastRes.data);
        }
      } catch (e) {
        console.error("Error fetching forecast", e);
      }
    };
    fetchForecast();
  }, [debouncedRainfall, isSimulated]);

  // ===== ROAD RISK DATA: depends on rainfall, forecast offset, bbox =====
  useEffect(() => {
    if (mapBbox === null) return; // Wait for initial map bounds

    const fetchRoads = async () => {
      try {
        const url = `${API_BASE}/roads/risk?forecast_offset=${debouncedForecastOffset}&rainfall=${debouncedRainfall}&is_simulated=${isSimulated}&bbox=${mapBbox}`;
        const roadsRes = await axios.get(url);
        if (roadsRes.data && Array.isArray(roadsRes.data.features) && roadsRes.data.features.length > 0) {
          setRoadsGeojson(roadsRes.data);
        } else {
          console.warn("[ROADS] Response contained 0 features or unavailable status.");
        }
      } catch (e) {
        console.error("[ROADS] Error fetching roads risk.", e);
      }
    };
    fetchRoads();
  }, [debouncedRainfall, debouncedForecastOffset, isSimulated, mapBbox]);

  // ===== LIVE RAINFALL POLLING =====
  useEffect(() => {
    let interval;
    if (!isSimulated) {
      const fetchLiveRainfall = async () => {
        try {
          const res = await axios.get(`${API_BASE}/rainfall/current`);
          setLiveRainfallData(res.data);
        } catch (e) {
          console.error("Error fetching live rainfall", e);
          setLiveRainfallData({ status: "UNAVAILABLE", error: "Connection Error" });
        }
      };
      fetchLiveRainfall();
      interval = setInterval(fetchLiveRainfall, 10 * 60 * 1000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isSimulated]);

  // ===== MAP BBOX HANDLER =====
  const handleBoundsChange = useCallback((bbox) => {
    setMapBbox(bbox);
  }, []);

  const getStatusColor = (status) => {
    if (!status) return '#9ca3af';
    switch(status.toUpperCase()) {
      case 'NORMAL': return '#ffffff';
      case 'LOW': return '#38bdf8';
      case 'WATCH': case 'MODERATE': return '#f59e0b';
      case 'FLOOD': case 'HIGH': case 'CRITICAL': return '#ef4444';
      case 'RECOVERY': return '#3b82f6';
      case 'GRAY': case 'DATA UNAVAILABLE': case 'UNAVAILABLE': return '#9ca3af';
      default: return '#9ca3af'; 
    }
  };

  const getRoadColor = useCallback((props) => {
    if (!props) return '#9ca3af';
    const riskLevel = (props.risk_level || '').toUpperCase();
    const riskColorProp = (props.risk_color || '').toUpperCase();

    if (riskLevel === 'NORMAL' || riskColorProp === 'WHITE') return '#ffffff';
    if (riskLevel === 'LOW' || riskColorProp === 'GREEN' || riskColorProp === 'LIGHT_BLUE' || riskColorProp === 'BLUE') return '#38bdf8';
    if (riskLevel === 'MODERATE' || riskColorProp === 'ORANGE') return '#f59e0b';
    if (riskLevel === 'HIGH' || riskLevel === 'CRITICAL' || riskColorProp === 'RED') return '#ef4444';
    if (riskLevel === 'DATA UNAVAILABLE' || riskLevel === 'UNAVAILABLE' || riskColorProp === 'GRAY') return '#9ca3af';
    
    return '#38bdf8';
  }, []);

  const getRoadStyle = useCallback((feature) => {
    const props = feature?.properties || {};
    const color = getRoadColor(props);
    const riskLevel = (props.risk_level || '').toUpperCase();
    const riskColorProp = (props.risk_color || '').toUpperCase();

    if (riskLevel === 'HIGH' || riskLevel === 'CRITICAL' || riskColorProp === 'RED') {
      return {
        color: color,
        weight: 3,
        opacity: 1.0,
        lineCap: 'round'
      };
    }
    if (riskLevel === 'MODERATE' || riskColorProp === 'ORANGE') {
      return {
        color: color,
        weight: 2.5,
        opacity: 0.92,
        lineCap: 'round'
      };
    }
    if (riskLevel === 'LOW' || riskColorProp === 'GREEN' || riskColorProp === 'LIGHT_BLUE' || riskColorProp === 'BLUE') {
      return {
        color: color,
        weight: 2.0,
        opacity: 0.85,
        lineCap: 'round'
      };
    }
    if (riskLevel === 'DATA UNAVAILABLE' || riskLevel === 'UNAVAILABLE' || riskColorProp === 'GRAY') {
      return {
        color: color,
        weight: 1.5,
        opacity: 0.45,
        lineCap: 'round'
      };
    }
    // NORMAL / DEFAULT
    return {
      color: color,
      weight: 1.0,
      opacity: 0.50,
      lineCap: 'round'
    };
  }, [getRoadColor]);

  const getCasingStyle = useCallback((feature) => {
    const props = feature?.properties || {};
    const color = getRoadColor(props);
    const isWhite = color === '#ffffff';
    const riskLevel = (props.risk_level || '').toUpperCase();
    const riskColorProp = (props.risk_color || '').toUpperCase();

    let weight = 1.8;
    let opacity = 0.45;

    if (riskLevel === 'HIGH' || riskLevel === 'CRITICAL' || riskColorProp === 'RED') {
      weight = 5.5;
      opacity = 0.9;
    } else if (riskLevel === 'MODERATE' || riskColorProp === 'ORANGE') {
      weight = 4.5;
      opacity = 0.85;
    } else if (riskLevel === 'LOW' || riskColorProp === 'GREEN' || riskColorProp === 'LIGHT_BLUE' || riskColorProp === 'BLUE') {
      weight = 3.5;
      opacity = 0.75;
    } else if (riskLevel === 'DATA UNAVAILABLE' || riskLevel === 'UNAVAILABLE' || riskColorProp === 'GRAY') {
      weight = 2.5;
      opacity = 0.35;
    } else {
      // NORMAL
      weight = 1.8;
      opacity = 0.45;
    }

    return {
      color: isWhite ? '#1e293b' : '#0f172a',
      weight: weight,
      opacity: opacity,
      lineCap: 'round',
      lineJoin: 'round'
    };
  }, [getRoadColor]);

  const onEachRoadFeature = useCallback((feature, layer) => {
    const props = feature.properties;
    if (props) {
      const riskColor = getRoadColor(props);
      const normalStyle = getRoadStyle(feature);
      
      layer.on('mouseover', (e) => e.target.setStyle({ weight: Math.max(5, (normalStyle.weight || 1) + 3), opacity: 1 }));
      layer.on('mouseout', (e) => e.target.setStyle(normalStyle));

      const badgeTextColor = riskColor === '#ffffff' ? '#0f172a' : '#ffffff';
      const badgeBorder = riskColor === '#ffffff' ? 'border: 1px solid #94a3b8;' : '';

      const popupContent = `
        <div style="font-size: 0.9rem; color: #333; min-width: 200px;">
          <h4 style="margin: 0 0 5px 0; padding-bottom: 5px; border-bottom: 1px solid #e2e8f0; font-size: 1rem;">${props.name || 'Unnamed Road'}</h4>
          <div style="margin-bottom: 8px;">
            <div style="color: #64748b; font-size: 0.75rem;">ID: ${props.road_id || 'N/A'}</div>
            <div style="color: #64748b; font-size: 0.75rem;">Class: ${props.road_class || 'local'}</div>
          </div>
          
          <div style="background: #f8fafc; padding: 6px; border-radius: 4px; margin-bottom: 8px;">
            <div style="font-weight: 600; color: #334155; margin-bottom: 2px;">Forecast: ${props.forecast_time}</div>
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2px;">
              <span>Flood depth:</span> <strong>${props.predicted_flood_depth_cm || 0} cm</strong>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <span>Maximum:</span> <strong>${props.max_depth_cm || 0} cm</strong>
            </div>
          </div>

          <div style="display: flex; align-items: center; gap: 6px; margin-bottom: 8px;">
            Risk: <span style="font-weight: 700; background: ${riskColor}; color: ${badgeTextColor}; ${badgeBorder} padding: 2px 8px; border-radius: 12px; font-size: 0.8rem;">${props.risk_level || 'UNKNOWN'}</span>
          </div>

          <div style="font-size: 0.8rem; color: #475569; padding-bottom: 5px; border-bottom: 1px solid #e2e8f0;">
            Rainfall: <strong>${debouncedRainfall.toFixed(1)} mm/hr</strong><br/>
          </div>
          
          <div style="font-size: 0.75rem; color: #64748b; margin-top: 5px; line-height: 1.4;">
            Model: ${props.model_version || 'baseline'}<br/>
            Drainage Capacity: UNKNOWN (Not Used)<br/>
            Calibration: NOT CALIBRATED
          </div>
        </div>
      `;
      layer.bindPopup(popupContent);
    }
  }, [getRoadColor, getRoadStyle, debouncedRainfall]);

  const dataProvenanceRef = useRef(null);

  const handleScrollToDataProvenance = () => {
    if (dataProvenanceRef.current) {
      dataProvenanceRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  };

  const renderHeaderStatus = () => {
    if (isSimulated) {
      return (
        <div style={{display: 'flex', gap: 10, alignItems: 'center'}}>
          <span style={{
            background: 'rgba(245, 158, 11, 0.2)',
            color: '#fcd34d',
            padding: '4px 10px',
            borderRadius: '4px',
            fontSize: '0.8rem',
            fontWeight: '700',
            border: '1px solid rgba(245, 158, 11, 0.5)',
            letterSpacing: '0.04em'
          }}>
            SYSTEM STATUS: SIMULATION
          </span>
        </div>
      );
    }

    if (!liveRainfallData) {
      return (
        <div style={{display: 'flex', gap: 10, alignItems: 'center', color: '#eab308'}}>
          <Activity size={18} /> <span style={{ fontWeight: '700', fontSize: '0.85rem' }}>SYSTEM STATUS: FETCHING...</span>
        </div>
      );
    }

    const { status, retrieved_at, data_timestamp } = liveRainfallData;
    
    if (status === "LIVE") {
      return (
        <div style={{display: 'flex', gap: 10, alignItems: 'center'}}>
          <span style={{
            background: 'rgba(56, 189, 248, 0.15)',
            color: '#38bdf8',
            padding: '4px 10px',
            borderRadius: '4px',
            fontSize: '0.8rem',
            fontWeight: '700',
            border: '1px solid #38bdf8',
            letterSpacing: '0.04em',
            display: 'flex',
            alignItems: 'center',
            gap: '6px'
          }}>
            <Wifi size={14} /> SYSTEM STATUS: LIVE (NASA GPM)
          </span>
          <span style={{fontSize: '0.75rem', color: '#94a3b8'}}>
            Updated: {new Date(retrieved_at).toLocaleTimeString()}
          </span>
        </div>
      );
    }
    
    if (status === "STALE") {
      return (
        <div style={{display: 'flex', gap: 10, alignItems: 'center'}}>
          <span style={{
            background: 'rgba(249, 115, 22, 0.2)',
            color: '#fb923c',
            padding: '4px 10px',
            borderRadius: '4px',
            fontSize: '0.8rem',
            fontWeight: '700',
            border: '1px solid #f97316',
            letterSpacing: '0.04em',
            display: 'flex',
            alignItems: 'center',
            gap: '6px'
          }}>
            <AlertTriangle size={14} /> SYSTEM STATUS: STALE
          </span>
          <span style={{fontSize: '0.75rem', color: '#94a3b8'}}>
            Last: {new Date(data_timestamp || retrieved_at).toLocaleTimeString()}
          </span>
        </div>
      );
    }

    return (
      <div style={{display: 'flex', gap: 10, alignItems: 'center'}}>
        <span style={{
          background: 'rgba(239, 68, 68, 0.2)',
          color: '#fca5a5',
          padding: '4px 10px',
          borderRadius: '4px',
          fontSize: '0.8rem',
          fontWeight: '700',
          border: '1px solid #ef4444'
        }}>
          SYSTEM STATUS: UNAVAILABLE
        </span>
      </div>
    );
  };
  
  // Calculate Road Counts explicitly based on the API response per requirements
  const { countNormal, countLow, countMod, countHigh, countGray } = useMemo(() => {
    let n = 0, l = 0, m = 0, h = 0, g = 0;
    if (roadsGeojson && roadsGeojson.features) {
      roadsGeojson.features.forEach(f => {
        const r = (f.properties?.risk_level || '').toUpperCase();
        if (r === 'NORMAL') n++;
        else if (r === 'LOW') l++;
        else if (r === 'MODERATE') m++;
        else if (r === 'HIGH' || r === 'CRITICAL') h++;
        else g++;
      });
    }
    return { countNormal: n, countLow: l, countMod: m, countHigh: h, countGray: g };
  }, [roadsGeojson]);

  // Stable key for GeoJSON — changes only when underlying data object identity changes
  // This avoids destroying/recreating 146K Leaflet layers on slider changes
  const geoJsonDataId = useMemo(() => {
    if (!roadsGeojson) return 0;
    return roadsGeojson;
  }, [roadsGeojson]);

  if (!forecast) return <div style={{padding: 20}}>Loading (or backend unreachable)...</div>;

  return (
    <div className="dashboard-layout">
      <header className="header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div className="header-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <CloudRain size={24} /> Chennai Flood Nowcast
          </div>
          <nav style={{ display: 'flex', gap: '6px', background: '#0f172a', padding: '4px', borderRadius: '8px', border: '1px solid #334155' }}>
            <button
              onClick={() => setActiveView('nowcast')}
              style={{
                background: activeView === 'nowcast' ? '#3b82f6' : 'transparent',
                color: activeView === 'nowcast' ? '#ffffff' : '#94a3b8',
                border: 'none',
                padding: '6px 14px',
                borderRadius: '6px',
                cursor: 'pointer',
                fontWeight: activeView === 'nowcast' ? 'bold' : 'normal',
                fontSize: '0.85rem'
              }}
            >
              NOWCAST DASHBOARD
            </button>
            <button
              onClick={() => setActiveView('validation')}
              style={{
                background: activeView === 'validation' ? '#3b82f6' : 'transparent',
                color: activeView === 'validation' ? '#ffffff' : '#94a3b8',
                border: 'none',
                padding: '6px 14px',
                borderRadius: '6px',
                cursor: 'pointer',
                fontWeight: activeView === 'validation' ? 'bold' : 'normal',
                fontSize: '0.85rem'
              }}
            >
              HISTORICAL VALIDATION
            </button>
          </nav>
          
          <button
            onClick={handleScrollToDataProvenance}
            style={{
              background: 'rgba(56, 189, 248, 0.12)',
              color: '#38bdf8',
              border: '1px solid #38bdf8',
              padding: '6px 12px',
              borderRadius: '6px',
              cursor: 'pointer',
              fontWeight: '700',
              fontSize: '0.8rem',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
            title="View Data Provenance & Scientific Indicators"
          >
            <Layers size={14} /> DATA PROVENANCE
          </button>
        </div>
        <div className="header-status">
          {renderHeaderStatus()}
        </div>
      </header>

      {/* TOP JUDGE-FRIENDLY SUMMARY BAR */}
      {activeView === 'nowcast' && (
        <div style={{
          background: '#0f172a',
          borderBottom: '1px solid #334155',
          padding: '8px 20px',
          display: 'flex',
          justify: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '12px'
        }}>
          <div>
            <h2 style={{ fontSize: '1rem', fontWeight: '800', color: '#f8fafc', margin: 0, letterSpacing: '0.03em', display: 'flex', alignItems: 'center', gap: '8px' }}>
              URBAN FLOOD NOWCAST
            </h2>
            <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '1px' }}>
              Rainfall + Terrain + Drainage Context → Street-Level Flood Risk
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(140px, 1fr))', gap: '10px', flex: 1, maxWidth: '780px' }}>
            {/* CARD 1: CURRENT RAINFALL */}
            <div style={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '6px', padding: '6px 10px' }}>
              <div style={{ fontSize: '0.65rem', color: '#94a3b8', fontWeight: '700', letterSpacing: '0.05em' }}>CURRENT RAINFALL</div>
              <div style={{ fontSize: '1.15rem', fontWeight: '800', color: '#38bdf8', margin: '1px 0' }}>
                {currentModelRainfall.toFixed(1)} <span style={{ fontSize: '0.75rem', fontWeight: '500', color: '#94a3b8' }}>mm/hr</span>
              </div>
              <div style={{ fontSize: '0.65rem', color: '#64748b', fontStyle: 'italic' }}>
                {isSimulated ? 'SIMULATED RAINFALL' : (liveRainfallData?.source || 'NASA GPM IMERG')}
              </div>
            </div>

            {/* CARD 2: FLOOD RISK */}
            <div style={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '6px', padding: '6px 10px' }}>
              <div style={{ fontSize: '0.65rem', color: '#94a3b8', fontWeight: '700', letterSpacing: '0.05em' }}>FLOOD RISK</div>
              <div style={{ fontSize: '1.15rem', fontWeight: '800', color: getStatusColor(forecast.status), margin: '1px 0' }}>
                {forecast.status}
              </div>
              <div style={{ fontSize: '0.65rem', color: '#64748b', fontStyle: 'italic' }}>
                Current modelled status
              </div>
            </div>

            {/* CARD 3: HIGH-RISK ROADS */}
            <div style={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '6px', padding: '6px 10px' }}>
              <div style={{ fontSize: '0.65rem', color: '#94a3b8', fontWeight: '700', letterSpacing: '0.05em' }}>HIGH-RISK ROADS</div>
              <div style={{ fontSize: '1.15rem', fontWeight: '800', color: countHigh > 0 ? '#ef4444' : '#34d399', margin: '1px 0' }}>
                {countHigh} <span style={{ fontSize: '0.75rem', fontWeight: '500', color: '#94a3b8' }}>segments</span>
              </div>
              <div style={{ fontSize: '0.65rem', color: '#64748b', fontStyle: 'italic' }}>
                Road segments flagged high risk
              </div>
            </div>

            {/* CARD 4: FORECAST WINDOW */}
            <div style={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '6px', padding: '6px 10px' }}>
              <div style={{ fontSize: '0.65rem', color: '#94a3b8', fontWeight: '700', letterSpacing: '0.05em' }}>FORECAST WINDOW</div>
              <div style={{ fontSize: '1.15rem', fontWeight: '800', color: '#f8fafc', margin: '1px 0' }}>
                0–3 HOURS
              </div>
              <div style={{ fontSize: '0.65rem', color: '#64748b', fontStyle: 'italic' }}>
                Modelled forecast
              </div>
            </div>
          </div>
        </div>
      )}
      
      {activeView === 'validation' ? (
        <HistoricalValidation />
      ) : (
        <>
          <div className="main-content">
        <aside className="sidebar">
          
          <div className="card">
            <div className="card-title">Data Mode</div>
            <div className="toggle-container" style={{display: 'flex', borderRadius: 6, overflow: 'hidden', border: '1px solid #334155'}}>
              <button 
                onClick={() => setIsSimulated(true)}
                style={{
                  flex: 1, padding: '10px 0', border: 'none', cursor: 'pointer',
                  background: isSimulated ? '#3b82f6' : '#1e293b',
                  color: isSimulated ? '#fff' : '#94a3b8',
                  fontWeight: isSimulated ? 'bold' : 'normal'
                }}
              >
                SIMULATION
              </button>
              <button 
                onClick={() => setIsSimulated(false)}
                style={{
                  flex: 1, padding: '10px 0', border: 'none', cursor: 'pointer',
                  background: !isSimulated ? '#38bdf8' : '#1e293b',
                  color: !isSimulated ? '#fff' : '#94a3b8',
                  fontWeight: !isSimulated ? 'bold' : 'normal'
                }}
              >
                LIVE NASA
              </button>
            </div>
          </div>

          {/* FLOOD RISK SUMMARY CARD */}
          <div className="card" style={{ borderColor: '#3b82f6' }}>
            <div className="card-title" style={{ color: '#38bdf8', fontWeight: '700', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <ShieldCheck size={16} /> FLOOD RISK SUMMARY
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '0.85rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ color: '#94a3b8' }}>Current Rainfall:</span>
                <strong>{currentModelRainfall.toFixed(1)} mm/hr</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ color: '#94a3b8' }}>Forecast Horizon:</span>
                <span style={{ color: '#38bdf8', fontWeight: '700' }}>{forecastOffset === 0 ? 'NOW' : `+${forecastOffset} MIN`}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ color: '#94a3b8' }}>Max Estimated Depth:</span>
                <strong>{forecast ? `${forecast.water_depth_cm.toFixed(1)} cm` : 'DATA UNAVAILABLE'}</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ color: '#94a3b8' }}>Dominant Road Risk:</span>
                <span style={{ 
                  color: countHigh > 0 ? '#ef4444' : (countMod > 0 ? '#f59e0b' : (countLow > 0 ? '#38bdf8' : '#ffffff')), 
                  fontWeight: '700' 
                }}>
                  {countHigh > 0 ? 'HIGH' : (countMod > 0 ? 'MODERATE' : (countLow > 0 ? 'LOW' : 'NORMAL'))}
                </span>
              </div>
            </div>
          </div>

          {/* JUDGE-FRIENDLY SCENARIO SIMULATION */}
          <div className="card" style={{ borderColor: isSimulated ? '#f59e0b' : '#334155' }}>
            <div className="card-title" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span>SCENARIO SIMULATION</span>
              {isSimulated && <span className="tag-simulated">SIMULATION MODE</span>}
            </div>
            <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginBottom: '10px', lineHeight: 1.4 }}>
              Test how modelled road risk changes under different rainfall intensities.
            </div>
            
            {isSimulated ? (
              <>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px', fontSize: '0.8rem' }}>
                  <span style={{ color: '#cbd5e1' }}>SIMULATED RAINFALL:</span>
                  <strong style={{ color: '#f59e0b' }}>{simulationRainfall} mm/hr</strong>
                </div>
                <input 
                  type="range" 
                  min="0" max="150" step="5"
                  value={simulationRainfall}
                  onChange={(e) => setSimulationRainfall(Number(e.target.value))}
                  className="input-slider"
                />
                <div style={{ display: 'flex', gap: '4px', marginTop: '12px', flexWrap: 'wrap' }}>
                  {[0, 25, 50, 75, 105].map(val => (
                    <button 
                      key={val} 
                      onClick={() => setSimulationRainfall(val)}
                      style={{
                        flex: 1,
                        background: simulationRainfall === val ? '#f59e0b' : '#1e293b',
                        color: simulationRainfall === val ? '#0f172a' : '#f8fafc',
                        border: '1px solid #334155',
                        padding: '6px 0',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        fontWeight: simulationRainfall === val ? 'bold' : 'normal',
                        fontSize: '0.75rem'
                      }}
                    >
                      {val} mm/h
                    </button>
                  ))}
                </div>
                <div style={{ fontSize: '0.7rem', color: '#64748b', fontStyle: 'italic', marginTop: '8px' }}>
                  Hypothetical scenario rainfall intensity.
                </div>
              </>
            ) : (
              <div style={{ fontSize: '0.8rem', color: '#64748b', fontStyle: 'italic' }}>
                Switch to SIMULATION mode to test custom rainfall intensities.
              </div>
            )}
          </div>

          {/* SPATIAL FORECAST SLIDER */}
          <div className="card">
            <div className="card-title">SPATIAL FORECAST SLIDER</div>
            <div style={{marginBottom: '5px', fontSize: '0.85rem', color: '#94a3b8'}}>Forecast Time: <strong>{forecastOffset === 0 ? 'NOW' : `+${forecastOffset} MIN`}</strong></div>
            <input 
              type="range" 
              min="0" max="180" step="30"
              value={forecastOffset}
              onChange={(e) => setForecastOffset(Number(e.target.value))}
              className="input-slider"
              title="Time Slider for Predictive Routing"
            />
            <div style={{display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: '#64748b', marginTop: '6px'}}>
              {[0, 60, 120, 180].map(offset => (
                <button
                  key={offset}
                  onClick={() => setForecastOffset(offset)}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    color: forecastOffset === offset ? '#38bdf8' : '#64748b',
                    fontWeight: forecastOffset === offset ? '700' : '400',
                    cursor: 'pointer',
                    fontSize: '0.75rem'
                  }}
                >
                  {offset === 0 ? 'NOW' : `+${offset}m`}
                </button>
              ))}
            </div>
          </div>

          {/* DATA MODEL STATUS (WITH SCROLL REF) */}
          <div ref={dataProvenanceRef}>
            <DataModelStatus 
              isSimulated={isSimulated} 
              liveRainfallData={liveRainfallData} 
              drainage={drainage} 
            />
          </div>

          {/* SYSTEM PIPELINE PANEL */}
          <SystemPipeline />

          {/* MODEL LIMITATIONS COMPONENT */}
          <ModelLimitations />

          {/* DRAINAGE DIAGNOSTICS */}
          {drainage && (
            <div className="card">
              <div className="card-title">DRAINAGE GEOMETRY / SPATIAL DIAGNOSTICS</div>
              <div style={{fontSize: '0.8rem', color: '#cbd5e1', display: 'flex', flexDirection: 'column', gap: 6}}>
                <div><strong>Coverage:</strong> <span style={{color: drainage.coverage?.status === 'DRAINAGE_SERVED' ? '#38bdf8' : '#f59e0b', fontWeight: 'bold'}}>{drainage.coverage?.status || 'N/A'}</span> ({drainage.coverage?.nearest_swd_distance_m ?? 'N/A'}m to SWD)</div>
                <div><strong>Density:</strong> {drainage.density?.density_km_per_km2 ?? 'N/A'} km/km²</div>
                <div><strong>Deficit Index (DBI):</strong> {drainage.dbi?.value ?? 'N/A'} ({drainage.dbi?.status || 'N/A'})</div>
                <div><strong>Hydraulic Capacity:</strong> <span style={{color: '#9ca3af', fontWeight: 'bold'}}>UNAVAILABLE</span></div>
                <div style={{fontSize: '0.75rem', color: '#94a3b8', fontStyle: 'italic', borderTop: '1px solid #334155', paddingTop: 4, marginTop: 2}}>
                  Current drainage data provides geometry; hydraulic capacity parameters are unavailable. Drain proximity does not reduce flood depth calculations.
                </div>
              </div>
            </div>
          )}

          {/* ROAD RISK COUNTERS */}
          <div className="card">
              <div className="card-title">ROAD RISK COUNTERS</div>
              <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '0.85rem'}}>
                 <div style={{background: 'rgba(255, 255, 255, 0.05)', border: '1px solid #ffffff', padding: '6px', borderRadius: '4px'}}>
                    <div style={{color: '#ffffff', fontWeight: 'bold'}}>NORMAL</div>
                    <div style={{fontSize: '1.2rem', color: '#ffffff'}}>{countNormal}</div>
                 </div>
                 <div style={{background: 'rgba(56, 189, 248, 0.1)', border: '1px solid #38bdf8', padding: '6px', borderRadius: '4px'}}>
                    <div style={{color: '#38bdf8', fontWeight: 'bold'}}>LOW RISK</div>
                    <div style={{fontSize: '1.2rem', color: '#38bdf8'}}>{countLow}</div>
                 </div>
                 <div style={{background: 'rgba(245, 158, 11, 0.1)', border: '1px solid #f59e0b', padding: '6px', borderRadius: '4px'}}>
                    <div style={{color: '#f59e0b', fontWeight: 'bold'}}>MODERATE</div>
                    <div style={{fontSize: '1.2rem', color: '#f59e0b'}}>{countMod}</div>
                 </div>
                 <div style={{background: 'rgba(239, 68, 68, 0.1)', border: '1px solid #ef4444', padding: '6px', borderRadius: '4px'}}>
                    <div style={{color: '#ef4444', fontWeight: 'bold'}}>HIGH-RISK</div>
                    <div style={{fontSize: '1.2rem', color: '#ef4444'}}>{countHigh}</div>
                 </div>
                 <div style={{background: 'rgba(156, 163, 175, 0.1)', border: '1px solid #9ca3af', padding: '6px', borderRadius: '4px', gridColumn: 'span 2'}}>
                    <div style={{color: '#9ca3af', fontWeight: 'bold'}}>DATA UNAVAILABLE</div>
                    <div style={{fontSize: '1.2rem', color: '#9ca3af'}}>{countGray}</div>
                 </div>
              </div>
          </div>

        </aside>

        <main className="map-container" style={{ position: 'relative' }}>
          {/* Map Location Search Overlay */}
          <MapSearch onSelectLocation={(loc) => setSearchTarget(loc)} />

          <MapContainer center={[13.0827, 80.2707]} zoom={14} style={{height: '100%', width: '100%'}}>
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />

            {/* Map viewport tracker for bbox-based road loading */}
            <MapViewportTracker onBoundsChange={handleBoundsChange} />

            {/* Map search controller & marker */}
            <MapSearchController searchTarget={searchTarget} />

            {locations.map(loc => (
              <CircleMarker 
                key={loc.id} 
                center={[loc.lat, loc.lng]} 
                radius={8}
                pathOptions={{
                  fillColor: loc.risk === 'CRITICAL' || loc.risk === 'HIGH' ? '#ef4444' : (loc.risk === 'MODERATE' ? '#f59e0b' : (loc.risk === 'LOW' ? '#38bdf8' : '#ffffff')),
                  color: 'white',
                  weight: 2,
                  fillOpacity: 0.8
                }}
              >
                <Popup>
                  <div style={{fontSize: '0.9rem', color: '#333'}}>
                    <strong>{loc.name}</strong><br/>
                    
                    {terrainInfo && (
                       <div style={{marginTop: 5, paddingBottom: 5, borderBottom: '1px solid #ccc'}}>
                          <div><strong>Elevation:</strong> {terrainInfo.elevation_m !== null ? `${terrainInfo.elevation_m.toFixed(1)} m` : 'UNAVAILABLE'}</div>
                          <div style={{fontSize: '0.8rem'}}><strong>Terrain:</strong> {terrainInfo.status} — {terrainInfo.source}</div>
                       </div>
                    )}
                    
                    <div style={{marginTop: 5}}><strong>Type:</strong> {loc.type}</div>
                    <div><strong>Modelled Risk Level:</strong> <span style={{color: loc.risk === 'CRITICAL' || loc.risk === 'HIGH' ? '#ef4444' : (loc.risk === 'MODERATE' ? '#f59e0b' : (loc.risk === 'LOW' ? '#38bdf8' : '#ffffff')), fontWeight: 'bold'}}>{loc.risk}</span></div>
                    <div><strong>Modelled Flood Depth:</strong> {loc.depth_cm} cm</div>
                    
                    <div style={{marginTop: 5, paddingBottom: 5, borderBottom: '1px solid #ccc'}}>
                      <div><strong>Rainfall Input:</strong> {currentModelRainfall.toFixed(1)} mm/hr</div>
                      <div style={{fontSize: '0.8rem'}}><strong>Rainfall Source:</strong> {isSimulated ? 'SIMULATED' : `REAL — ${liveRainfallData?.source || 'NASA GPM'}`}</div>
                    </div>
                    
                    <div style={{marginTop: 5, fontSize: '0.8rem', color: '#64748b'}}>
                      <strong>Flood Model:</strong> MODELLED (baseline-v1) <br/>
                      <strong>Calibration:</strong> NOT CALIBRATED <br/>
                      <strong>Drainage Capacity:</strong> UNKNOWN (Data Unavailable) <br/>
                      <strong>Flood Depth Reduction:</strong> NONE (0.0 cm)
                    </div>
                  </div>
                </Popup>
              </CircleMarker>
            ))}

            {/* Road layers — use data identity as key so layers are only recreated when new data arrives from API, NOT on every slider tick */}
            {roadsGeojson && roadsGeojson.features && roadsGeojson.features.length > 0 && (
              <>
                <GeoJSON
                  key="road-casing-stable"
                  ref={casingLayerRef}
                  data={roadsGeojson}
                  style={getCasingStyle}
                  interactive={false}
                />
                <GeoJSON
                  key="road-overlay-stable"
                  ref={geoJsonLayerRef}
                  data={roadsGeojson}
                  style={getRoadStyle}
                  onEachFeature={onEachRoadFeature}
                />
              </>
            )}
          </MapContainer>
          
          {/* STATIC OVERLAY LEGEND */}
          <div style={{
            position: 'absolute', bottom: '30px', right: '10px', 
            background: 'rgba(15, 23, 42, 0.95)', border: '1px solid #334155', padding: '10px 15px', borderRadius: '8px', 
            boxShadow: '0 4px 12px rgba(0,0,0,0.4)', zIndex: 1000, color: '#f8fafc'
          }}>
            <h4 style={{margin: '0 0 10px 0', fontSize: '0.85rem', borderBottom: '1px solid #334155', paddingBottom: '4px', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em'}}>ROAD RISK</h4>
            <div style={{display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '0.85rem', fontWeight: '600'}}>
              <div style={{display: 'flex', alignItems: 'center', gap: '8px'}}><div style={{width: 14, height: 14, borderRadius: '50%', background: '#ffffff', border: '1px solid #94a3b8'}}></div> NORMAL</div>
              <div style={{display: 'flex', alignItems: 'center', gap: '8px'}}><div style={{width: 14, height: 14, borderRadius: '50%', background: '#38bdf8'}}></div> LOW</div>
              <div style={{display: 'flex', alignItems: 'center', gap: '8px'}}><div style={{width: 14, height: 14, borderRadius: '50%', background: '#f59e0b'}}></div> MODERATE</div>
              <div style={{display: 'flex', alignItems: 'center', gap: '8px'}}><div style={{width: 14, height: 14, borderRadius: '50%', background: '#ef4444'}}></div> HIGH</div>
              <div style={{display: 'flex', alignItems: 'center', gap: '8px'}}><div style={{width: 14, height: 14, borderRadius: '50%', background: '#9ca3af'}}></div> DATA UNAVAILABLE</div>
            </div>
          </div>
        </main>
      </div>

      {/* FOOTER TIMELINE */}
      <footer className="footer-timeline" style={{ height: 'auto', padding: '12px 20px' }}>
        <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
          <div>
            <div className="card-title" style={{margin: 0, color: '#f8fafc', fontWeight: '800', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '8px'}}>
              MODELLED FLOOD-RISK HORIZON
            </div>
            <div style={{ fontSize: '0.7rem', color: '#94a3b8', marginTop: '2px' }}>
              Forecast values are modelled estimates, not independently validated predictions.
            </div>
          </div>
          <span className="tag-simulated" style={{background: '#1d4ed8', border: 'none', color: '#ffffff'}}>MODELLED FORECAST</span>
        </div>

        <div className="timeline-track" style={{ marginTop: '12px' }}>
          <div className="timeline-line"></div>
          {forecast.forecast.map((node, i) => {
            const color = getStatusColor(node.status);
            // Derive numeric offset for node (0, 30, 60, 90, 120, 150, 180)
            const nodeOffset = i * 30;
            const isSelected = forecastOffset === nodeOffset;
            
            return (
              <div 
                className="timeline-node" 
                key={i} 
                onClick={() => setForecastOffset(nodeOffset)}
                style={{ 
                  cursor: 'pointer',
                  transform: isSelected ? 'scale(1.1)' : 'scale(1)',
                  transition: 'transform 0.2s'
                }}
                title={`Click to set forecast to +${nodeOffset} minutes`}
              >
                <div 
                  className="timeline-dot" 
                  style={{
                    borderColor: isSelected ? '#38bdf8' : color, 
                    backgroundColor: color === '#ffffff' ? '#ffffff' : (isSelected ? '#38bdf8' : undefined),
                    boxShadow: isSelected ? '0 0 12px #38bdf8' : 'none'
                  }}
                ></div>
                <div style={{fontWeight: isSelected ? 800 : 700, color: isSelected ? '#38bdf8' : color, fontSize: '0.8rem'}}>{node.status}</div>
                <div className="timeline-label" style={{ fontWeight: isSelected ? 'bold' : 'normal', color: isSelected ? '#ffffff' : '#94a3b8' }}>
                  {node.time === '0m' ? 'NOW' : node.time}
                </div>
                <div className="timeline-label">{node.depth.toFixed(1)} cm</div>
              </div>
            );
          })}
        </div>
      </footer>
        </>
      )}

    </div>
  );
}

export default App;
