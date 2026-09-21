import React, { useState, useEffect } from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup, GeoJSON } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { CloudRain, AlertTriangle, Navigation, Activity, BarChart3, Wifi, WifiOff, Clock, Info } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import axios from 'axios';

const API_BASE = "http://localhost:8000/api";

function App() {
  const [isSimulated, setIsSimulated] = useState(true);
  const [simulationRainfall, setSimulationRainfall] = useState(0);
  const [liveRainfallData, setLiveRainfallData] = useState(null);
  const [terrainInfo, setTerrainInfo] = useState(null);
  const [forecastOffset, setForecastOffset] = useState(0);
  
  const [forecast, setForecast] = useState(null);
  const [roadsGeojson, setRoadsGeojson] = useState(null);
  const [locations, setLocations] = useState([]);
  const [drainage, setDrainage] = useState(null);
  const [historyData, setHistoryData] = useState([]);
  const [dataStatus, setDataStatus] = useState(null);

  const requestIdRef = React.useRef(0);

  const liveRainfall = (liveRainfallData?.status === "LIVE" || liveRainfallData?.status === "STALE") 
    ? (liveRainfallData.rainfall_rate || 0) 
    : 0;

  const currentModelRainfall = isSimulated ? simulationRainfall : liveRainfall;

  useEffect(() => {
    fetchData();
  }, [currentModelRainfall, isSimulated, forecastOffset]);

  useEffect(() => {
    let interval;
    if (!isSimulated) {
      fetchLiveRainfall(); // initial fetch
      interval = setInterval(fetchLiveRainfall, 10 * 60 * 1000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isSimulated]);

  const fetchLiveRainfall = async () => {
    try {
      const res = await axios.get(`${API_BASE}/rainfall/current`);
      setLiveRainfallData(res.data);
    } catch (e) {
      console.error("Error fetching live rainfall", e);
      setLiveRainfallData({ status: "UNAVAILABLE", error: "Connection Error" });
    }
  };

  const fetchData = async () => {
    const currentRequestId = ++requestIdRef.current;
    console.log("[MODEL RAINFALL]", currentModelRainfall);
    console.log("[ROAD RISK REQUEST]", {
      rainfall: currentModelRainfall,
      forecastOffset,
      isSimulated,
      requestId: currentRequestId
    });

    try {
      const forecastRes = await axios.get(`${API_BASE}/flood/forecast?rainfall=${currentModelRainfall}&is_simulated=${isSimulated}`);
      if (currentRequestId === requestIdRef.current) {
        setForecast(forecastRes.data);
      }
    } catch (e) {
      console.error("Error fetching forecast", e);
    }
    
    if (currentRequestId !== requestIdRef.current) return;

    try {
      const roadsRes = await axios.get(`${API_BASE}/roads/risk?forecast_offset=${forecastOffset}&rainfall=${currentModelRainfall}&is_simulated=${isSimulated}`);
      if (currentRequestId === requestIdRef.current) {
        console.log(`[ROADS] response #${currentRequestId} status: ${roadsRes.data?.road_data_status}, feature count: ${roadsRes.data?.features?.length}`);
        if (roadsRes.data && Array.isArray(roadsRes.data.features) && roadsRes.data.features.length > 0) {
          setRoadsGeojson(roadsRes.data);
        } else {
          console.warn("[ROADS] Response contained 0 features or unavailable status. Retaining existing valid road geometry.");
        }
      }
    } catch (e) {
      console.error("[ROADS] Transient error fetching roads risk. Retaining existing valid road geometry.", e);
    }

    if (currentRequestId !== requestIdRef.current) return;

    try {
      const locRes = await axios.get(`${API_BASE}/locations/critical`);
      if (currentRequestId === requestIdRef.current) setLocations(locRes.data.locations || []);
    } catch (err) { console.error("Error fetching locations", err); }

    try {
      const drainRes = await axios.get(`${API_BASE}/drainage/diagnostics?latitude=13.0827&longitude=80.2707`);
      if (currentRequestId === requestIdRef.current) setDrainage(drainRes.data);
    } catch (err) { console.error("Error fetching drainage diagnostics", err); }
    
    try {
      const statusRes = await axios.get(`${API_BASE}/data-status`);
      if (currentRequestId === requestIdRef.current) setDataStatus(statusRes.data);
    } catch (err) { console.error("Error fetching data status", err); }
    
    try {
      const terrainRes = await axios.get(`${API_BASE}/terrain/elevation?latitude=13.0827&longitude=80.2707`);
      if (currentRequestId === requestIdRef.current) setTerrainInfo(terrainRes.data);
    } catch (err) { console.error("Error fetching terrain data", err); }
  };

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

  const getRoadColor = (props) => {
    if (!props) return '#9ca3af';
    const riskLevel = (props.risk_level || '').toUpperCase();
    const riskColorProp = (props.risk_color || '').toUpperCase();

    if (riskLevel === 'NORMAL' || riskColorProp === 'WHITE') return '#ffffff';
    if (riskLevel === 'LOW' || riskColorProp === 'GREEN' || riskColorProp === 'LIGHT_BLUE' || riskColorProp === 'BLUE') return '#38bdf8';
    if (riskLevel === 'MODERATE' || riskColorProp === 'ORANGE') return '#f59e0b';
    if (riskLevel === 'HIGH' || riskLevel === 'CRITICAL' || riskColorProp === 'RED') return '#ef4444';
    if (riskLevel === 'DATA UNAVAILABLE' || riskLevel === 'UNAVAILABLE' || riskColorProp === 'GRAY') return '#9ca3af';
    
    return '#38bdf8';
  };

  const getRoadStyle = (feature) => {
    const props = feature?.properties || {};
    const color = getRoadColor(props);
    return {
      color: color,
      weight: 5,
      opacity: 0.9,
      lineCap: 'round'
    };
  };

  const onEachRoadFeature = (feature, layer) => {
    const props = feature.properties;
    if (props) {
      const riskColor = getRoadColor(props);
      
      layer.setStyle({
        color: riskColor,
        weight: 5,
        opacity: 0.9,
        lineCap: 'round'
      });
      
      layer.on('mouseover', (e) => e.target.setStyle({ weight: 8 }));
      layer.on('mouseout', (e) => e.target.setStyle({ weight: 5 }));

      const badgeTextColor = riskColor === '#ffffff' ? '#0f172a' : '#ffffff';
      const badgeBorder = riskColor === '#ffffff' ? 'border: 1px solid #94a3b8;' : '';

      // Popup Content satisfying the 11-point popup requirement verbatim
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
            Rainfall: <strong>${currentModelRainfall.toFixed(1)} mm/hr</strong><br/>
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
  };

  const renderHeaderStatus = () => {
    if (isSimulated) {
      return (
        <div style={{display: 'flex', gap: 10, alignItems: 'center'}}>
          <span className="tag-simulated">SIMULATION MODE</span>
          <span>MANUAL INPUT</span>
        </div>
      );
    }

    if (!liveRainfallData) {
      return (
        <div style={{display: 'flex', gap: 10, alignItems: 'center', color: '#eab308'}}>
          <Activity size={18} /> <span>FETCHING NASA GPM...</span>
        </div>
      );
    }

    const { status, retrieved_at, data_timestamp } = liveRainfallData;
    
    if (status === "LIVE") {
      return (
        <div style={{display: 'flex', gap: 10, alignItems: 'center', color: '#38bdf8'}}>
          <Wifi size={18} /> <span>LIVE NASA GPM / IMERG</span>
          <span style={{fontSize: '0.8rem', color: '#94a3b8', marginLeft: 10}}>
            Last updated: {new Date(retrieved_at).toLocaleTimeString()}
          </span>
        </div>
      );
    }
    
    if (status === "STALE") {
      return (
        <div style={{display: 'flex', gap: 10, alignItems: 'center', color: '#f97316'}}>
          <AlertTriangle size={18} /> <span>NASA DATA UNAVAILABLE (STALE)</span>
          <span style={{fontSize: '0.8rem', color: '#94a3b8', marginLeft: 10}}>
            Last known: {new Date(data_timestamp || retrieved_at).toLocaleString()}
          </span>
        </div>
      );
    }

    return (
      <div style={{display: 'flex', gap: 10, alignItems: 'center', color: '#ef4444'}}>
        <WifiOff size={18} /> <span>NASA DATA UNAVAILABLE</span>
      </div>
    );
  };
  
  // Calculate Road Counts explicitly based on the API response per requirements
  let countNormal = 0, countLow = 0, countMod = 0, countHigh = 0, countGray = 0;
  if (roadsGeojson && roadsGeojson.features) {
    roadsGeojson.features.forEach(f => {
      const r = (f.properties?.risk_level || '').toUpperCase();
      if (r === 'NORMAL') countNormal++;
      else if (r === 'LOW') countLow++;
      else if (r === 'MODERATE') countMod++;
      else if (r === 'HIGH' || r === 'CRITICAL') countHigh++;
      else countGray++;
    });
  }

  if (!forecast) return <div style={{padding: 20}}>Loading (or backend unreachable)...</div>;

  return (
    <div className="dashboard-layout">
      <header className="header">
        <div className="header-title">
          <CloudRain size={24} /> Chennai Flood Nowcast
        </div>
        <div className="header-status">
          {renderHeaderStatus()}
        </div>
      </header>
      
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
            <div style={{display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: '#64748b', marginTop: '4px'}}>
              <span>NOW</span>
              <span>+60m</span>
              <span>+120m</span>
              <span>+180m</span>
            </div>
          </div>

          <div className="card">
            <div className="card-title">CURRENT CONDITIONS</div>
            <div style={{display: 'flex', flexDirection: 'column', gap: 10, fontSize: '0.95rem'}}>
              <div>
                <strong>Rainfall:</strong> {currentModelRainfall.toFixed(1)} mm/hr
                {isSimulated ? (
                  <div className="tag-simulated" style={{marginTop: 5, display: 'inline-block', marginLeft: 10}}>Synthetic Scenario</div>
                ) : (
                  liveRainfallData && (
                    <div style={{fontSize: '0.8rem', color: '#38bdf8', marginTop: 5}}>
                      {liveRainfallData.source || 'NASA GPM IMERG'} • {liveRainfallData.status === "LIVE" ? "REAL" : liveRainfallData.status}
                    </div>
                  )
                )}
              </div>
              <div style={{display: 'flex', alignItems: 'center', gap: 5}}>
                <strong>Flood Status:</strong> 
                <span className={`status-indicator status-${forecast.status.toLowerCase()}`}></span>
                <span style={{color: getStatusColor(forecast.status), fontWeight: 'bold'}}>{forecast.status}</span>
              </div>
              <div>
                <strong>Max Flood Depth:</strong> {forecast.water_depth_cm.toFixed(1)} cm
              </div>
            </div>
          </div>
          
          {isSimulated && (
            <div className="card">
              <div className="card-title">Simulation Scenario (Rainfall)</div>
              <input 
                type="range" 
                min="0" max="150" step="5"
                value={simulationRainfall}
                onChange={(e) => setSimulationRainfall(Number(e.target.value))}
                className="input-slider"
              />
              <div style={{display: 'flex', gap: 5, marginTop: 15, flexWrap: 'wrap'}}>
                {[0, 10, 25, 50, 100].map(val => (
                  <button 
                     key={val} 
                     onClick={() => setSimulationRainfall(val)}
                     style={{
                       background: simulationRainfall === val ? '#3b82f6' : '#334155',
                       color: 'white', border: 'none', padding: '5px 10px', borderRadius: 4, cursor: 'pointer'
                     }}
                  >
                    {val} mm/hr
                  </button>
                ))}
              </div>
            </div>
          )}

          {drainage && (
            <div className="card">
              <div className="card-title">DRAINAGE DIAGNOSTICS (INFORMATIONAL)</div>
              <div style={{fontSize: '0.8rem', color: '#cbd5e1', display: 'flex', flexDirection: 'column', gap: 6}}>
                <div><strong>Coverage:</strong> <span style={{color: drainage.coverage?.status === 'DRAINAGE_SERVED' ? '#38bdf8' : '#f59e0b', fontWeight: 'bold'}}>{drainage.coverage?.status || 'N/A'}</span> ({drainage.coverage?.nearest_swd_distance_m ?? 'N/A'}m to SWD)</div>
                <div><strong>Density:</strong> {drainage.density?.density_km_per_km2 ?? 'N/A'} km/km²</div>
                <div><strong>Deficit Index (DBI):</strong> {drainage.dbi?.value ?? 'N/A'} ({drainage.dbi?.status || 'N/A'})</div>
                <div><strong>Hydraulic Capacity:</strong> <span style={{color: '#9ca3af', fontWeight: 'bold'}}>UNKNOWN</span></div>
                <div style={{fontSize: '0.75rem', color: '#94a3b8', fontStyle: 'italic', borderTop: '1px solid #334155', paddingTop: 4, marginTop: 2}}>
                  Informational spatial diagnostics only. Drain proximity does not reduce flood depth calculations.
                </div>
              </div>
            </div>
          )}

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
          <MapContainer center={[13.0500, 80.2400]} zoom={13} style={{height: '100%', width: '100%'}}>
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />

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

            {roadsGeojson && roadsGeojson.features && roadsGeojson.features.length > 0 && (
              <>
                <GeoJSON
                  key={`road-casing-${forecastOffset}-${currentModelRainfall}-${isSimulated}`}
                  data={roadsGeojson}
                  style={(feature) => {
                    const props = feature?.properties || {};
                    const color = getRoadColor(props);
                    const isWhite = color === '#ffffff';
                    return {
                      color: isWhite ? '#1e293b' : '#0f172a',
                      weight: isWhite ? 8 : 7,
                      opacity: 0.85,
                      lineCap: 'round',
                      lineJoin: 'round'
                    };
                  }}
                  interactive={false}
                />
                <GeoJSON
                  key={`real-chennai-road-layer-${forecastOffset}-${currentModelRainfall}-${isSimulated}`}
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
            <h4 style={{margin: '0 0 10px 0', fontSize: '0.85rem', borderBottom: '1px solid #334155', paddingBottom: '4px', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em'}}>FLOOD RISK</h4>
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
      <footer className="footer-timeline">
        <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
          <div className="card-title" style={{margin: 0}}>Forecast Timeline</div>
          <span className="tag-simulated" style={{background: '#1d4ed8'}}>MODELLED</span>
        </div>
        <div className="timeline-track">
          <div className="timeline-line"></div>
          {forecast.forecast.map((node, i) => {
            const color = getStatusColor(node.status);
            return (
              <div className="timeline-node" key={i}>
                <div className="timeline-dot" style={{borderColor: color, backgroundColor: color === '#ffffff' ? '#ffffff' : undefined}}></div>
                <div style={{fontWeight: 700, color: color}}>{node.status}</div>
                <div className="timeline-label">{node.time}</div>
                <div className="timeline-label">{node.depth.toFixed(1)} cm</div>
              </div>
            );
          })}
        </div>
      </footer>

    </div>
  );
}

export default App;
