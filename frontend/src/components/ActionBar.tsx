import React from 'react';

interface ActionBarProps {
  left?: React.ReactNode;
  right?: React.ReactNode;
  children?: React.ReactNode;
}

const ActionBar: React.FC<ActionBarProps> = ({ left, right, children }) => {
  return (
    <div style={{ marginTop: 24 }}>
      <div className="glass-card" style={{ padding: 16, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>{left}</div>
        <div style={{ marginLeft: 'auto' }}>{right || children}</div>
      </div>
    </div>
  );
};

export default ActionBar;

