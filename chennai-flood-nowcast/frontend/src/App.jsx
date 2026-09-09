import React, { useState, useEffect } from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup, Polyline } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { CloudRain, AlertTriangle, Navigation, Activity, BarChart3 } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import axios from 'axios';

const API_BASE = "http://localhost:8000/api";

function App() {
  const [isSimulated, setIsSimulated] = useState(true);
  const [rainfall, setRainfall] = useState(0);
  const [forecast, setForecast] = useState(null);
  const [roads, setRoads] = useState([]);
  const [locations, setLocations] = useState([]);
  const [drainage, setDrainage] = useState(null);
  const [historyData, setHistoryData] = useState([]);


  useEffect(() => {
    fetchData();
  }, [rainfall, isSimulated]);

  const fetchData = async () => {
    try {
      const forecastRes = await axios.get(`${API_BASE}/flood/forecast?rainfall=${rainfall}`);
      setForecast(forecastRes.data);
      
      const roadsRes = await axios.get(`${API_BASE}/roads/risk`);
      setRoads(roadsRes.data.roads);
      
      const locRes = await axios.get(`${API_BASE}/locations/critical`);
      setLocations(locRes.data.locations);
      
      const drainRes = await axios.get(`${API_BASE}/drainage/status`);
      setDrainage(drainRes.data.drainage);
      
      // Simulate historical reading points based on current forecast
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

  if (!forecast) return <div style={{padding: 20}}>Loading (or backend unreachable)...</div>;

  return (
    <div className="dashboard-layout">
      {/* HEADER */}
      <header className="header">
        <div className="header-title">
          <CloudRain size={24} /> Chennai Flood Nowcast
        </div>
        <div className="header-status">
          {isSimulated && <span className="tag-simulated">SIMULATION MODE</span>}
          <span>LIVE DATA: UNAVAILABLE (NASA GPM PENDING)</span>
        </div>
      </header>
      
      <div className="main-content">
        {/* SIDEBAR */}
        <aside className="sidebar">
          <div className="card">
            <div className="card-title">System Status</div>
            <div style={{display: 'flex', alignItems: 'center'}}>
              <span className={`status-indicator status-${forecast.status.toLowerCase()}`}></span>
              <span className="score" style={{color: getStatusColor(forecast.status)}}>{forecast.status}</span>
            </div>
            <p style={{marginTop: 5, color: '#94a3b8'}}>Estimated water depth: {forecast.water_depth_cm.toFixed(1)} cm</p>
          </div>
          
          <div className="card">
            <div className="card-title">Simulation Control</div>
            <div style={{display: 'flex', justifyContent: 'space-between', marginBottom: 10}}>
              <span>Rainfall Input:</span>
              <span style={{fontWeight: 600, color: '#38bdf8'}}>{rainfall} mm/hr</span>
            </div>
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
                  {val}
                </button>
              ))}
            </div>
          </div>
          
          {drainage && (
            <div className="card">
              <div className="card-title">Drainage Stress <span className="tag-simulated" style={{fontSize:'0.6rem'}}>SIMULATED</span></div>
              <div className="score" style={{fontSize: '1.5rem'}}>{drainage.load_percentage}% LOAD</div>
              <div style={{marginTop: 10}}>
                <div style={{height: 8, background: '#334155', borderRadius: 4, overflow: 'hidden'}}>
                  <div style={{height: '100%', width: `${drainage.load_percentage}%`, background: drainage.load_percentage > 80 ? '#ef4444' : '#eab308'}}></div>
                </div>
              </div>
            </div>
          )}

          <div className="card" style={{ flexGrow: 1, display: 'flex', flexDirection: 'column', minHeight: 200 }}>
            <div className="card-title" style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: 5 }}><BarChart3 size={16} /> Depth History</span>
              <span className="tag-simulated" style={{ fontSize: '0.6rem' }}>SIMULATED</span>
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
                  <strong>{loc.name}</strong><br/>
                  Type: {loc.type}<br/>
                  Risk: {loc.risk}<br/>
                  Water Depth: {loc.depth_cm} cm
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
                    <strong>{road.name}</strong><br/>
                    Risk: {road.risk}<br/>
                    Depth: {road.depth_cm} cm<br/>
                    <span className="tag-simulated" style={{fontSize: '0.6rem'}}>SIMULATED</span>
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
          <span className="tag-simulated">SIMULATED FORECAST</span>
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
