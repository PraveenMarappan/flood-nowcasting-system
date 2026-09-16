import React, { useState, useEffect } from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup, Polyline } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { CloudRain, AlertTriangle, Navigation, Activity, BarChart3, Wifi, WifiOff, Clock } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import axios from 'axios';

const API_BASE = "http://localhost:8000/api";

function App() {
  const [isSimulated, setIsSimulated] = useState(true);
  const [rainfall, setRainfall] = useState(0);
  const [liveRainfallData, setLiveRainfallData] = useState(null);
  const [terrainInfo, setTerrainInfo] = useState(null);
  
  const [forecast, setForecast] = useState(null);
  const [roads, setRoads] = useState([]);
  const [locations, setLocations] = useState([]);
  const [drainage, setDrainage] = useState(null);
  const [historyData, setHistoryData] = useState([]);
  const [dataStatus, setDataStatus] = useState(null);

  // Fetch forecast and dependent data whenever rainfall changes
  useEffect(() => {
    fetchData();
  }, [rainfall, isSimulated]);

  // Handle LIVE data polling every 10 mins
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
      
      const roadsRes = await axios.get(`${API_BASE}/roads/risk`);
      setRoads(roadsRes.data.roads);
      
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
      
      // History map
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
    switch(status) {
      case 'NORMAL': return '#10b981';
      case 'WATCH': return '#eab308';
      case 'FLOOD': return '#f97316';
      case 'CRITICAL': return '#ef4444';
      case 'RECOVERY': return '#3b82f6';
      default: return '#94a3b8';
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

  if (!forecast) return <div style={{padding: 20}}>Loading (or backend unreachable)...</div>;

  return (
    <div className="dashboard-layout">
      {/* HEADER */}
      <header className="header">
        <div className="header-title">
          <CloudRain size={24} /> Chennai Flood Nowcast
        </div>
        <div className="header-status">
          {renderHeaderStatus()}
        </div>
      </header>
      
      <div className="main-content">
        {/* SIDEBAR */}
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
              {terrainInfo && (
                <div>
                   <strong>Ref Elevation:</strong> {terrainInfo.elevation_m !== null ? `${terrainInfo.elevation_m.toFixed(1)} m` : 'UNAVAILABLE'}
                   <div style={{fontSize: '0.8rem', color: terrainInfo.status === 'REAL' ? '#10b981' : '#94a3b8', display: 'inline-block', marginLeft: 6}}>
                     {terrainInfo.source} • {terrainInfo.status}
                   </div>
                </div>
              )}
              {drainage && (
                <div style={{display: 'flex', alignItems: 'center', gap: 5}}>
                  <strong>Drainage Stress:</strong> {drainage.load_percentage}% LOAD
                </div>
              )}
              {!isSimulated && liveRainfallData && (
                <div style={{fontSize: '0.8rem', color: '#94a3b8', marginTop: 5}}>
                  Last Updated: {liveRainfallData.data_timestamp || liveRainfallData.retrieved_at}
                </div>
              )}
            </div>
          </div>
          
          {isSimulated && (
            <div className="card">
              <div className="card-title">Simulation Scenario</div>
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

          {dataStatus && (
            <div className="card">
              <div className="card-title">DATA QUALITY PANEL</div>
              <div style={{display: 'flex', flexDirection: 'column', gap: 8}}>
                <div style={{background: '#1e293b', padding: 8, borderRadius: 6}}>
                     <div style={{textTransform: 'capitalize', fontWeight: 'bold', fontSize: '0.9rem'}}>Data Confidence</div>
                     <div style={{display: 'flex', alignItems: 'center', gap: 5, fontSize: '0.8rem', marginTop: 4}}>
                        <span style={{
                          background: dataStatus.data_confidence === 'HIGH' ? '#047857' : (dataStatus.data_confidence === 'MEDIUM' ? '#d97706' : '#be123c'), 
                          color: 'white', padding: '2px 6px', borderRadius: 4, fontWeight: 'bold'
                        }}>{dataStatus.data_confidence}</span> 
                     </div>
                </div>
                {Object.entries(dataStatus.sources).map(([key, info]) => (
                  <div key={key} style={{background: '#1e293b', padding: 8, borderRadius: 6}}>
                    <div style={{textTransform: 'capitalize', fontWeight: 'bold', fontSize: '0.9rem'}}>{key.replace('_', ' ')}</div>
                    <div style={{display: 'flex', alignItems: 'center', gap: 5, fontSize: '0.8rem', marginTop: 4}}>
                       <span style={{
                         background: info.status === 'REAL' ? '#047857' : (info.status === 'MODELLED' ? '#1d4ed8' : (info.status === 'SIMULATED' ? '#b45309' : '#475569')), 
                         color: 'white', padding: '2px 6px', borderRadius: 4, fontWeight: 'bold'
                       }}>{info.status}</span> 
                       <span style={{color: '#94a3b8'}}>{info.source}</span>
                    </div>
                    {info.calibration_status && (
                       <div style={{fontSize: '0.75rem', color: '#94a3b8', marginTop: 4}}>
                          Calibration: {info.calibration_status}
                       </div>
                    )}
                  </div>
                ))}
                
                <div style={{background: '#1e293b', padding: 8, borderRadius: 6}}>
                    <div style={{textTransform: 'capitalize', fontWeight: 'bold', fontSize: '0.9rem'}}>Validation</div>
                    <div style={{display: 'flex', alignItems: 'center', gap: 5, fontSize: '0.8rem', marginTop: 4}}>
                       <span style={{background: '#475569', color: 'white', padding: '2px 6px', borderRadius: 4, fontWeight: 'bold'}}>
                         NOT AVAILABLE
                       </span>
                    </div>
                </div>
              </div>
            </div>
          )}

          <div className="card" style={{ flexGrow: 1, display: 'flex', flexDirection: 'column', minHeight: 200 }}>
            <div className="card-title" style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: 5 }}><BarChart3 size={16} /> Depth History</span>
              <span className="tag-simulated" style={{ fontSize: '0.6rem', background: '#1d4ed8' }}>MODELLED</span>
            </div>
            <div style={{ flex: 1, width: '100%', minHeight: 150, marginTop: 10 }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={historyData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                  <XAxis dataKey="time" stroke="#94a3b8" fontSize={12} tickLine={false} axisLine={false} />
                  <YAxis stroke="#94a3b8" fontSize={12} tickLine={false} axisLine={false} width={30} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', color: '#f8fafc' }}
                    itemStyle={{ color: '#38bdf8' }}
                  />
                  <Line type="monotone" dataKey="depth" stroke="#38bdf8" strokeWidth={3} dot={{ r: 4, fill: '#1e293b', strokeWidth: 2 }} activeDot={{ r: 6 }} name="Depth (cm)" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </aside>

        {/* MAP */}
        <main className="map-container">
          <MapContainer center={[13.0827, 80.2707]} zoom={12} style={{height: '100%', width: '100%'}}>
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
                      <strong>Drainage Coupling:</strong> UNAVAILABLE
                    </div>
                  </div>
                </Popup>
              </CircleMarker>
            ))}

            {roads.map(road => (
              road.coords && (
                <Polyline
                  key={`road-${road.id}`}
                  positions={road.coords}
                  pathOptions={{
                    color: road.risk === 'CRITICAL' ? '#ef4444' : (road.risk === 'HIGH' ? '#f97316' : (road.risk === 'MODERATE' ? '#eab308' : '#22c55e')),
                    weight: 4,
                    opacity: 0.8
                  }}
                >
                  <Popup>
                    <div style={{fontSize: '0.9rem', color: '#333'}}>
                      <strong>{road.name}</strong><br/>
                      
                      {terrainInfo && (
                         <div style={{marginTop: 5, paddingBottom: 5, borderBottom: '1px solid #ccc'}}>
                            <div><strong>Elevation:</strong> {terrainInfo.elevation_m !== null ? `${terrainInfo.elevation_m.toFixed(1)} m` : 'UNAVAILABLE'}</div>
                            <div style={{fontSize: '0.8rem'}}><strong>Terrain:</strong> {terrainInfo.status} — {terrainInfo.source}</div>
                         </div>
                      )}
                      
                      <div style={{marginTop: 5}}><strong>Model-based Road Risk:</strong> <span style={{color: road.risk === 'CRITICAL' ? '#ef4444' : (road.risk === 'HIGH' ? '#f97316' : (road.risk === 'MODERATE' ? '#eab308' : '#22c55e')), fontWeight: 'bold'}}>{road.risk}</span></div>
                      <div><strong>Modelled Flood Depth:</strong> {road.depth_cm} cm</div>
                      
                      <div style={{marginTop: 5, paddingBottom: 5, borderBottom: '1px solid #ccc'}}>
                        <div><strong>Rainfall Input:</strong> {rainfall.toFixed(1)} mm/hr</div>
                        <div style={{fontSize: '0.8rem'}}><strong>Rainfall Source:</strong> {isSimulated ? 'SIMULATED' : `REAL — ${liveRainfallData?.source || 'NASA GPM'}`}</div>
                      </div>
                      
                      <div style={{marginTop: 5, fontSize: '0.8rem', color: '#64748b'}}>
                        <strong>Flood Model:</strong> MODELLED (baseline-v1) <br/>
                        <strong>Calibration:</strong> NOT CALIBRATED <br/>
                        <strong>Drainage Coupling:</strong> UNAVAILABLE
                      </div>
                    </div>
                  </Popup>
                </Polyline>
              )
            ))}
          </MapContainer>
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
