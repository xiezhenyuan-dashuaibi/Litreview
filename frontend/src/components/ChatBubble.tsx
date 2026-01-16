import React from 'react';

interface ChatBubbleProps {
  type: 'user' | 'assistant';
  content: string;
  timestamp?: string;
}

const ChatBubble: React.FC<ChatBubbleProps> = ({ type, content, timestamp }) => {
  const isUser = type === 'user';
  return (
    <div style={{ display: 'flex', justifyContent: isUser ? 'flex-end' : 'flex-start', padding: '8px 0' }}>
      <div
        className="glass-card"
        style={{
          maxWidth: '70%',
          padding: '12px 16px',
          borderRadius: 12,
          background: isUser ? 'linear-gradient(135deg, #ff4d4f, #d22b2b)' : 'rgba(255,255,255,0.75)',
          color: isUser ? '#fff' : '#333'
        }}
      >
        <div style={{ whiteSpace: 'pre-wrap' }}>{content}</div>
        {timestamp && (
          <div style={{ fontSize: 12, opacity: 0.7, marginTop: 8, textAlign: 'right' }}>{timestamp}</div>
        )}
      </div>
    </div>
  );
};

export default ChatBubble;

