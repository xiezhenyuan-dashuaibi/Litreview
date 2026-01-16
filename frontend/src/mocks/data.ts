import { Paper, SummaryResult, ClusterScheme } from '../types';

export const mockPapers: Paper[] = [
  {
    id: 'paper_1',
    title: '基于深度学习的图像识别方法研究',
    authors: ['张三', '李四', '王五'],
    year: 2023,
    abstract: '本文提出了一种新的深度学习模型，通过改进卷积神经网络结构，在图像识别任务中取得了显著的性能提升。实验结果表明，该方法在多个数据集上都优于现有方法。',
    keywords: ['深度学习', '图像识别', '卷积神经网络', '计算机视觉'],
    method: '实验研究',
    conclusion: '提出的方法在准确率上有显著提升，达到了95.2%的识别准确率。',
    fileName: 'paper_1.pdf'
  },
  {
    id: 'paper_2',
    title: '自然语言处理中的注意力机制综述',
    authors: ['李明', '陈华', '赵强'],
    year: 2022,
    abstract: '注意力机制已成为自然语言处理领域的核心技术。本文系统回顾了注意力机制的发展历程，分析了其在不同任务中的应用效果。',
    keywords: ['注意力机制', '自然语言处理', '深度学习', 'Transformer'],
    method: '文献综述',
    conclusion: '注意力机制在NLP任务中展现出优越性能，是未来研究的重要方向。',
    fileName: 'paper_2.pdf'
  },
  {
    id: 'paper_3',
    title: '强化学习在自动驾驶中的应用研究',
    authors: ['刘涛', '孙丽', '周杰'],
    year: 2023,
    abstract: '本文探讨了强化学习技术在自动驾驶决策系统中的应用。通过设计合适的奖励函数和状态空间，实现了在复杂交通环境下的安全驾驶。',
    keywords: ['强化学习', '自动驾驶', '决策系统', '智能交通'],
    method: '仿真实验',
    conclusion: '强化学习方法能够有效处理自动驾驶中的复杂决策问题。',
    fileName: 'paper_3.pdf'
  },
  {
    id: 'paper_4',
    title: '联邦学习隐私保护机制研究',
    authors: ['吴芳', '郑伟', '何静'],
    year: 2022,
    abstract: '针对联邦学习中的隐私泄露问题，本文提出了一种新的差分隐私保护机制。理论分析和实验验证表明，该机制在保护隐私的同时保持了模型性能。',
    keywords: ['联邦学习', '隐私保护', '差分隐私', '机器学习安全'],
    method: '理论分析+实验',
    conclusion: '提出的隐私保护机制有效平衡了隐私保护和模型效用。',
    fileName: 'paper_4.pdf'
  },
  {
    id: 'paper_5',
    title: '图神经网络在社交网络分析中的应用',
    authors: ['马超', '林娜', '黄磊'],
    year: 2023,
    abstract: '社交网络数据具有复杂的图结构特征。本文利用图神经网络技术，提出了一种新的社交关系挖掘方法，在用户推荐和社群发现任务中表现优异。',
    keywords: ['图神经网络', '社交网络', '关系挖掘', '推荐系统'],
    method: '数据挖掘',
    conclusion: '图神经网络能够有效捕捉社交网络的结构特征和语义信息。',
    fileName: 'paper_5.pdf'
  }
];

export const mockSummaryResults: SummaryResult[] = [
  {
    paperId: 'paper_1',
    title: '基于深度学习的图像识别方法研究',
    background: '图像识别是计算机视觉的核心任务，传统方法在处理复杂场景时存在局限性',
    method: '提出改进的卷积神经网络结构，采用多尺度特征融合和注意力机制',
    conclusion: '在多个数据集上达到95.2%的识别准确率，优于现有方法',
    limitations: '计算复杂度较高，需要进一步优化模型效率',
    markdownPath: '/summaries/paper_1.md',
    status: 'completed'
  },
  {
    paperId: 'paper_2',
    title: '自然语言处理中的注意力机制综述',
    background: '注意力机制已成为NLP领域的重要技术，需要系统性的梳理和总结',
    method: '通过文献调研，分析注意力机制在不同NLP任务中的应用效果',
    conclusion: '注意力机制在机器翻译、文本分类等任务中显著提升性能',
    limitations: '注意力机制的可解释性仍需进一步研究',
    markdownPath: '/summaries/paper_2.md',
    status: 'completed'
  },
  {
    paperId: 'paper_3',
    title: '强化学习在自动驾驶中的应用研究',
    background: '自动驾驶需要处理复杂的交通环境和决策问题',
    method: '设计基于深度强化学习的决策系统，采用DDPG算法进行训练',
    conclusion: '在仿真环境中实现了安全高效的自动驾驶决策',
    limitations: '真实场景中的应用仍需进一步验证',
    markdownPath: '/summaries/paper_3.md',
    status: 'processing'
  }
];

export const mockClusterSchemes: ClusterScheme[] = [
  {
    id: 'method_based',
    name: '方法维度分组',
    description: '按照研究方法进行文献分类，便于比较不同方法的优缺点',
    applicableScenario: '适合对研究方法进行系统性分析和比较的研究',
    groups: [
      {
        id: 'experimental',
        name: '实验研究',
        description: '通过实验验证方法有效性的研究',
        papers: ['paper_1', 'paper_4'],
        theme: '采用实验设计和数据分析的研究方法'
      },
      {
        id: 'theoretical',
        name: '理论分析',
        description: '基于理论推导和分析的研究',
        papers: ['paper_2'],
        theme: '通过理论分析和文献综述开展的研究'
      },
      {
        id: 'simulation',
        name: '仿真研究',
        description: '通过仿真实验验证方法的研究',
        papers: ['paper_3', 'paper_5'],
        theme: '利用仿真环境进行方法验证和性能评估'
      }
    ]
  },
  {
    id: 'application_based',
    name: '应用域分组',
    description: '按照应用领域进行文献分类，突出不同领域的特点',
    applicableScenario: '适合分析AI技术在不同领域的应用现状和趋势',
    groups: [
      {
        id: 'computer_vision',
        name: '计算机视觉',
        description: '图像处理和视觉理解相关的研究',
        papers: ['paper_1'],
        theme: '专注于图像识别、目标检测等视觉任务'
      },
      {
        id: 'nlp',
        name: '自然语言处理',
        description: '文本处理和语言理解相关的研究',
        papers: ['paper_2'],
        theme: '处理文本数据，实现语言理解和生成'
      },
      {
        id: 'autonomous_systems',
        name: '自主系统',
        description: '自动驾驶和智能决策相关的研究',
        papers: ['paper_3', 'paper_4'],
        theme: '构建能够自主决策和学习的智能系统'
      },
      {
        id: 'social_networks',
        name: '社交网络',
        description: '社交网络分析和挖掘相关的研究',
        papers: ['paper_5'],
        theme: '分析社交网络数据，发现社群结构和用户行为模式'
      }
    ]
  },
  {
    id: 'technology_based',
    name: '技术路线分组',
    description: '按照核心技术进行分类，便于技术对比和融合',
    applicableScenario: '适合分析不同AI技术的发展现状和融合趋势',
    groups: [
      {
        id: 'deep_learning',
        name: '深度学习',
        description: '基于深度神经网络的方法',
        papers: ['paper_1', 'paper_2'],
        theme: '利用多层神经网络学习数据特征和模式'
      },
      {
        id: 'reinforcement_learning',
        name: '强化学习',
        description: '通过与环境交互学习最优策略',
        papers: ['paper_3'],
        theme: '通过试错学习，优化决策策略'
      },
      {
        id: 'graph_learning',
        name: '图学习',
        description: '处理图结构数据的学习方法',
        papers: ['paper_4', 'paper_5'],
        theme: '在图结构上进行学习和推理'
      }
    ]
  }
];