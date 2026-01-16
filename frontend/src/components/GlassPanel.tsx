import React from 'react';

interface GlassPanelProps {
  title?: React.ReactNode;
  extra?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
}

const GlassPanel: React.FC<GlassPanelProps> = ({ title, extra, children, className, style }) => {
  return (
    <div
      className={`glass-card ${className || ''}`}
      style={{
        padding: 24,
        borderRadius: 16,
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        ...style
      }}
    >
      {(title || extra) && (
        <div style={{ display: 'flex', alignItems: 'center', marginBottom: 16, flex: '0 0 auto' }}>
          <div style={{ fontWeight: 700, fontSize: 18 }}>{title}</div>
          {extra && <div style={{ marginLeft: 'auto' }}>{extra}</div>}
        </div>
      )}
      {children}
    </div>
  );
};

export default GlassPanel;
