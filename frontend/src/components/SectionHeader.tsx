import React from 'react';

interface SectionHeaderProps {
  title: string;
  subtitle?: string;
  right?: React.ReactNode;
}

const SectionHeader: React.FC<SectionHeaderProps> = ({ title, subtitle, right }) => {
  return (
    <div className="section-title" style={{ marginBottom: '20px', alignItems: 'flex-start' }}>
      <div>
        <h2 style={{ margin: 0 }}>{title}</h2>
        {subtitle && (
          <p style={{ marginTop: '6px', color: '#666' }}>{subtitle}</p>
        )}
      </div>
      {right && <div style={{ marginLeft: 'auto' }}>{right}</div>}
    </div>
  );
};

export default SectionHeader;

