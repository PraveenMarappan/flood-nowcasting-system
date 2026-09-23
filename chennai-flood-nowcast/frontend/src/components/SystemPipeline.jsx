import React from 'react';
import { Cpu } from 'lucide-react';

export default function SystemPipeline() {
  const steps = [
    { title: 'NASA GPM IMERG', desc: 'Regional Rainfall Input' },
    { title: 'RUNOFF ESTIMATION', desc: 'Impervious Curve Method' },
    { title: 'TERRAIN / FLOW', desc: 'USGS SRTM D8 Factors' },
    { title: 'DRAINAGE DIAGNOSTICS', desc: 'SWD 2023 Geometry Only' },
    { title: 'FLOOD-RISK ESTIMATE', desc: 'Spatial Depth Heuristic' },
    { title: 'ROAD-RISK MAP', desc: 'Street-Level Overlay' },
    { title: 'DECISION SUPPORT', desc: 'Operational Nowcasting' }
  ];

  return (
    <div className="card" style={{ borderColor: '#334155' }}>
      <div className="card-title" style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#38bdf8', fontWeight: '700' }}>
        <Cpu size={15} /> HOW THE SYSTEM WORKS
      </div>
      
      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginTop: '10px' }}>
        {steps.map((step, idx) => (
          <React.Fragment key={idx}>
            <div style={{ 
              background: 'rgba(15, 23, 42, 0.6)', 
              border: '1px solid #1e293b', 
              borderRadius: '6px', 
              padding: '6px 10px',
              display: 'flex',
              justify: 'space-between',
              alignItems: 'center'
            }}>
              <div>
                <div style={{ fontSize: '0.75rem', fontWeight: '700', color: '#f8fafc' }}>{step.title}</div>
                <div style={{ fontSize: '0.68rem', color: '#94a3b8' }}>{step.desc}</div>
              </div>
              <span style={{ fontSize: '0.68rem', fontWeight: '700', color: '#38bdf8', background: 'rgba(56,189,248,0.1)', padding: '1px 6px', borderRadius: '4px' }}>
                Step {idx + 1}
              </span>
            </div>
            {idx < steps.length - 1 && (
              <div style={{ display: 'flex', justifyContent: 'center', color: '#475569', margin: '-2px 0' }}>
                ↓
              </div>
            )}
          </React.Fragment>
        ))}
      </div>

      <div style={{ fontSize: '0.7rem', color: '#64748b', fontStyle: 'italic', marginTop: '10px', borderTop: '1px solid #334155', paddingTop: '6px' }}>
        Current drainage data provides geometry; hydraulic capacity parameters are unavailable.
      </div>
    </div>
  );
}
