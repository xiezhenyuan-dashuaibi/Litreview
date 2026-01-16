import React, { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Input, Typography, Modal } from 'antd';
import { PlayCircleOutlined, FormOutlined, RadarChartOutlined } from '@ant-design/icons';
import PaperShell from '../components/PaperShell';
import SectionHeader from '../components/SectionHeader';
import GlassPanel from '../components/GlassPanel';
import { systemConfigApi, researchApi, clusterApi } from '../services/api';
import { useAppContext } from '../stores/AppContext';

const { Paragraph, Title } = Typography;

const ClusterPage: React.FC = () => {
  const navigate = useNavigate();
  const { dispatch } = useAppContext();
  const [topic, setTopic] = useState('');
  const [desc, setDesc] = useState('');
  const [isAnalysing, setIsAnalysing] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // 自动获取环境变量回填
  useEffect(() => {
    const fetchEnv = async () => {
      try {
        const res = await systemConfigApi.getEnv();
        if (res.status === 'success' && res.data) {
          if (res.data.RESEARCH_TOPIC) setTopic(res.data.RESEARCH_TOPIC);
          if (res.data.RESEARCH_DESCRIPTION) setDesc(res.data.RESEARCH_DESCRIPTION);
        }
      } catch (e) {
        console.error("Failed to fetch env", e);
      }
    };
    fetchEnv();
  }, []);

  const canStart = topic.trim().length > 0 && desc.trim().length > 0;

  const handleStartAnalysis = async () => {
    if (!canStart) return;
    
    try {
      // 1. 保存研究信息
      const saveRes = await researchApi.save(topic.trim(), desc.trim());
      if (saveRes.status !== 'success') {
        Modal.error({ title: '保存失败', content: saveRes.message || '请稍后重试' });
        return;
      }

      // 2. 进入加载状态
      setIsAnalysing(true);
      dispatch({ type: 'CLUSTER_START' });

      // 3. 调用聚类API
      const clusterRes = await clusterApi.analyze({ 
        taskId: `cluster_${Date.now()}`,
        k: 20,
        similarityThreshold: 0.75
      });

      if (clusterRes.status === 'success' && clusterRes.data) {
        // 获取真正的 taskId
        const taskId = (clusterRes.data as any).taskId; // 需要确保类型定义正确，或临时断言

        // 4. 建立WebSocket连接监听进度
        const ws = new WebSocket('ws://localhost:8001/ws/cluster/monitor');
        
        ws.onopen = () => {
          // 连接成功后发送 taskId
          ws.send(JSON.stringify({ taskId }));
        };

        ws.onmessage = (event) => {
          try {
            const msg = JSON.parse(event.data);
            if (msg.type === 'cluster_complete') {
              // 接收到完成信号和数据
              dispatch({ 
                type: 'CLUSTER_COMPLETE', 
                payload: { 
                  schemes: [], 
                  graphData: msg.payload.graph 
                } 
              });
              ws.close();
              navigate('/plan');
            } else if (msg.type === 'cluster_failed') {
              Modal.error({ title: '聚类失败', content: msg.message });
              setIsAnalysing(false);
              ws.close();
            } else if (msg.type === 'cluster_progress') {
              // 可选：更新UI上的进度条或消息
              // console.log('Progress:', msg.progress, msg.message);
            }
          } catch (e) {
            console.error('WS parse error', e);
          }
        };

        ws.onerror = (e) => {
          console.error('WS error', e);
          Modal.error({ title: '连接错误', content: '无法连接到进度监控服务' });
          setIsAnalysing(false);
        };

        ws.onclose = (e) => {
          if (e.code !== 1000) { // 非正常关闭
             console.warn('WS closed unexpectedly', e);
             // 仅记录日志，不强制退出loading，以免闪烁或误判
          }
        };
      } else {
         Modal.error({ title: '启动失败', content: clusterRes.message || '请稍后重试' });
         setIsAnalysing(false);
      }

    } catch (e: any) {
      Modal.error({ title: '操作失败', content: e.response?.data?.message || e.message || '请稍后重试' });
      setIsAnalysing(false);
    }
  };

  // 生成背景粒子
  const renderParticles = () => {
    if (!canStart) return null;
    return Array.from({ length: 12 }).map((_, i) => (
      <div
        key={i}
        className="particle"
        style={{
          width: Math.random() * 10 + 4,
          height: Math.random() * 10 + 4,
          left: `${Math.random() * 100}%`,
          top: `${Math.random() * 100}%`,
          animationDelay: `${Math.random() * 2}s`,
          opacity: Math.random() * 0.5 + 0.2
        }}
      />
    ));
  };

  if (isAnalysing) {
    return (
      <PaperShell>
        <SectionHeader
          title="深度分析中"
          subtitle="AI 正在根据您的研究主题进行深度聚类分析"
        />
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
          <GlassPanel style={{ padding: 60, alignItems: 'center', maxWidth: 600 }}>
            <div className="relative">
              <div className="animate-spin" style={{ 
                width: '100px', 
                height: '100px', 
                border: '6px solid #f3f3f3',
                borderTop: '6px solid #FA8C16',
                borderRadius: '50%',
                marginBottom: 32,
                animation: 'spin 1.5s linear infinite'
              }} />
              <div className="absolute inset-0 flex items-center justify-center mb-8">
                <RadarChartOutlined style={{ fontSize: 40, color: '#FA8C16', opacity: 0.8 }} className="animate-pulse" />
              </div>
            </div>
            
            <Title level={3} style={{ marginBottom: 16 }}>正在进行深度研究与聚类</Title>
            <Paragraph type="secondary" style={{ textAlign: 'center', fontSize: 16 }}>
              正在分析文献内容，并梳理文献脉络。<br/>
              这可能需要约一小时，请勿刷新页面...
            </Paragraph>
          </GlassPanel>
        </div>
      </PaperShell>
    );
  }

  return (
    <PaperShell>
      <SectionHeader
        title="研究背景与聚类启动"
        subtitle="确认您的研究主题与内容描述，以便AI更精准地组织文献聚类"
      />

      <div style={{ display: 'grid', gridTemplateColumns: '2fr 3fr', gap: 24, height: '100%' }}>
        {/* 左侧：研究信息填写 */}
        <GlassPanel 
          title={<span><FormOutlined /> 研究背景信息</span>} 
          style={{ display: 'flex', flexDirection: 'column', height: '100%', minHeight: 0 }}
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16, flex: 1, minHeight: 0 }}>
            <div style={{ display: 'flex', flexDirection: 'column', flex: '2 0 0', minHeight: 0 }}>
              <Paragraph strong style={{ marginBottom: 8 }}>研究题目</Paragraph>
              <Input.TextArea 
                placeholder="请输入您的研究主题（例如：基于深度学习的医学图像分割研究）" 
                value={topic} 
                onChange={(e) => setTopic(e.target.value)}
                style={{ flex: 1, resize: 'none' }}
                className="soft-input"
              />
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', flex: '5 0 0', minHeight: 0 }}>
              <Paragraph strong style={{ marginBottom: 8 }}>研究内容描述</Paragraph>
              <Input.TextArea 
                placeholder="请详细介绍您的研究思路、方法、主要内容等信息，帮助AI更好地理解你的研究..." 
                value={desc} 
                onChange={(e) => setDesc(e.target.value)}
                style={{ flex: 1, resize: 'none' }}
                className="soft-input"
              />
            </div>
          </div>
        </GlassPanel>

        {/* 右侧：启动按钮 */}
        <GlassPanel 
          style={{ 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'center', 
            height: '100%', 
            minHeight: 0,
            background: 'rgba(255,255,255,0.4)',
            position: 'relative',
            overflow: 'hidden'
          }}
        >
          {canStart && <div className="particle-bg">{renderParticles()}</div>}
          
          <div style={{ textAlign: 'center', zIndex: 1 }} ref={containerRef}>
            <div className={`cluster-btn-wrapper ${canStart ? 'active' : ''}`}>
              <div className="cluster-ring" />
              <div className="orbit-dot" />
              
              <Button
                type="primary"
                shape="circle"
                size="large"
                disabled={!canStart}
                onClick={handleStartAnalysis}
                className="cluster-glass-btn"
                style={{
                  width: 240,
                  height: 240,
                  fontSize: 28,
                  fontWeight: 'bold',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  borderWidth: 0,
                  color: canStart ? '#fff' : '#999',
                  background: canStart ? undefined : 'rgba(255, 255, 255, 0.5)'
                }}
              >
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 16, zIndex: 2 }}>
                  {canStart ? (
                    <RadarChartOutlined className="cluster-icon-spin" style={{ fontSize: 72 }} />
                  ) : (
                    <PlayCircleOutlined style={{ fontSize: 72, opacity: 0.5 }} />
                  )}
                  <span className={canStart ? 'text-glow' : ''} style={{ letterSpacing: 4 }}>
                    {canStart ? '开始聚类' : '等待填写'}
                  </span>
                </div>
              </Button>
            </div>
            

          </div>
        </GlassPanel>
      </div>
    </PaperShell>
  );
};

export default ClusterPage;
