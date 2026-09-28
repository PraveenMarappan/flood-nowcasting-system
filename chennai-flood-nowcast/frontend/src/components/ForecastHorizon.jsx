import React, { useState, useEffect, useRef } from 'react';

export default function ForecastHorizon({
  forecast,
  forecastOffset,
  setForecastOffset,
  getStatusColor,
  isCollapsed,
  setIsCollapsed,
  panelHeight,
  setPanelHeight,
  onResize
}) {
  const [isDragging, setIsDragging] = useState(false);
  const startYRef = useRef(0);
  const startHeightRef = useRef(0);
  const [isHoveredHandle, setIsHoveredHandle] = useState(false);
  const animFrameRef = useRef(null);

  const toggleCollapse = () => {
    const nextState = !isCollapsed;
    setIsCollapsed(nextState);
    try {
      localStorage.setItem('floodNowcast.forecastPanelCollapsed', String(nextState));
    } catch (e) {
      console.warn("Unable to save to localStorage", e);
    }
    if (onResize) onResize();
  };

  const handlePointerDown = (e) => {
    if (e.button !== 0) return;
    
    e.preventDefault();
    const startY = e.clientY;
    const isMobile = window.innerWidth < 768;
    const collapsedHeight = isMobile ? 44 : 46;
    const startHeight = isCollapsed ? collapsedHeight : panelHeight;
    
    startYRef.current = startY;
    startHeightRef.current = startHeight;
    setIsDragging(true);

    const handlePointerMove = (moveEvent) => {
      const deltaY = moveEvent.clientY - startYRef.current;
      const calculatedHeight = startHeightRef.current - deltaY;
      
      const minHeight = isMobile ? 44 : 46;
      const maxHeight = Math.min(300, Math.floor(window.innerHeight * 0.45));

      const clampedHeight = Math.max(minHeight, Math.min(maxHeight, calculatedHeight));

      if (clampedHeight <= minHeight + 15) {
        if (!isCollapsed) {
          setIsCollapsed(true);
          try {
            localStorage.setItem('floodNowcast.forecastPanelCollapsed', 'true');
          } catch (err) {}
        }
      } else {
        if (isCollapsed) {
          setIsCollapsed(false);
          try {
            localStorage.setItem('floodNowcast.forecastPanelCollapsed', 'false');
          } catch (err) {}
        }
        setPanelHeight(clampedHeight);
        try {
          localStorage.setItem('floodNowcast.forecastPanelHeight', String(clampedHeight));
        } catch (err) {}
      }

      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
      animFrameRef.current = requestAnimationFrame(() => {
        if (onResize) onResize();
      });
    };

    const handlePointerUp = (upEvent) => {
      setIsDragging(false);
      try {
        if (upEvent.target && upEvent.target.releasePointerCapture) {
          upEvent.target.releasePointerCapture(upEvent.pointerId);
        }
      } catch (err) {}
      window.removeEventListener('pointermove', handlePointerMove);
      window.removeEventListener('pointerup', handlePointerUp);
      if (onResize) onResize();
    };

    try {
      if (e.target && e.target.setPointerCapture) {
        e.target.setPointerCapture(e.pointerId);
      }
    } catch (err) {}
    window.addEventListener('pointermove', handlePointerMove);
    window.addEventListener('pointerup', handlePointerUp);
  };

  const isMobile = typeof window !== 'undefined' && window.innerWidth < 768;
  const collapsedHeight = isMobile ? 44 : 46;
  const currentHeight = isCollapsed ? collapsedHeight : panelHeight;

  if (!forecast || !forecast.forecast) return null;

  return (
    <footer
      className="footer-timeline"
      style={{
        height: `${currentHeight}px`,
        transition: isDragging ? 'none' : 'height 250ms cubic-bezier(0.4, 0, 0.2, 1)',
        position: 'relative',
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'flex-start',
        padding: isCollapsed ? '6px 20px' : '10px 20px',
        boxSizing: 'border-box',
        flexShrink: 0,
        userSelect: isDragging ? 'none' : 'auto'
      }}
    >
      {/* DRAG HANDLE BAR */}
      <div
        className="drag-handle-bar"
        onPointerDown={handlePointerDown}
        onMouseEnter={() => setIsHoveredHandle(true)}
        onMouseLeave={() => setIsHoveredHandle(false)}
        title="Drag to resize forecast horizon panel"
        aria-label="Drag to resize forecast horizon panel"
        style={{
          cursor: 'ns-resize',
          width: '100%',
          height: '14px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          position: 'absolute',
          top: 0,
          left: 0,
          zIndex: 10,
          userSelect: 'none',
          touchAction: 'none'
        }}
      >
        <div
          style={{
            width: '40px',
            height: '4px',
            borderRadius: '2px',
            backgroundColor: isHoveredHandle || isDragging ? '#38bdf8' : '#475569',
            transition: 'background-color 0.2s',
            opacity: 0.85
          }}
        />
      </div>

      {/* HEADER ROW */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginTop: '4px',
          height: '32px',
          minHeight: '32px',
          flexShrink: 0
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', overflow: 'hidden' }}>
          <div
            className="card-title"
            style={{
              margin: 0,
              color: '#f8fafc',
              fontWeight: '800',
              fontSize: '0.85rem',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              whiteSpace: 'nowrap'
            }}
          >
            MODELLED FLOOD-RISK HORIZON
          </div>
          {!isCollapsed && (
            <div
              style={{
                fontSize: '0.7rem',
                color: '#94a3b8',
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis'
              }}
            >
              Forecast values are modelled estimates, not independently validated predictions.
            </div>
          )}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexShrink: 0 }}>
          <span
            className="tag-simulated"
            style={{
              background: '#1d4ed8',
              border: 'none',
              color: '#ffffff',
              fontSize: '0.75rem',
              padding: '2px 8px'
            }}
          >
            MODELLED FORECAST
          </span>
          <button
            type="button"
            onClick={toggleCollapse}
            aria-label={isCollapsed ? 'Expand forecast panel' : 'Collapse forecast panel'}
            title={isCollapsed ? 'Expand forecast panel' : 'Collapse forecast panel'}
            style={{
              background: 'rgba(255, 255, 255, 0.06)',
              border: '1px solid #334155',
              borderRadius: '4px',
              color: '#f8fafc',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              padding: '3px 8px',
              fontSize: '0.95rem',
              fontWeight: 'bold',
              lineHeight: 1,
              transition: 'background-color 0.2s, color 0.2s, border-color 0.2s'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = 'rgba(56, 189, 248, 0.15)';
              e.currentTarget.style.borderColor = '#38bdf8';
              e.currentTarget.style.color = '#38bdf8';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.06)';
              e.currentTarget.style.borderColor = '#334155';
              e.currentTarget.style.color = '#f8fafc';
            }}
          >
            {isCollapsed ? '⌃' : '⌄'}
          </button>
        </div>
      </div>

      {/* TIMELINE TRACK */}
      {!isCollapsed && (
        <div className="timeline-track" style={{ marginTop: '12px', flex: 1, alignItems: 'center' }}>
          <div className="timeline-line"></div>
          {forecast.forecast.map((node, i) => {
            const color = getStatusColor(node.status);
            const nodeOffset = i * 30;
            const isSelected = forecastOffset === nodeOffset;

            return (
              <div
                className="timeline-node"
                key={i}
                onClick={() => setForecastOffset(nodeOffset)}
                style={{
                  cursor: 'pointer',
                  transform: isSelected ? 'scale(1.1)' : 'scale(1)',
                  transition: 'transform 0.2s'
                }}
                title={`Click to set forecast to +${nodeOffset} minutes`}
              >
                <div
                  className="timeline-dot"
                  style={{
                    borderColor: isSelected ? '#38bdf8' : color,
                    backgroundColor: color === '#ffffff' ? '#ffffff' : isSelected ? '#38bdf8' : undefined,
                    boxShadow: isSelected ? '0 0 12px #38bdf8' : 'none'
                  }}
                ></div>
                <div
                  style={{
                    fontWeight: isSelected ? 800 : 700,
                    color: isSelected ? '#38bdf8' : color,
                    fontSize: '0.8rem'
                  }}
                >
                  {node.status}
                </div>
                <div
                  className="timeline-label"
                  style={{
                    fontWeight: isSelected ? 'bold' : 'normal',
                    color: isSelected ? '#ffffff' : '#94a3b8'
                  }}
                >
                  {node.time === '0m' ? 'NOW' : node.time}
                </div>
                <div className="timeline-label">{node.depth.toFixed(1)} cm</div>
              </div>
            );
          })}
        </div>
      )}
    </footer>
  );
}
