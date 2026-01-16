import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { FileTextOutlined, BranchesOutlined, CheckCircleOutlined, ReadOutlined } from '@ant-design/icons';

interface UIOverlayProps {
  onStartResearch?: () => void;
}

const UIOverlay: React.FC<UIOverlayProps> = ({ onStartResearch }) => {
  const navigate = useNavigate();
  const [btnHover, setBtnHover] = useState(false);

  const handleStartClick = () => {
    if (onStartResearch) {
      onStartResearch();
    } else {
      navigate('/start');
    }
  };

  const flowContainerRef = useRef<HTMLDivElement>(null);
  const r1 = useRef<HTMLDivElement>(null);
  const r2 = useRef<HTMLDivElement>(null);
  const r3 = useRef<HTMLDivElement>(null);
  const r4 = useRef<HTMLDivElement>(null);
  const [line, setLine] = useState<{w:number;h:number;x1:number;x2:number;y:number;ready:boolean}>({w:0,h:0,x1:0,x2:0,y:0,ready:false});

  useEffect(() => {
    const compute = () => {
      const cont = flowContainerRef.current;
      const a = r1.current, b = r2.current, c = r3.current, d = r4.current;
      if (!cont || !a || !b || !c || !d) return;
      const cr = cont.getBoundingClientRect();
      const center = (el: HTMLElement) => {
        const r = el.getBoundingClientRect();
        return { x: r.left + r.width / 2 - cr.left, y: r.top + r.height / 2 - cr.top };
      };
      const p1 = center(a);
      const p4 = center(d);
      setLine({ w: cr.width, h: cr.height, x1: p1.x, x2: p4.x, y: p1.y, ready: true });
    };
    compute();
    const onResize = () => compute();
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  return (
    <div className="ui-overlay kaiti-font text-[#1a1a1a] glow-white">
      {/* 底部毛玻璃白色底栏（漂浮在 Hero 之上、底部组件之下） */}
      <div className="bottom-glass"></div>
      {/* Slogan */}
      <div className="absolute top-[15%] left-[8%] interactive fade-in" style={{ animationDelay: '0.2s' }}>
        <div className="opacity-90">
          <div className="kaiti-font text-5xl font-bold leading-tight">
            AI 文献综述生成器
          </div>
          <div className="kaiti-font text-xl mt-4 tracking-wide opacity-80">
            AI批量阅读并整理文献，智能组织综述结构，生成科研级综述。
          </div>
          <div className="kaiti-font text-base mt-3 opacity-70">
            ●批量阅读并整理上百篇文献
          </div>
          <div className="kaiti-font text-base mt-3 opacity-70">
            ●可生成上万字毕设级文献综述
          </div>
          <div className="kaiti-font text-base mt-3 opacity-70">
            ●成本不到100元
          </div>
        </div>
      </div>

      



      {/* 底部流程 + 开始按钮布局：左3/4流程，右1/4按钮 */}
      <div className="absolute bottom-[6%] left-0 right-0 px-12 fade-in" style={{ animationDelay: '0.6s', zIndex: 1 }}>
        <div className="max-w-7xl mx-auto flex items-center">
          {/* 左侧 3/4：流程指示 */}
          <div className="relative w-3/4 interactive" ref={flowContainerRef}>
            <div className="flex items-center justify-between pr-8">
              <div className="flow-item" ref={r1}>
                <div className="flow-icon"><FileTextOutlined /></div>
                <div className="flow-text">1.AI文献整理</div>
              </div>
              <div className="flow-item" style={{ animationDelay: '0.08s' }} ref={r2}>
                <div className="flow-icon"><BranchesOutlined /></div>
                <div className="flow-text">2.综述组织思路</div>
              </div>
              <div className="flow-item" style={{ animationDelay: '0.16s' }} ref={r3}>
                <div className="flow-icon"><CheckCircleOutlined /></div>
                <div className="flow-text">3.综述方案确认</div>
              </div>
              <div className="flow-item" style={{ animationDelay: '0.24s' }} ref={r4}>
                <div className="flow-icon"><ReadOutlined /></div>
                <div className="flow-text">4.文献综述生成</div>
              </div>
            </div>
          </div>

          {/* 右侧 1/4：开始按钮 */}
          <div className="w-1/4 flex justify-end interactive">
            <div
              onMouseEnter={() => setBtnHover(true)}
              onMouseLeave={() => setBtnHover(false)}
              onClick={handleStartClick}
              className={`cta-button cta-glowPulse ${btnHover ? 'cta-active' : ''} interactive`}
            >
              <span className="text-lg tracking-widest">开始</span>
            </div>
          </div>
        </div>
      </div>

    </div>
  );
};

export default UIOverlay;
