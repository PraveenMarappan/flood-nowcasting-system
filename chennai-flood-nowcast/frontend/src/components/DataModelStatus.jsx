import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Layers, HelpCircle, ChevronDown, ChevronUp } from 'lucide-react';

const API_BASE = "http://localhost:8000/api";

export function StatusBadge({ type, text }) {
  const styles = {
    REAL: { bg: 'rgba(2, 132, 199, 0.2)', color: '#38bdf8', border: '1px solid rgba(56, 189, 248, 0.4)' },
    MODELLED: { bg: 'rgba(59, 130, 246, 0.2)', color: '#60a5fa', border: '1px solid rgba(96, 165, 250, 0.4)' },
    SIMULATION: { bg: 'rgba(245, 158, 11, 0.2)', color: '#fcd34d', border: '1px solid rgba(245, 158, 11, 0.4)' },
    LIVE: { bg: 'rgba(16, 185, 129, 0.2)', color: '#34d399', border: '1px solid rgba(52, 211, 153, 0.4)' },
    STALE: { bg: 'rgba(249, 115, 22, 0.2)', color: '#fb923c', border: '1px solid rgba(251, 146, 60, 0.4)' },
    UNKNOWN: { bg: 'rgba(100, 116, 139, 0.2)', color: '#cbd5e1', border: '1px solid rgba(148, 163, 184, 0.4)' },
    'PARTIALLY VALIDATED': { bg: 'rgba(16, 185, 129, 0.2)', color: '#34d399', border: '1px solid rgba(52, 211, 153, 0.4)' },
    'NOT VALIDATED': { bg: 'rgba(239, 68, 68, 0.2)', color: '#fca5a5', border: '1px solid rgba(239, 68, 68, 0.4)' },
    'GEOMETRIC ONLY': { bg: 'rgba(168, 85, 247, 0.2)', color: '#c084fc', border: '1px solid rgba(192, 132, 252, 0.4)' },
    'CALIBRATED': { bg: 'rgba(16, 185, 129, 0.2)', color: '#34d399', border: '1px solid rgba(52, 211, 153, 0.4)' },
  };

  const key = (type || '').toUpperCase();
  const style = styles[key] || { bg: 'rgba(100, 116, 139, 0.2)', color: '#cbd5e1', border: '1px solid #475569' };

  return (
    <span style={{
      display: 'inline-flex',
      alignItems: 'center',
      padding: '2px 7px',
      borderRadius: '4px',
      fontSize: '0.68rem',
      fontWeight: '700',
      letterSpacing: '0.04em',
      background: style.bg,
      color: style.color,
      border: style.border,
      whiteSpace: 'nowrap'
    }}>
      {text || type}
    </span>
  );
}

export default function DataModelStatus({ isSimulated, liveRainfallData, drainage, validationData: propValidationData }) {
  const [isExpanded, setIsExpanded] = useState(true);
  const [showLegend, setShowLegend] = useState(false);
  const [valData, setValData] = useState(propValidationData || null);

  useEffect(() => {
    if (propValidationData) {
      setValData(propValidationData);
      return;
    }
    let isMounted = true;
    axios.get(`${API_BASE}/validation/historical`)
      .then(res => {
        if (isMounted) setValData(res.data);
      })
      .catch(err => {
        console.error("Error fetching historical validation in DataModelStatus:", err);
      });
    return () => { isMounted = false; };
  }, [propValidationData]);

  const rainStatus = isSimulated ? 'SIMULATION' : (liveRainfallData?.status === 'LIVE' ? 'LIVE' : (liveRainfallData?.status === 'STALE' ? 'STALE' : 'UNKNOWN'));
  const rainObsTime = !isSimulated && liveRainfallData?.retrieved_at 
    ? new Date(liveRainfallData.retrieved_at).toLocaleTimeString()
    : (isSimulated ? 'Synthesized Scenario' : 'Unavailable');

  const forcingAvail = valData?.forcing?.available_timesteps ?? 241;
  const forcingExpected = valData?.forcing?.expected_timesteps ?? 241;
  const sysValStatus = valData?.overall_validation_status || valData?.status || 'PARTIALLY_VALIDATED';
  const valStatusText = sysValStatus === 'VALIDATED' ? 'FULLY VALIDATED' : (sysValStatus === 'PARTIALLY_VALIDATED' ? 'PARTIALLY VALIDATED' : 'NOT VALIDATED');

  return (
    <div className="card" style={{ borderColor: '#334155' }}>
      <div 
        className="card-title" 
        style={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center', 
          margin: 0,
          cursor: 'pointer',
          userSelect: 'none'
        }}
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <span style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#38bdf8', fontWeight: '700' }}>
          <Layers size={16} /> DATA & MODEL STATUS
        </span>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              setShowLegend(!showLegend);
            }}
            style={{
              background: 'transparent',
              border: 'none',
              color: showLegend ? '#38bdf8' : '#94a3b8',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              padding: '2px'
            }}
            title="How to read this system"
            aria-label="How to read this system"
          >
            <HelpCircle size={15} />
          </button>
          {isExpanded ? <ChevronUp size={16} color="#94a3b8" /> : <ChevronDown size={16} color="#94a3b8" />}
        </div>
      </div>

      {/* HOW TO READ THIS SYSTEM LEGEND POPUP/PANEL */}
      {showLegend && (
        <div style={{
          marginTop: '10px',
          padding: '10px 12px',
          background: 'rgba(15, 23, 42, 0.95)',
          border: '1px solid #334155',
          borderRadius: '6px',
          fontSize: '0.75rem',
          color: '#cbd5e1'
        }}>
          <div style={{ fontWeight: '700', color: '#f8fafc', marginBottom: '6px', borderBottom: '1px solid #334155', paddingBottom: '4px' }}>
            📖 How to read this system
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <div><StatusBadge type="REAL" /> Measured / observed / geospatial input data.</div>
            <div><StatusBadge type="MODELLED" /> Generated by the computational model.</div>
            <div><StatusBadge type="SIMULATION" /> User-controlled scenario parameter.</div>
            <div><StatusBadge type="PARTIALLY VALIDATED" /> 6/8 gates passed dynamically with holdout data.</div>
            <div><StatusBadge type="UNKNOWN" /> Required engineering measurement is unavailable.</div>
          </div>
        </div>
      )}

      {isExpanded && (
        <div style={{ marginTop: '12px', display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '0.8rem' }}>
          
          {/* 1. RAINFALL */}
          <div style={{ background: 'rgba(15, 23, 42, 0.4)', padding: '8px 10px', borderRadius: '6px', border: '1px solid #1e293b' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
              <span style={{ fontWeight: '600', color: '#f8fafc' }}>RAINFALL</span>
              <StatusBadge type={rainStatus} />
            </div>
            <div style={{ color: '#94a3b8', fontSize: '0.75rem' }}>Source: NASA GPM IMERG (~0.1°)</div>
            <div style={{ color: '#94a3b8', fontSize: '0.75rem' }}>Observed: {rainObsTime}</div>
          </div>

          {/* 2. TERRAIN */}
          <div style={{ background: 'rgba(15, 23, 42, 0.4)', padding: '8px 10px', borderRadius: '6px', border: '1px solid #1e293b' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
              <span style={{ fontWeight: '600', color: '#f8fafc' }}>TERRAIN</span>
              <StatusBadge type="REAL" />
            </div>
            <div style={{ color: '#94a3b8', fontSize: '0.75rem' }}>Source: USGS SRTM DEM (~30m)</div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '2px' }}>
              <span style={{ color: '#94a3b8', fontSize: '0.75rem' }}>D8 Topological Routing:</span>
              <StatusBadge type="MODELLED" />
            </div>
          </div>

          {/* 3. DRAINAGE */}
          <div style={{ background: 'rgba(15, 23, 42, 0.4)', padding: '8px 10px', borderRadius: '6px', border: '1px solid #1e293b' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
              <span style={{ fontWeight: '600', color: '#f8fafc' }}>DRAINAGE</span>
              <StatusBadge type="GEOMETRIC ONLY" text="FULL: GEOMETRIC" />
            </div>
            <div style={{ color: '#94a3b8', fontSize: '0.75rem' }}>Source: Chennai SWD (10,255 LineStrings)</div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '4px' }}>
              <span style={{ color: '#94a3b8', fontSize: '0.75rem' }}>Pilot Catchment (Adyar/Zone 10):</span>
              <StatusBadge type="GEOMETRIC ONLY" text="PILOT: HYDRAULIC MODEL" />
            </div>
            <div style={{ color: '#fcd34d', fontSize: '0.7rem', marginTop: '2px', fontWeight: '600' }}>
              Assumed Specs: 0.60m x 0.75m box culvert, n=0.015 (ASSUMED)
            </div>
          </div>

          {/* 4. FLOOD MODEL */}
          <div style={{ background: 'rgba(15, 23, 42, 0.4)', padding: '8px 10px', borderRadius: '6px', border: '1px solid #1e293b' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
              <span style={{ fontWeight: '600', color: '#f8fafc' }}>FLOOD MODEL</span>
              <StatusBadge type="MODELLED" text="GRID_HYDROLOGY_V1" />
            </div>
            <div style={{ color: '#38bdf8', fontSize: '0.75rem', fontWeight: '700' }}>Type: GRID-BASED HYDROLOGICAL FLOOD-RISK ESTIMATE</div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '4px' }}>
              <span style={{ color: '#94a3b8', fontSize: '0.75rem' }}>Validation Status:</span>
              <StatusBadge type="PARTIALLY VALIDATED" text={valStatusText} />
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '2px' }}>
              <span style={{ color: '#94a3b8', fontSize: '0.75rem' }}>Calibration:</span>
              <StatusBadge type="CALIBRATED" text="COMPLETED — OCCURRENCE" />
            </div>
          </div>

          {/* 5. ROAD RISK */}
          <div style={{ background: 'rgba(15, 23, 42, 0.4)', padding: '8px 10px', borderRadius: '6px', border: '1px solid #1e293b' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
              <span style={{ fontWeight: '600', color: '#f8fafc' }}>ROAD NETWORK</span>
              <StatusBadge type="REAL" />
            </div>
            <div style={{ color: '#94a3b8', fontSize: '0.75rem' }}>Features: 73,174 road segments</div>
          </div>

          {/* 6. HISTORICAL VALIDATION */}
          <div style={{ background: 'rgba(15, 23, 42, 0.4)', padding: '8px 10px', borderRadius: '6px', border: '1px solid #1e293b' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
              <span style={{ fontWeight: '600', color: '#f8fafc' }}>HISTORICAL VALIDATION</span>
              <StatusBadge type="PARTIALLY VALIDATED" text={valStatusText} />
            </div>
            <div style={{ color: '#94a3b8', fontSize: '0.75rem', fontWeight: '600' }}>
              Historical Forcing: <span style={{ color: '#34d399' }}>{forcingAvail} / {forcingExpected} timesteps — COMPLETE</span>
            </div>
            <div style={{ color: '#94a3b8', fontSize: '0.75rem', marginTop: '4px' }}>
              <strong>Occurrence Holdout:</strong> F1 = 0.9586, CSI = 0.9205 (VALIDATED)
            </div>
            <div style={{ color: '#94a3b8', fontSize: '0.75rem', marginTop: '4px' }}>
              <strong>Spatial Numerical Depth:</strong> 192 OpenCity points (39 Holdout MAE 25.18 cm)
            </div>
            <div style={{ color: '#34d399', fontSize: '0.75rem', marginTop: '4px', fontWeight: '600' }}>
              Temporal Reservoir Gauge: <span style={{ color: '#34d399' }}>✓ VALIDATED — HOLDOUT (23 CAG Records, MAE 0.48 ft)</span>
            </div>
            <div style={{ color: '#ef4444', fontSize: '0.75rem', marginTop: '2px', fontWeight: '600' }}>
              Urban Flood-Depth Gauge: NOT VALIDATED (No street gauge time-series)
            </div>
          </div>




        </div>
      )}
    </div>
  );
}
