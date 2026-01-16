import plotly.graph_objects as go
import plotly.colors as pc
import numpy as np
import textwrap
from collections import Counter
from .core_algorithm import comprehensive_process_function
from .system_service import  AI_call
import os
import re



def plot_swimlane(categories_dict, papers_dict):
    """
    接收原始数据字典，内部进行布局计算、坐标映射、统计分析并绘图。
    """
    # ==========================================
    # 1. 解析分类结构与布局计算
    # ==========================================
    # 辅助函数：解析标签 '0' -> (0, -1), '0-1' -> (0, 1) 用于排序
    def parse_key(k):
        parts = list(map(int, k.split('-')))
        if len(parts) == 1: return (parts[0], -1) # 父类排前面
        return tuple(parts)

    # 对 keys 进行排序，确保绘图顺序：父类0 -> 子类0-0, 0-1... -> 父类1...
    sorted_keys = sorted(categories_dict.keys(), key=parse_key)
    
    # 重构层级结构以便绘图
    # 结构: {p_id: {'desc': str, 'children': [{'id': str, 'desc': str}]}}
    hierarchy = {}
    for k in sorted_keys:
        parts = list(map(int, k.split('-')))
        p_id = parts[0]
        if p_id not in hierarchy:
            hierarchy[p_id] = {'desc': "", 'children': []}
            
        if len(parts) == 1:
            hierarchy[p_id]['desc'] = categories_dict[k]
        else:
            hierarchy[p_id]['children'].append({
                'id': k, 
                'desc': categories_dict[k],
                'sort_id': parts[1]
            })

    # 分配颜色和Y轴坐标
    colors = pc.qualitative.Pastel
    
    layout_data = [] # 用于绘制左侧表头
    label_to_y = {}  # 映射表：'0-1' -> 绝对Y坐标 (用于画点)
    row_colors = {}  # 映射表：绝对Y坐标 -> 颜色
    
    current_y = 0
    
    for p_id in sorted(hierarchy.keys()):
        p_info = hierarchy[p_id]
        children = sorted(p_info['children'], key=lambda x: x['sort_id'])
        
        if not children: continue
        
        p_color = colors[p_id % len(colors)]
        p_y_start = current_y
        
        children_layout_info = []
        
        for child in children:
            # 记录映射
            label_to_y[child['id']] = current_y
            row_colors[current_y] = p_color
            
            children_layout_info.append({
                'label': child['id'],
                'description': child['desc'],
                'y_center': current_y + 0.5,
                'y_start': current_y,
                'y_end': current_y + 1
            })
            current_y += 1
            
        # 记录父类布局信息
        layout_data.append({
            'label': f"父类 {p_id}",
            'description': p_info['desc'],
            'y_start': p_y_start,
            'y_end': current_y, # 到所有子类结束
            'center': (p_y_start + current_y) / 2,
            'color': p_color,
            'children': children_layout_info
        })
        
    total_rows = current_y

    # ==========================================
    # 2. 处理文献数据 (计算坐标与活跃期)
    # ==========================================
    scatter_x = []
    scatter_y = []
    scatter_c = []
    
    # 用于统计每个赛道的实际绘图坐标 (X轴)
    # 改为记录包含抖动的实际坐标，而非原始年份，以确保横线与点的位置精确匹配
    x_coords_by_label = {lbl: [] for lbl in label_to_y.keys()}
    
    np.random.seed(42) # 固定绘图时的抖动随机性
    
    all_years = [] # 用于动态计算横轴范围

    for title, info in papers_dict.items():
        lbl = info['label']
        year = info['year']
        
        if lbl not in label_to_y: continue # 跳过未知的分类
        
        # 计算抖动坐标
        base_y = label_to_y[lbl]
        jitter_x = np.random.uniform(0.1, 0.9)
        jitter_y = np.random.uniform(0.1, 0.9)
        
        final_x = year + jitter_x
        final_y = base_y + jitter_y
        
        # 收集实际坐标
        x_coords_by_label[lbl].append(final_x)
        
        scatter_x.append(final_x)
        scatter_y.append(final_y)
        scatter_c.append(row_colors[base_y])
        all_years.append(final_x)

    # 计算活跃期线条 (15% - 85%)
    lines_by_color = {}
    
    for lbl, x_vals in x_coords_by_label.items():
        if not x_vals: continue
        
        # 使用实际坐标计算分位数
        p15 = np.percentile(x_vals, 15)
        p85 = np.percentile(x_vals, 85)
        
        y_center = label_to_y[lbl] + 0.5
        c = row_colors[label_to_y[lbl]]
        
        if c not in lines_by_color:
            lines_by_color[c] = {'x': [], 'y': []}
            
        lines_by_color[c]['x'].extend([p15, p85, None])
        lines_by_color[c]['y'].extend([y_center, y_center, None])

    # 动态计算横轴范围
    if all_years:
        plot_range = [int(np.floor(min(all_years))), int(np.ceil(max(all_years)))]
    else:
        plot_range = [1975, 2030] # 默认兜底

    # ==========================================
    # 3. 开始绘图
    # ==========================================
    fig = go.Figure()
    shapes = []
    
    SPLIT_POINT = 0.12 
    COL_1_WIDTH = SPLIT_POINT / 2
    GAP = 0.05

    # 辅助函数：为 Plotly 悬浮标签进行文本换行，并保留原有的换行结构
    def wrap_html(text, width=60):
        if not text: return ""
        # 先按原始换行符分割，对每一段分别进行 wrap，确保“1. 2.”的结构不被破坏
        paragraphs = text.split('\n')
        wrapped_paragraphs = []
        for para in paragraphs:
            if para.strip():
                wrapped_paragraphs.extend(textwrap.wrap(para, width=width))
            else:
                wrapped_paragraphs.append("") # 保留空行
        return "<br>".join(wrapped_paragraphs)

    # --- A. 绘制左侧表头 ---
    for p_data in layout_data:
        # 父类块
        shapes.append(dict(
            type="rect", xref="paper", yref="y",
            x0=0, x1=COL_1_WIDTH,
            y0=p_data['y_start'] + GAP, y1=p_data['y_end'] - GAP,
            fillcolor=p_data['color'], line=dict(width=2, color="white"), layer="below"
        ))
        # 父类文字
        fig.add_trace(go.Scatter(
            x=[COL_1_WIDTH/2], y=[p_data['center']],
            xaxis='x2', yaxis='y',
            text=[p_data['label']], mode='text',
            textfont=dict(size=14, color="black", weight="bold"),
            hovertext=[wrap_html(p_data['description'])], hoverinfo='text', showlegend=False
        ))

        for c_data in p_data['children']:
            # 子类块
            shapes.append(dict(
                type="rect", xref="paper", yref="y",
                x0=COL_1_WIDTH, x1=SPLIT_POINT,
                y0=c_data['y_start'] + GAP, y1=c_data['y_end'] - GAP,
                fillcolor=p_data['color'], opacity=0.6,
                line=dict(width=1, color="white"), layer="below"
            ))
            # 子类文字
            fig.add_trace(go.Scatter(
                x=[(COL_1_WIDTH + SPLIT_POINT)/2], y=[c_data['y_center']],
                xaxis='x2', yaxis='y',
                text=[c_data['label']], mode='text',
                textfont=dict(size=11, color="black"),
                hovertext=[wrap_html(c_data['description'])], hoverinfo='text', showlegend=False
            ))
            # 分割线
            shapes.append(dict(
                type="line", xref="paper", yref="y",
                x0=SPLIT_POINT, x1=1,
                y0=c_data['y_start'], y1=c_data['y_start'],
                line=dict(color="#eeeeee", width=1), layer="below"
            ))

    # --- B. 绘制活跃期线条 ---
    for color_code, coords in lines_by_color.items():
        fig.add_trace(go.Scatter(
            x=coords['x'], y=coords['y'],
            xaxis='x', yaxis='y',
            mode='lines',
            line=dict(width=6, color=color_code),
            opacity=0.5, hoverinfo='skip', showlegend=False
        ))

    # --- C. 绘制文献散点 ---
    fig.add_trace(go.Scatter(
        x=scatter_x, y=scatter_y,
        xaxis='x', yaxis='y',
        mode='markers',
        marker=dict(
            size=5, color=scatter_c, opacity=0.9,
            line=dict(width=0.5, color='black')
        ),
        hoverinfo='skip', showlegend=False
    ))

    # --- D. 布局设置 ---
    fig.update_layout(
        title="学科发展脉络 - 文献分布热力散点图",
        height=max(800, total_rows * 50), # 动态高度，每行至少50px
        width=1200,
        plot_bgcolor="white",
        shapes=shapes,
        xaxis=dict(
            domain=[SPLIT_POINT, 1], range=plot_range,
            title="发表年份", showgrid=True, gridcolor="#f0f0f0",
            tickmode='linear', dtick=1, zeroline=False
        ),
        xaxis2=dict(
            domain=[0, SPLIT_POINT], range=[0, SPLIT_POINT],
            showgrid=False, showticklabels=False, zeroline=False, fixedrange=True
        ),
        yaxis=dict(
            range=[0, total_rows],
            showticklabels=False, showgrid=False, zeroline=False
        ),
        hoverlabel=dict(
            bgcolor="white",
            font_size=13,
            font_family="Microsoft YaHei",
            align="left"
        ),
        margin=dict(l=20, r=20, t=60, b=40)
    )

    return fig

def construct_swimlane_data(anchor, cluster_keywords_map, sub_results_storage):
    """
    根据第一轮和第二轮的聚类结果，构造 plot_swimlane 所需的数据结构。
    """
    # 初始化目标字典
    categories_dict = {}
    papers_dict = {}

    # --- 1. 构造 categories_dict (分类体系) ---

    # 添加父类描述 (来自第一轮 anchor + keywords)
    for p_id, p_desc in anchor.items():
        if p_id == -1: continue # 略过噪音
        # 获取第一轮的关键词
        p_kws = cluster_keywords_map.get(p_id, "暂无关键词")
        
        # 处理关键词列表为字符串
        if isinstance(p_kws, list):
            p_kws_str = " ".join(p_kws)
        else:
            p_kws_str = str(p_kws)

        # 按照用户要求的格式组合字符串
        categories_dict[str(p_id)] = f"1. 分类描述\n{p_desc}\n2. 内容关键词\n{p_kws_str}"

    # 添加子类描述 (来自 sub_results_storage)
    for p_id, sub_data in sub_results_storage.items():
        sub_anchors = sub_data['anchor']    # 第二轮生成的子类锚点描述
        sub_keywords = sub_data['keywords'] # 第二轮生成的子类关键词
        
        for s_id, s_desc in sub_anchors.items():
            if s_id == -1: continue # 略过噪音
            
            # 获取该子类的关键词
            s_kws = sub_keywords.get(s_id, "暂无关键词")
            # 处理关键词列表为字符串
            if isinstance(s_kws, list):
                s_kws_str = " ".join(s_kws)
            else:
                s_kws_str = str(s_kws)
                
            # 构造 "父类ID-子类ID" 格式
            cat_key = f"{p_id}-{s_id}"
            categories_dict[cat_key] = f"1. 分类描述\n{s_desc}\n2. 内容关键词\n{s_kws_str}"

    # --- 2. 构造 papers_dict (文献数据) ---

    for p_id, sub_data in sub_results_storage.items():
        res2 = sub_data['results']  # 第二轮该父类下的所有文献
        for title, meta in res2.items():
            s_id = meta['label']
            if s_id == -1: continue # 略过噪音
            
            # 构造 papers_dict 的 Entry
            papers_dict[title] = {
                "label": f"{p_id}-{s_id}",  # 映射到具体的子类
                "year": meta.get('year', 2024) # 如果没有年份，给定默认值
            }

    # --- 3. 验证数据结构 (可选) ---
    print(f"成功构造 categories_dict，包含 {len(categories_dict)} 个分类")
    print(f"成功构造 papers_dict，包含 {len(papers_dict)} 篇文献")
    
    return categories_dict, papers_dict


def build_context_text(anchor, cluster_keywords_map, sub_results_storage):
        """
        从聚类结果中提取结构化文本，用于 Prompt 上下文
        """
        context_lines = []
        
        # 遍历所有父类
        for p_id in sorted([pid for pid in anchor.keys() if pid != -1]):
            p_desc = anchor[p_id]
            p_kws = cluster_keywords_map.get(p_id, [])
            
            context_lines.append(f"【主要研究方向 {p_id}】")
            context_lines.append(f"  - 宏观描述: {p_desc}")
            context_lines.append(f"  - 核心关键词: {p_kws}")
            context_lines.append(f"  - 下属细分分支:")
            
            # 获取该父类下的子类信息
            if p_id in sub_results_storage:
                sub_data = sub_results_storage[p_id]
                sub_anchors = sub_data['anchor']
                sub_keywords = sub_data['keywords']
                
                for s_id in sorted([sid for sid in sub_anchors.keys() if sid != -1]):
                    s_desc = sub_anchors[s_id]
                    s_kws = sub_keywords.get(s_id, [])
                    context_lines.append(f"    （分支 {p_id}-{s_id}）")
                    context_lines.append(f"      * 分支描述: {s_desc}")
                    context_lines.append(f"      * 分支关键词: {s_kws}")
            
            context_lines.append("") # 空行分隔
            
        return "\n".join(context_lines)

def gen_outline(anchor, cluster_keywords_map, sub_results_storage,paper_desc = "暂未提供"):
    # 构建完整的上下文信息
    research_context = build_context_text(anchor, cluster_keywords_map, sub_results_storage)
    gen_outline_prompt = f"""# 上下文背景

## 情景角色

你是一位在顶级期刊中撰写文献综述综述的主编，当前正在为一篇研究论文编撰文献综述。在你面前的工作流程中，你们已经阅读了指定领域众多的文献，并且将这些文献按照宏观领域进行了切分，以及按照分支梳理了脉络，现在你需要根据当前的成果，计划出一份逻辑严密、叙事流畅、引人入胜的文献综述大纲以及写作指导方案。

## 你们正在撰写的研究论文

{paper_desc}

---

# 任务书

在你前面的工作中，你们已经将众多文献进行了有意识的分类与梳理，并且整理成了资料。你的核心任务是将这些离散的、碎片化的分类资料，重构为一份**逻辑严密、叙事流畅、引人入胜的文献综述大纲**。请注意：你的工作**不是**简单的“填空题”（把分类描述信息填进大纲），而是**“编剧”**（构建领域脉络故事线）。你对于章节的划分需要跟随前面工作已有的分类，但你可以打破原有的 Label ID 顺序，挑选一种学术发展的内在逻辑来重新编排章节顺序，同时也可以对原有的类型的描述与定位进行优化，最终的目的是为你们正在撰写的研究论文写一份适配的文献综述，力求文献综述的章节逻辑形成一条连贯的河流，而非一盘散沙。

## 核心思维路径

1.  **深度逻辑重构（第一步，至关重要）**：
    * 阅读所有【主要研究方向】与下属细分分支，并分析它们之间的深层联系：是时间上的演进？是“理论-方法-应用”的层级？还是“核心问题-多种解决路径或视角”的对抗？又或是其他某种学术上的侧重点的联系？
    * **抛弃原有的 ID 顺序**。根据你发现的逻辑链条，重新规划章节的出场顺序。

2.  **构建叙事弧光**：
    * 确立全文的主旨：我们要写的文献综述准备讲一个怎样的“科学故事”？
    * 确定我们要讲什么样的科学故事之后，再基于第一步所规划的章节顺序，以”讲故事“的内核思考该以什么样的描述语言来串联起各章节之间的逻辑关系，构思每个章节的叙事线索、过渡句、突出点、语言风格等。

3.  **编写导演剧本（写作指导）**：
    * 在每个章节下提供**【写作指导】**，告诉未来的作者：这一部分该怎么写？如何进行说理才能让读者明白该章节的重要性、定位、与其他章节的联系？该怎么引入与承接上文？该以什么线索进行叙事（例如强调某种冲突）？该如何优雅地过渡到下一章？这样才能让读者更加明了该领域的发展地图。
    * 每一个【写作指导】都需要考虑到该模块写作时的启承转合，追踪描述该模块具体的每一语义单元该如何写作，也即该模块先写...，再以什么样的逻辑转而写...，最后...。
    * **拒绝平铺直叙，注重逻辑桥接**，不要写成“第一部分讲A，第二部分讲B”，而要采用**“以观点或视角为中心”**的写法。挑选一种学术的内在逻辑来编排以上内容，同时优化其描述方式，使文献综述整体形成一条连贯的河流，而非一盘散沙。
    * 深刻理解**学术论文中的“讲故事”思维**，学术论文中的“讲故事”并非使用比喻等修辞手法绘声绘色地描述研究内容，文献综述的语言风格仍旧需要保持严谨专业，学术论文中的“讲故事”是指在梳理文献发展脉络时，每个章节模块间都有清晰的逻辑以及语言承接，例如由A发展到B，或者C与D之间具有对比等等，在叙述时具有故事性。
    * 你可以指导后续的作者花较多的笔墨来桥接每个章节，例如使用较多的承接、引入、对比、推理等手段来让读者明白为什么要写该章节、该章节为什么重要、该章节与前一章节之间的联系等，这也是形成学术论文中的“讲故事”感的重要方式。

## 输出结构示例

在你的输出中，你需要且仅需要以md的格式给出文献综述的大纲以及每个模块的写作思路与要求，除此之外不要输出其他任何内容。
注意在一级标题和二级标题之后，需要依据格式标注出该部分对应了哪个研究分类，在“【】”中标注出该类型的id，父分类（parent class）仅需标注出p_id（如【0】），子分类（sub class）则需标注出p_id-s_id（如【1-2】），**注意【】之中没有空格，例如【1-2】不能写成【1 - 2】**。
请参考以下格式输出（仅为格式示例，最终内容请根据实际情况，经过严密思考后给出）：
```example
# [综述总标题：精准概括研究领域的核心主题]
...（此处叙述本文献综述的总的**写作思路指导**，你需要思考以什么样的逻辑、视角将当前的分类逻辑串联起来，告诉未来的作者如何这里以“讲故事”的感觉进行写作，例如“此模块大致叙述该领域当前发展情况，逻辑严密、叙事流畅、引人入胜地叙述...视角下的学术研究是如何发展的，因此本文献综述将以...的逻辑梳理该领域的文献，...。”，300-500字左右。）

## 1. [一级标题] - 对应主要研究方向【p_id1】
...（此处叙述该模块的**写作思路指导**，你需要思考该怎样简单承接前文并“讲故事”般梳理该章节中几个子章节的联系，告诉未来的作者这里需要怎么写，例如“作为第一部分的总描述，此模块不仅需要...来简单承接上文，还需要...来引入下文，此处可以以...的逻辑，以...的话术再叙述...，从而引入...，润滑章节间的联系...。”，200-400字左右。）

### 1.1 [二级标题] - 对应分支【p_id1-s_id2】
...（此处叙述该模块的**写作思路指导**，你需要思考该如何整理思路逻辑并丝滑引入对文献的具体介绍中，提出写作逻辑与要求来告诉未来的作者这里需要怎么写，例如“此处可以按照...的逻辑来讲述研究发展的故事，从...入手，再讲到...，以...话术来进行转折，最后开始对文献进行详细介绍...。要求不要单纯罗列文献，而要指出...，...。“，300-500字左右。）

### 1.2 [二级标题] - 对应分支【p_id1-s_id1】
...（此处叙述该模块的**写作思路指导**，类似的，你需要思考该如何承接上一部分并引入本部分的内容，提出写作逻辑与要求来告诉未来的作者这里需要怎么写，例如“此处需要...来承接上文，并通过...话术来引入本部分的文献综述。对文献进行综述的时候可以采用...的思路，先以...话术来...，再以...话术来...，再...，...。在具体写作的时候需要凸显该分支...，重点描述...。”，300-500字左右。）

## 2. [一级标题] - 对应主要研究方向【p_id3】
...（同）

...

## 4. 文献总结与展望
...（最后的固定章节是文献总结与展望，你同样需要指导该部分应如何写作，300-600字左右。）
```
以上仅仅是示例，在具体的回答中，对每个模块的写作思路指导都需要具体描述，逻辑越清晰、指导越学术，越好，且不能在大纲内容前后添加任何额外的内容（例如额外的讲解）。

---

# 研究领域分类详情

{research_context}

---

# 关键提示


请根据以上**任务书**以及**研究领域分类详情**，计划出一份逻辑严密、叙事流畅、引人入胜的文献综述大纲与写作指导方案。尤其关注任务书中核心思维路径部分的要求，你的输出案例如下（仅供参考风格，内容需根据实际素材生成）：

# ...
...（300-500字左右。）

## 1. ... - 对应主要研究方向【...】
...（200-400字左右。）

### 1.1 ... - 对应分支【...】
...（300-500字左右。）

### 1.2 ... - 对应分支【...】
...（300-500字左右。）

## 2. ... - 对应主要研究方向【...】
...（200-400字左右。）

### 2.1 ... - 对应分支【...】
...（300-500字左右。）

### 2.2 ... - 对应分支【...】
...（300-500字左右。）

## 3 文献总结与展望
...（300-500字左右。）

以上仅仅是一个简单的回复结构示例，你需要做严谨的思考与详细扎实的工作，每一个【写作指导】都需要考虑到该模块写作时的启承转合，追踪描述该模块具体的每一语义单元该如何写作。
请根据以上要求，开始构思并输出这份文献综述大纲与写作指导方案，语言精炼，7000字以内。"""

    try:
        # 获取 API 配置
        api_key = os.environ.get('ARK_API_KEY', '')
        model_name = os.environ.get('ARK_MODEL', 'deepseek-v3-2-251201')
                
        # 调用 AI
        outline_resp = AI_call(gen_outline_prompt, api_key, model_name)
        outline_dict = {}
        
        # 使用更稳健的策略：
        # 1. ^(#+\s+.*?) -> 捕获标题行的大部分内容 (Group 1)
        # 2. 【(\d+(?:-\d+)?)】 -> 锚定行尾的 ID (Group 2)
        # 中间的 .*? 会自动吞掉 ID 前面的分隔符（如空格、- 等）
        # 但为了防止 Group 1 匹配太短（只匹配到 #），我们需要让中间部分尽可能明确
        # 最好的办法是：捕获整个行，然后在代码里拆
        pattern = re.compile(r'^(#+\s+.*?)【(\d+(?:-\d+)?)】\s*$', re.MULTILINE)
        
        # 1. 先找到所有匹配的标题行及其位置
        matches = list(pattern.finditer(outline_resp))
        
        # [补丁] 提取 'start' 部分 (第一个匹配标题之前的所有内容)
        if matches:
            start_content = outline_resp[:matches[0].start()].strip()
            if start_content:
                outline_dict['start'] = start_content
        
        # 遍历所有带 ID 的标题
        last_match_end = 0
        for i, match in enumerate(matches):
            # 提取 Key (Group 2)
            key = match.group(2)
            
            # 提取原始标题 (Group 1)，这可能包含 " - 对应..." 后缀
            raw_title = match.group(1).strip()
            
            # 清洗标题：移除 " - 对应" 或 " - 主要" 等后缀
            # 逻辑：找到最后一个 " - " 或 "对应"，并截断
            # 也可以用正则替换，更灵活
            clean_title = re.sub(r'(\s*[-—]\s*对应.*$)|(\s*[-—]\s*主要.*$)', '', raw_title).strip()
            # 如果清洗后变为空（不太可能），则回退到 raw_title
            if not clean_title:
                clean_title = raw_title
            

            start_pos = match.end()
                        
            # 确定当前段落的结束位置
            if i + 1 < len(matches):
                # 如果还有下一个带 ID 的标题，则结束位置是下一个标题的开始
                end_pos = matches[i+1].start()
            else:
                # 如果是最后一个带 ID 的标题，我们需要小心不要把 'end' 部分（如总结）吞进去
                # 策略：从 start_pos 开始向后搜索下一个以 # 开头的行（非带 ID 的标题）
                remaining_text = outline_resp[start_pos:]
                # 搜索下一个 Markdown 标题 (## ...)
                # 注意：这个标题肯定是不带 【ID】 的，因为带 ID 的都在 matches 里
                next_header_match = re.search(r'^\s*#+\s+.*$', remaining_text, re.MULTILINE)
                
                if next_header_match:
                    # 找到了不带 ID 的新标题（例如 "## 总结"）
                    # 结束位置 = 当前起始位置 + 新标题在剩余文本中的起始位置
                    end_pos = start_pos + next_header_match.start()
                else:
                    # 没找到后续标题，说明真到头了
                    end_pos = len(outline_resp)

            last_match_end = end_pos # 记录最后处理到的位置
            
            # 提取正文内容
            content = outline_resp[start_pos:end_pos].strip()
            
            # 组合 Value: 清洗后的标题 + 换行 + 正文
            full_text = f"{clean_title}\n\n{content}"
            
            outline_dict[key] = full_text

        # [补丁] 提取 'end' 部分 (最后一个匹配章节之后的所有内容)
        # 这将捕获 "## 文献总结与展望" 及其内容，因为它不带 【x-x】 标记
        if matches and last_match_end < len(outline_resp):
            end_content = outline_resp[last_match_end:].strip()
            if end_content:
                outline_dict['end'] = end_content

        default_start = "你将负责文献综述的开篇小节，也即第一个二级标题之前的内容，请按照前述要求，为整篇文献综述写作总领小节，逻辑清晰地介绍串联全文的线索。"
        default_end = "你将负责文献综述的结尾小节。请以总结与展望为主，凝练回顾全文主线，指出关键洞见与局限，并提出未来研究方向与发展趋势，形成有力度的收束。"

        def _extract_end_by_keywords(text: str):
            if not text:
                return None
            header_re = re.compile(r'(?m)^\s*(#{1,6})\s+(.+?)\s*$')
            candidates = []
            for m in header_re.finditer(text):
                level = len(m.group(1))
                title = (m.group(2) or '').strip()
                if level == 2 and any(k in title for k in ("总结", "展望", "评述")):
                    candidates.append(m.start())
            if not candidates:
                return None
            return text[candidates[-1]:].strip()

        start_txt = (outline_dict.get('start') or '').strip()
        if (not start_txt) or (len(start_txt) > 700):
            outline_dict['start'] = default_start

        end_txt = (outline_dict.get('end') or '').strip()
        if (not end_txt) or (len(end_txt) > 700):
            moved = None
            for k in list(outline_dict.keys()):
                if k in ('start', 'end'):
                    continue
                v = outline_dict.get(k) or ''
                first = (v.splitlines()[:1] or [''])[0].strip()
                if first.startswith('##') and any(t in first for t in ("总结", "展望", "评述")):
                    moved = outline_dict.pop(k)
                    break
            if moved and (len((moved or '').strip()) <= 700):
                outline_dict['end'] = moved
            else:
                kw_end = _extract_end_by_keywords(outline_resp or '')
                kw_end = (kw_end or '').strip()
                outline_dict['end'] = kw_end if kw_end and len(kw_end) <= 700 else default_end

        print(f"\n[解析完成] 成功提取 {len(outline_dict)} 个章节 (含 start/end)")

        # 打印前两个 key 验证一下
        for k in list(outline_dict.keys())[:2]:
            print(f"  Key: {k} => Title: {outline_dict[k].splitlines()[0]}")

        return outline_resp, outline_dict
                
    except Exception as e:
        print(f"⚠️ 错误: {e}")
        outline_resp = None
        outline_dict = {}
        return outline_resp, outline_dict



if __name__ == "__main__":


    # 配置权重
    weights_config_1 = {
        'main': 0.05,
        'summary': 0.2,
        'map': 0.55,
        'lineage': 0.2,
        'year': 0.0

    }
    weights_config_2 = {
        'main': 0.1,
        'summary': 0.2,
        'map': 0.4,
        'lineage': 0.2,
        'year': 0.1
    }

    keyword_section_weights_1 = {
                    'main': 0.1,
                    'summary': 0.2,    
                    'map': 0.35,
                    'lineage': 0.35
                }
    keyword_section_weights_2 = {
                    'main': 0.2,
                    'summary': 0.3,    
                    'map': 0.2,
                    'lineage': 0.3
                }

    folder_path = "C:\\测试空文件夹\\文献整理合集"

    # 第一轮：全局聚类
    print("\n\n======== Round 1: Global Clustering ========")
    results1, anchor1, evaluation_text1, cluster_keywords_map1 = comprehensive_process_function(
        method='KMEANS', 
        weights_config_1=weights_config_1,
        keyword_section_weights=keyword_section_weights_1,
        folder_path=folder_path,
        n_components=20,
        k_penalty=0.02,
        similarity_threshold=0.75
    )

    # 统计第一轮的类别 (排除噪音 -1)
    # 注意：results 的 value 可能是 list [coords, label, kws] 或 dict {'coords_3d':..., 'label':..., ...}
    # 根据之前的 pprint 输出，value 是 dict 结构
    labels_found = sorted(list(set(v['label'] for v in results1.values() if v['label'] != -1)))
    print(f"\n======== Round 1 Found Clusters: {labels_found} ========")

    # 第二轮：对每个子类进行细分
    sub_results_storage = {} # 存储每一轮的结果

    for label_id in labels_found:
        print(f"\n\n======== Round 2: Sub-clustering for Label {label_id} ========")
        try:
            # 调用第二轮处理函数
            # 注意：这里需要传入上一轮的 results，以便函数内部筛选属于 label_id 的文章
            res2, anc2, eval2, kws2 = comprehensive_process_function(
                method='KMEANS', 
                weights_config_2=weights_config_2,
                keyword_section_weights=keyword_section_weights_2,
                label=label_id,       # 指定要细分的父类 ID
                results=results1,      # 传入第一轮的完整结果
                n_components=20,
                k_penalty=0.01,
                similarity_threshold=0.75
            )
            
            sub_results_storage[label_id] = {
                'results': res2,
                'anchor': anc2,
                'evaluation': eval2,
                'keywords': kws2
            }
            
            # 简单打印该子类的结果统计
            sub_labels = [v['label'] for v in res2.values()]
            print(f"  -> Label {label_id} subdivided into: {Counter(sub_labels)}")
            
        except Exception as e:
            print(f"  [ERROR] Failed to process Label {label_id}: {e}")

    # --- 最终结果展示 (可选) ---
    print("\n\n======== Final Summary ========")
    import pprint
    pp = pprint.PrettyPrinter(indent=2)

    print(">>> Round 1 Anchors:")
    pp.pprint(anchor1)
    
    print("\n>>> Round 2 Sub-clustering Stats:")
    for pid, data in sub_results_storage.items():
        print(f"  Parent Label {pid}: {len(data['results'])} papers processed")
        print(f"    Sub-anchors: {list(data['anchor'].keys())}")
        print(f"    Sub-anchors values: {data['anchor']}")


    


    # 调用构造函数
    categories_dict, papers_dict = construct_swimlane_data(anchor1, cluster_keywords_map1, sub_results_storage)

    # 打印一个示例查看
    if papers_dict:
        first_title = list(papers_dict.keys())[0]
        print(f"示例文献: {first_title} -> {papers_dict[first_title]}")
        
        plot_swimlane(categories_dict, papers_dict)



    outline_resp,outline_dict = gen_outline(anchor1, cluster_keywords_map1, sub_results_storage)
    print(outline_resp)
    print(outline_dict)

    