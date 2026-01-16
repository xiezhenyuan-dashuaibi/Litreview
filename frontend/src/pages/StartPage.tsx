import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, Form, Input, Button, Typography, Alert, Space, Switch, Image } from 'antd';
import { KeyOutlined, FolderOutlined, RocketOutlined, CheckCircleOutlined, CloseCircleOutlined, ApiOutlined, DownOutlined } from '@ant-design/icons';
import PaperShell from '../components/PaperShell';
import SectionHeader from '../components/SectionHeader';
import GlassPanel from '../components/GlassPanel';
import { useAppContext } from '../stores/AppContext';
import { systemApi, systemDebugApi, systemConfigApi } from '../services/api';

const { Title, Paragraph } = Typography;

const StartPage: React.FC = () => {
  const navigate = useNavigate();
  const { dispatch } = useAppContext();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>('');
  const [modelOk, setModelOk] = useState<boolean | null>(null);
  const [ocrOk, setOcrOk] = useState<boolean | null>(null);
  const [workingDirOk, setWorkingDirOk] = useState<boolean | null>(null);
  const [browseBusy, setBrowseBusy] = useState<boolean>(false);
  const [costGuideOpen, setCostGuideOpen] = useState<boolean>(false);
  const [ocrGuideOpen, setOcrGuideOpen] = useState<boolean>(false);
  const [modelGuideOpen, setModelGuideOpen] = useState<boolean>(false);
  const [isCollectionMode, setIsCollectionMode] = useState<boolean>(false);
  const bothApisOk = modelOk === true && ocrOk === true;
  const canStart = bothApisOk && workingDirOk === true;
  const printedRef = useRef(false);
  const startedRef = useRef(false);

  const onFinish = async (values: any, targetPath: string = '/upload') => {
    setLoading(true);
    setError('');
    try {
      const response = await systemApi.start({
        apiKey: values.apiKey,
        workingDirectory: values.workingDirectory,
        accessKeyId: values.accessKeyId,
        secretAccessKey: values.secretAccessKey
      });
      if (response.status === 'success' && response.data) {
        dispatch({
          type: 'SYSTEM_INIT',
          payload: {
            apiKey: values.apiKey,
            workingDirectory: values.workingDirectory,
            accessKeyId: values.accessKeyId,
            secretAccessKey: values.secretAccessKey,
            sessionId: response.data.sessionId
          }
        });
        
        // 如果是直接进入聚类模式，需要伪造前序步骤的完成状态
        if (targetPath === '/cluster') {
          dispatch({
            type: 'UPLOAD_COMPLETE',
            payload: {
              taskId: 'manual_import_' + Date.now(),
              extractPath: values.workingDirectory
            }
          });
          dispatch({
            type: 'SUMMARY_COMPLETE',
            payload: {
              results: [] // 聚类页不依赖具体摘要内容，只依赖状态
            }
          });
        }

        navigate(targetPath);
      } else {
        setError(response.message || '系统启动失败');
      }
    } catch (err: any) {
      setError(err.response?.data?.message || '网络错误，请重试');
    } finally {
      setLoading(false);
    }
  };

  const startSystem = async () => {
    const values = form.getFieldsValue();
    if (!values.apiKey || !values.accessKeyId || !values.secretAccessKey || !values.workingDirectory) return;
    const target = isCollectionMode ? '/cluster' : '/upload';
    await onFinish(values, target);
    try {
      await systemConfigApi.save({
        apiKey: values.apiKey,
        workingDirectory: values.workingDirectory,
        accessKeyId: values.accessKeyId,
        secretAccessKey: values.secretAccessKey
      });
      await systemDebugApi.printEnv();
    } catch {}
  };

  const onTestConnections = async (values: any) => {
    setLoading(true);
    setError('');
    try {
      const wsUrl = `ws://${window.location.host}/ws/system/test-connections`;
      const ws = new WebSocket(wsUrl);
      ws.onopen = () => {
        ws.send(JSON.stringify({
          apiKey: values.apiKey,
          accessKeyId: values.accessKeyId,
          secretAccessKey: values.secretAccessKey
        }));
      };
      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data);
          if (msg.type === 'model') setModelOk(!!msg.ok);
          if (msg.type === 'ocr') setOcrOk(!!msg.ok);
          if (msg.type === 'error') setError(msg.message || '连接测试失败');
          if (msg.type === 'done') {
            setLoading(false);
            ws.close();
          }
        } catch (_) {}
      };
      ws.onerror = () => {
        setError('连接测试失败');
        setLoading(false);
      };
    } catch (err: any) {
      setError('连接测试失败');
      setLoading(false);
    }
  };

  

  useEffect(() => {
    (async () => {
      try {
        const cfg = await systemConfigApi.getEnv();
        const data = cfg.data as any;
        const patch: any = {};
        if (data?.ARK_API_KEY) patch.apiKey = data.ARK_API_KEY;
        if (data?.VOLC_ACCESS_KEY) patch.accessKeyId = data.VOLC_ACCESS_KEY;
        if (data?.VOLC_SECRET_KEY) patch.secretAccessKey = data.VOLC_SECRET_KEY;
        if (Object.keys(patch).length) {
          form.setFieldsValue(patch);
        }
      } catch (e) {}
    })();
  }, []);

  useEffect(() => {
    const path = form.getFieldValue('workingDirectory');
    if (path) {
      (async () => {
        try {
          const chk = await systemApi.checkWorkingDir(path, isCollectionMode);
          setWorkingDirOk(chk.status === 'success' && chk.data?.ok === true);
        } catch {
          setWorkingDirOk(false);
        }
      })();
    }
  }, [isCollectionMode]);

  const handlePickDir = async () => {
    setBrowseBusy(true);
    setError('');
    try {
      const pick = await systemApi.pickWorkingDir();
      const path = pick.data?.path || '';
      form.setFieldsValue({ workingDirectory: path });
      if (path) {
        const chk = await systemApi.checkWorkingDir(path, isCollectionMode);
        setWorkingDirOk(chk.status === 'success' && chk.data?.ok === true);
      } else {
        setWorkingDirOk(false);
      }
    } catch (err: any) {
      
    } finally {
      setBrowseBusy(false);
    }
  };

  return (
    <PaperShell fillViewport>
      <SectionHeader
        title="系统配置"
        subtitle="配置 API 密钥与工作目录以启动文献综述系统"
        right={<RocketOutlined style={{ fontSize: 32, color: '#d22b2b' }} />}
      />

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: 24 }}>
        <GlassPanel title={<span>快速引导</span>} style={{ display: 'flex', flexDirection: 'column', minHeight: 0 }}>
          <div style={{ display: 'grid', gap: 24, flex: '1 1 0', minHeight: 0, overflowY: 'auto' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
              <ApiOutlined style={{ color: '#2F54EB' }} />
              <span>本平台所使用的API皆来自于“火山引擎”平台</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
              <KeyOutlined style={{ color: '#FA8C16' }} />
              <span>请先完成以下步骤以获取所需密钥与权限</span>
            </div>
            <div style={{ background: '#f7fbff', border: '1px solid #e6f4ff', borderRadius: 8, padding: 24 }}>
              <ol style={{ margin: 0, paddingLeft: 20, display: 'grid', gap: 16 }}>
                <li>
                  <span style={{ color: '#666', marginLeft: 6 }}>1. 注册/登录</span>
                  <a href="https://console.volcengine.com/ark/region:ark+cn-beijing/overview?briefPage=0&briefType=introduce&type=new" target="_blank" rel="noreferrer" style={{ color: '#2F54EB', textDecoration: 'underline' }}>火山引擎</a>
                  <span style={{ color: '#666', marginLeft: 6 }}>并自行承担成本</span>
                  <Button
                    shape="circle"
                    size="small"
                    icon={<DownOutlined />}
                    style={{ marginLeft: 8 }}
                    onClick={() => setCostGuideOpen(v => !v)}
                  />
                  {costGuideOpen && (
                    <div style={{ marginTop: 8, padding: 12, border: '1px dashed #d9d9d9', borderRadius: 8, background: '#fafafa' }}>
                      <div style={{ color: '#444', marginBottom: 8 }}>进入火山方舟官网，点击右上角登陆/注册。</div>
                      <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
                        <div style={{ flex: 1 }}>
                          <div style={{ height: 140, border: '1px dashed #c0c0c0', borderRadius: 6, background: '#fff', overflow: 'hidden' }}>
                            <Image
                              src={`/${encodeURI('登录界面.png')}`}
                              alt="登录界面"
                              width="100%"
                              height={140}
                              style={{ display: 'block' }}
                              preview={{ mask: '点击放大' }}
                            />
                          </div>
                        </div>
                        <div style={{ flex: 1, color: '#666' }}>
                          登入后可充值100元左右，为后续使用AI服务与OCR服务提供保障。
                        </div>
                      </div>
                    </div>
                  )}
                </li>
                <li>
                  <span style={{ color: '#666', margin: '0 6px' }}>2. 前往</span>
                  <a href="https://console.volcengine.com/ai/ability/detail/3/2" target="_blank" rel="noreferrer" style={{ color: '#2F54EB', textDecoration: 'underline' }}>开通OCR服务</a>
                  <Button
                    shape="circle"
                    size="small"
                    icon={<DownOutlined />}
                    style={{ marginLeft: 8 }}
                    onClick={() => setOcrGuideOpen(v => !v)}
                  />
                  {ocrGuideOpen && (
                    <div style={{ marginTop: 8, padding: 12, border: '1px dashed #d9d9d9', borderRadius: 8, background: '#fafafa' }}>
                      <div style={{ color: '#444', marginBottom: 8 }}>在“文字识别”栏目下找到“智能文档解析”服务并开通。</div>
                      <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
                        <div style={{ flex: 1 }}>
                          <div style={{ height: 140, border: '1px dashed #c0c0c0', borderRadius: 6, background: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#999' }}>
                            <Image
                              src={`/${encodeURI('OCR开通.png')}`}
                              alt="OCR开通"
                              width="100%"
                              height={140}
                              style={{ display: 'block' }}
                              preview={{ mask: '点击放大' }}
                            />
                          </div>
                        </div>
                        <div style={{ flex: 1, color: '#666' }}>
                          仅需开通“智能文档解析“服务，图中已开通。开通免费，后续按使用量计费。
                        </div>
                      </div>
                    </div>
                  )}
                </li>
                <li>
                  <span style={{ color: '#666', margin: '0 6px' }}>3. </span>
                  <a href="https://console.volcengine.com/iam/keymanage" target="_blank" rel="noreferrer" style={{ color: '#2F54EB', textDecoration: 'underline' }}>查看 Access Key</a>
                </li>
                <li>
                  <span style={{ color: '#666', margin: '0 6px' }}>4. 前往</span>
                  <a href="https://console.volcengine.com/ark/region:ark+cn-beijing/model/detail?Id=deepseek-v3-2" target="_blank" rel="noreferrer" style={{ color: '#2F54EB', textDecoration: 'underline' }}>开通deepseek‑V3.2 251210 模型</a>
                  <Button
                    shape="circle"
                    size="small"
                    icon={<DownOutlined />}
                    style={{ marginLeft: 8 }}
                    onClick={() => setModelGuideOpen(v => !v)}
                  />
                  {modelGuideOpen && (
                    <div style={{ marginTop: 8, padding: 12, border: '1px dashed #d9d9d9', borderRadius: 8, background: '#fafafa' }}>
                      <div style={{ color: '#444', marginBottom: 8 }}>点击右上角”API接入“按钮并按指示步骤开通。</div>
                      <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
                        <div style={{ flex: 1 }}>
                          <div style={{ height: 140, border: '1px dashed #c0c0c0', borderRadius: 6, background: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#999' }}>
                            <Image
                              src={`/${encodeURI('dsv3开通.png')}`}
                              alt="dsv3开通"
                              width="100%"
                              height={140}
                              style={{ display: 'block' }}
                              preview={{ mask: '点击放大' }}
                            />
                          </div>
                        </div>
                        <div style={{ flex: 1, color: '#666' }}>
                          deepseek‑V3.2 性价比较优，为本应用默认AI模型。同样，开通免费，后续按使用量计费。
                        </div>
                      </div>
                    </div>
                  )}
                </li>
                <li>
                  <span style={{ color: '#666', margin: '0 6px' }}>5. </span>
                  <a href="https://console.volcengine.com/ark/region:ark+cn-beijing/apiKey" target="_blank" rel="noreferrer" style={{ color: '#2F54EB', textDecoration: 'underline' }}>查看 API 密钥</a>
                </li>
              </ol>
            </div>
          </div>
        </GlassPanel>

        <GlassPanel 
          title={
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span>{isCollectionMode ? '基础配置' : '基础配置'}</span>
              <Space>
                <span style={{ fontSize: 14, fontWeight: 'normal', color: '#666' }}>已有文献整理合集</span>
                <Switch checked={isCollectionMode} onChange={setIsCollectionMode} />
              </Space>
            </div>
          }
          style={isCollectionMode ? { background: 'rgba(255, 247, 230, 0.9)', borderColor: '#ffd591' } : undefined}
        >
          

          <Form
            layout="vertical"
            onFinish={(vals) => onFinish(vals, isCollectionMode ? '/cluster' : '/upload')}
            form={form}
            initialValues={{
              workingDirectory: './literature_review',
              apiKey: '',
              accessKeyId: '',
              secretAccessKey: ''
            }}
          >
            <Form.Item
              label="OCR ● Access Key ID"
              name="accessKeyId"
              rules={[{ required: true, message: '请输入Access Key ID' }]}
            >
              <Input
                prefix={<KeyOutlined />}
                placeholder="请输入您的Access Key ID"
                size="large"
                className="soft-input"
                suffix={ocrOk === true ? <CheckCircleOutlined style={{ color: '#52C41A' }} /> : ocrOk === false ? <CloseCircleOutlined style={{ color: '#FF4D4F' }} /> : undefined}
              />
            </Form.Item>

            <Form.Item
              label="OCR ● Secret Access Key"
              name="secretAccessKey"
              rules={[{ required: true, message: '请输入Secret Access Key' }]}
            >
              <Input.Password
                prefix={<KeyOutlined />}
                placeholder="请输入您的Secret Access Key"
                size="large"
                className="soft-input"
                suffix={ocrOk === true ? <CheckCircleOutlined style={{ color: '#52C41A' }} /> : ocrOk === false ? <CloseCircleOutlined style={{ color: '#FF4D4F' }} /> : undefined}
              />
            </Form.Item>

            <Form.Item
              label="deepseek-V3.2 ● API密钥"
              name="apiKey"
              rules={[
                { required: true, message: '请输入API密钥' },
                { min: 10, message: 'API密钥长度不能少于10个字符' }
              ]}
            >
              <Input.Password
                prefix={<KeyOutlined />}
                placeholder="请输入您的API密钥"
                size="large"
                className="soft-input"
                suffix={modelOk === true ? <CheckCircleOutlined style={{ color: '#52C41A' }} /> : modelOk === false ? <CloseCircleOutlined style={{ color: '#FF4D4F' }} /> : undefined}
              />
            </Form.Item>

            <Form.Item label="工作目录" help={isCollectionMode ? "请选择包含“文献整理合集”文件夹的父目录" : "请选择一个空文件夹作为工作目录"}>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <Form.Item name="workingDirectory" noStyle rules={[{ required: true, message: '请选择工作目录路径' }]}>
                  <Input
                    prefix={<FolderOutlined />}
                    placeholder={isCollectionMode ? "请选择包含“文献整理合集”的目录" : "请选择空文件夹"}
                    size="large"
                    className="soft-input"
                    disabled
                    style={{ flex: 1 }}
                    suffix={workingDirOk === true ? <CheckCircleOutlined style={{ color: '#52C41A' }} /> : workingDirOk === false ? <CloseCircleOutlined style={{ color: '#FF4D4F' }} /> : undefined}
                  />
                </Form.Item>
                <Button onClick={handlePickDir}>浏览路径</Button>
              </div>
            </Form.Item>

            <Form.Item>
              <Space direction="vertical" style={{ width: '100%' }}>
                <Form.Item shouldUpdate>
                  {({ getFieldsValue }) => {
                    const vals = getFieldsValue();
                    const label = bothApisOk ? (isCollectionMode ? '直接开始文献聚类' : '启动系统') : '测试连接';
                    const disabled = browseBusy || loading || (bothApisOk && workingDirOk !== true);
                    const htmlType = bothApisOk && workingDirOk === true && !browseBusy ? 'submit' : undefined;
                    return (
                      <div style={{ position: 'relative' }}>
                        <Button
                          type="primary"
                          htmlType={htmlType}
                          onClick={label === '测试连接' ? () => { if (browseBusy) return; onTestConnections(vals); } : () => { if (browseBusy) return; startSystem(); }}
                          disabled={disabled}
                          loading={label === '测试连接' ? loading : false}
                          size="large"
                          style={{ width: '100%' }}
                          icon={<RocketOutlined />}
                          className="primary-red-btn"
                        >
                          {label}
                        </Button>
                        {browseBusy && (
                          <div style={{ position: 'absolute', inset: 0, cursor: 'not-allowed', background: 'transparent' }} />
                        )}
                      </div>
                    );
                  }}
                </Form.Item>
                
                
              </Space>
            </Form.Item>
          </Form>
        </GlassPanel>

      </div>
    </PaperShell>
  );
};

export default StartPage;
