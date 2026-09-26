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
  Clock,
  ShieldAlert,
  Activity,
  Droplet,
  Compass
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

  // Memoize chart data transformation for all 241 observations
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
  const depthVal = data.depth_validation || metrics.depth_validation || {};
  const forcing = data.forcing || metrics.forcing || {};

  return (
    <div style={{ flex: 1, overflowY: 'auto', width: '100%', padding: '24px', maxWidth: '1400px', margin: '0 auto', color: '#f8fafc', display: 'flex', flexDirection: 'column', gap: '24px' }}>
      
      {/* SECTION 1: MAIN VALIDATION STATUS BANNER */}
      <div style={{
        background: 'linear-gradient(135deg, rgba(239, 68, 68, 0.15) 0%, rgba(185, 28, 28, 0.25) 100%)',
        border: '1px solid #ef4444',
        borderRadius: '12px',
        padding: '20px 24px',
        boxShadow: '0 4px 20px rgba(239, 68, 68, 0.15)',
        display: 'flex',
        flexDirection: 'column',
        gap: '16px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
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
              <p style={{ margin: '4px 0 0 0', color: '#cbd5e1', fontSize: '0.9rem', maxWidth: '950px', lineHeight: '1.5' }}>
                Historical model validation has not been established because the available Chennai_2015 observations contain no numerical flood-depth measurements and the available numerical-depth observations have unknown event attribution. The historical rainfall forcing and model replay are complete and are provided for diagnostic evaluation.
              </p>
            </div>
          </div>
          <div style={{ display: 'flex', gap: '12px', fontSize: '0.85rem' }}>
            <span style={{ background: 'rgba(16, 185, 129, 0.2)', color: '#34d399', padding: '6px 12px', borderRadius: '6px', border: '1px solid rgba(16, 185, 129, 0.4)', fontWeight: '600' }}>
              Historical Forcing: {forcing.available_timesteps ?? 241} / {forcing.expected_timesteps ?? 241} (100% COMPLETE)
            </span>
            <span style={{ background: 'rgba(56, 189, 248, 0.15)', color: '#38bdf8', padding: '6px 12px', borderRadius: '6px', border: '1px solid rgba(56, 189, 248, 0.3)', fontWeight: '600' }}>
              Model: GRID_HYDROLOGY_V1
            </span>
          </div>
        </div>
        <div style={{ fontSize: '0.85rem', color: '#f8fafc', background: 'rgba(0,0,0,0.2)', padding: '10px 14px', borderRadius: '6px', border: '1px solid rgba(255,255,255,0.05)' }}>
          <strong>Scientific Notice:</strong> Independent historical validation has not been established.
        </div>
      </div>

      {/* DATA STATUS CARDS (8 SEPARATE CARDS) */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px' }}>
        <div style={{ background: '#0f172a', border: '1px solid #334155', borderRadius: '10px', padding: '16px' }}>
          <div style={{ color: '#94a3b8', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Rainfall Forcing</div>
          <div style={{ fontSize: '1.25rem', fontWeight: '700', color: '#34d399', marginTop: '4px' }}>241 / 241</div>
          <div style={{ fontSize: '0.8rem', color: '#34d399', fontWeight: '600', marginTop: '2px' }}>100% COMPLETE</div>
        </div>

        <div style={{ background: '#0f172a', border: '1px solid #334155', borderRadius: '10px', padding: '16px' }}>
          <div style={{ color: '#94a3b8', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Historical Replay</div>
          <div style={{ fontSize: '1.25rem', fontWeight: '700', color: '#34d399', marginTop: '4px' }}>241 / 241</div>
          <div style={{ fontSize: '0.8rem', color: '#34d399', fontWeight: '600', marginTop: '2px' }}>COMPLETE</div>
        </div>

        <div style={{ background: '#0f172a', border: '1px solid #334155', borderRadius: '10px', padding: '16px' }}>
          <div style={{ color: '#94a3b8', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>2015 FLOOD-DEPTH MEASUREMENTS</div>
          <div style={{ fontSize: '1.25rem', fontWeight: '700', color: '#f97316', marginTop: '4px' }}>0 numerical records</div>
          <div style={{ fontSize: '0.8rem', color: '#f97316', fontWeight: '600', marginTop: '2px' }}>SOURCE CONTAINS OCCURRENCE LOCATIONS ONLY</div>
        </div>

        <div style={{ background: '#0f172a', border: '1px solid #334155', borderRadius: '10px', padding: '16px' }}>
          <div style={{ color: '#94a3b8', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>UNKNOWN Depth Observations</div>
          <div style={{ fontSize: '1.25rem', fontWeight: '700', color: '#38bdf8', marginTop: '4px' }}>192 records</div>
          <div style={{ fontSize: '0.8rem', color: '#38bdf8', fontWeight: '600', marginTop: '2px' }}>DIAGNOSTIC ONLY</div>
        </div>

        <div style={{ background: '#0f172a', border: '1px solid #334155', borderRadius: '10px', padding: '16px' }}>
          <div style={{ color: '#94a3b8', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Calibration</div>
          <div style={{ fontSize: '1.25rem', fontWeight: '700', color: '#cbd5e1', marginTop: '4px' }}>NOT COMPLETED</div>
          <div style={{ fontSize: '0.8rem', color: '#64748b', marginTop: '2px' }}>Baseline parameters used</div>
        </div>

        <div style={{ background: '#0f172a', border: '1px solid #334155', borderRadius: '10px', padding: '16px' }}>
          <div style={{ color: '#94a3b8', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Independent Validation</div>
          <div style={{ fontSize: '1.25rem', fontWeight: '700', color: '#ef4444', marginTop: '4px' }}>NOT AVAILABLE</div>
          <div style={{ fontSize: '0.8rem', color: '#ef4444', fontWeight: '600', marginTop: '2px' }}>Numerical depth measurements unavailable</div>
        </div>

        <div style={{ background: '#0f172a', border: '1px solid #334155', borderRadius: '10px', padding: '16px' }}>
          <div style={{ color: '#94a3b8', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Drainage Hydraulics</div>
          <div style={{ fontSize: '1.25rem', fontWeight: '700', color: '#f59e0b', marginTop: '4px' }}>UNAVAILABLE</div>
          <div style={{ fontSize: '0.8rem', color: '#f59e0b', marginTop: '2px' }}>Geometry only, 0.0cm reduction</div>
        </div>

        <div style={{ background: '#0f172a', border: '1px solid #ef4444', borderRadius: '10px', padding: '16px' }}>
          <div style={{ color: '#94a3b8', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Final Validation Status</div>
          <div style={{ fontSize: '1.15rem', fontWeight: '800', color: '#ef4444', marginTop: '4px' }}>COMPLETE BUT NOT VALIDATED</div>
          <div style={{ fontSize: '0.75rem', color: '#fca5a5', marginTop: '2px' }}>Strict scientific classification</div>
        </div>
      </div>

      {/* SECTION 2: OBSERVATION ATTRIBUTION BREAKDOWN */}
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
                <th style={{ padding: '10px 14px' }}>Numerical Depth Records</th>
                <th style={{ padding: '10px 14px' }}>Attribution Status</th>
                <th style={{ padding: '10px 14px' }}>Validation Usage</th>
              </tr>
            </thead>
            <tbody>
              <tr style={{ borderBottom: '1px solid #1e293b' }}>
                <td style={{ padding: '12px 14px', fontWeight: '600', color: '#f8fafc' }}>Chennai_2015</td>
                <td style={{ padding: '12px 14px' }}>753</td>
                <td style={{ padding: '12px 14px', color: '#f97316', fontWeight: '600' }}>0</td>
                <td style={{ padding: '12px 14px', color: '#34d399', fontWeight: '600' }}>EVENT-ATTRIBUTED</td>
                <td style={{ padding: '12px 14px', color: '#cbd5e1' }}>Categorical occurrence locations only</td>
              </tr>
              <tr style={{ borderBottom: '1px solid #1e293b' }}>
                <td style={{ padding: '12px 14px', fontWeight: '600', color: '#f8fafc' }}>UNKNOWN</td>
                <td style={{ padding: '12px 14px' }}>192</td>
                <td style={{ padding: '12px 14px', color: '#38bdf8', fontWeight: '600' }}>192</td>
                <td style={{ padding: '12px 14px', color: '#ef4444', fontWeight: '600' }}>EVENT UNKNOWN</td>
                <td style={{ padding: '12px 14px', color: '#cbd5e1' }}>Diagnostic spatial comparison only</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div style={{ marginTop: '14px', padding: '12px', background: 'rgba(255, 255, 255, 0.03)', border: '1px solid rgba(255, 255, 255, 0.08)', borderRadius: '6px', fontSize: '0.85rem', color: '#cbd5e1', display: 'flex', flexDirection: 'column', gap: '6px' }}>
          <div><strong>Observation Scientific Notice:</strong></div>
          <ul style={{ margin: '4px 0 0 0', paddingLeft: '20px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <li>The <code>Chennai_2015</code> observation dataset IS AVAILABLE and contains 753 event-attributed observations.</li>
            <li>These 753 observations provide categorical/location-based flood occurrence information.</li>
            <li>The source dataset contains 0 numerical flood-depth measurements.</li>
            <li>Therefore, the <code>Chennai_2015</code> records cannot be used for continuous numerical flood-depth validation.</li>
            <li>Only numerical flood-depth measurements are unavailable; the dataset itself is available.</li>
          </ul>
        </div>
        <div style={{ marginTop: '10px', padding: '12px', background: 'rgba(239, 68, 68, 0.08)', border: '1px solid rgba(239, 68, 68, 0.25)', borderRadius: '6px', fontSize: '0.85rem', color: '#fca5a5' }}>
          <AlertTriangle size={16} style={{ display: 'inline', marginRight: '6px', color: '#ef4444' }} />
          <strong>Attribution Safeguard:</strong> Numerical depth does not establish event attribution. The 192 UNKNOWN observations therefore must not be interpreted as validation of the 2015 event.
        </div>
      </div>

      {/* SECTION 3: DIAGNOSTIC — UNKNOWN-EVENT SPATIAL DEPTH COMPARISON */}
      <div style={{ background: '#0f172a', border: '1px solid #334155', borderRadius: '12px', padding: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px', flexWrap: 'wrap', gap: '12px' }}>
          <div>
            <h3 style={{ margin: 0, fontSize: '1.1rem', color: '#38bdf8', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <BarChart2 size={20} /> DIAGNOSTIC — UNKNOWN-EVENT SPATIAL DEPTH COMPARISON
            </h3>
            <p style={{ margin: '6px 0 0 0', color: '#cbd5e1', fontSize: '0.85rem', maxWidth: '900px' }}>
              These metrics are calculated from 192 numerical-depth observations with UNKNOWN event attribution. They are diagnostic spatial comparisons only and are NOT 2015 event-validation metrics.
            </p>
          </div>
          <span style={{ fontSize: '0.8rem', background: 'rgba(239, 68, 68, 0.2)', border: '1px solid #ef4444', color: '#fca5a5', padding: '6px 12px', borderRadius: '6px', fontWeight: '800' }}>
            NOT 2015 VALIDATION
          </span>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px', marginTop: '16px' }}>
          <div style={{ background: '#1e293b', padding: '16px', borderRadius: '8px', border: '1px solid #334155' }}>
            <div style={{ color: '#94a3b8', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>MAE</div>
            <div style={{ fontSize: '1.6rem', fontWeight: '700', color: '#f8fafc', marginTop: '4px' }}>25.211 cm</div>
            <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '4px' }}>Mean Absolute Error</div>
          </div>
          <div style={{ background: '#1e293b', padding: '16px', borderRadius: '8px', border: '1px solid #334155' }}>
            <div style={{ color: '#94a3b8', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>RMSE</div>
            <div style={{ fontSize: '1.6rem', fontWeight: '700', color: '#f8fafc', marginTop: '4px' }}>31.161 cm</div>
            <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '4px' }}>Root Mean Square Error</div>
          </div>
          <div style={{ background: '#1e293b', padding: '16px', borderRadius: '8px', border: '1px solid #334155' }}>
            <div style={{ color: '#94a3b8', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Bias</div>
            <div style={{ fontSize: '1.6rem', fontWeight: '700', color: '#f8fafc', marginTop: '4px' }}>-25.211 cm</div>
            <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '4px' }}>Model Mean Bias</div>
          </div>
          <div style={{ background: '#1e293b', padding: '16px', borderRadius: '8px', border: '1px solid #334155' }}>
            <div style={{ color: '#94a3b8', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Median Absolute Error</div>
            <div style={{ fontSize: '1.6rem', fontWeight: '700', color: '#f8fafc', marginTop: '4px' }}>21.41 cm</div>
            <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '4px' }}>Median Absolute Error</div>
          </div>
          <div style={{ background: '#1e293b', padding: '16px', borderRadius: '8px', border: '1px solid #334155' }}>
            <div style={{ color: '#94a3b8', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Samples</div>
            <div style={{ fontSize: '1.6rem', fontWeight: '700', color: '#38bdf8', marginTop: '4px' }}>192</div>
            <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '4px' }}>Valid Comparisons</div>
          </div>
        </div>
      </div>

      {/* SECTION 4: NASA RAINFALL FORCING CHART */}
      <div style={{ background: '#0f172a', border: '1px solid #334155', borderRadius: '12px', padding: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px', flexWrap: 'wrap', gap: '8px' }}>
          <div>
            <h3 style={{ margin: 0, fontSize: '1.1rem', color: '#38bdf8' }}>
              Section 4: NASA GPM IMERG Historical Forcing — GPM_3IMERGHH V07B
            </h3>
            <p style={{ margin: '4px 0 0 0', color: '#cbd5e1', fontSize: '0.85rem' }}>
              Forcing completeness refers to availability of all 241 requested half-hourly IMERG timestamps. It does not imply model validation.
            </p>
          </div>
          <div style={{ display: 'flex', gap: '12px', fontSize: '0.8rem', background: '#1e293b', padding: '6px 12px', borderRadius: '6px', border: '1px solid #334155' }}>
            <div>Forcing: <strong>241 / 241 (100% COMPLETE)</strong></div>
            <div>Missing: <strong>0</strong></div>
            <div>Replay timestep: <strong>30 minutes</strong></div>
          </div>
        </div>

        <div style={{ width: '100%', height: 280, minWidth: 0 }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="timestamp" stroke="#94a3b8" tick={{ fontSize: 11 }} label={{ value: 'Time (UTC)', position: 'insideBottom', offset: -5, fill: '#94a3b8', style: { fontSize: 11 } }} />
              <YAxis stroke="#94a3b8" label={{ value: 'Rainfall Rate (mm/hr)', angle: -90, position: 'insideLeft', fill: '#94a3b8', style: { fontSize: 11 } }} />
              <Tooltip 
                contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', borderRadius: '6px', color: '#f8fafc' }}
                formatter={(val) => [`${val !== null ? val.toFixed(2) : 'Missing'} mm/hr`, 'NASA IMERG Rainfall Rate']}
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
        <div style={{ marginBottom: '12px' }}>
          <h3 style={{ margin: 0, fontSize: '1.1rem', color: '#f59e0b' }}>
            Section 5: MODELLED Historical Flood-Depth Replay — GRID_HYDROLOGY_V1
          </h3>
          <p style={{ margin: '4px 0 0 0', color: '#cbd5e1', fontSize: '0.85rem' }}>
            Chronological modelled flood-depth estimates produced by GRID_HYDROLOGY_V1 under the complete stored historical IMERG forcing. These are model outputs, not observed flood depths.
          </p>
        </div>

        <div style={{ width: '100%', height: 280, minWidth: 0 }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="timestamp" stroke="#94a3b8" tick={{ fontSize: 11 }} label={{ value: 'Time (UTC)', position: 'insideBottom', offset: -5, fill: '#94a3b8', style: { fontSize: 11 } }} />
              <YAxis stroke="#94a3b8" label={{ value: 'Modelled Flood Depth (cm)', angle: -90, position: 'insideLeft', fill: '#94a3b8', style: { fontSize: 11 } }} />
              <Tooltip 
                contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', borderRadius: '6px', color: '#f8fafc' }}
                formatter={(val) => [`${val !== null ? val.toFixed(2) : 'Missing'} cm`, 'Modelled Flood Depth']}
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
        <ol style={{ margin: 0, paddingLeft: '20px', color: '#cbd5e1', fontSize: '0.9rem', display: 'flex', flexDirection: 'column', gap: '12px', lineHeight: '1.5' }}>
          <li>
            <strong>2015 numerical depth data unavailable:</strong> The 753 Chennai_2015 records are event-attributed categorical observations, but contain 0 numerical flood-depth measurements.
          </li>
          <li>
            <strong>Unknown event attribution:</strong> The 192 numerical-depth observations have UNKNOWN event attribution and lack the sub-daily event timestamps required for event-specific validation.
          </li>
          <li>
            <strong>Complete forcing does not equal validation:</strong> The NASA IMERG historical forcing is complete at 241/241 timestamps and the historical replay is complete, but independent validation requires event-matched ground-truth observations.
          </li>
          <li>
            <strong>Uncalibrated parameters:</strong> GRID_HYDROLOGY_V1 currently uses baseline/assumed hydrological parameters, including the configured impervious-surface fraction (default 0.85 assumed baseline parameter) and runoff coefficients. These parameters have not been calibrated against event-matched observations.
          </li>
          <li>
            <strong>Drainage hydraulic coupling unavailable:</strong> The available stormwater-drain dataset provides drainage geometry but does not provide the engineering attributes required for hydraulic capacity modelling. Therefore hydraulic drainage coupling is unavailable and no numerical flood-depth reduction is applied.
          </li>
        </ol>
      </div>

      {/* SECTION 7: DATA PROVENANCE & TECHNICAL DETAILS */}
      <div style={{ background: '#0f172a', border: '1px solid #334155', borderRadius: '12px', padding: '20px' }}>
        <h3 style={{ margin: '0 0 16px 0', fontSize: '1.1rem', color: '#38bdf8', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Layers size={20} /> Section 7: Data Provenance & Model Specifications
        </h3>

        {/* PROVENANCE TABLE */}
        <div style={{ overflowX: 'auto', marginBottom: '20px' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem', textAlign: 'left' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid #334155', color: '#94a3b8' }}>
                <th style={{ padding: '10px 14px' }}>Component</th>
                <th style={{ padding: '10px 14px' }}>Source</th>
                <th style={{ padding: '10px 14px' }}>Status</th>
              </tr>
            </thead>
            <tbody>
              <tr style={{ borderBottom: '1px solid #1e293b' }}>
                <td style={{ padding: '10px 14px', fontWeight: '600' }}>Rainfall</td>
                <td style={{ padding: '10px 14px' }}>NASA GES DISC GPM_3IMERGHH V07B</td>
                <td style={{ padding: '10px 14px', color: '#34d399', fontWeight: '600' }}>REAL</td>
              </tr>
              <tr style={{ borderBottom: '1px solid #1e293b' }}>
                <td style={{ padding: '10px 14px', fontWeight: '600' }}>DEM</td>
                <td style={{ padding: '10px 14px' }}>USGS SRTM 1 Arc-Second</td>
                <td style={{ padding: '10px 14px', color: '#34d399', fontWeight: '600' }}>REAL</td>
              </tr>
              <tr style={{ borderBottom: '1px solid #1e293b' }}>
                <td style={{ padding: '10px 14px', fontWeight: '600' }}>Stormwater Drain Geometry</td>
                <td style={{ padding: '10px 14px' }}>OpenCity / Greater Chennai Corporation, 2023</td>
                <td style={{ padding: '10px 14px', color: '#34d399', fontWeight: '600' }}>REAL GEOMETRY</td>
              </tr>
              <tr style={{ borderBottom: '1px solid #1e293b' }}>
                <td style={{ padding: '10px 14px', fontWeight: '600' }}>Flood Observations</td>
                <td style={{ padding: '10px 14px' }}>Source-specific attribution from normalized observation dataset</td>
                <td style={{ padding: '10px 14px', color: '#34d399', fontWeight: '600' }}>REAL OBSERVATIONS</td>
              </tr>
              <tr style={{ borderBottom: '1px solid #1e293b' }}>
                <td style={{ padding: '10px 14px', fontWeight: '600' }}>Flood Model</td>
                <td style={{ padding: '10px 14px' }}>GRID_HYDROLOGY_V1</td>
                <td style={{ padding: '10px 14px', color: '#38bdf8', fontWeight: '600' }}>MODELLED</td>
              </tr>
            </tbody>
          </table>
        </div>

        {/* SPECIFICATIONS GRID */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '16px', fontSize: '0.85rem' }}>
          <div style={{ background: '#1e293b', padding: '12px 16px', borderRadius: '8px', border: '1px solid #334155' }}>
            <div style={{ color: '#94a3b8', textTransform: 'uppercase', fontSize: '0.75rem' }}>Model Version</div>
            <div style={{ fontWeight: '600', color: '#38bdf8', marginTop: '4px' }}>GRID_HYDROLOGY_V1</div>
            <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '2px' }}>Type: GRID-BASED HYDROLOGICAL FLOOD-DEPTH ESTIMATE</div>
          </div>
          <div style={{ background: '#1e293b', padding: '12px 16px', borderRadius: '8px', border: '1px solid #334155' }}>
            <div style={{ color: '#94a3b8', textTransform: 'uppercase', fontSize: '0.75rem' }}>Model Status</div>
            <div style={{ fontWeight: '600', color: '#ef4444', marginTop: '4px' }}>IMPLEMENTED — NOT VALIDATED</div>
            <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '2px' }}>Legacy Comparison: LEGACY_HEURISTIC</div>
          </div>
          <div style={{ background: '#1e293b', padding: '12px 16px', borderRadius: '8px', border: '1px solid #334155' }}>
            <div style={{ color: '#94a3b8', textTransform: 'uppercase', fontSize: '0.75rem' }}>Spatial Tolerance</div>
            <div style={{ fontWeight: '600', color: '#f8fafc', marginTop: '4px' }}>Spatial matching tolerance: 50 m</div>
            <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '2px' }}>Distance calculated in metres using geodesic WGS84 distance</div>
          </div>
          <div style={{ background: '#1e293b', padding: '12px 16px', borderRadius: '8px', border: '1px solid #334155' }}>
            <div style={{ color: '#94a3b8', textTransform: 'uppercase', fontSize: '0.75rem' }}>Drainage Status</div>
            <div style={{ fontWeight: '600', color: '#f59e0b', marginTop: '4px' }}>DRAINAGE_GEOMETRIC_ONLY</div>
            <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '2px' }}>Geometry: REAL | Hydraulics: UNAVAILABLE | Reduction: 0.0 cm</div>
          </div>
        </div>

        <div style={{ marginTop: '16px', padding: '12px', background: 'rgba(255, 255, 255, 0.03)', border: '1px solid rgba(255, 255, 255, 0.08)', borderRadius: '6px', fontSize: '0.85rem', color: '#cbd5e1', display: 'flex', flexDirection: 'column', gap: '6px' }}>
          <div><strong>Hydrological Model Note:</strong> GRID_HYDROLOGY_V1 is a hydrologically informed grid model using spatial excess rainfall, terrain-derived flow accumulation and empirical ponding/depth behaviour. It is not a calibrated full hydraulic solver. Topographic routing uses topographic D8 flow accumulation/routing.</div>
          <div><strong>Drainage Safeguard Note:</strong> 0.0 cm represents the model's intentional no-subtraction safeguard because hydraulic drainage capacity is unavailable. It does not mean real drains have zero influence on flooding.</div>
        </div>
      </div>

    </div>
  );
}
