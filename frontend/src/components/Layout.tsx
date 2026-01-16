import React from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { Layout as AntLayout, Menu, Button } from 'antd';
import { 
  HomeOutlined, 
  UploadOutlined, 
  FileTextOutlined, 
  ClusterOutlined,
  MessageOutlined,
  EditOutlined,
  CheckCircleOutlined 
} from '@ant-design/icons';
import { useAppContext } from '../stores/AppContext';

const { Header, Sider, Content } = AntLayout;

const Layout: React.FC = () => {
  const { state } = useAppContext();
  const location = useLocation();
  const navigate = useNavigate();

  const currentKey = location.pathname.slice(1);
  const baseMenuItems = [
    {
      key: 'upload',
      icon: <UploadOutlined />,
      label: '文件上传',
      disabled: !state.system.isInitialized
    },
    {
      key: 'summary',
      icon: <FileTextOutlined />,
      label: '文献摘要',
      disabled: !state.upload.taskId
    },
    {
      key: 'cluster',
      icon: <ClusterOutlined />,
      label: '聚类分析',
      disabled: state.summary.status !== 'completed'
    },
    {
      key: 'plan',
      icon: <MessageOutlined />,
      label: '方案展示',
      disabled: state.cluster.schemes.length === 0
    },
    {
      key: 'generate',
      icon: <EditOutlined />,
      label: '综述生成',
      disabled: !state.cluster.selectedScheme
    },
    {
      key: 'result',
      icon: <CheckCircleOutlined />,
      label: '结果查看',
      disabled: state.generate.status !== 'completed'
    }
  ];

  const handleMenuClick = (key: string) => {
    navigate(`/${key}`);
  };

  

  return (
    <AntLayout style={{ minHeight: '100vh' }} className="paper-bg serif">
      <Header style={{ 
        background: 'rgba(255,255,255,0.7)', 
        padding: '0 24px', 
        display: 'flex', 
        alignItems: 'center',
        justifyContent: 'space-between',
        borderBottom: '1px solid rgba(0,0,0,0.06)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <h2 className="serif ink-text" style={{ margin: 0 }}>AI文献综述生成器</h2>
        </div>
        
      </Header>
      
      <AntLayout>
        <Sider width={200} style={{ background: 'rgba(255,255,255,0.7)' }}>
          <Menu
            mode="inline"
            selectedKeys={[currentKey]}
            items={baseMenuItems}
            onClick={() => {}}
            style={{ height: '100%', borderRight: 0 }}
          />
        </Sider>
        
        <Content style={{ 
          margin: '16px 24px 24px', 
          padding: '24px', 
          background: 'rgba(255,255,255,0.75)',
          borderRadius: '16px',
          boxShadow: '0 10px 30px rgba(0,0,0,0.06)',
          border: '1px solid rgba(255,255,255,0.6)',
          display: 'flex',
          flexDirection: 'column',
          flex: '1 1 0',
          minHeight: 0,
          overflow: 'hidden'
        }} className="serif">
          <Outlet />
        </Content>
      </AntLayout>
    </AntLayout>
  );
};

export default Layout;
