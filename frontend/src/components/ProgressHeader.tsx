import React from 'react';
import { Progress } from 'antd';

interface ProgressHeaderProps {
  percent: number;
  text?: string;
  subtext?: string;
}

const ProgressHeader: React.FC<ProgressHeaderProps> = ({ percent, text, subtext }) => {
  return (
    <div className="glass-card" style={{ padding: 16, marginBottom: 16, width: '100%' }}>
      <div style={{ display: 'flex', alignItems: 'center' }}>
        <div style={{ fontWeight: 700, fontSize: 16 }}>{text || ''}</div>
        <div style={{ marginLeft: 'auto', color: '#666' }}>{subtext}</div>
      </div>
      <div style={{ marginTop: 8 }}>
        <Progress
          percent={Math.max(0, Math.min(100, Math.round(percent)))}
          size="small"
          status={percent >= 100 ? 'success' : 'normal'}
        />
      </div>
    </div>
  );
};

export default ProgressHeader;
