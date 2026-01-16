import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, Upload, Button, Typography, Space, Alert, List, Modal, Input } from 'antd';
import { InboxOutlined, UploadOutlined, FilePdfOutlined } from '@ant-design/icons';
import PaperShell from '../components/PaperShell';
import SectionHeader from '../components/SectionHeader';
import GlassPanel from '../components/GlassPanel';
import { useAppContext } from '../stores/AppContext';
import { researchApi, systemApi } from '../services/api';
import type { UploadFile } from 'antd/es/upload';
import type { UploadChangeParam } from 'antd/es/upload';

const { Dragger } = Upload;

const UploadPage: React.FC = () => {
  const navigate = useNavigate();
  const { state, dispatch } = useAppContext();
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string>('');
  const [statusText, setStatusText] = useState<string>('');
  const [postUploadMode, setPostUploadMode] = useState<boolean>(false);
  const [topic, setTopic] = useState<string>('');
  const [desc, setDesc] = useState<string>('');
  const leftPanelRef = useRef<HTMLDivElement | null>(null);
  const [panelHeight, setPanelHeight] = useState<number>(0);
  const [rawFile, setRawFile] = useState<File | null>(null);

  useEffect(() => {
    if (leftPanelRef.current && panelHeight === 0) {
      setPanelHeight(leftPanelRef.current.offsetHeight);
    }
  }, [panelHeight]);

  useEffect(() => {
    (async () => {
      try {
        const st = await systemApi.checkStatus();
        const ok = !!(st.data as any)?.workdir;
        if (!ok && state.system.isInitialized) {
          await systemApi.start({
            apiKey: state.system.apiKey,
            workingDirectory: state.system.workingDirectory,
            accessKeyId: state.system.accessKeyId,
            secretAccessKey: state.system.secretAccessKey
          });
        }
      } catch (_) {}
    })();
  }, [state.system.isInitialized]);

  const props = {
    name: 'file',
    multiple: false,
    accept: '.zip',
    maxCount: 1,
    fileList,
    beforeUpload: (file: File) => {
      const isZip = file.name.toLowerCase().endsWith('.zip');
      if (!isZip) {
        setError('只能上传ZIP格式的文件！');
        return Upload.LIST_IGNORE as any;
      }
      setError('');
      setRawFile(file);
      return false; // 手动上传，文件仍会进入列表并由 onChange 接管
    },
    onChange: (info: UploadChangeParam<UploadFile>) => {
      const list = info.fileList.slice(-1);
      setFileList(list);
      try {
        const f = (info.file as any)?.originFileObj as File;
        if (f) setRawFile(f);
      } catch {}
    },
    onRemove: () => {
      setFileList([]);
      setError('');
      setRawFile(null);
    }
  };

  const handleUpload = async () => {
    if (fileList.length === 0) {
      setError('请先选择要上传的文件！');
      return;
    }

    setUploading(true);
    setError('');
    setStatusText('正在解压与校验PDF...');

    try {

      const first = fileList[0] as any;
      const file = (rawFile as File) || (first?.originFileObj as File);
      if (!file) {
        setError('未获取到上传文件，请重新选择ZIP后再试');
        setUploading(false);
        setStatusText('');
        return;
      }
      const fd = new FormData();
      fd.append('file', file);
      const apiBase = (import.meta as any)?.env?.VITE_API_BASE || 'http://127.0.0.1:8001/api';
      const url = `${apiBase}/upload/zip`;
      const res = await fetch(url, { method: 'POST', body: fd });
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
      const response = await res.json();

      if (response && response.status === 'success' && response.data) {
        dispatch({
          type: 'UPLOAD_COMPLETE',
          payload: {
            taskId: response.data.taskId,
            extractPath: response.data.extractPath
          }
        });
        setStatusText('上传完成');
        setPostUploadMode(true);
      } else {
        setError(response?.message || '上传失败');
        Modal.error({
          title: '校验失败',
          content: response?.message || '压缩包校验失败，请确认仅包含PDF文件后重试',
        });
      }
    } catch (err: any) {
      const msg = err.response?.data?.message || '上传失败，请重试';
      Modal.error({
        title: '上传/校验失败',
        content: msg,
      });
    } finally {
      setUploading(false);
      setStatusText('');
    }
  };

  return (
    <PaperShell>
      <SectionHeader
        title="上传文献压缩包并描述研究主题"
        subtitle="请将 PDF 文献打包为 ZIP 上传，系统将自动解析，并描述你的研究主题"
        right={<InboxOutlined style={{ fontSize: 32, color: '#d22b2b' }} />}
      />
      <div className="page-grid">
        <GlassPanel title={<span>{postUploadMode ? '填写研究信息' : '上传文件'}</span>} style={{ height: '60vh', display: 'flex', flexDirection: 'column', minHeight: 0 }}>

        {error && (
          <Alert
            message="上传错误"
            description={error}
            type="error"
            showIcon
            style={{ marginBottom: '24px' }}
          />
        )}

        {!postUploadMode ? (
          <div className="upload-area" ref={leftPanelRef} style={{ overflowY: 'auto' }}>
            <Dragger {...props} disabled={uploading}>
              <p className="ant-upload-drag-icon">
                <InboxOutlined style={{ fontSize: '48px', color: '#d22b2b' }} />
              </p>
              <p className="ant-upload-text">点击或拖拽ZIP文件到此区域上传</p>
              <p className="ant-upload-hint">
                支持单个ZIP文件，文件大小不超过200MB
              </p>
            </Dragger>
            {uploading && (
              <div style={{ width: '100%', textAlign: 'center', padding: '12px 0', color: '#2F54EB' }}>
                {statusText || '上传并解析中...'}
              </div>
            )}
          </div>
        ) : (
          <div ref={leftPanelRef} style={{ display: 'flex', flexDirection: 'column', gap: 12, flex: '1 1 0', minHeight: 0, overflowY: 'auto' }}>
            <Input.TextArea 
              placeholder="请输入您的研究主题" 
              value={topic} 
              onChange={(e) => setTopic(e.target.value)}
              style={{ flex: '2 0 0', minHeight: 0 }}
            />
            <Input.TextArea 
              placeholder="请详细介绍您的研究" 
              value={desc} 
              onChange={(e) => setDesc(e.target.value)}
              style={{ flex: '5 0 0', minHeight: 0 }}
            />
          </div>
        )}

        <div style={{ marginTop: '24px', textAlign: 'center' }}>
          {!postUploadMode ? (
            <Space>
              <Button 
                type="primary" 
                size="large" 
                icon={<UploadOutlined />}
                onClick={handleUpload}
                loading={uploading}
                disabled={uploading || fileList.length === 0}
                className="primary-red-btn"
              >
                开始上传
              </Button>
              <Button 
                size="large"
                onClick={() => navigate('/start')}
                disabled={uploading}
              >
                返回配置
              </Button>
            </Space>
          ) : (
            <Space>
              <Button 
                type="primary" 
                size="large" 
                onClick={async () => {
                  if (!topic.trim() || !desc.trim()) return;
                  try {
                    const res = await researchApi.save(topic.trim(), desc.trim());
                    if (res.status === 'success') {
                      navigate('/summary');
                    } else {
                      Modal.error({ title: '保存失败', content: res.message || '请稍后重试' });
                    }
                  } catch (e: any) {
                    Modal.error({ title: '保存失败', content: e.response?.data?.message || e.message || '请稍后重试' });
                  }
                }}
                disabled={!topic.trim() || !desc.trim()}
                className="primary-red-btn"
              >
                确认并进入下一步
              </Button>
            </Space>
          )}
        </div>
        </GlassPanel>

        <GlassPanel title={<span>{postUploadMode ? '研究信息填写说明' : '上传说明'}</span>} style={{ height: 'auto' }}>
          <div style={{ color: '#666', fontSize: '14px' }}>
            {!postUploadMode ? (
              <>
                <p style={{ marginBottom: '8px' }}><strong>文件要求：</strong></p>
                <ul style={{ margin: '0 0 16px 20px' }}>
                  <li>仅支持ZIP格式的压缩文件</li>
                  <li>压缩包内应仅包含PDF格式的学术文献</li>
                  <li>建议上传100-150篇文献以获得最佳效果</li>
                </ul>
              </>
            ) : (
              <>
                <p style={{ marginBottom: 8 }}><strong>填写指南：</strong></p>
                <ul style={{ margin: '0 0 16px 20px' }}>
                  <li>上框：简要描述你的研究主题，后续AI会结合你的研究主题进行整理</li>
                  <li>下框：可再详细介绍你的研究思路、方法、主要内容等信息，帮助AI更好地理解你的研究，整理更精准贴切</li>
                  <li>填写完成后点击确认进入下一步</li>
                </ul>
              </>
            )}
          </div>
        </GlassPanel>
      </div>
    </PaperShell>
  );
};

export default UploadPage;
