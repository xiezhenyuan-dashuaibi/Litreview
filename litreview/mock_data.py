mock_papers = [
    {
        "id": "paper_1",
        "title": "基于深度学习的图像识别方法研究",
        "authors": ["张三", "李四", "王五"],
        "year": 2023,
        "abstract": "提出新的深度学习模型，改进卷积神经网络结构。",
        "keywords": ["深度学习", "图像识别", "卷积神经网络", "计算机视觉"],
        "method": "实验研究",
        "conclusion": "准确率提升至95.2%",
        "fileName": "paper_1.pdf",
    },
    {
        "id": "paper_2",
        "title": "自然语言处理中的注意力机制综述",
        "authors": ["李明", "陈华", "赵强"],
        "year": 2022,
        "abstract": "系统回顾注意力机制的发展与应用。",
        "keywords": ["注意力机制", "自然语言处理", "深度学习", "Transformer"],
        "method": "文献综述",
        "conclusion": "在多任务中显著提升性能",
        "fileName": "paper_2.pdf",
    },
]

mock_cluster_schemes = [
    {
        "id": "method_based",
        "name": "方法维度分组",
        "description": "按照研究方法分类",
        "applicableScenario": "适合系统性方法比较",
        "groups": [
            {
                "id": "experimental",
                "name": "实验研究",
                "description": "通过实验验证",
                "papers": ["paper_1"],
                "theme": "实验设计与数据分析",
            },
            {
                "id": "theoretical",
                "name": "理论分析",
                "description": "理论推导与综述",
                "papers": ["paper_2"],
                "theme": "理论分析与文献综述",
            },
        ],
    }
]
