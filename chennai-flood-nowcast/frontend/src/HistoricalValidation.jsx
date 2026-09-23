import React, { useEffect, useState, useMemo, useRef } from 'react';
import axios from 'axios';
import { 
  AlertTriangle, 
  Info, 
  Database, 
  BarChart2, 
  CheckCircle2, 
  XCircle, 
  FileText, 
  Layers, 
  Clock 
} from 'lucide-react';
import { 
  ResponsiveContainer, 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip 
} from 'recharts';

const API_BASE = "http://localhost:8000/api";

// Module-level cache so data persists across tab switches without re-fetching
let _historicalDataCache = null;

export default function HistoricalValidation() {
  const [data, setData] = useState(_historicalDataCache);
  const [loading, setLoading] = useState(_historicalDataCache === null);
  const [error, setError] = useState(null);
  const fetchedRef = useRef(false);

  useEffect(() => {
    // Skip fetch if already cached
    if (_historicalDataCache !== null || fetchedRef.current) return;
    fetchedRef.current = true;

    const fetchHistoricalValidation = async () => {
      try {
        setLoading(true);
        const res = await axios.get(`${API_BASE}/validation/historical`);
        _historicalDataCache = res.data;
        setData(res.data);
        setError(null);
      } catch (err) {
        console.error("Error fetching historical validation data:", err);
        setError("Failed to load historical validation dataset from backend.");
      } finally {
        setLoading(false);
      }
    };
    fetchHistoricalValidation();
  }, []);

  const rawTimeseries = data?.timeseries || [];

  // Memoize chart data transformation to avoid recomputing on every render
  const chartData = useMemo(() => rawTimeseries.map(item => {
    const dt = item.timestamp_utc ? new Date(item.timestamp_utc) : null;
    const timeLabel = dt ? `${dt.getUTCMonth() + 1}/${dt.getUTCDate()} ${String(dt.getUTCHours()).padStart(2, '0')}:${String(dt.getUTCMinutes()).padStart(2, '0')}` : item.timestamp_utc;
    return {
      timestamp: timeLabel,
      fullTimestamp: item.timestamp_utc,
      rainfall: item.rainfall_mm_hr !== undefined ? item.rainfall_mm_hr : null,
      modelDepth: item.model_depth_cm !== undefined ? item.model_depth_cm : null,
    };
  }), [rawTimeseries]);

  if (loading) {
    return (
      <div style={{ padding: '40px', color: '#94a3b8', textAlign: 'center', flex: 1 }}>
        <Clock size={32} className="animate-spin" style={{ marginBottom: '12px', color: '#38bdf8' }} />
        <div>Loading Historical Validation Replay Data...</div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div style={{ padding: '40px', color: '#ef4444', textAlign: 'center', flex: 1 }}>
        <AlertTriangle size={32} style={{ marginBottom: '12px' }} />
        <div>{error || "No data available."}</div>
      </div>
    );
  }

  const metrics = data.metrics || {};
  const depthVal = metrics.depth_validation || {};
  const forcing = metrics.forcing || {};

  return (
    <div style={{ flex: 1, overflowY: 'auto', width: '100%', padding: '24px', maxWidth: '1400px', margin: '0 auto', color: '#f8fafc', display: 'flex', flexDirection: 'column', gap: '24px' }}>
      
      {/* SECTION 1: NOT VALIDATED STATUS BANNER */}
      <div style={{
        background: 'linear-gradient(135deg, rgba(239, 68, 68, 0.15) 0%, rgba(185, 28, 28, 0.25) 100%)',
        border: '1px solid #ef4444',
        borderRadius: '12px',
        padding: '20px 24px',
        boxShadow: '0 4px 20px rgba(239, 68, 68, 0.15)',
        display: 'flex',
        alignItems: 'center',
        justify: 'space-between',
        flexWrap: 'wrap',
        gap: '16px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div style={{
            background: '#ef4444',
            color: '#ffffff',
            padding: '10px 18px',
            borderRadius: '8px',
            fontWeight: '900',
            fontSize: '1.25rem',
            letterSpacing: '0.08em',
            boxShadow: '0 2px 8px rgba(239, 68, 68, 0.4)'
          }}>
            NOT VALIDATED
          </div>
          <div>
            <h2 style={{ margin: 0, fontSize: '1.3rem', fontWeight: '700', color: '#f8fafc' }}>
              Historical Validation Status: NOT VALIDATED
            </h2>
            <p style={{ margin: '4px 0 0 0', color: '#cbd5e1', fontSize: '0.9rem' }}>
              The flood forecasting model is currently unvalidated for historical accuracy. Replay forcing and spatial comparisons are provided for diagnostic evaluation only.
            </p>
          </div>
        </div>
        <div style={{ display: 'flex', gap: '12px', fontSize: '0.85rem' }}>
          <span style={{ background: 'rgba(255, 255, 255, 0.08)', padding: '6px 12px', borderRadius: '6px', border: '1px solid rgba(255, 255, 255, 0.1)' }}>
            Forcing: <strong>128 / 241</strong>
          </span>
          <span style={{ background: 'rgba(239, 68, 68, 0.15)', color: '#fca5a5', padding: '6px 12px', borderRadius: '6px', border: '1px solid rgba(239, 68, 68, 0.3)' }}>
            Missing: <strong>113</strong>
          </span>
        </div>
      </div>

      {/* SECTION 2: OBSERVATION ATTRIBUTION */}
      <div style={{ background: '#0f172a', border: '1px solid #334155', borderRadius: '12px', padding: '20px' }}>
        <h3 style={{ margin: '0 0 16px 0', fontSize: '1.1rem', color: '#38bdf8', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Database size={20} /> Section 2: Observation Attribution Breakdown
        </h3>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem', textAlign: 'left' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid #334155', color: '#94a3b8' }}>
                <th style={{ padding: '10px 14px' }}>Dataset Population</th>
                <th style={{ padding: '10px 14px' }}>Total Records</th>
                <th style={{ padding: '10px 14px' }}>Observed Depth Available</th>
                <th style={{ padding: '10px 14px' }}>Status</th>
                <th style={{ padding: '10px 14px' }}>Validation Usage</th>
              </tr>
            </thead>
            <tbody>
              <tr style={{ borderBottom: '1px solid #1e293b' }}>
                <td style={{ padding: '12px 14px', fontWeight: '600' }}>Chennai_2015</td>
                <td style={{ padding: '12px 14px' }}>753 records</td>
                <td style={{ padding: '12px 14px', color: '#f97316' }}>0 observed depth</td>
                <td style={{ padding: '12px 14px' }}><span style={{ color: '#ef4444', fontWeight: 'bold' }}>NOT_COMPUTABLE</span></td>
                <td style={{ padding: '12px 14px', color: '#94a3b8' }}>Categorical records only (no depth data)</td>
              </tr>
              <tr style={{ borderBottom: '1px solid #1e293b' }}>
                <td style={{ padding: '12px 14px', fontWeight: '600' }}>UNKNOWN</td>
                <td style={{ padding: '12px 14px' }}>192 records</td>
                <td style={{ padding: '12px 14px', color: '#38bdf8' }}>192 observed depth</td>
                <td style={{ padding: '12px 14px' }}><span style={{ color: '#38bdf8', fontWeight: 'bold' }}>AVAILABLE</span></td>
                <td style={{ padding: '12px 14px', color: '#94a3b8' }}>Spatial depth comparison only</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div style={{ marginTop: '14px', padding: '12px', background: 'rgba(56, 189, 248, 0.05)', border: '1px solid rgba(56, 189, 248, 0.2)', borderRadius: '6px', fontSize: '0.85rem', color: '#cbd5e1' }}>
          <Info size={16} style={{ display: 'inline', marginRight: '6px', color: '#38bdf8' }} />
          <strong>Notice:</strong> The 192 depth observations used for spatial depth comparisons have unknown event attribution and cannot be interpreted as a 2015 event-specific validation.
        </div>
      </div>

      {/* SECTION 3: UNKNOWN-EVENT SPATIAL DEPTH COMPARISON */}
      <div style={{ background: '#0f172a', border: '1px solid #334155', borderRadius: '12px', padding: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '8px' }}>
          <h3 style={{ margin: 0, fontSize: '1.1rem', color: '#38bdf8', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <BarChart2 size={20} /> Section 3: UNKNOWN-EVENT SPATIAL DEPTH COMPARISON
          </h3>
          <span style={{ fontSize: '0.8rem', background: '#1e293b', border: '1px solid #334155', padding: '4px 10px', borderRadius: '4px', color: '#94a3b8' }}>
            Metric Population: <strong>UNKNOWN_EVENT_DEPTH_OBSERVATIONS</strong>
          </span>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
          <div style={{ background: '#1e293b', padding: '16px', borderRadius: '8px', border: '1px solid #334155' }}>
            <div style={{ color: '#94a3b8', fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>MAE</div>
            <div style={{ fontSize: '1.6rem', fontWeight: '700', color: '#f8fafc', marginTop: '4px' }}>25.242 cm</div>
            <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '4px' }}>Mean Absolute Error</div>
          </div>
          <div style={{ background: '#1e293b', padding: '16px', borderRadius: '8px', border: '1px solid #334155' }}>
            <div style={{ color: '#94a3b8', fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>RMSE</div>
            <div style={{ fontSize: '1.6rem', fontWeight: '700', color: '#f8fafc', marginTop: '4px' }}>31.186 cm</div>
            <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '4px' }}>Root Mean Square Error</div>
          </div>
          <div style={{ background: '#1e293b', padding: '16px', borderRadius: '8px', border: '1px solid #334155' }}>
            <div style={{ color: '#94a3b8', fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Bias</div>
            <div style={{ fontSize: '1.6rem', fontWeight: '700', color: '#f8fafc', marginTop: '4px' }}>-25.242 cm</div>
            <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '4px' }}>Model Mean Bias</div>
          </div>
          <div style={{ background: '#1e293b', padding: '16px', borderRadius: '8px', border: '1px solid #334155' }}>
            <div style={{ color: '#94a3b8', fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Median Absolute Error</div>
            <div style={{ fontSize: '1.6rem', fontWeight: '700', color: '#f8fafc', marginTop: '4px' }}>21.41 cm</div>
            <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '4px' }}>Median Absolute Error</div>
          </div>
          <div style={{ background: '#1e293b', padding: '16px', borderRadius: '8px', border: '1px solid #334155' }}>
            <div style={{ color: '#94a3b8', fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Samples</div>
            <div style={{ fontSize: '1.6rem', fontWeight: '700', color: '#38bdf8', marginTop: '4px' }}>192</div>
            <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '4px' }}>Valid Comparisons</div>
          </div>
        </div>
      </div>

      {/* SECTION 4: NASA GPM IMERG RAINFALL REPLAY CHART */}
      <div style={{ background: '#0f172a', border: '1px solid #334155', borderRadius: '12px', padding: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '8px' }}>
          <div>
            <h3 style={{ margin: 0, fontSize: '1.1rem', color: '#38bdf8' }}>
              Section 4: NASA GPM IMERG Historical Forcing — Available Data
            </h3>
            <p style={{ margin: '4px 0 0 0', color: '#94a3b8', fontSize: '0.85rem' }}>
              Historical precipitation timeseries replay using stored GPM_3IMERGHH V07B dataset.
            </p>
          </div>
          <div style={{ display: 'flex', gap: '12px', fontSize: '0.8rem', background: '#1e293b', padding: '6px 12px', borderRadius: '6px', border: '1px solid #334155' }}>
            <div>Forcing: <strong>128 / 241</strong></div>
            <div>Missing: <strong>113</strong></div>
            <div>Replay timestep: <strong>30 minutes</strong></div>
          </div>
        </div>

        <div style={{ width: '100%', height: 280, minWidth: 0 }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="timestamp" stroke="#94a3b8" tick={{ fontSize: 11 }} />
              <YAxis stroke="#94a3b8" label={{ value: 'Rainfall (mm/hr)', angle: -90, position: 'insideLeft', fill: '#94a3b8', style: { fontSize: 12 } }} />
              <Tooltip 
                contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', borderRadius: '6px', color: '#f8fafc' }}
                formatter={(val) => [`${val !== null ? val.toFixed(2) : 'Missing'} mm/hr`, 'Rainfall']}
              />
              <Line 
                type="monotone" 
                dataKey="rainfall" 
                stroke="#38bdf8" 
                strokeWidth={2} 
                dot={false}
                connectNulls={false} 
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* SECTION 5: MODELLED HISTORICAL FLOOD-DEPTH REPLAY CHART */}
      <div style={{ background: '#0f172a', border: '1px solid #334155', borderRadius: '12px', padding: '20px' }}>
        <div style={{ marginBottom: '16px' }}>
          <h3 style={{ margin: 0, fontSize: '1.1rem', color: '#f59e0b' }}>
            Section 5: MODELLED Historical Flood-Depth Replay Chart
          </h3>
          <p style={{ margin: '4px 0 0 0', color: '#94a3b8', fontSize: '0.85rem' }}>
            Chronological flood depth outputs produced by FloodModelService under stored historical forcing.
          </p>
        </div>

        <div style={{ width: '100%', height: 280, minWidth: 0 }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="timestamp" stroke="#94a3b8" tick={{ fontSize: 11 }} />
              <YAxis stroke="#94a3b8" label={{ value: 'Modelled Depth (cm)', angle: -90, position: 'insideLeft', fill: '#94a3b8', style: { fontSize: 12 } }} />
              <Tooltip 
                contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', borderRadius: '6px', color: '#f8fafc' }}
                formatter={(val) => [`${val !== null ? val.toFixed(2) : 'Missing'} cm`, 'MODELLED Flood Depth']}
              />
              <Line 
                type="monotone" 
                dataKey="modelDepth" 
                stroke="#f59e0b" 
                strokeWidth={2} 
                dot={false}
                connectNulls={false} 
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* SECTION 6: WHY THIS IS NOT YET VALIDATED */}
      <div style={{ background: '#0f172a', border: '1px solid #334155', borderRadius: '12px', padding: '20px' }}>
        <h3 style={{ margin: '0 0 16px 0', fontSize: '1.1rem', color: '#ef4444', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <AlertTriangle size={20} /> Section 6: WHY THIS IS NOT YET VALIDATED
        </h3>
        <ul style={{ margin: 0, paddingLeft: '20px', color: '#cbd5e1', fontSize: '0.9rem', display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <li>
            <strong>Zero 2015 Observed Depth Records:</strong> The 753 Chennai_2015 attributed benchmark observations contain zero numerical depth measurements (categorical flood presence only).
          </li>
          <li>
            <strong>Unknown Event Attribution:</strong> The 192 depth observations used for spatial comparison belong to UNKNOWN events and lack sub-daily timestamps.
          </li>
          <li>
            <strong>Incomplete Historical Forcing:</strong> Only 128 of 241 expected 30-minute IMERG timesteps are available for the replay window (113 timesteps missing).
          </li>
          <li>
            <strong>Uncalibrated Hydrologic Parameters:</strong> Impervious surface fraction (0.85) and runoff coefficients are baseline spatial heuristics and have not undergone historical tuning.
          </li>
          <li>
            <strong>Uncoupled Drainage Capacity:</strong> Stormwater drain hydraulic capacity is UNKNOWN and provides 0.0 cm numerical depth reduction in the flood model.
          </li>
        </ul>
      </div>

      {/* SECTION 7: DATA PROVENANCE */}
      <div style={{ background: '#0f172a', border: '1px solid #334155', borderRadius: '12px', padding: '20px' }}>
        <h3 style={{ margin: '0 0 16px 0', fontSize: '1.1rem', color: '#38bdf8', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Layers size={20} /> Section 7: Data Provenance
        </h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '16px', fontSize: '0.85rem' }}>
          <div style={{ background: '#1e293b', padding: '12px 16px', borderRadius: '8px', border: '1px solid #334155' }}>
            <div style={{ color: '#94a3b8', textTransform: 'uppercase', fontSize: '0.75rem' }}>Forcing Dataset</div>
            <div style={{ fontWeight: '600', color: '#f8fafc', marginTop: '4px' }}>NASA GES DISC GPM_3IMERGHH V07B</div>
          </div>
          <div style={{ background: '#1e293b', padding: '12px 16px', borderRadius: '8px', border: '1px solid #334155' }}>
            <div style={{ color: '#94a3b8', textTransform: 'uppercase', fontSize: '0.75rem' }}>Observation Sources</div>
            <div style={{ fontWeight: '600', color: '#f8fafc', marginTop: '4px' }}>OpenCity / GCC / Crowd-Sourced</div>
          </div>
          <div style={{ background: '#1e293b', padding: '12px 16px', borderRadius: '8px', border: '1px solid #334155' }}>
            <div style={{ color: '#94a3b8', textTransform: 'uppercase', fontSize: '0.75rem' }}>Model Version</div>
            <div style={{ fontWeight: '600', color: '#f8fafc', marginTop: '4px' }}>v3-spatial-heuristic (baseline-v1)</div>
          </div>
          <div style={{ background: '#1e293b', padding: '12px 16px', borderRadius: '8px', border: '1px solid #334155' }}>
            <div style={{ color: '#94a3b8', textTransform: 'uppercase', fontSize: '0.75rem' }}>Spatial Tolerance</div>
            <div style={{ fontWeight: '600', color: '#f8fafc', marginTop: '4px' }}>50.0m (Point-to-Grid Euclidean)</div>
          </div>
        </div>
      </div>

    </div>
  );
}
