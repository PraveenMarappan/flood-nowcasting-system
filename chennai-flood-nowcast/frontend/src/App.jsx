import React, { useState, useEffect } from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup, GeoJSON } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { CloudRain, AlertTriangle, Navigation, Activity, BarChart3, Wifi, WifiOff, Clock, Info } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import axios from 'axios';

const API_BASE = "http://localhost:8000/api";

function App() {
  const [isSimulated, setIsSimulated] = useState(true);
  const [rainfall, setRainfall] = useState(0);
  const [liveRainfallData, setLiveRainfallData] = useState(null);
  const [terrainInfo, setTerrainInfo] = useState(null);
  const [forecastOffset, setForecastOffset] = useState(0);
  
  const [forecast, setForecast] = useState(null);
  const [roadsGeojson, setRoadsGeojson] = useState(null);
  const [locations, setLocations] = useState([]);
  const [drainage, setDrainage] = useState(null);
  const [historyData, setHistoryData] = useState([]);
  const [dataStatus, setDataStatus] = useState(null);

  useEffect(() => {
    fetchData();
  }, [rainfall, isSimulated, forecastOffset]);

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
      if (res.data.status === "LIVE" || res.data.status === "STALE") {
        setRainfall(res.data.rainfall_rate || 0);
      }
    } catch (e) {
      console.error("Error fetching live rainfall", e);
      setLiveRainfallData({ status: "UNAVAILABLE", error: "Connection Error" });
    }
  };

  const fetchData = async () => {
    try {
      const forecastRes = await axios.get(`${API_BASE}/flood/forecast?rainfall=${rainfall}&is_simulated=${isSimulated}`);
      setForecast(forecastRes.data);
      
      const roadsRes = await axios.get(`${API_BASE}/roads/risk?forecast_offset=${forecastOffset}&rainfall=${rainfall}&is_simulated=${isSimulated}`);
      setRoadsGeojson(roadsRes.data);
      
      const locRes = await axios.get(`${API_BASE}/locations/critical`);
      setLocations(locRes.data.locations);
      
      const drainRes = await axios.get(`${API_BASE}/drainage/status`);
      setDrainage(drainRes.data.drainage);
      
      try {
        const statusRes = await axios.get(`${API_BASE}/data-status`);
        setDataStatus(statusRes.data);
      } catch (err) {
        console.error("Error fetching data status", err);
      }
      
      try {
        const terrainRes = await axios.get(`${API_BASE}/terrain/elevation?latitude=13.0827&longitude=80.2707`);
        setTerrainInfo(terrainRes.data);
      } catch (err) {
        console.error("Error fetching terrain data", err);
      }
      
      if (forecastRes.data) {
        const hData = [
          { time: '-2h', depth: Math.max(0, forecastRes.data.water_depth_cm * 0.2), rain: rainfall * 0.1 },
          { time: '-1h', depth: Math.max(0, forecastRes.data.water_depth_cm * 0.5), rain: rainfall * 0.4 },
          { time: 'Now', depth: forecastRes.data.water_depth_cm, rain: rainfall }
        ];
        setHistoryData(hData);
      }
    } catch (e) {
      console.error("Error fetching data", e);
    }
  };

  const getStatusColor = (status) => {
    if (!status) return '#94a3b8';
    switch(status.toUpperCase()) {
      case 'NORMAL': case 'LOW': return '#10b981'; // Green
      case 'WATCH': case 'MODERATE': return '#f59e0b'; // Orange
      case 'FLOOD': case 'HIGH': case 'CRITICAL': return '#ef4444'; // Red
      case 'RECOVERY': return '#3b82f6';
      case 'GRAY': case 'DATA UNAVAILABLE': return '#9ca3af'; // Gray
      default: return '#94a3b8'; 
    }
  };

  const onEachRoadFeature = (feature, layer) => {
    const props = feature.properties;
    if (props) {
      // Dynamic rendering style natively mapping GeoJSON Risk classes precisely
      const riskColor = props.risk_color === 'GREEN' ? '#10b981' : 
                        props.risk_color === 'ORANGE' ? '#f59e0b' : 
                        props.risk_color === 'RED' ? '#ef4444' : '#9ca3af';
      
      layer.setStyle({
        color: riskColor,
        weight: 5,
        opacity: 0.9,
        lineCap: 'round'
      });
      
      layer.on('mouseover', (e) => e.target.setStyle({ weight: 8 }));
      layer.on('mouseout', (e) => e.target.setStyle({ weight: 5 }));

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
            Risk: <span style="font-weight: 700; background: ${riskColor}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.8rem;">${props.risk_level || 'UNKNOWN'}</span>
          </div>

          <div style="font-size: 0.8rem; color: #475569; padding-bottom: 5px; border-bottom: 1px solid #e2e8f0;">
            Rainfall: <strong>${rainfall.toFixed(1)} mm/hr</strong><br/>
          </div>
          
          <div style="font-size: 0.75rem; color: #64748b; margin-top: 5px; line-height: 1.4;">
            Model: ${props.model_version || 'baseline'}<br/>
            Drainage: NOT USED<br/>
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
        <div style={{display: 'flex', gap: 10, alignItems: 'center', color: '#10b981'}}>
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
  let countLow = 0, countMod = 0, countHigh = 0, countGray = 0;
  if (roadsGeojson && roadsGeojson.features) {
    roadsGeojson.features.forEach(f => {
      const r = f.properties.risk_level;
      if (r === 'LOW') countLow++;
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
                  background: !isSimulated ? '#10b981' : '#1e293b',
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
                <strong>Rainfall:</strong> {rainfall.toFixed(1)} mm/hr
                {isSimulated ? (
                  <div className="tag-simulated" style={{marginTop: 5, display: 'inline-block', marginLeft: 10}}>Synthetic Scenario</div>
                ) : (
                  liveRainfallData && (
                    <div style={{fontSize: '0.8rem', color: '#10b981', marginTop: 5}}>
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
                value={rainfall}
                onChange={(e) => setRainfall(Number(e.target.value))}
                className="input-slider"
              />
              <div style={{display: 'flex', gap: 5, marginTop: 15, flexWrap: 'wrap'}}>
                {[0, 10, 25, 50, 100].map(val => (
                  <button 
                     key={val} 
                     onClick={() => setRainfall(val)}
                     style={{
                       background: rainfall === val ? '#3b82f6' : '#334155',
                       color: 'white', border: 'none', padding: '5px 10px', borderRadius: 4, cursor: 'pointer'
                     }}
                  >
                    {val} mm/hr
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="card">
              <div className="card-title">ROAD RISK COUNTERS</div>
              <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '0.85rem'}}>
                 <div style={{background: 'rgba(16, 185, 129, 0.1)', border: '1px solid #10b981', padding: '6px', borderRadius: '4px'}}>
                    <div style={{color: '#10b981', fontWeight: 'bold'}}>LOW ROADS</div>
                    <div style={{fontSize: '1.2rem'}}>{countLow}</div>
                 </div>
                 <div style={{background: 'rgba(245, 158, 11, 0.1)', border: '1px solid #f59e0b', padding: '6px', borderRadius: '4px'}}>
                    <div style={{color: '#f59e0b', fontWeight: 'bold'}}>MODERATE</div>
                    <div style={{fontSize: '1.2rem'}}>{countMod}</div>
                 </div>
                 <div style={{background: 'rgba(239, 68, 68, 0.1)', border: '1px solid #ef4444', padding: '6px', borderRadius: '4px'}}>
                    <div style={{color: '#ef4444', fontWeight: 'bold'}}>HIGH-RISK</div>
                    <div style={{fontSize: '1.2rem'}}>{countHigh}</div>
                 </div>
                 <div style={{background: 'rgba(156, 163, 175, 0.1)', border: '1px solid #9ca3af', padding: '6px', borderRadius: '4px'}}>
                    <div style={{color: '#9ca3af', fontWeight: 'bold'}}>UNAVAILABLE</div>
                    <div style={{fontSize: '1.2rem'}}>{countGray}</div>
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
                  fillColor: loc.risk === 'CRITICAL' ? '#ef4444' : (loc.risk === 'HIGH' ? '#f97316' : '#3b82f6'),
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
                    <div><strong>Modelled Risk Level:</strong> <span style={{color: loc.risk === 'CRITICAL' ? '#ef4444' : (loc.risk === 'HIGH' ? '#f97316' : '#3b82f6'), fontWeight: 'bold'}}>{loc.risk}</span></div>
                    <div><strong>Modelled Flood Depth:</strong> {loc.depth_cm} cm</div>
                    
                    <div style={{marginTop: 5, paddingBottom: 5, borderBottom: '1px solid #ccc'}}>
                      <div><strong>Rainfall Input:</strong> {rainfall.toFixed(1)} mm/hr</div>
                      <div style={{fontSize: '0.8rem'}}><strong>Rainfall Source:</strong> {isSimulated ? 'SIMULATED' : `REAL — ${liveRainfallData?.source || 'NASA GPM'}`}</div>
                    </div>
                    
                    <div style={{marginTop: 5, fontSize: '0.8rem', color: '#64748b'}}>
                      <strong>Flood Model:</strong> MODELLED (baseline-v1) <br/>
                      <strong>Calibration:</strong> NOT CALIBRATED <br/>
                      <strong>Drainage:</strong> NOT USED
                    </div>
                  </div>
                </Popup>
              </CircleMarker>
            ))}

            {roadsGeojson && roadsGeojson.features && (
              <GeoJSON
                key={`roads-${forecastOffset}-${rainfall}-${isSimulated}`} // Force React to rebuild the native leaflet layers when API outputs alter natively
                data={roadsGeojson}
                onEachFeature={onEachRoadFeature}
              />
            )}
          </MapContainer>
          
          {/* STATIC OVERLAY LEGEND */}
          <div style={{
            position: 'absolute', bottom: '30px', right: '10px', 
            background: 'white', padding: '10px 15px', borderRadius: '8px', 
            boxShadow: '0 4px 6px rgba(0,0,0,0.3)', zIndex: 1000, color: '#333'
          }}>
            <h4 style={{margin: '0 0 10px 0', fontSize: '0.9rem', borderBottom: '1px solid #ddd', paddingBottom: '4px'}}>FLOOD RISK</h4>
            <div style={{display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '0.85rem', fontWeight: '600'}}>
              <div style={{display: 'flex', alignItems: 'center', gap: '8px'}}><div style={{width: 14, height: 14, borderRadius: '50%', background: '#10b981'}}></div> LOW</div>
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
          {forecast.forecast.map((node, i) => (
            <div className="timeline-node" key={i}>
              <div className="timeline-dot" style={{borderColor: getStatusColor(node.status)}}></div>
              <div style={{fontWeight: 700, color: getStatusColor(node.status)}}>{node.status}</div>
              <div className="timeline-label">{node.time}</div>
              <div className="timeline-label">{node.depth.toFixed(1)} cm</div>
            </div>
          ))}
        </div>
      </footer>

    </div>
  );
}

export default App;
