import React, { useState } from 'react';
import { AlertCircle, ChevronDown, ChevronUp } from 'lucide-react';

export default function ModelLimitations() {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="card" style={{ borderColor: '#334155' }}>
      <div 
        className="card-title" 
        style={{ 
          display: 'flex', 
          justify: 'space-between', 
          alignItems: 'center', 
          margin: 0, 
          cursor: 'pointer',
          userSelect: 'none'
        }}
        onClick={() => setIsOpen(!isOpen)}
      >
        <span style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#f59e0b', fontWeight: '700' }}>
          <AlertCircle size={15} /> MODEL LIMITATIONS
        </span>
        {isOpen ? <ChevronUp size={16} color="#94a3b8" /> : <ChevronDown size={16} color="#94a3b8" />}
      </div>

      {isOpen && (
        <div style={{ marginTop: '10px', display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '0.75rem', color: '#cbd5e1' }}>
          <div style={{ padding: '6px 8px', background: 'rgba(15, 23, 42, 0.5)', borderRadius: '4px', borderLeft: '3px solid #f59e0b' }}>
            1. NASA GPM IMERG rainfall has approximately 0.1° (~11 km) spatial resolution and represents grid-cell averages, not micro-gauge point rainfall.
          </div>
          <div style={{ padding: '6px 8px', background: 'rgba(15, 23, 42, 0.5)', borderRadius: '4px', borderLeft: '3px solid #f59e0b' }}>
            2. Stormwater drain dataset provides 10,255 LineString geometries used for spatial proximity diagnostics; pipe diameters and 1D hydraulic cross-sections require engineering data.
          </div>
          <div style={{ padding: '6px 8px', background: 'rgba(15, 23, 42, 0.5)', borderRadius: '4px', borderLeft: '3px solid #f59e0b' }}>
            3. Flood depth estimates are produced by GRID_HYDROLOGY_V1 (grid-based hydrological runoff excess, SRTM D8 flow accumulation, and ponding scaling).
          </div>
          <div style={{ padding: '6px 8px', background: 'rgba(15, 23, 42, 0.5)', borderRadius: '4px', borderLeft: '3px solid #f59e0b' }}>
            4. Forcing, terrain D8 routing, occurrence calibration, 80/20 holdout validation, road risk, nowcast horizons, and warning triggers are VALIDATED. Sub-daily numerical flood depth gauge records remain an explicit blocker for continuous numerical depth validation.
          </div>
          <div style={{ padding: '6px 8px', background: 'rgba(15, 23, 42, 0.5)', borderRadius: '4px', borderLeft: '3px solid #f59e0b' }}>
            5. Nowcasting results should be interpreted as scientific decision-support estimates for emergency routing and disaster response.
          </div>
        </div>
      )}
    </div>
  );
}
