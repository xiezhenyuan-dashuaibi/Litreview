import React from 'react';
import { Progress, Typography } from 'antd';

const { Text } = Typography;

interface ProgressBarProps {
  percent: number;
  status?: 'normal' | 'exception' | 'active' | 'success';
  format?: (percent: number) => string;
  strokeColor?: string | { [key: string]: string };
  showInfo?: boolean;
  size?: 'small' | 'default';
  className?: string;
}

const ProgressBar: React.FC<ProgressBarProps> = ({
  percent,
  status = 'normal',
  format,
  strokeColor,
  showInfo = true,
  size = 'default',
  className
}) => {
  return (
    <div className={className}>
      <Progress
        percent={percent}
        status={status}
        format={format}
        strokeColor={strokeColor}
        showInfo={showInfo}
        size={size}
      />
    </div>
  );
};

export default ProgressBar;