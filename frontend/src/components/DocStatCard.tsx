import React from 'react';

interface DocStatCardProps {
  icon: React.ReactNode;
  value: string | number;
  label: string;
}

const DocStatCard: React.FC<DocStatCardProps> = ({ icon, value, label }) => {
  return (
    <div className="glass-card" style={{ padding: 16, textAlign: 'center' }}>
      <div style={{ marginBottom: 12 }}>{icon}</div>
      <div style={{ fontSize: 28, fontWeight: 800, color: '#2C2C2C' }}>{value}</div>
      <div style={{ color: '#666' }}>{label}</div>
    </div>
  );
};

export default DocStatCard;

