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
            1. NASA GPM IMERG rainfall has approximately 0.1° spatial resolution and is not street-level rainfall.
          </div>
          <div style={{ padding: '6px 8px', background: 'rgba(15, 23, 42, 0.5)', borderRadius: '4px', borderLeft: '3px solid #f59e0b' }}>
            2. Current drainage data contains real storm-water-drain geometry, but hydraulic engineering parameters are unavailable.
          </div>
          <div style={{ padding: '6px 8px', background: 'rgba(15, 23, 42, 0.5)', borderRadius: '4px', borderLeft: '3px solid #f59e0b' }}>
            3. Current flood-depth estimates are spatial heuristic model outputs.
          </div>
          <div style={{ padding: '6px 8px', background: 'rgba(15, 23, 42, 0.5)', borderRadius: '4px', borderLeft: '3px solid #f59e0b' }}>
            4. Historical validation is not yet established because forcing coverage is incomplete and depth observations lack reliable event attribution.
          </div>
          <div style={{ padding: '6px 8px', background: 'rgba(15, 23, 42, 0.5)', borderRadius: '4px', borderLeft: '3px solid #f59e0b' }}>
            5. Results should be interpreted as decision-support estimates, not guaranteed flood predictions.
          </div>
        </div>
      )}
    </div>
  );
}
