import React from 'react';
import { Card, Typography, Tag, Space } from 'antd';
import { FilePdfOutlined } from '@ant-design/icons';

const { Title, Paragraph, Text } = Typography;

interface PaperCardProps {
  title: string;
  authors: string[];
  year: number;
  abstract: string;
  keywords: string[];
  method: string;
  className?: string;
}

const PaperCard: React.FC<PaperCardProps> = ({
  title,
  authors,
  year,
  abstract,
  keywords,
  method,
  className
}) => {
  return (
    <Card 
      className={className}
      hoverable
      style={{ marginBottom: '16px' }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: '16px' }}>
        <FilePdfOutlined style={{ fontSize: '24px', color: '#FF4D4F', marginTop: '4px' }} />
        
        <div style={{ flex: 1 }}>
          <Title level={4} style={{ margin: '0 0 8px 0', fontSize: '16px' }}>
            {title}
          </Title>
          
          <div style={{ marginBottom: '8px' }}>
            <Text type="secondary">
              {authors.join(', ')} • {year}
            </Text>
          </div>
          
          <div style={{ marginBottom: '12px' }}>
            <Tag color="blue">{method}</Tag>
          </div>
          
          <Paragraph 
            ellipsis={{ rows: 3, expandable: true, symbol: '展开' }}
            style={{ marginBottom: '12px' }}
          >
            {abstract}
          </Paragraph>
          
          <div>
            <Space wrap size="small">
              {keywords.map((keyword, index) => (
                <Tag key={index} style={{ fontSize: '12px' }}>
                  {keyword}
                </Tag>
              ))}
            </Space>
          </div>
        </div>
      </div>
    </Card>
  );
};

export default PaperCard;