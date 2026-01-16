import React from 'react';

interface PaperShellProps {
  children: React.ReactNode;
  className?: string;
  fillViewport?: boolean;
}

const PaperShell: React.FC<PaperShellProps> = ({ children, className, fillViewport }) => {
  return (
    <div
      className={`paper-bg serif ${className || ''}`}
      style={{
        ...(fillViewport ? { minHeight: '100vh' } : { flex: '1 1 0', minHeight: 0 }),
        padding: '32px 24px',
        position: 'relative',
        display: 'flex',
        flexDirection: 'column'
      }}
    >
      {children}
    </div>
  );
};

export default PaperShell;
