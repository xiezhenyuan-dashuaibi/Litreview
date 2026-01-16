import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, Button, Typography, Progress, Table, Tag, Space, Alert, Tabs } from 'antd';
import PaperShell from '../components/PaperShell';
import SectionHeader from '../components/SectionHeader';
import GlassPanel from '../components/GlassPanel';
import ProgressHeader from '../components/ProgressHeader';
import { FileTextOutlined, CheckCircleOutlined, ClockCircleOutlined, ExclamationCircleOutlined } from '@ant-design/icons';
import PaperCard from '../components/PaperCard';
import { useAppContext } from '../stores/AppContext';
import { summaryApi } from '../services/api';
import { mockSummaryResults } from '../mocks/data';

const { Title, Paragraph, Text } = Typography;

const SummaryPage: React.FC = () => {
  const navigate = useNavigate();
  const { state, dispatch } = useAppContext();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>('');
  const [summaryTaskId, setSummaryTaskId] = useState<string>(state.upload.taskId || 'mock_task');
  const [allFiles, setAllFiles] = useState<string[]>([]);
  const [processingFiles, setProcessingFiles] = useState<string[]>([]);
  const [completedFiles, setCompletedFiles] = useState<string[]>([]);
  const [failedFiles, setFailedFiles] = useState<string[]>([]);

  useEffect(() => {
    if (state.summary.status === 'idle') {
      startSummary();
    }
  }, [state.summary.status]);

  useEffect(() => {
    const wsUrl = `ws://${window.location.host}/ws/summary/run`;
    const tid = state.upload.taskId || summaryTaskId || 'mock_task';
    const ws = new WebSocket(wsUrl);
    ws.onopen = () => {
      ws.send(JSON.stringify({ taskId: tid }));
    };
    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        if (msg.type === 'init') {
          setAllFiles(msg.files || []);
          setCompletedFiles([]);
          setProcessingFiles([]);
          setFailedFiles([]);
          dispatch({ type: 'SUMMARY_START', payload: { total: (msg.files || []).length } });
        } else if (msg.type === 'batch_start') {
          setProcessingFiles(msg.files || []);
        } else if (msg.type === 'batch_done') {
          setCompletedFiles((prev) => [...prev, ...(msg.files || [])]);
          setProcessingFiles([]);
          dispatch({
            type: 'SUMMARY_PROGRESS',
            payload: { completed: (completedFiles.length + (msg.files || []).length), failed: failedFiles.length }
          });
        } else if (msg.type === 'done') {
          dispatch({ type: 'SUMMARY_COMPLETE', payload: { results: [] } });
        } else if (msg.type === 'error') {
          setError(msg.message || '处理过程中出现错误');
        }
      } catch (e) {}
    };
    ws.onerror = () => setError('网络错误，无法建立处理连接');
    return () => ws.close();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const startSummary = async () => {
    setLoading(true);
    setError('');

    try {
      const tid = state.upload.taskId || summaryTaskId || 'mock_task';
      setSummaryTaskId(tid);
      await summaryApi.startSummary(tid);
    } catch (err: any) {
      setError(err.message || '启动摘要生成失败');
    } finally {
      setLoading(false);
    }
  };

  const remainingFiles = allFiles.filter(f => !completedFiles.includes(f) && !processingFiles.includes(f));

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircleOutlined style={{ color: '#52C41A' }} />;
      case 'processing':
        return <ClockCircleOutlined style={{ color: '#FA8C16' }} />;
      case 'failed':
        return <ExclamationCircleOutlined style={{ color: '#FF4D4F' }} />;
      default:
        return <FileTextOutlined />;
    }
  };

  const getStatusTag = (status: string) => {
    switch (status) {
      case 'completed':
        return <Tag color="success">已完成</Tag>;
      case 'processing':
        return <Tag color="warning">处理中</Tag>;
      case 'failed':
        return <Tag color="error">失败</Tag>;
      default:
        return <Tag>待处理</Tag>;
    }
  };

  const columns = [
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 80,
      render: (status: string) => getStatusIcon(status)
    },
    {
      title: '文献标题',
      dataIndex: 'title',
      key: 'title',
      ellipsis: true
    },
    {
      title: '研究方法',
      dataIndex: 'method',
      key: 'method',
      width: 120,
      render: (method: string) => <Tag>{method}</Tag>
    },
    {
      title: '处理状态',
      dataIndex: 'status',
      key: 'statusText',
      width: 100,
      render: (status: string) => getStatusTag(status)
    }
  ];

  return (
    <PaperShell>


      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24, alignItems: 'stretch', height: '100%' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16, height: '100%', minHeight: 0 }}>
          <div style={{ flex: '0 0 auto' }}>
            <ProgressHeader
              percent={state.summary.progress}
              text="AI文献整理进度（中途不可暂停）"
              subtext={state.summary.currentFile ? `当前处理：${state.summary.currentFile}` : ''}
            />
          </div>

          {error && (
            <Alert
              message="处理错误"
              description={error}
              type="error"
              showIcon
            />
          )}

          <GlassPanel className="fixed-panel-todo" style={{ display: 'flex', flexDirection: 'column', flex: '0 0 auto', minHeight: 0 }}>
            <div style={{ display: 'flex', alignItems: 'center', marginBottom: 12 }}>
              <div style={{ fontWeight: 700 }}>待完成任务</div>
              {state.summary.status === 'processing' && (
                <div style={{ marginLeft: 'auto' }}>
                  <div className="animate-spin" style={{ 
                    width: 24, height: 24,
                    border: '3px solid #f3f3f3', borderTop: '3px solid #2F54EB',
                    borderRadius: '50%'
                  }} />
                </div>
              )}
            </div>
            <div style={{ border: '1px solid #e5e7eb', borderRadius: 8, padding: 12, flex: 1, minHeight: 0, overflowY: 'auto' }}>
              {(processingFiles.length === 0 && remainingFiles.length === 0) ? (
                <div style={{ color: '#999' }}>暂无待完成项</div>
              ) : (
                <div style={{ display: 'grid', gap: 8 }}>
                  {processingFiles.length > 0 && (
                    <div style={{ background: '#fffaf0', border: '1px solid #ffe58f', borderRadius: 8, padding: 8 }}>
                      <div style={{ fontWeight: 700, marginBottom: 6 }}>{`正在处理的文献...`}</div>
                      {processingFiles.map((n) => (
                        <div key={n} style={{ color: '#8c6d1f', fontSize: 12 }}>{n}</div>
                      ))}
                    </div>
                  )}
                  {remainingFiles.map((n) => (
                    <div key={n} style={{ background: '#fff', border: '1px solid #eee', borderRadius: 8, padding: 8 }}>
                      <div style={{ fontWeight: 700 }}>{n}</div>
                      <div style={{ color: '#666', fontSize: 12 }}>等待分析...</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </GlassPanel>
        </div>

        <div style={{ height: '100%', minHeight: 0 }}>
          <GlassPanel 
            title={<span>已完成分析</span>} 
            className="fixed-panel-done"
            style={{ display: 'flex', flexDirection: 'column', flex: '0 0 auto', minHeight: 0 }}
          >
            <div style={{ border: '1px solid #e5e7eb', borderRadius: 8, padding: 12, flex: 1, minHeight: 0, overflowY: 'auto' }}>
              {(state.summary.status === 'idle' && completedFiles.length === 0) && (
                <div style={{ color: '#999' }}>暂无已完成项</div>
              )}
              {completedFiles.length > 0 && (
                <div style={{ display: 'grid', gap: 8 }}>
                  {completedFiles.map((n) => (
                    <div key={n} style={{ background: '#fff', border: '1px solid #eee', borderRadius: 8, padding: 8 }}>
                      <div style={{ fontWeight: 700 }}>{n}</div>
                      <div style={{ color: '#666', fontSize: 12 }}>已完成</div>
                    </div>
                  ))}
                </div>
              )}
              {(state.summary.status === 'completed' && state.summary.results.length > 0) && (
                <div style={{ display: 'grid', gap: 8 }}>
                  {state.summary.results.map((item: any) => (
                    <div key={item.paperId} style={{ background: '#fff', border: '1px solid #eee', borderRadius: 8, padding: 8 }}>
                      <div style={{ fontWeight: 700 }}>{item.title}</div>
                      <div style={{ color: '#666', fontSize: 12 }}>{item.method}</div>
                    </div>
                  ))}
                </div>
              )}
              {(state.summary.status !== 'idle' && completedFiles.length === 0 && state.summary.results.length === 0) && (
                <div style={{ color: '#999' }}>暂无已完成项</div>
              )}
            </div>
          </GlassPanel>
        </div>
      </div>

      {state.summary.status === 'completed' && (
        <div className="fab-next-step">
          <Button
            type="primary"
            size="large"
            onClick={() => navigate('/cluster')}
            className="primary-red-btn"
            style={{
              position: 'fixed',
              bottom: 120,
              right: 120,
              zIndex: 1000
            }}
          >
            下一步
          </Button>
        </div>
      )}


    </PaperShell>
  );
};

export default SummaryPage;
