import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Space } from 'antd';
import {
  CopyOutlined,
  DownloadOutlined,
  HomeOutlined
} from '@ant-design/icons';
import PaperShell from '../components/PaperShell';
import GlassPanel from '../components/GlassPanel';
import { useAppContext } from '../stores/AppContext';

const ResultPage: React.FC = () => {
  const navigate = useNavigate();
  const { state } = useAppContext();

  const handleDownload = () => {
    // 创建并下载文件
    const blob = new Blob([state.generate.content], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `literature_review_${new Date().toISOString().slice(0, 10)}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleNewReview = () => {
    // 重置状态并返回首页
    navigate('/');
  };

  const charCount = (state.generate.content || '').replace(/\s/g, '').length;

  const handleCopy = async () => {
    const text = String(state.generate.content || '');
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(text);
        return;
      }
    } catch {
    }
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.setAttribute('readonly', 'true');
    ta.style.position = 'fixed';
    ta.style.left = '-9999px';
    ta.style.top = '0';
    document.body.appendChild(ta);
    ta.focus();
    ta.select();
    try {
      document.execCommand('copy');
    } finally {
      document.body.removeChild(ta);
    }
  };

  return (
    <PaperShell>
      

      <GlassPanel title={<span>预览</span>} style={{ flex: '1 1 0', minHeight: 0, display: 'flex', flexDirection: 'column' }}>
        <div style={{ background: '#fafafa', padding: '24px', borderRadius: '8px', fontFamily: 'monospace', fontSize: '14px', lineHeight: '1.6', whiteSpace: 'pre-wrap', border: '1px solid #d9d9d9', flex: '1 1 0', minHeight: 0, overflowY: 'auto', position: 'relative' }}>
          <div style={{ position: 'absolute', top: 12, right: 12, zIndex: 2, background: 'rgba(255,255,255,0.92)', border: '1px solid rgba(0,0,0,0.08)', borderRadius: 12, padding: '8px 10px', boxShadow: '0 6px 16px rgba(0,0,0,0.10)', display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{ color: '#666', fontSize: 12 }}>{`字数：${charCount}`}</span>
            <Button size="small" icon={<CopyOutlined />} onClick={handleCopy}>
              复制全文
            </Button>
          </div>
          {state.generate.content}
        </div>
      </GlassPanel>

      <div style={{ textAlign: 'center', marginTop: 24 }}>
        <Space size="large">
          <Button 
            size="large"
            icon={<HomeOutlined />}
            onClick={handleNewReview}
          >
            开始新的综述
          </Button>
          <Button 
            type="primary" 
            size="large"
            icon={<DownloadOutlined />}
            onClick={handleDownload}
            className="primary-red-btn"
          >
            下载综述
          </Button>
        </Space>
      </div>

      
    </PaperShell>
  );
};

export default ResultPage;
