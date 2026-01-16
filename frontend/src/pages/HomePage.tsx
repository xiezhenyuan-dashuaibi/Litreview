import React from 'react';
import ThreeScene from '../components/ThreeScene';
import UIOverlay from '../components/UIOverlay';

const HomePage: React.FC = () => {
  const handleStartResearch = () => {
    // 使用原生导航，避免React Router的延迟
    window.location.href = '/start';
  };

  return (
    <div className="w-full h-screen relative overflow-hidden research-overlay">
      {/* Three.js 场景 */}
      <ThreeScene />
      
      {/* UI 覆盖层 */}
      <UIOverlay onStartResearch={handleStartResearch} />
    </div>
  );
};

export default HomePage;