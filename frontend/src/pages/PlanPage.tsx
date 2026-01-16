import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, Button, Typography, Empty } from 'antd';
import { ProjectOutlined, RocketOutlined } from '@ant-design/icons';
import PaperShell from '../components/PaperShell';
import SectionHeader from '../components/SectionHeader';
import GlassPanel from '../components/GlassPanel';
import { useAppContext } from '../stores/AppContext';
import Plot from 'react-plotly.js';

const { Paragraph } = Typography;

const PlanPage: React.FC = () => {
  const navigate = useNavigate();
  const { state, dispatch } = useAppContext();
  const [graphData, setGraphData] = useState<any>(null);

  useEffect(() => {
    if (state.cluster.graphData) {
      setGraphData(state.cluster.graphData);
    }
  }, [state.cluster.graphData]);

  return (
    <PaperShell>
      <SectionHeader
        title="方案展示"
        subtitle="查看AI生成的文献聚类方案与知识脉络图谱"
      />
      
      <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: 24, minHeight: 0 }}>
        {/* 泳池图展示区域 */}
        <GlassPanel 
          title={<span><ProjectOutlined /> 知识脉络图谱（泳池图）</span>}
          style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0 }}
        >
          <div style={{ 
            flex: 1, 
            background: 'rgba(255,255,255,0.5)', 
            borderRadius: 12, 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'center',
            border: '2px dashed #d9d9d9',
            margin: 16,
            overflow: 'hidden'
          }}>
            {graphData ? (
              <Plot
                data={graphData.data}
                layout={{
                  ...graphData.layout,
                  autosize: true,
                  width: undefined,
                  height: undefined,
                  margin: { l: 50, r: 20, t: 60, b: 40 },
                  paper_bgcolor: 'rgba(0,0,0,0)',
                  plot_bgcolor: 'rgba(0,0,0,0)'
                }}
                useResizeHandler={true}
                style={{ width: '100%', height: '100%' }}
                config={{ responsive: true, displayModeBar: false }}
              />
            ) : (
              <Empty
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                description={
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontSize: 16, fontWeight: 500, color: '#666' }}>泳池图渲染区域</span>
                    <span style={{ fontSize: 14, color: '#999' }}>暂无数据，请先进行聚类分析</span>
                  </div>
                }
              />
            )}
          </div>
          <div style={{ padding: '0 24px 16px', color: '#666' }}>
            <Paragraph>
              该图谱展示了不同研究主题随时间的演变过程，横轴为时间线，纵轴为聚类主题。
              后续正式文献综述的撰写将按照该知识脉络图谱进行组织。
            </Paragraph>
          </div>
        </GlassPanel>

        {/* 底部操作区 */}
        <div style={{ display: 'flex', justifyContent: 'center', paddingBottom: 24 }}>
          <Button 
            type="primary" 
            size="large"
            className="primary-red-btn"
            style={{ 
              height: 56, 
              padding: '0 48px', 
              fontSize: 18, 
              display: 'flex', 
              alignItems: 'center', 
              gap: 12 
            }}
            onClick={() => {
              dispatch({ type: 'GENERATE_RESET' });
              navigate('/generate');
            }}
          >
            <RocketOutlined /> 生成正式文献综述
          </Button>
        </div>
      </div>
    </PaperShell>
  );
};

export default PlanPage;
