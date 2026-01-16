import React, { useEffect, useState, useRef } from 'react';
import { Input, Button } from 'antd';
import { useNavigate } from 'react-router-dom';
import PaperShell from '../components/PaperShell';
import GlassPanel from '../components/GlassPanel';
import { useAppContext } from '../stores/AppContext';
import { generateApi, systemApi } from '../services/api';

type OutlineItem = { key: string; title: string; level: number; parentId?: string; children?: string[] };

const GeneratePage: React.FC = () => {
  const { state, dispatch } = useAppContext();
  const navigate = useNavigate();
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string>('');
  const [editableContent, setEditableContent] = useState('');
  const [isEditing, setIsEditing] = useState(false);
  const [outline, setOutline] = useState<OutlineItem[]>([]);
  const [nodeContents, setNodeContents] = useState<Record<string, string>>({});
  const [activeKey, setActiveKey] = useState<string | null>(null);
  const [draftValue, setDraftValue] = useState<string>('');

  const getDisplayTitle = (key: string | null) => {
    if (!key) return '生成的文章';
    if (key.includes('::h1::')) return key.split('::h1::')[1] || key;
    if (key.includes('::h2::')) return key.split('::h2::')[1] || key;
    if (key.includes('::h3::')) return key.split('::h3::')[1] || key;
    if (key.includes('::h4::')) return key.split('::h4::')[1] || key;
    return key;
  };

  const startedRef = useRef(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    // 只要状态是 idle 且未开始，就自动开始
    // 或者：虽然状态不是 idle (可能是刷新后保留的)，但没有内容且未开始，也重新开始
    const shouldStart = (state.generate.status === 'idle' || !state.generate.content) && !startedRef.current;
    
    if (shouldStart) {
      startedRef.current = true;
      // 如果状态不是 idle，先重置一下确保一致性
      if (state.generate.status !== 'idle') {
          dispatch({ type: 'GENERATE_RESET' });
          // 等待下一个 tick 再开始，或者直接开始（因为 dispatch 是同步的通常没问题，但为了保险起见）
          setTimeout(() => startGeneration(), 0);
      } else {
          startGeneration();
      }
    }
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
        startedRef.current = false;
      }
    };
  }, [state.generate.status]);

  useEffect(() => {
    if (state.generate.content) {
      setEditableContent(state.generate.content);
    }
  }, [state.generate.content]);

  const startGeneration = async () => {
    setGenerating(true);
    setError('');

    try {
      dispatch({ type: 'GENERATE_START' });

      const response = await generateApi.startGeneration({
        schemeId: state.cluster.selectedScheme || 'default',
        model: 'gpt-4',
        temperature: 0.7
      });

      if (response.status === 'success' && response.data) {
        const generationId = (response.data as any).generationId;
        
        // 建立 WebSocket 连接 (使用 127.0.0.1 尝试绕过可能存在的 localhost 代理/拦截)
        const ws = new WebSocket('ws://127.0.0.1:8001/ws/generate/monitor');
        
        ws.onopen = () => {
          ws.send(JSON.stringify({ generationId }));
        };

        ws.onmessage = (event) => {
          try {
            const msg = JSON.parse(event.data);
            
            // 统一排序逻辑
            const getSortedKeys = (keys: string[]) => {
                const sorted = keys.sort((a, b) => {
                    if (a === 'start') return -1;
                    if (b === 'start') return 1;
                    if (a === 'end') return 1;
                    if (b === 'end') return -1;
                    
                    const partsA = a.split('-').map(Number);
                    const partsB = b.split('-').map(Number);
                    
                    // 比较第一部分 (大章)
                    if (partsA[0] !== partsB[0]) return partsA[0] - partsB[0];
                    
                    // 第一部分相同，比较长度 (长度短的在前，如 '0' 在 '0-0' 前)
                    if (partsA.length !== partsB.length) return partsA.length - partsB.length;
                    
                    // 长度也相同 (如 '0-1' vs '0-2')
                    return partsA[1] - partsB[1];
                });
                console.log('[GeneratePage] Sorted keys:', sorted);
                return sorted;
            };

            // 辅助函数：兼容处理字典或字符串内容，并保证顺序
            const processContent = (rawContent: any) => {
                if (typeof rawContent === 'string') return rawContent;
                if (typeof rawContent === 'object' && rawContent !== null) {
                    // 先获取排好序的 key
                    const keys = getSortedKeys(Object.keys(rawContent));
                    // 按顺序提取 value 并拼接
                    return keys.map(key => rawContent[key]).join('\n\n');
                }
                return '';
            };

            // 排序并逐章展示逻辑
            const playContentAnimation = (contentDict: Record<string, string>) => {
                // 使用统一的排序逻辑
                const keys = getSortedKeys(Object.keys(contentDict));

                let currentIndex = 0;
                let currentContent = '';

                // 清空当前内容准备开始动画
                dispatch({
                    type: 'GENERATE_PROGRESS',
                    payload: { progress: 99, content: '', currentSection: '准备展示全文...' }
                });

                const timer = setInterval(() => {
                    if (currentIndex >= keys.length) {
                        clearInterval(timer);
                        dispatch({
                            type: 'GENERATE_COMPLETE',
                            payload: { content: currentContent }
                        });
                        
                        if (currentContent) {
                           const parsed = parseOutline('Generated', currentContent);
                           setOutline(parsed.items);
                           setNodeContents(parsed.contents);
                        }

                        setGenerating(false);
                        ws.close();
                        return;
                    }

                    const key = keys[currentIndex];
                    const sectionContent = contentDict[key];
                    
                    // 追加新章节
                    if (currentContent) currentContent += '\n\n';
                    currentContent += sectionContent;

                    // 更新显示
                    dispatch({
                        type: 'GENERATE_PROGRESS',
                        payload: { 
                            progress: 99, 
                            content: currentContent, 
                            currentSection: `正在展示章节: ${key}` 
                        }
                    });
                    
                    if (currentContent) {
                       const parsed = parseOutline('Generated', currentContent);
                       setOutline(parsed.items);
                       setNodeContents(parsed.contents);
                    }

                    currentIndex++;
                }, 2000); // 每2秒展示一章
            };

            if (msg.type === 'generate_progress') {
               const contentStr = processContent(msg.content);
               dispatch({
                type: 'GENERATE_PROGRESS',
                payload: {
                  progress: msg.progress,
                  content: contentStr,
                  currentSection: msg.currentSection
                }
              });
              
              if (contentStr) {
                 const parsed = parseOutline('Generated', contentStr);
                 setOutline(parsed.items);
                 setNodeContents(parsed.contents);
              }

            } else if (msg.type === 'generate_complete') {
              if (typeof msg.payload.content === 'object' && msg.payload.content !== null) {
                  playContentAnimation(msg.payload.content);
              } else {
                  const finalContentStr = processContent(msg.payload.content);
                  dispatch({
                    type: 'GENERATE_COMPLETE',
                    payload: { content: finalContentStr }
                  });
                  
                  if (finalContentStr) {
                     const parsed = parseOutline('Generated', finalContentStr);
                     setOutline(parsed.items);
                     setNodeContents(parsed.contents);
                  }
                  ws.close();
                  setGenerating(false);
              }
            } else if (msg.type === 'generate_failed') {
              setError(msg.message);
              ws.close();
              setGenerating(false);
            }
          } catch (e) {
            console.error('WS parse error', e);
          }
        };

        ws.onerror = (e) => {
           console.error('WS Error', e);
           setError('连接生成服务失败');
           setGenerating(false);
        };

      } else {
        setError(response.message || '生成失败');
        setGenerating(false);
      }
    } catch (err: any) {
      setError(err.message || '生成失败，请重试');
      setGenerating(false);
    }
  };

  const parseOutline = (sectionName: string, content: string) => {
    const items: OutlineItem[] = [];
    const contents: Record<string, string> = {};
    const lines = content.split('\n');
    const offsets: number[] = [];
    let acc = 0;
    for (let i = 0; i < lines.length; i++) {
      offsets[i] = acc;
      acc += lines[i].length + 1;
    }
    type Root = { title: string; level: number; lineIndex: number; start: number; subs: Sub[] };
    type Sub = { title: string; level: number; lineIndex: number; start: number; leaves: Leaf[] };
    type Leaf = { title: string; level: number; lineIndex: number; start: number };
    
    const roots: Root[] = [];
    let currentRoot: Root | null = null;
    let currentSub: Sub | null = null;

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      if (line.startsWith('# ')) {
        currentRoot = { title: line.replace(/^#\s+/, ''), level: 1, lineIndex: i, start: offsets[i], subs: [] };
        roots.push(currentRoot);
        currentSub = null;
      } else if (line.startsWith('## ')) {
        currentRoot = { title: line.replace(/^##\s+/, ''), level: 2, lineIndex: i, start: offsets[i], subs: [] };
        roots.push(currentRoot);
        currentSub = null;
      } else if (line.startsWith('### ') && currentRoot) {
        currentSub = { title: line.replace(/^###\s+/, ''), level: 3, lineIndex: i, start: offsets[i], leaves: [] };
        currentRoot.subs.push(currentSub);
      } else if (line.startsWith('#### ') && currentSub) {
        currentSub.leaves.push({ title: line.replace(/^####\s+/, ''), level: 4, lineIndex: i, start: offsets[i] });
      }
    }
    const docEnd = content.length;
    for (let hi = 0; hi < roots.length; hi++) {
      const root = roots[hi];
      const nextRootStart = hi + 1 < roots.length ? roots[hi + 1].start : docEnd;
      const rootId = `${sectionName}::h${root.level}::${root.title}`;
      const childKeys: string[] = [];
      const firstSubStart = root.subs.length > 0 ? root.subs[0].start : nextRootStart;
      const rootBaseKey = `${rootId}::base`;
      const rootHeadingLen = lines[root.lineIndex].length + 1;
      contents[rootBaseKey] = content.slice(root.start + rootHeadingLen, firstSubStart);
      
      for (let ji = 0; ji < root.subs.length; ji++) {
        const sub = root.subs[ji];
        const nextSubStart = ji + 1 < root.subs.length ? root.subs[ji + 1].start : nextRootStart;
        const subId = `${sectionName}::h3::${sub.title}`;
        childKeys.push(subId);
        items.push({ key: subId, title: sub.title, level: 3, parentId: rootId });
        contents[subId] = content.slice(sub.start, nextSubStart);
        for (let ki = 0; ki < sub.leaves.length; ki++) {
          const leaf = sub.leaves[ki];
          const nextLeafStart = ki + 1 < sub.leaves.length ? sub.leaves[ki + 1].start : nextSubStart;
          const leafId = `${sectionName}::h4::${leaf.title}`;
          items.push({ key: leafId, title: leaf.title, level: 4, parentId: subId });
          contents[leafId] = content.slice(leaf.start, nextLeafStart);
        }
      }
      items.push({ key: rootId, title: root.title, level: root.level, children: childKeys });
    }
    if (roots.length === 0) {
      const soloId = `${sectionName}::h2::${sectionName}`;
      items.push({ key: soloId, title: sectionName, level: 2, children: [] });
      contents[`${soloId}::base`] = content;
    }
    return { items, contents };
  };

  const simulateGeneration = () => {
    const sections = [
      { name: '引言', content: '# 文献综述\n\n## 引言\n\n随着人工智能技术的快速发展，机器学习和深度学习方法在各个领域都取得了显著的进展。本文通过系统性的文献回顾，分析了当前AI技术在不同应用场景中的研究现状和发展趋势。' },
      { name: '相关工作', content: '\n\n## 相关工作\n\n### 2.1 深度学习在图像识别中的应用\n\n近年来，深度学习技术在图像识别领域取得了突破性进展。张三等人(2023)提出了改进的卷积神经网络结构，通过多尺度特征融合和注意力机制，在多个数据集上达到了95.2%的识别准确率。该方法相比传统方法在准确率上有显著提升，但计算复杂度较高，需要进一步优化模型效率。\n\n### 2.2 自然语言处理中的注意力机制\n\n注意力机制已成为自然语言处理领域的核心技术。李明等人(2022)系统回顾了注意力机制的发展历程，分析了其在机器翻译、文本分类等任务中的应用效果。研究表明，注意力机制在NLP任务中展现出优越性能，但可解释性仍需进一步研究。' },
      { name: '方法分析', content: '\n\n## 方法分析\n\n### 3.1 实验研究方法\n\n实验研究方法在AI领域应用广泛，主要通过设计实验来验证方法的有效性。这类研究通常具有可重复性和量化结果的特点，能够为理论假设提供实证支持。\n\n### 3.2 理论分析方法\n\n理论分析方法主要通过理论推导和文献调研来支撑研究观点。这类研究为领域发展提供了重要的理论基础，有助于深入理解技术原理和发展规律。\n\n### 3.3 仿真研究方法\n\n仿真研究方法利用计算机仿真环境来验证方法的有效性。这类研究能够在可控环境下测试算法性能，为实际应用提供重要参考。' },
      { name: '应用现状', content: '\n\n## 应用现状\n\n### 4.1 计算机视觉领域\n\n在计算机视觉领域，AI技术主要应用于图像识别、目标检测等任务。相关研究专注于提升识别精度和处理速度，为自动驾驶、医疗诊断等应用提供了技术支撑。\n\n### 4.2 自然语言处理领域\n\n自然语言处理领域的研究主要关注文本理解和生成。注意力机制等技术的应用显著提升了机器翻译、文本分类等任务的性能。\n\n### 4.3 自主系统领域\n\n自主系统领域的研究致力于构建能够自主决策和学习的智能系统。强化学习等技术在自动驾驶、机器人控制等应用中表现出色。' },
      { name: '结论与展望', content: '\n\n## 结论与展望\n\n### 5.1 主要结论\n\n通过对相关文献的系统分析，可以得出以下主要结论：\n\n1. 深度学习技术在各个领域都取得了显著进展，但仍面临计算效率和可解释性等挑战。\n2. 不同研究方法各有优势，实验研究提供实证支持，理论分析提供基础支撑，仿真研究提供验证环境。\n3. AI技术的应用范围不断扩大，从传统的图像识别、自然语言处理扩展到更复杂的自主决策系统。\n\n### 5.2 未来展望\n\n未来的研究方向可能包括：\n\n1. 提升AI模型的效率和可解释性\n2. 探索不同研究方法的融合应用\n3. 扩展AI技术在新兴领域的应用\n4. 加强AI技术的安全性和可靠性研究\n\n## 参考文献\n\n[1] 张三, 李四, 王五. 基于深度学习的图像识别方法研究[J]. 计算机学报, 2023, 46(3): 123-135.\n\n[2] 李明, 陈华, 赵强. 自然语言处理中的注意力机制综述[J]. 软件学报, 2022, 33(8): 2456-2470.\n\n[3] 刘涛, 孙丽, 周杰. 强化学习在自动驾驶中的应用研究[J]. 自动化学报, 2023, 49(5): 1023-1035.\n\n[4] 吴芳, 郑伟, 何静. 联邦学习隐私保护机制研究[J]. 通信学报, 2022, 43(12): 78-89.\n\n[5] 马超, 林娜, 黄磊. 图神经网络在社交网络分析中的应用[J]. 计算机研究与发展, 2023, 60(4): 789-801.' }
    ];

    let currentContent = '';
    let currentProgress = 0;

    const generateInterval = setInterval(() => {
      if (currentProgress < sections.length) {
        const sec = sections[currentProgress];
        currentContent += sec.content;
        currentProgress++;
        const parsed = parseOutline(sections[currentProgress - 1].name, sec.content);
        setOutline(prev => {
          const existed = new Set(prev.map(i => i.key));
          const toAdd = parsed.items.filter(i => !existed.has(i.key));
          return [...prev, ...toAdd];
        });
        setNodeContents(prev => ({ ...prev, ...parsed.contents }));
        dispatch({
          type: 'GENERATE_PROGRESS',
          payload: {
            progress: (currentProgress / sections.length) * 100,
            content: currentContent,
            currentSection: currentProgress < sections.length ? sections[currentProgress].name : '完成'
          }
        });
      } else {
        clearInterval(generateInterval);
        dispatch({
          type: 'GENERATE_COMPLETE',
          payload: { content: currentContent }
        });
      }
    }, 2000); // 每2秒生成一个章节
    intervalRef.current = generateInterval;
  };

  const stripH3Body = (raw: string) => {
    const lines = raw.split('\n');
    if (lines.length > 0 && lines[0].startsWith('### ')) {
      return lines.slice(1).join('\n');
    }
    return raw;
  };

  const stripH1Body = (raw: string) => {
    const lines = raw.split('\n');
    if (lines.length > 0 && lines[0].startsWith('# ')) {
      return lines.slice(1).join('\n');
    }
    return raw;
  };

  const stripH2Body = (raw: string) => {
    const lines = raw.split('\n');
    if (lines.length > 0 && lines[0].startsWith('## ')) {
      return lines.slice(1).join('\n');
    }
    return raw;
  };

  const stripH4Body = (raw: string) => {
    const lines = raw.split('\n');
    if (lines.length > 0 && lines[0].startsWith('#### ')) {
      return lines.slice(1).join('\n');
    }
    return raw;
  };

  const visualizeTrailingNewline = (s: string) => (s.endsWith('\n') ? s + '\u00A0' : s);
  const normalizeInput = (s: string) => s.replace(/\u00A0$/, '');

  const buildFullContentFrom = (contents: Record<string, string>) => {
    const roots = outline.filter(i => i.level === 1 || i.level === 2);
    const parts: string[] = [];
    for (const root of roots) {
      const prefix = root.level === 1 ? '# ' : '## ';
      parts.push(`${prefix}${root.title}`);
      const base = (contents[`${root.key}::base`] || '').trim();
      if (base) parts.push(base);
      const h3s = outline.filter(i => i.level === 3 && i.parentId === root.key);
      for (const h3 of h3s) {
        const h3Raw = (contents[h3.key] || '').trim();
        if (h3Raw) parts.push(h3Raw);
        const h4s = outline.filter(i => i.level === 4 && i.parentId === h3.key);
        for (const h4 of h4s) {
          const h4Raw = (contents[h4.key] || '').trim();
          if (h4Raw) parts.push(h4Raw);
        }
      }
    }
    return parts.filter(Boolean).join('\n\n');
  };

  const handleSelectSection = (key: string) => {
    let updated = nodeContents;
    if (activeKey && activeKey.includes('::h3::')) {
      const prev = draftValue;
      const title = activeKey.split('::h3::')[1] || '';
      const raw = `### ${title}\n${prev}`;
      updated = { ...nodeContents, [activeKey]: raw };
      setNodeContents(updated);
    }
    setActiveKey(key);
    if (key.includes('::h1::') || key.includes('::h2::')) {
      const base = updated[`${key}::base`] || '';
      const baseClean = key.includes('::h1::') ? stripH1Body(base) : stripH2Body(base);
      const children = outline.filter(i => i.level === 3 && i.parentId === key);
      const combined = [baseClean, ...children.map(c => updated[c.key] || '')]
        .filter(Boolean)
        .join('\n\n');
      setDraftValue(combined);
    } else {
      const raw = updated[key] || '';
      const body = stripH3Body(raw);
      setDraftValue(body);
    }
  };

  const handleDraftChange = (v: string) => {
    setDraftValue(v);
  };

  const handleSave = () => {
    // 保存编辑后的内容
    dispatch({
      type: 'GENERATE_PROGRESS',
      payload: {
        progress: 100,
        content: editableContent,
        currentSection: '已保存'
      }
    });
    setIsEditing(false);
  };

  const handleDownload = () => {
    // 创建并下载文件
    const blob = new Blob([editableContent], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'literature_review.md';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <PaperShell>
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 24, height: '100%', minHeight: 0, alignItems: 'stretch' }}>
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%', minHeight: 0 }}>
          <GlassPanel 
            title={<span>{getDisplayTitle(activeKey)}</span>}
            style={{ display: 'flex', flexDirection: 'column', flex: '1 1 0', minHeight: 0, overflow: 'hidden' }}
          >
            {activeKey && (activeKey.includes('::h1::') || activeKey.includes('::h2::')) ? (
              <div style={{ flex: 1, minHeight: 0, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 12 }}>
                {(() => {
                  const baseClean = activeKey.includes('::h1::') 
                    ? stripH1Body(nodeContents[`${activeKey}::base`] || '')
                    : stripH2Body(nodeContents[`${activeKey}::base`] || '');
                  return baseClean ? (
                    <div style={{ flex: '0 0 auto' }}>
                      <Input.TextArea
                        value={visualizeTrailingNewline(baseClean)}
                        onChange={e => setNodeContents(s => ({ ...s, [`${activeKey}::base`]: normalizeInput(e.target.value) }))}
                        autoSize={{ minRows: 2 }}
                      />
                    </div>
                  ) : null;
                })()}
                {outline.filter(i => i.level === 3 && i.parentId === activeKey).map(h3 => (
                  <div key={h3.key} style={{ marginTop: 8 }}>
                    <div style={{ fontWeight: 700, color: '#999', userSelect: 'none', pointerEvents: 'none' }}>{`### ${h3.title}`}</div>
                    <div style={{ flex: '0 0 auto' }}>
                      <Input.TextArea
                        value={visualizeTrailingNewline(stripH3Body(nodeContents[h3.key] || ''))}
                        onChange={e => setNodeContents(s => ({ ...s, [h3.key]: `### ${h3.title}\n${normalizeInput(e.target.value)}` }))}
                        autoSize={{ minRows: 2 }}
                      />
                    </div>
                    {outline.filter(i => i.level === 4 && i.parentId === h3.key).map(h4 => (
                      <div key={h4.key} style={{ marginTop: 6, marginLeft: 12 }}>
                        <div style={{ fontWeight: 700, color: '#bbb', userSelect: 'none', pointerEvents: 'none' }}>{`#### ${h4.title}`}</div>
                        <div style={{ flex: '0 0 auto' }}>
                          <Input.TextArea
                            value={visualizeTrailingNewline(stripH4Body(nodeContents[h4.key] || ''))}
                            onChange={e => setNodeContents(s => ({ ...s, [h4.key]: `#### ${h4.title}\n${normalizeInput(e.target.value)}` }))}
                            autoSize={{ minRows: 2 }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            ) : (!activeKey ? (
              <div style={{ flex: 1, minHeight: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#999' }}>
                请点击右侧目录选择
              </div>
            ) : (
              <div style={{ flex: 1, minHeight: 0, overflowY: 'auto' }}>
                <Input.TextArea 
                  value={visualizeTrailingNewline(draftValue)}
                  onChange={e => handleDraftChange(normalizeInput(e.target.value))}
                  autoSize={{ minRows: 2 }}
                />
              </div>
            ))}
          </GlassPanel>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%', minHeight: 0 }}>
          <GlassPanel 
            title={<span>已生成目录</span>}
            extra={<span style={{ fontSize: 15, color: '#999' }}>请勿刷新页面！</span>}
            style={{ display: 'flex', flexDirection: 'column', flex: '1 1 0', minHeight: 0, overflow: 'hidden' }}
          >
            <div style={{ overflowY: 'auto', flex: 1, minHeight: 0 }}>
              {outline.filter(i => i.level === 1 || i.level === 2).map(root => (
                <div key={root.key} style={{ marginBottom: 8 }}>
                  <div
                    onClick={() => handleSelectSection(root.key)}
                    style={{
                      padding: '10px 12px',
                      borderRadius: 8,
                      background: activeKey === root.key ? '#fff' : 'transparent',
                      boxShadow: activeKey === root.key ? '0 6px 16px rgba(0,0,0,0.06)' : 'none',
                      cursor: 'pointer',
                      fontWeight: 700,
                      fontSize: root.level === 1 ? '1.1em' : '1em'
                    }}
                  >
                    {root.title}
                  </div>
                  {outline.filter(i => i.level === 3 && i.parentId === root.key).map(h3 => (
                    <div
                      key={h3.key}
                      onClick={() => handleSelectSection(h3.key)}
                      style={{
                        marginTop: 6,
                        marginLeft: 12,
                        padding: '8px 10px',
                        borderRadius: 8,
                        background: activeKey === h3.key ? '#fff' : 'transparent',
                        boxShadow: activeKey === h3.key ? '0 6px 16px rgba(0,0,0,0.06)' : 'none',
                        cursor: 'pointer'
                      }}
                    >
                      {h3.title}
                    </div>
                  ))}
                </div>
              ))}
            </div>
            <div style={{ marginTop: 12, borderTop: '1px solid #eee', paddingTop: 12, flex: '0 0 auto', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
              {state.generate.status !== 'completed' ? (
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <div className="animate-pulseGlow" style={{ width: 10, height: 10, borderRadius: '50%', background: '#2F54EB' }} />
                  <span>{state.generate.currentSection || 'AI正在生成，约10分钟...'}</span>
                </div>
              ) : (
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span
                    onClick={async () => {
                      try {
                        await systemApi.openRawContentFolder();
                      } catch {
                      }
                    }}
                    style={{ fontSize: 12, color: '#2F54EB', cursor: 'pointer', userSelect: 'none', textDecoration: 'underline' }}
                  >
                    若存在乱序，可手动排序
                  </span>
                  <Button onClick={() => window.location.reload()}>
                    重新生成
                  </Button>
                  <Button
                    type="primary"
                    onClick={() => {
                      let working = nodeContents;
                      if (activeKey && activeKey.includes('::h3::')) {
                        const title = activeKey.split('::h3::')[1] || '';
                        working = { ...working, [activeKey]: `### ${title}\n${draftValue}` };
                        setNodeContents(working);
                      } else if (activeKey && activeKey.includes('::h4::')) {
                        const title = activeKey.split('::h4::')[1] || '';
                        working = { ...working, [activeKey]: `#### ${title}\n${draftValue}` };
                        setNodeContents(working);
                      }
                      const full = buildFullContentFrom(working);
                      dispatch({ type: 'GENERATE_PROGRESS', payload: { progress: 100, content: full, currentSection: '完成' } });
                      navigate('/result');
                    }}
                  >
                    确定 →
                  </Button>
                </div>
              )}
            </div>
          </GlassPanel>
        </div>
      </div>
    </PaperShell>
  );
};

export default GeneratePage;
