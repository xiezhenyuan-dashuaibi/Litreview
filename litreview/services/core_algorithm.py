import numpy as np
import pandas as pd
import torch
from sentence_transformers import SentenceTransformer
import umap
from sklearn.metrics.pairwise import cosine_distances
from sklearn.cluster import DBSCAN, KMeans
import plotly.graph_objects as go
import os
import re
import jieba
import jieba.posseg as pseg
from sklearn.metrics import silhouette_score
from litreview.services.system_service import  AI_call
import json
import time
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
import copy



def extract_contrastive_keywords(
    labels_dict: dict,  # [修改] 传入 {title: label_id} 的字典
    docs_struct_dict, 
    section_weights: dict,
    top_n=5  # 最终需要的关键词数量
):
    print(f"🚀 正在执行双层 AI 关键词提取流程...")
    
    # 获取 API 配置
    api_key = os.environ.get('ARK_API_KEY', '')
    model_name = os.environ.get('ARK_MODEL', 'deepseek-v3-2-251201')

    # 辅助函数：带重试的 AI 调用
    def safe_ai_call(prompt_text, stage_name):
        ai_try = 0
        for _ in range(3):
            try:
                ai_try += 1
                print(f"[{stage_name}][AI_TRY] {ai_try}...", flush=True)
                # 假设 AI_call 是你外部定义的函数
                response = AI_call(prompt_text, api_key, model_name)
                if response:
                    print(f"[{stage_name}][AI_DONE] Length: {len(response)}", flush=True)
                    return response
            except Exception as e:
                print(f"[{stage_name}][AI_ERROR] {str(e)}", flush=True)
                time.sleep(1)
        return ""

    # ==========================================
    # 第一层：对每个 Label 进行独立画像 (纵向深挖 - 并行处理)
    # ==========================================
    # 从 labels_dict 中提取所有涉及的有效 Label
    valid_labels = sorted(list(set([int(l) for l in labels_dict.values() if l != -1])))
    
    # 存储第一层的结果: {label: "raw_description_text"}
    stage1_descriptions = {}

    from concurrent.futures import ThreadPoolExecutor, as_completed

    def process_single_label(label):
        """处理单个 Label 的辅助函数，用于并行执行"""
        print(f"\n--- Processing Label {label} (Stage 1) ---")
        
        # 1. 拼接该 Label 下的所有文本 (按章节拼接)
        section_agg = {sec: [] for sec in ['main', 'summary', 'map', 'lineage']}
        
        local_doc_count = 0
        # 遍历所有文档 (使用 docs_struct_dict 的 keys)
        for title, doc_parts in docs_struct_dict.items():
            # 跳过锚点文章，防止干扰关键词生成
            if title.startswith("__ANCHOR_"):
                continue

            # 从字典中安全获取 label
            current_label = labels_dict.get(title, -1)
            
            if int(current_label) == label:
                for sec in section_agg.keys():
                    content = doc_parts.get(sec, "")
                    if content:
                        section_agg[sec].append(content)
                local_doc_count += 1

        # 2. 将权重转换为自然语言提示
        weight_desc = []
        for sec, w in section_weights.items():
            importance = "极高" if w >= 0.5 else ("较高" if w >= 0.3 else "一般")
            weight_desc.append(f"- {sec} 章节 (权重 {w}): 重要程度{importance}")
        weight_prompt_str = "\n".join(weight_desc)

        # 3. 构造第一层 Prompt
        full_text_context = ""
        for sec, texts in section_agg.items():
            if not texts: continue
            
            # 获取该章节的权重信息
            w = section_weights.get(sec, 0.0)
            importance = "极高" if w >= 0.5 else ("较高" if w >= 0.3 else "一般")
            
            full_text_context += f"\n\n=== {sec.upper()} SECTION START (Weight: {w} - Importance: {importance}) ===\n"
            full_text_context += f"【提示】：本章节权重为 {w} ({importance})，请在分析时给予相应关注。\n"
            full_text_context += "\n".join(texts)
            full_text_context += f"\n=== {sec.upper()} SECTION END ===\n"

        prompt_stage_1 = f"""你是一位负责撰写顶级综述文章的资深学术编辑。这里有 {local_doc_count} 篇属于【同一章节/子领域】的学术论文内容。请根据这些内容，完成任务书中的任务。
---

# 任务书

你是一位负责撰写顶级综述文章的资深学术编辑。这里有 {local_doc_count} 篇属于【同一聚类】的学术论文内容。这些内容被分为了 main(正文/细节), summary(摘要/概括), map(定位图谱), lineage(发展脉络) 四个部分。现在将这些部分都随机打乱并拼接起来，你需要分别阅读这四个部分的内容，并且赋予其不同的关注度，最终总结与提炼出这组文章的共性特征（也即大部分文章都有这样的特征），要求所总结出的特征描述依次审查并判断“领域及子领域”、“流派”、“结论贡献与研究目的”、“技术与方法论”、“应用/理论”等等方面是否存在共性，若有则以一两个词语或语句描述该方面的共性（若无则也不必强行联系，因为你的整理工作是为了辅助写文献综述，所找出的共性特征需要直观），同时还需关注文章除了以上方面外，是否还存在着其他某种专业领域的侧重点的共性（例如可以从高频的词语进行推断），若有则也需要作为特征描述罗列出来。

## 任务要求

1. 在前面的工作流中，我们已经将目标文献库中的文献都进行了整理，我们将每篇文献都提取了 main, summary, map, lineage 四个部分的内容，main 部分是对文章的详细描述，summary 部分是对文章的摘要总结，map 部分是文章的定位图谱，lineage 部分是文章的发展脉络梳理。
2. 首先阅读打乱后的 main, summary, map, lineage 四个部分的内容，对每个部分的内容赋予不同的关注度，在后续提取共性特征时，重点关注权重高的章节，从中寻找共性特征的蛛丝马迹。章节权重设置如下：
{weight_prompt_str}
3. 在提取共性特征时，你需要以具有特点的、概括性的短语或语句来描述这些文章存在的共性特征。共性特征意味着有大部分的文献都有这样的特点。
4. 在描述共性特征时，你需要**牢记**：你提取共性特征的目的是为了辅助后续的文献综述的撰写，因此你所描述的共性特征必须是直观的、真实的，并且是从某个学术专业角度精准切入的，易于后续文献综述的组织逻辑的，而非找到一个奇特但难以用于文献综述组织的共性特征。
5. 在提取共性特征时，可以依次从以下几个方面考虑共性特征，这些方面都是文献综述中易于组织文章的视角，注意在考虑这些方面的共性特征时，若共性特征不明显则不要强行关联（共性特征应该直观），若在这些方面存在着共性特征则需要用一两个短语或语句描述出来，若不存在则无需描述：
  - 领域及子领域：哪些研究方向是这些文章共同关注的？
  - 流派：这些文章是否都属于同一研究流派？
  - 结论贡献与研究目的：这些文章是否有着类似的贡献或者研究的目的？
  - 技术与方法论：这些文章是否都采用了相似的研究方法或技术路线？
  - 应用/理论：这些文章是否均关注理论的提出与发展还是均偏向于应用的研究？
当然，除了以上的可以考虑的方面外，**有很大可能文章还存在着其他专业领域视角下的共性特征**，若有则也需描述出来。

## 输出格式

请输出约 10-20 个短语或简短描述句，用分号分隔。不要输出任何解释，直接输出短语。输出格式示例如下：
```输出格式示例
'xxxxxxxx(短语或语句1)', 'xxxxxxxx(短语或语句2)', 'xxxxxxxx(短语或语句3)', 'xxxxxxxx(短语或语句4)', 'xxxxxxxx(短语或语句5)',
'xxxxxxxx(短语或语句6)', 'xxxxxxxx(短语或语句7)', 'xxxxxxxx(短语或语句8)', 'xxxxxxxx(短语或语句9)', 'xxxxxxxx(短语或语句10)',
'xxxxxxxx(短语或语句11)', 'xxxxxxxx(短语或语句12)', 'xxxxxxxx(短语或语句13)', 'xxxxxxxx(短语或语句14)', 'xxxxxxxx(短语或语句15)'
```
确保能描述清楚文章存在的共性特征，描述可以带着专业领域的视角与词语。

---

# 待阅读内容：

{full_text_context[:40000]}  

---

# 关键提示

请根据以上**任务书**以及**待阅读内容**，进行详细的分析与总结，输出符合要求格式的、具有特点的、概括性的短语或语句来描述这些文章存在的共性特征，以辅助后续文献综述的撰写。
"""
        
        # 调用 AI
        res = safe_ai_call(prompt_stage_1, f"Stage1-Label{label}")
        return label, res if res else "无有效内容"

    # 使用线程池并行处理所有 Label
    # max_workers=5 控制并发数，避免瞬间打满 API 限制
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_label = {executor.submit(process_single_label, label): label for label in valid_labels}
        
        for future in as_completed(future_to_label):
            label = future_to_label[future]
            try:
                l, res_text = future.result()
                stage1_descriptions[l] = res_text
            except Exception as exc:
                print(f"[ERROR] Label {label} generated an exception: {exc}")
                stage1_descriptions[label] = "Error during processing"

    # ==========================================
    # 第二层：全局对比与微调 (横向对比)
    # ==========================================
    print(f"\n--- Processing Global Contrast (Stage 2) ---")
    
    # 构造输入：将第一层的结果整理好
    stage1_summary_str = json.dumps(stage1_descriptions, indent=2, ensure_ascii=False)

    # 构造第二层 Prompt (对比与提纯)
    prompt_stage_2 = f"""你是一位负责撰写顶级综述文章的资深学术编辑。请根据以下各类文献的共性特征信息，完成任务书中的任务。

---

# 任务书

你是由顶级期刊聘请的**综述架构总编**。我们正在撰写一篇大规模的学术文献综述，目前已经通过算法将海量文献聚类为若干个【子主题集合】（Label），并由各板块编辑提交了各集合的初步的**特征画像**。你的核心任务是：**横向对比**所有子主题的特征，消除冗余，弱化共性，强化差异，并最终定稿为一组**层次分明、内容逻辑互斥互补、适合作为综述章节标题**的描述语句，**让人一眼看了就知道这一类label的文章在我们要写的文献综述中应该被如何组织与呈现**。

## 任务要求

1. **上帝视角与横向对比（核心）**：
   - 请勿孤立地看待每个 Label。必须将所有 Label 放在一起审视。你的核心任务是调整各 Label 的特征描述，强化差异，弱化共性，这样在后续的文献综述撰写中，才能更有组织逻辑。
   - **寻找“最大区分度”**：如果 Label A 和 Label B 的初步描述中都出现了特定领域关键词，这说明初步描述不够精准。你需要进一步分析A与B是否分别有侧重，将各label中都通用的词汇转化为具有**限定修饰**的学术流派或应用场景描述，来将各label进行合理的区分。注意在区分时，不可捏造或强行偏移原有描述的范围，要做到真实不牵强。

2. **分析与点评**：
   对当前各编辑给出的各文献集合的特征描述进行综合分析与点评，判断各label之间的特征描述是否有重叠、是否有侧重，阐述各label之间的重叠之处与差异之处，并说明可以怎样去适度强调差异之处，从而使文献综述的撰写更具逻辑性与完整性。

3. **描述重写**：
   - 我们的目的是写综述，不是做标签云。输出的语句必须具备**宏观的学术概括性**。
   - 拒绝碎片化的名词堆砌，**提倡结构化的短语**。
   - 基于输入数据，但不要被输入数据限制住。如果输入数据过于琐碎，请将其概括；如果输入数据过于宽泛，请根据其与其他类的对比结果进行窄化。
   - 保持“信、达、雅”。信：不歪曲原意；达：通顺流畅；雅：学术用语规范。
   - 所重写的特征描述必须包含如下的特性：
     1. 不论是以何种视角，各label的描述间需要存在区别性，体现出各label间分类的差异，同时这样的差异最好存在逻辑上的互补，例如领域、方法、贡献等等层面的互补，这样在逻辑上的完整才有利于组织文献综述。
     2. 对各label的描述兼具概括性与精确性，既不能泛泛而谈，又不能陷入对于某篇文章的细节的过度描述，而是需要精确地概括label类别下文章的整体偏向与侧重点。
   - 对于每一个label，输出5个左右的描述短语或语句即可，**让人一眼看了就知道这一类label的文章在我们要写的文献综述中应该被如何组织与呈现**。
   - 重写描述时需要重点参考上面的“分析与点评”部分，体现出“分析与点评”部分的结论（例如在“分析与点评”部分指出label 0与label 1的差异主要在于一个偏向理论研究一个偏向实际应用，则重写的描述中可以分别有“xxx理论研究”与“xxx应用研究”）。

4. **❌ Bad Case (太泛/太细/无区分度)**：
  - "经济研究" (太泛，如果是综述，这一章没法写)
  - "ResNet50, VGG16, Dropout" (太细，这是技术细节罗列，若这一系列文章都是关于某一技术细节的研究，那这样的罗列才可取)
  - "技术优化" (无区分度，可能每个类都有这样的优化，不可泛泛而谈，仅当其他类型中的确与该描述互斥，这样的描述才算有区分度，才可取)

## 输出格式

请**严格**按照以下 JSON 格式输出，包含两部分：
1. **evaluation**: 一段**分析与点评**。判断各label之间的特征描述是否有重叠、是否有侧重，阐述各label之间的重叠之处与差异之处，并说明可以怎样去适度强调差异之处，从而使文献综述的撰写更具逻辑性与完整性。
2. **results**: 修正后的描述列表。每个 Label 输出 **5 个左右** 最具区别性、兼具概括性与精确性的描述短语或语句（最好还具备逻辑上的互补性与完整性，但不是必须），让人一眼看了就知道这一类label的文章在我们要写的文献综述中应该被如何组织与呈现。
输出格式如下，**在正式输出中不要带有任何Markdown标记（如```json）**：
```json
{{
    "evaluation": "...",
    "results": {{
        "0": [
            "描述语句1",
            "描述语句2",
            ...
            "描述语句5"
        ],
        "1": [
            ...
        ],
        ...
    }}
}}
```
---

# 各板块编辑提交的初步画像

{stage1_summary_str}

---

# 关键提示


请根据以上**任务书**以及**各板块的初步画像**，进行各板块的画像微调，输出消除冗余，弱化共性，强化差异，并最终定稿为一组**层次分明、内容逻辑互斥互补、适合作为综述章节标题**的描述语句，**让人明晰在文献综述中应该如何组织与呈现这一类label的文章**。
输出简单示例如下（不包括```json等md格式）

{{
    "evaluation": "xxxxxxxxxxxxx",
    "results": {{
        "0": [
            "xxxxxx",
            "xxxxxx",
            ...
        ],
        "1": [
            ...
        ],
        ...
    }}
}}
    """

    final_res_str = safe_ai_call(prompt_stage_2, "Stage2-Global")
    
    # ==========================================
    # 解析结果与返回
    # ==========================================
    cluster_keywords_map = {}
    evaluation_text = ""
    
    if final_res_str:
        try:
            # 尝试清洗数据，防止 AI 输出 Markdown 标记
            clean_json_str = final_res_str.strip()
            if clean_json_str.startswith("```json"):
                clean_json_str = clean_json_str[7:]
            if clean_json_str.endswith("```"):
                clean_json_str = clean_json_str[:-3]
            
            # 解析 JSON
            data = json.loads(clean_json_str)
            
            # 提取点评
            evaluation_text = data.get('evaluation', '无点评')
            print(f"\n[AI点评]: {evaluation_text}\n")
            
            # 提取结果
            raw_results = data.get("results", {})
            
            # 转换 key 为 int 类型并赋值
            for k, v in raw_results.items():
                try:
                    label_int = int(k)
                    cluster_keywords_map[label_int] = v[:top_n] # 截取前 N 个
                except ValueError:
                    continue
                    
        except json.JSONDecodeError:
            print("[ERROR] Stage 2 返回的不是合法的 JSON，尝试正则提取...")
            evaluation_text = "JSON 解析失败，无法获取点评。"
            # 兜底：如果 JSON 解析失败，这里的 fallback 逻辑可以根据实际情况写
            # 简单策略：如果解析失败，就用第一层的结果凑合一下（分割分号）
            for lab, desc in stage1_descriptions.items():
                cluster_keywords_map[lab] = desc.split(";")[:top_n]

    else:
        print("[ERROR] Stage 2 调用失败")
        evaluation_text = "Stage 2 调用失败，无点评。"

    # 打印最终结果供调试
    for l, kws in cluster_keywords_map.items():
        print(f"Label {l}: {kws}")

    return cluster_keywords_map, evaluation_text



def extract_sections_to_dict(folder_path, section_start_str):
    """
    读取指定文件夹下的所有 .md 文件，提取标题和指定章节内容，构建字典。

    参数:
    - folder_path: str, 包含md文件的文件夹路径
    - section_start_str: str, 指定章节的开始字符串 (例如 "## 论文主要内容" 或 "论文主要内容")
                         注意：函数会严格匹配该字符串，如果你的md里是二级标题，建议输入 "## 论文主要内容"

    返回:
    - result_dict: dict, {文章标题: 指定章节内容}
    """
    result_dict = {}

    # 1. 检查文件夹是否存在
    if not os.path.exists(folder_path):
        print(f"错误: 文件夹不存在 - {folder_path}")
        return {}

    # 2. 获取所有 .md 文件
    files = sorted([f for f in os.listdir(folder_path) if f.endswith('.md')])
    print(f"在 {folder_path} 中发现 {len(files)} 个 Markdown 文件，开始处理...")

    count_success = 0
    
    for filename in files:
        file_path = os.path.join(folder_path, filename)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # --- A. 提取标题 ---
            # 逻辑：匹配 "# 论文整理：" 或 "# 论文整理:" 开头，直到遇到下一个换行符加#或者文件结束
            # re.DOTALL 模式下 . 可以匹配换行符，但这里我们用非贪婪匹配 .*?
            # (?=\n#|\Z) 是正向预查，表示“后面必须跟着换行符+# 或者 文件结束”，但不包含在匹配结果中
            title_pattern = r'#\s*论文整理[：:]\s*(.*?)(?=\n#|\Z)'
            title_match = re.search(title_pattern, content, re.DOTALL)
            
            if title_match:
                # 获取匹配组并去除首尾空白
                title = title_match.group(1).strip()
            else:
                # 如果没找到标准标题格式，使用文件名作为备选标题
                title = os.path.splitext(filename)[0]
                # print(f"  [警告] 文件 '{filename}' 未找到标准标题格式，使用文件名代替。")

            # --- B. 提取指定章节内容 ---
            # 逻辑：匹配输入的 start_str，直到遇到下一个 "##" 或者文件结束
            # re.escape 用于自动转义输入字符串中的特殊字符（如 * ? 等）
            # \s* 匹配标题后可能存在的换行
            section_pattern = re.escape(section_start_str) + r'\s*(.*?)(?=\n\s*##|\Z)'
            section_match = re.search(section_pattern, content, re.DOTALL)

            if section_match:
                section_content = section_match.group(1).strip()
                
                # 只有当内容不为空时才加入字典
                if section_content:
                    if "年份" in section_start_str:
                        cleaned = re.sub(r"\([^)]*\)", "", section_content)
                        cleaned = re.sub(r"（[^）]*）", "", cleaned)
                        years = re.findall(r"(?<!\d)(?:19|20)\d{2}(?!\d)", cleaned)
                        if years:
                            result_dict[title] = int(years[-1])
                            count_success += 1
                        else:
                            print(f"  [跳过] 文件 '{title}' 未在章节中找到年份。")
                    else:
                        result_dict[title] = section_content
                        count_success += 1
                else:
                    print(f"  [跳过] 文件 '{title}' 中找到章节 '{section_start_str}' 但内容为空。")
            else:
                # 如果没找到该章节，可以选择跳过或记录日志
                # print(f"  [跳过] 文件 '{title}' 中未找到章节: {section_start_str}")
                pass

        except Exception as e:
            print(f"  [错误] 处理文件 '{filename}' 时出错: {e}")

    print(f"处理完成。成功提取 {count_success} 篇文章的指定内容。")
    return result_dict


def analyze_documents_to_vec(
    docs_dict: dict, 
    n_dim_reduce: int = 20, 
    method: str = 'DBSCAN', 
    model_name: str = 'BAAI/bge-m3', 
    **kwargs
) -> dict:
    """
    对文档进行BERT向量化、降维、聚类(DBSCAN/HDBSCAN/KMEANS)并进行3D可视化。
    噪音点(-1)将以浅灰色半透明显示。
    """
    
    # 1. 数据准备
    titles = sorted(list(docs_dict.keys()))
    contents = [docs_dict[t] for t in titles]
    print(f"正在处理 {len(titles)} 篇文章...")

    # 2. 模型加载
    print(f"正在准备语义模型: {model_name} ...")
    
    # 强制使用 CPU，避免 DirectML/CUDA 的兼容性问题
    device = 'cpu'
    print(f"🖥️  当前使用计算设备: {str(device).upper()}")


    project_root = os.getcwd()
    models_dir = os.path.join(project_root, "models")
    local_folder_name = model_name.replace("/", "_")
    local_model_path = os.path.join(models_dir, local_folder_name)
    
    embedder = None
    if os.path.exists(local_model_path) and len(os.listdir(local_model_path)) > 0:
        print(f"✅ 检测到本地模型: {local_model_path}")
        try:
            embedder = SentenceTransformer(local_model_path, device=device)
        except Exception:
            print("❌ 本地加载失败，准备重新下载...")
    
    if embedder is None:
        print(f"🌐 正在下载模型: {model_name}")
        embedder = SentenceTransformer(model_name, device=device)
        if not os.path.exists(models_dir):
            os.makedirs(models_dir)
        embedder.save(local_model_path)
        print("✅ 模型已缓存到本地。")

    # 3. 向量化
    print("正在生成高维向量...")
    # CPU 批次大小建议保守一点
    batch_size = 32
    
    embeddings = embedder.encode(contents, show_progress_bar=True, batch_size=batch_size, device=device)
    
    # 4. 第一次降维 (UMAP)
    # 动态调整 n_components：不能超过样本数 - 2（预留一点空间）
    # 同时 n_neighbors 也不能超过样本数
    n_samples = len(embeddings)
    safe_n_components = min(n_dim_reduce, n_samples - 2) if n_samples > 2 else min(n_dim_reduce, n_samples)
    safe_n_neighbors = min(15, n_samples - 1) if n_samples > 1 else 1
    
    # 如果样本极少，直接不降维或者做极简处理
    if n_samples <= n_dim_reduce:
        print(f"样本数 ({n_samples}) <= 目标维度 ({n_dim_reduce})，跳过 UMAP 降维，直接使用原始向量...")
        clusterable_embedding = embeddings
    else:
        print(f"正在进行第一次降维 (UMAP -> {safe_n_components}维)...")
        reducer_cluster = umap.UMAP(
            n_neighbors=safe_n_neighbors, 
            n_components=safe_n_components, 
            metric='cosine', 
            min_dist=0.0,
            random_state=42,
            n_jobs=1
        )
        clusterable_embedding = reducer_cluster.fit_transform(embeddings)
    
    # --- 5. 聚类 (新增 HDBSCAN 支持) ---
    print(f"正在执行聚类 ({method.upper()})...")
    
    if method.upper() == 'DBSCAN':
        eps = kwargs.get('eps', 0.5)
        min_samples = kwargs.get('min_samples', 3)
        clusterer = DBSCAN(eps=eps, min_samples=min_samples, metric='euclidean')
        labels = clusterer.fit_predict(clusterable_embedding)
        
    elif method.upper() == 'HDBSCAN':
        # 尝试使用 sklearn 自带的 HDBSCAN (sklearn >= 1.3)
        # 如果没有，尝试使用 hdbscan 独立库
        try:
            from sklearn.cluster import HDBSCAN
            # HDBSCAN 参数：min_cluster_size 是核心参数
            num_of_papers = len(titles)
            min_cluster_size = kwargs.get('min_cluster_size', max(5, num_of_papers // 10))
            min_samples = kwargs.get('min_samples', 3) 
            # cluster_selection_epsilon 用于控制微观合并程度，类似 DBSCAN 的 eps
            cluster_selection_epsilon = kwargs.get('cluster_selection_epsilon', 0.3)

            clusterer = HDBSCAN(
                min_cluster_size=min_cluster_size, 
                min_samples=min_samples,
                cluster_selection_epsilon=cluster_selection_epsilon,
                metric='euclidean'
            )
            labels = clusterer.fit_predict(clusterable_embedding)
        except ImportError:
            print("⚠️ 未找到 sklearn.cluster.HDBSCAN，尝试导入 hdbscan 库...")
            try:
                import hdbscan
                min_cluster_size = kwargs.get('min_cluster_size', 3)
                min_samples = kwargs.get('min_samples', None)
                cluster_selection_epsilon = kwargs.get('cluster_selection_epsilon', 0.3)
                clusterer = hdbscan.HDBSCAN(
                    min_cluster_size=min_cluster_size, 
                    min_samples=min_samples, 
                    cluster_selection_epsilon=cluster_selection_epsilon,
                    metric='euclidean'
                )
                labels = clusterer.fit_predict(clusterable_embedding)
            except ImportError:
                raise ImportError("请安装 scikit-learn >= 1.3 或 pip install hdbscan 以使用 HDBSCAN 功能。")

    elif method.upper() == 'KMEANS':
        n_clusters = kwargs.get('n_clusters', 5)
        clusterer = KMeans(n_clusters=n_clusters, random_state=42)
        labels = clusterer.fit_predict(clusterable_embedding)
    else:
        raise ValueError("Method must be 'DBSCAN', 'HDBSCAN' or 'KMEANS'")

    num_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    print(f"聚类完成，共发现 {num_clusters} 个聚类 (Label -1 为噪音)。")

    # 6. 第二次降维 (可视化)
    print("正在进行第二次降维 (UMAP -> 3维可视化)...")
    reducer_viz = umap.UMAP(
        n_neighbors=15,
        n_components=3, 
        metric='cosine',
        min_dist=0.1,
        random_state=42,
        n_jobs=1
    )
    embedding_3d = reducer_viz.fit_transform(embeddings)

    # 8. 返回结果
    result_dict = {}
    for i, title in enumerate(titles):
        coords_20d = clusterable_embedding[i].tolist()
        coords_3d = embedding_3d[i].tolist()
        label = int(labels[i])
        result_dict[title] = [coords_20d, coords_3d, label]
        
    return result_dict


def process_and_classify_target_section(folder_path, target_section, method='DBSCAN',anchor_docs=None,  **kwargs):


    
    # 调用函数
    docs_data = extract_sections_to_dict(folder_path, target_section)
    if anchor_docs:
        # 仅在非年份章节打印详细日志，避免刷屏
        if "年份" not in target_section:
            print(f"\n🚩 正在注入 {len(anchor_docs)} 个 AI 锚点到数据集中...")
            
        for label_id, text in anchor_docs.items():
            # 构造特殊 Title
            anchor_title = f"__ANCHOR_{label_id}__"
            
            # [关键修改点] 特殊处理年份章节
            if "年份" in target_section:
                # 锚点统一设置为 2025 (或任何你希望它出现在时间轴上的位置)
                # 这样在后续计算 intersection 时，锚点就不会因为缺少年份而被过滤掉
                docs_data[anchor_title] = "2025" 
            else:
                # 其他章节使用 AI 生成的描述文本
                docs_data[anchor_title] = text

    if "年份" in target_section:
        return docs_data
 
    # 打印前2个结果看看
    print("\n--- 提取结果示例 ---")
    for i, (title, content) in enumerate(docs_data.items()):
        if i >= 2: break
        print(f"【键】: {title}")
        print(f"【值】: {content}") # 只打印前50个字
        print("-" * 30)
        

    input_data = docs_data

    
    # 2. 调用函数
    # 使用 DBSCAN (注意：eps 参数需要根据数据密度调整，如果聚类全是-1，尝试调大 eps)
    if method =='DBSCAN':
        eps = kwargs.get('eps', 0.5)
        min_samples = kwargs.get('min_samples', 3)
        results = analyze_documents_to_vec(
            input_data, 
            n_dim_reduce=20, 
            method=method, 
            eps=eps,           # DBSCAN 邻域半径 (重要参数)
            min_samples=min_samples      # 最小样本数
            
        )
    elif method =='KMEANS':
        n_clusters = kwargs.get('n_clusters', 3)
        results = analyze_documents_to_vec(
            input_data, 
            n_dim_reduce=20, 
            method=method, 
            n_clusters=n_clusters
            
        )
    elif method =='HDBSCAN':
        min_samples = kwargs.get('min_samples', 3)
        cluster_selection_epsilon=kwargs.get('cluster_selection_epsilon', 0.3)
        results = analyze_documents_to_vec(
                input_data, 
                n_dim_reduce=20, 
                method=method, 
                min_cluster_size=3,
                min_samples=min_samples,
                cluster_selection_epsilon=cluster_selection_epsilon
            )
    else:
        raise ValueError("Method must be 'DBSCAN', 'HDBSCAN' or 'KMEANS'")
    # 3. 查看返回结果的一个例子
    for i in range(3):
        first_key = list(results.keys())[i]
        print(f"\n返回示例: {first_key} -> {results[first_key]}")

    return results, docs_data

def multi_view_clustering_and_visualize(
    data_dict: dict, 
    weights_config: dict, 
    method: str = 'DBSCAN',
    docs_text_dict: dict = None, # [新增] 用于提取关键词的原文 {title: full_text}
    visualize: bool = True,
    keyword_section_weights: dict = None,
    **kwargs
) -> dict:
    """
    基于加权多视图融合的聚类与可视化函数。

    参数:
    - data_dict: dict, {标题: [vec_main(20d), vec_summary(20d), vec_map(20d), vec_lineage(20d), year(int)]}
    - weights_config: dict, 权重配置，例如 {'main': 0.1, 'summary': 0.1, 'map': 0.5, 'lineage': 0.2, 'year': 0.1}
    - method: str, 'DBSCAN', 'HDBSCAN', 'KMEANS'
    - **kwargs: 传递给聚类算法的参数 (如 eps, min_cluster_size, n_clusters)

    返回:
    - result_dict: {标题: [[x, y, z], label]}
    """
    try:
        from sklearn.cluster import HDBSCAN
        HAS_SKLEARN_HDBSCAN = True
    except ImportError:
        HAS_SKLEARN_HDBSCAN = False
        try:
            import hdbscan
            HAS_HDBSCAN_LIB = True
        except ImportError:
            HAS_HDBSCAN_LIB = False
    # 1. 解析数据
    titles = list(data_dict.keys())
    raw_values = list(data_dict.values())
    n_samples = len(titles)
    
    print(f"正在处理 {n_samples} 篇文章的多维特征...")

    # 将数据拆分为 5 个独立的矩阵/数组
    # 假设输入 list 顺序严格对应：[main, summary, map, lineage, year]
    vecs_main = np.array([v[0] for v in raw_values])
    vecs_summary = np.array([v[1] for v in raw_values])
    vecs_map = np.array([v[2] for v in raw_values])
    vecs_lineage = np.array([v[3] for v in raw_values])
    val_years = np.array([v[4] for v in raw_values]).reshape(-1, 1)

    # 2. 计算各维度的距离矩阵 (N x N)
    print("正在计算各分视图的距离矩阵...")
    
    # A. 文本向量使用余弦距离 (Cosine Distance)
    # cosine_distances 结果范围是 [0, 2]，通常语义相似都在 [0, 1] 之间
    d_main = cosine_distances(vecs_main)
    d_summary = cosine_distances(vecs_summary)
    d_map = cosine_distances(vecs_map)
    d_lineage = cosine_distances(vecs_lineage)
    
    # B. 年份使用数值距离 (L1 Distance) 并归一化
    # 计算两两之间的年份差绝对值
    d_year_raw = np.abs(val_years - val_years.T)
    # 归一化：除以最大跨度，将范围压缩到 [0, 1]
    max_year_span = np.max(d_year_raw)
    if max_year_span == 0:
        d_year = np.zeros_like(d_year_raw)
    else:
        d_year = d_year_raw / max_year_span

    # 3. 加权融合 (Weighted Fusion)
    print("正在进行加权距离融合...")
    # 获取权重，如果没有提供则默认为 0
    w_main = weights_config.get('main', 0.0)
    w_sum = weights_config.get('summary', 0.0)
    w_map = weights_config.get('map', 0.0)
    w_lin = weights_config.get('lineage', 0.0)
    w_year = weights_config.get('year', 0.0)
    
    # 计算综合距离矩阵
    d_final = (d_main * w_main + 
               d_summary * w_sum + 
               d_map * w_map + 
               d_lineage * w_lin + 
               d_year * w_year)
    
    # 确保距离矩阵没有负数 (浮点数误差保护)
    d_final = np.maximum(d_final, 0)

    # 4. 执行聚类 (基于预计算距离矩阵)
    print(f"正在执行聚类 ({method})...")
    # 初始化 labels 为全 -1 (噪音)，长度与样本数相同
    labels = np.full(n_samples, -1, dtype=int)

    if method.upper() == 'DBSCAN':
        eps = kwargs.get('eps', 0.1)
        min_samples = kwargs.get('min_samples', 3)
        step = 0.001 if eps >= 0.001 else max(eps / 2, 1e-6)
        max_iter = 500
        
        def _run(e):
            c = DBSCAN(eps=e, min_samples=min_samples, metric='precomputed')
            ls = c.fit_predict(d_final)
            k = len(set(ls)) - (1 if -1 in ls else 0)
            nz_count = list(ls).count(-1)
            nz = (nz_count / n_samples) if n_samples > 0 else 0.0
            return ls, k, nz

        # Initial Run
        labels, k, nz = _run(eps)
        print(f"Initial run: eps = {eps}, clusters = {k}, noise_ratio = {nz:.3f}")
        
        for i in range(max_iter):
            # 1. Check Success
            if (2 <= k <= 5) and (nz <= 0.4):
                print("Target reached.")
                break
                
            # 2. Check Conflict (Stop)
            if (k == 1) and (nz > 0.4):
                print("Conflict detected (Single cluster but high noise). Stopping.")
                break
            
            # 3. Determine Direction
            direction = 0
            if k == 1:
                direction = -1 # Decrease eps to split
            elif (nz > 0.4) or (k > 5):
                direction = 1  # Increase eps to merge or include noise
            
            if direction == 0:
                break # Should be covered by success check, but for safety
                
            # 4. Trial Move
            eps_trial = max(eps + direction * step, 1e-6)
            labels_trial, k_trial, nz_trial = _run(eps_trial)
            print(f"Trial {i+1}: eps_try = {eps_trial:.4f}, clusters = {k_trial}, noise_ratio = {nz_trial:.3f}")
            
            # 5. Check "Overshot" (Backtrack logic)
            overshot = False
            if direction == -1: # Tried decreasing
                # If we split too much (>5) or noise became too high (>0.4)
                if (k_trial > 5) or (nz_trial > 0.4):
                    overshot = True
            else: # Tried increasing
                # If we merged too much (became 1 cluster)
                # Note: If noise > 0.4 still, it's not overshot, it's just 'not enough increase'.
                # Overshot is only when we killed the clusters.
                if k_trial < 2:
                    overshot = True
            
            if overshot:
                # User: "回调一半" -> Reduce step, do NOT update eps
                step = max(step / 2, 1e-6)
                print(f"  -> Overshot! Staying at eps={eps}, reducing step to {step}")
            else:
                # Move successful (or at least valid direction)
                eps = eps_trial
                labels, k, nz = labels_trial, k_trial, nz_trial
                # Should we reduce step on success? User implied binary search behavior.
                # Let's keep step same if moving towards goal, but maybe safer to keep it.
                # If we are bouncing, the overshot logic handles it.
                print(f"  -> Accepted. New eps={eps}")

        print(f"Final Result: eps = {eps}, clusters = {k}, noise_ratio = {nz:.3f}")

    elif method.upper() == 'HDBSCAN':
        # HDBSCAN 处理 precomputed 需要特定设置
        num_of_papers = len(titles)
        # 初始 min_cluster_size
        min_cluster_size = kwargs.get('min_cluster_size', max(5, num_of_papers // 10))
        
        # 仿照 DBSCAN 的自适应逻辑调整 cluster_selection_epsilon
        eps = kwargs.get('cluster_selection_epsilon', 0.3)
        step = 0.001 if eps >= 0.001 else max(eps / 2, 1e-6)
        max_iter = 500
        
        def _run(e, mcs):
            # mcs: min_cluster_size
            if HAS_SKLEARN_HDBSCAN:
                # sklearn 1.3+ 支持 metric='precomputed'
                clusterer = HDBSCAN(min_cluster_size=mcs, metric='precomputed', cluster_selection_epsilon=e)
                ls = clusterer.fit_predict(d_final)
            elif HAS_HDBSCAN_LIB:
                # 独立库 hdbscan 支持
                clusterer = hdbscan.HDBSCAN(min_cluster_size=mcs, metric='precomputed', cluster_selection_epsilon=e)
                ls = clusterer.fit_predict(d_final.astype(np.float64))
            else:
                raise ImportError("请安装 scikit-learn >= 1.3 或 pip install hdbscan")
            
            # 统计聚类信息
            unique_labels = set(ls)
            k = len(unique_labels) - (1 if -1 in ls else 0)
            nz_count = list(ls).count(-1)
            nz = (nz_count / n_samples) if n_samples > 0 else 0.0
            
            # 计算各簇大小 (排除噪音)
            sizes = []
            if k > 0:
                # 统计每个 label 的数量
                from collections import Counter
                counts = Counter(ls)
                for lbl, count in counts.items():
                    if lbl != -1:
                        sizes.append(count)
            sizes.sort()
            return ls, k, nz, sizes

        # Initial Run
        labels, k, nz, sizes = _run(eps, min_cluster_size)
        print(f"Initial run (HDBSCAN): eps={eps:.4f}, min_cluster_size={min_cluster_size}, clusters={k}, noise_ratio={nz:.3f}, sizes={sizes}")
        
        last_valid_result = None

        for i in range(max_iter):
            # --- 1. Check Success (Basic) ---
            target_reached = False
            if (2 <= k <= 5) and (nz <= 0.4):
                target_reached = True
            
            # --- 2. Check Balance (Advanced) ---
            # 只有当基本目标达成时，才检查平衡性，以免干扰正常的收敛
            balanced = True
            if target_reached and k >= 2:
                min_s = min(sizes)
                max_s = max(sizes)
                # 判据：如果最小簇 < 最大簇的 1/5，认为悬殊
                # 或者如果最小簇太小 (例如 < 3) 也可以考虑增加 mcs
                if min_s < (max_s / 5.0):
                    balanced = False
            
            if target_reached:
                if balanced:
                    print("Target reached and clusters are balanced.")
                    last_valid_result = None
                    break
                else:
                    # 尝试自适应调整 min_cluster_size
                    # 上限保护：不要超过总数的一半，否则可能这就不是聚类了
                    limit_mcs = max(5, n_samples // 3)
                    if min_cluster_size < limit_mcs:
                        # Save fallback
                        print(f"Target reached but imbalance detected (sizes={sizes}). Saving state as fallback.")
                        last_valid_result = (eps, min_cluster_size, labels, k, nz, sizes)

                        min_cluster_size += 1
                        print(f"Increasing min_cluster_size to {min_cluster_size}...")
                        # 调整了超参，重新运行当前 eps，看看效果
                        # 注意：不 break，继续循环，让 eps 逻辑也有机会微调
                        labels, k, nz, sizes = _run(eps, min_cluster_size)
                        print(f"  -> Rerun with new mcs: clusters={k}, noise={nz:.3f}, sizes={sizes}")
                        # 如果调整后导致 k<2 或 noise>0.2，下一次循环的 eps 调整逻辑会接手处理
                        continue 
                    else:
                        print("Target reached but imbalance detected. Cannot increase min_cluster_size further (limit reached). Accepting result.")
                        break

            # --- 3. Check Conflict (Stop) ---
            if (k == 1) and (nz > 0.4):
                print("Conflict detected (Single cluster but high noise). Stopping.")
                break
            
            # --- 4. Determine Direction (EPS Adjustment) ---
            direction = 0
            if k == 1:
                direction = -1 # Decrease eps to split
            elif (nz > 0.4) or (k > 5):
                direction = 1  # Increase eps to merge or include noise
            
            if direction == 0:
                # 理论上 target_reached 应该捕获了，但为了安全
                if k == 0: direction = -1 # 尝试调整
                else: break 
                
            # --- 5. Trial Move ---
            eps_trial = max(eps + direction * step, 1e-6)
            labels_trial, k_trial, nz_trial, sizes_trial = _run(eps_trial, min_cluster_size)
            print(f"Trial {i+1}: eps_try={eps_trial:.4f}, mcs={min_cluster_size}, clusters={k_trial}, noise={nz_trial:.3f}, sizes={sizes_trial}")
            
            # --- 6. Check "Overshot" ---
            overshot = False
            if direction == -1: # Tried decreasing
                if (k_trial > 5) or (nz_trial > 0.4):
                    overshot = True
            else: # Tried increasing
                if k_trial < 2:
                    overshot = True
            
            if overshot:
                step = max(step / 2, 1e-6)
                print(f"  -> Overshot! Staying at eps={eps}, reducing step to {step}")
            else:
                eps = eps_trial
                labels, k, nz, sizes = labels_trial, k_trial, nz_trial, sizes_trial
                print(f"  -> Accepted. New eps={eps}")

        # Loop finished or broken
        # Check if we failed to find a valid result with the new mcs, and need to revert
        final_target_reached = (2 <= k <= 5) and (nz <= 0.4)
        if (not final_target_reached) and (last_valid_result is not None):
            print("Current result did not meet targets after increasing min_cluster_size. Reverting to last valid result.")
            eps, min_cluster_size, labels, k, nz, sizes = last_valid_result

        print(f"Final Result: eps={eps}, mcs={min_cluster_size}, clusters={k}, noise_ratio={nz:.3f}, sizes={sizes}")

    elif method.upper() == 'KMEANS':

        k_penalty = kwargs.get('k_penalty', 0.02)
        user_k = kwargs.get('n_clusters', 'auto')
        
        # 1. 嵌入到欧氏空间 (10维)
        temp_reducer = umap.UMAP(n_components=10, metric='precomputed', random_state=42, n_jobs=1)
        temp_coords = temp_reducer.fit_transform(d_final)
        

        # --- A. 自动选择 K 值 (带倾向性的轮廓系数) ---
        if isinstance(user_k, int):
            final_k = user_k
            print(f"  - KMeans: 用户指定 K={final_k}")
        else:
            print(f"  - KMeans: 自动寻找最佳 K (Range: 2-8, Penalty: {k_penalty})...")
            best_score = -100 # 初始值设低点
            best_k = 3
            
            # 搜索范围
            max_search = min(9, len(titles))
            
            for k in range(2, max_search):
                km = KMeans(n_clusters=k, random_state=42, n_init=10)
                l = km.fit_predict(temp_coords)
                
                # 1. 原始数学得分 (-1 到 1)
                sil_score = silhouette_score(temp_coords, l)
                
                # 2. 计算调整后得分 (核心修改)
                # 逻辑：每一多增加一个类，就扣掉 k_penalty 分
                # 比如 k=3 扣 0.06，k=5 扣 0.1
                # 如果 sil_score 提升不够大，就会被扣分抵消，从而选更小的 K
                adjusted_score = sil_score - (k * k_penalty)
                
                print(f"    k={k}, raw_score={sil_score:.4f} -> adj_score={adjusted_score:.4f}")
                
                if adjusted_score > best_score:
                    best_score = adjusted_score
                    best_k = k
            
            final_k = best_k
            print(f"  -> 最终选择 K={final_k}")

        # --- 3. 核心改进：迭代去噪流程 ---
        print("  - KMeans: 执行迭代式中心校正...")
        
        # 第一轮：粗聚类 (受噪音影响的质心)
        kmeans_pass1 = KMeans(n_clusters=final_k, random_state=42, n_init=10)
        labels_pass1 = kmeans_pass1.fit_predict(temp_coords)
        centers_pass1 = kmeans_pass1.cluster_centers_
        
        # 计算每个点到粗质心的距离
        dists = np.linalg.norm(temp_coords - centers_pass1[labels_pass1], axis=1)
        
        # 筛选“核心样本” (Core Samples)
        # 我们不删固定比例，而是用统计学方法：距离 > 中位数 + 1.5倍IQR (或者 2倍标准差)
        # 这样，紧密的类一个都不会删，松散的类才会删
        mask_core = np.ones(len(temp_coords), dtype=bool)
        
        for k in range(final_k):
            cluster_mask = (labels_pass1 == k)
            if np.sum(cluster_mask) < 2: continue # 只有1个点的类，保留
            
            c_dists = dists[cluster_mask]
            
            # 使用 IQR (四分位距) 检测异常值，这比标准差更抗干扰
            q1 = np.percentile(c_dists, 25)
            q3 = np.percentile(c_dists, 75)
            iqr = q3 - q1
            # 阈值：超过 Q3 + 1.5 * IQR 的算离群点 (这是箱线图的标准定义)
            # 你可以调整这个系数：1.5 是标准，2.0 更宽容
            threshold = q3 + 1.5 * iqr
            
            # 标记该类中的噪音
            # 注意：这里我们只是为了“重新计算质心”而标记，不是最终删除
            local_noise = cluster_mask & (dists > threshold)
            mask_core[local_noise] = False
            
        print(f"    初步识别出 {np.sum(~mask_core)} 个潜在噪音，正在基于核心样本重新计算质心...")
        
        # 第二轮：精聚类 (使用纯净样本计算质心)
        # 我们只用 mask_core=True 的数据来训练 KMeans
        core_coords = temp_coords[mask_core]
        
        if len(core_coords) < final_k:
            # 极端情况保护：如果剔除太多，就回退到第一轮
            labels = labels_pass1
        else:
            kmeans_pass2 = KMeans(n_clusters=final_k, random_state=42, n_init=10)
            kmeans_pass2.fit(core_coords) # 注意：只 Fit 核心数据！
            
            # 获取了“修正后的质心”
            clean_centers = kmeans_pass2.cluster_centers_
            
            # 第三轮：最终分配 (Re-assign)
            # 用“修正后的质心”去预测**所有数据** (包括刚才被踢掉的)
            # 这样，原本因为质心偏移而被误判的点，可能会找到正确的归宿
            labels_final = kmeans_pass2.predict(temp_coords)
            
            # --- 4. 最终噪音标记 ---
            # 现在我们有了准确的质心和归类，再做一次距离检查
            # 依然离得很远的点，就是真正的噪音了
            new_dists = np.linalg.norm(temp_coords - clean_centers[labels_final], axis=1)
            
            final_labels = labels_final.copy()
            
            for k in range(final_k):
                c_mask = (labels_final == k)
                if np.sum(c_mask) == 0: continue
                
                c_dists = new_dists[c_mask]
                
                # 再次使用 IQR 阈值，这次是最终判决
                q1 = np.percentile(c_dists, 25)
                q3 = np.percentile(c_dists, 75)
                iqr = q3 - q1
                threshold = q3 + 1.5 * iqr  # 这里的系数决定了最终的去噪力度
                
                # 只有真的远得离谱的才标记为 -1
                noise_idx = c_mask & (new_dists > threshold)
                final_labels[noise_idx] = -1
            
            labels = final_labels
        

    elif method.upper() == 'ANCHOR':
        print("  -> 执行锚点吸附逻辑 (Anchor Adsorption)...")
        
        # 1. 识别锚点索引
        anchor_indices = []
        anchor_label_map = {} # {matrix_index: label_id}
        
        for idx, t in enumerate(titles):
            if t.startswith("__ANCHOR_"):
                anchor_indices.append(idx)
                # 解析 Label ID，例如 __ANCHOR_3__ -> 3
                try:
                    # 使用正则提取数字，比较稳健
                    match = re.search(r'__ANCHOR_(\d+)__', t)
                    if match:
                        lbl = int(match.group(1))
                    else:
                        lbl = 999 # Fallback
                except:
                    lbl = 999
                
                anchor_label_map[idx] = lbl
                labels[idx] = lbl # 锚点自己属于自己这组

        if not anchor_indices:
            print("⚠️ 警告: 选择了 ANCHOR 模式但未在数据中发现红旗点 (Titles starting with __ANCHOR_)。")
            print("   -> 将退化为全噪音结果。")
        else:
            # 2. 吸附计算 (Two-Stage Adaptive Adsorption)
            
            sim_threshold = kwargs.get('similarity_threshold', 0.75)
            # 基础距离阈值 (Sim > 0.75 => Dist < 0.25)
            dist_threshold_base = 1.0 - sim_threshold
            
            print(f"  -> 吸附参数: Sim > {sim_threshold} (Dist < {dist_threshold_base:.3f})")
            print("  -> 执行两阶段自适应吸附...")

            # --- Stage 1: 全局共识筛选 ---
            # 这一步是为了找出那些"毫无争议"的样本，先把它们摘出来
            # 同时也找出一批"待定样本"，用它们的分布来计算 Stage 2 的动态阈值
            
            # 1. 计算每个锚点的平均距离 (用于 Stage 1 的均值归一化)
            anchors_dists_all = d_final[:, anchor_indices]
            anchor_means = np.mean(anchors_dists_all, axis=0) # (N_anchors,)
            anchor_means = np.maximum(anchor_means, 1e-6)
            
            consensus_hard_limit = 0.6 # 距离 > 0.6 (Sim < 0.4) 即使共识也认为是噪音
            
            stage1_confirmed_mask = np.zeros(n_samples, dtype=bool)
            
            # 第一轮遍历：只标记，不计算 Q75
            for i in range(n_samples):
                if i in anchor_label_map: continue
                
                raw_dists = d_final[i, anchor_indices]
                
                # 1.1 原始距离最优
                idx_raw = np.argmin(raw_dists)
                dist_raw_best = raw_dists[idx_raw]
                
                # 1.2 均值归一化最优
                norm_dists_mean = raw_dists / anchor_means
                idx_norm_mean = np.argmin(norm_dists_mean)
                
                # 判定共识
                if (idx_raw == idx_norm_mean) and (dist_raw_best < consensus_hard_limit):
                    # 锁定！
                    target_real_idx = anchor_indices[idx_raw]
                    labels[i] = anchor_label_map[target_real_idx]
                    stage1_confirmed_mask[i] = True
                else:
                    # 待定，留给 Stage 2
                    labels[i] = -1 # 暂时标记为噪音
            
            # --- Stage 2: 基于剩余样本的动态 Q75 重判 ---
            
            # 找出所有"非锚点"且"非 Stage 1 锁定"的样本
            # 这些就是"难啃的骨头"，我们要用它们的分布来计算 Q75
            remaining_mask = (~stage1_confirmed_mask)
            # 还要排除锚点本身
            for idx in anchor_indices:
                remaining_mask[idx] = False
                
            if np.sum(remaining_mask) > 0:
                print(f"  -> Stage 1 锁定了 {np.sum(stage1_confirmed_mask)} 个样本，剩余 {np.sum(remaining_mask)} 个样本进入 Stage 2...")
                
                # 计算这些剩余样本到各个锚点的距离矩阵
                # shape: (N_remaining, N_anchors)
                remaining_dists = d_final[remaining_mask][:, anchor_indices]
                
                # 计算动态 Q75 (对应距离的 Q25)
                # 这反映了"在难样本中，大家离这个锚点一般有多远"
                anchor_q25_dynamic = np.percentile(remaining_dists, 25, axis=0)
                anchor_q25_dynamic = np.maximum(anchor_q25_dynamic, 1e-6)
                
                # 第二轮遍历：只处理 remaining 的样本
                remaining_indices = np.where(remaining_mask)[0]
                
                for i in remaining_indices:
                    raw_dists = d_final[i, anchor_indices]
                    
                    # 计算动态归一化相似度
                    # Sim_Norm = (1 - Dist) / (1 - Q25_Dist)
                    sims = 1.0 - raw_dists
                    sims_q75 = 1.0 - anchor_q25_dynamic
                    sims_q75 = np.maximum(sims_q75, 1e-6)
                    
                    norm_sims = sims / sims_q75
                    
                    best_norm_sim_idx = np.argmax(norm_sims)
                    best_norm_sim = norm_sims[best_norm_sim_idx]
                    
                    # 判定
                    if best_norm_sim >= 0.75:
                        target_real_idx = anchor_indices[best_norm_sim_idx]
                        labels[i] = anchor_label_map[target_real_idx]
                    else:
                        labels[i] = -1 # 最终噪音
            else:
                print("  -> Stage 1 已覆盖所有样本，跳过 Stage 2。")

            # --- Stage 3: 类别平衡调整 (Class Balancing) ---
            print("  -> 执行 Stage 3: 类别平衡调整...")
            
            # 最大迭代次数，防止死循环
            max_balance_iters = 25 
            iter_count = 0
            
            # 预计算相似度均值 (用于归一化)
            # anchor_means 是距离均值，这里转换为相似度均值
            anchor_sim_means = 1.0 - anchor_means
            anchor_sim_means = np.maximum(anchor_sim_means, 1e-6)

            while iter_count < max_balance_iters:
                # 1. 统计当前各类别数量 (仅针对锚点类别)
                current_counts = {}
                for idx in anchor_indices:
                    lbl = anchor_label_map[idx]
                    current_counts[lbl] = 0
                
                # 统计实际分布
                unique_labels_arr, counts_arr = np.unique(labels, return_counts=True)
                total_assigned = 0
                for l, c in zip(unique_labels_arr, counts_arr):
                    if l in current_counts: # 只关心锚点类别
                        current_counts[l] = c
                        total_assigned += c
                
                if total_assigned == 0:
                    break

                # 2. 识别 A 组 (Rich) 和 B 组 (Poor)
                group_a_labels = [] # Rich
                group_b_labels = [] # Poor
                
                threshold_ratio = total_assigned / 10.0
                threshold_absolute = 4
                
                for lbl, cnt in current_counts.items():
                    if cnt <= threshold_absolute or cnt <= threshold_ratio:
                        group_b_labels.append(lbl)
                    else:
                        group_a_labels.append(lbl)
                
                # 停止条件：没有 B 组（都平衡了）或没有 A 组（没资源了）
                if not group_b_labels or not group_a_labels:
                    if not group_b_labels:
                        print(f"    [Iter {iter_count}] 平衡完成：所有类别数量均满足要求。")
                    else:
                        print(f"    [Iter {iter_count}] 停止平衡：没有富裕组 (A组) 可供提取。")
                    break
                
                # 3. 寻找最佳迁移候选
                # 找到属于 A 组的所有样本索引
                mask_a = np.isin(labels, group_a_labels)
                candidate_indices = np.where(mask_a)[0]
                
                if len(candidate_indices) == 0:
                    break

                # 找到属于 B 组的所有锚点索引
                b_anchor_indices = [idx for idx in anchor_indices if anchor_label_map[idx] in group_b_labels]
                
                # 候选样本到 B 组锚点的距离矩阵
                # shape: (N_candidates, N_b_anchors)
                dists_sub = d_final[candidate_indices][:, b_anchor_indices]
                
                # 转换为相似度
                sims_sub = 1.0 - dists_sub
                
                # 获取 B 组锚点对应的均值
                anchor_mean_map = {uid: m for uid, m in zip(anchor_indices, anchor_sim_means)}
                b_means = np.array([anchor_mean_map[uid] for uid in b_anchor_indices])
                
                # 计算归一化相似度矩阵 Norm_Sim = Sim / Mean
                # 注意防止除以0
                b_means = np.maximum(b_means, 1e-6)
                norm_sims_sub = sims_sub / b_means[None, :]
                
                # 找最大值
                max_idx_flat = np.argmax(norm_sims_sub)
                r_idx, c_idx = np.unravel_index(max_idx_flat, norm_sims_sub.shape)
                
                # 执行迁移
                real_sample_idx = candidate_indices[r_idx]
                target_anchor_idx = b_anchor_indices[c_idx]
                target_label = anchor_label_map[target_anchor_idx]
                
                labels[real_sample_idx] = target_label
                iter_count += 1
            
            print(f"  -> Stage 3 完成，共执行 {iter_count} 次迁移调整。")
    else:
        raise ValueError(f"Unknown method: {method}")

    # 统计聚类结果
    n_clusters_found = len(set(labels)) - (1 if -1 in labels else 0)
    n_noise = list(labels).count(-1)
    print(f"聚类完成: 发现 {n_clusters_found} 个类, {n_noise} 个噪音点。")
    # --- [关键步骤] 5. 关键词提取 (如果提供了文本) ---
    cluster_keywords_map = {}
    evaluation_text = ""
    if docs_text_dict is not None:
        
        # 如果用户没传权重，给默认值
        if keyword_section_weights is None:
            keyword_section_weights = {'main': 0.15, 'summary': 0.2, 'map': 0.35, 'lineage': 0.3}
            
        # 构建 labels_dict: {title: label_id}
        # 确保 labels 和 titles 索引一致
        labels_dict = {t: l for t, l in zip(titles, labels)}
        
        cluster_keywords_map, evaluation_text = extract_contrastive_keywords(
            labels_dict, # [修改] 传入字典
            docs_text_dict, # 传入完整字典
            section_weights=keyword_section_weights, # [传入权重]
            top_n=5
        )
    else:
        print("未提供原文内容，跳过关键词提取。")
    # 5. 降维可视化 (基于综合距离矩阵直接降到 3D)
    print("正在进行可视化降维 (UMAP precomputed -> 3D)...")
    reducer_viz = umap.UMAP(
        n_components=3,
        metric='precomputed', # 关键：直接使用我们算好的加权距离
        random_state=42,
        n_neighbors=15,
        min_dist=0.1,
        n_jobs=1
    )
    coords_3d = reducer_viz.fit_transform(d_final)
    # 6. 绘制图表 [修改部分]
    if visualize:
        print("正在绘制 3D 可视化图表...")
        df_plot = pd.DataFrame(coords_3d, columns=['x', 'y', 'z'])
        df_plot['title'] = titles
        df_plot['label'] = labels
        
        # 标记是否为锚点，方便绘图筛选
        df_plot['is_anchor'] = df_plot['title'].apply(lambda x: x.startswith("__ANCHOR_"))

        fig = go.Figure()

        # A. 绘制噪音点
        df_noise = df_plot[(df_plot['label'] == -1) & (~df_plot['is_anchor'])]
        if not df_noise.empty:
            fig.add_trace(go.Scatter3d(
                x=df_noise['x'], y=df_noise['y'], z=df_noise['z'],
                mode='markers', name='Noise (其他)',
                marker=dict(size=3, color='lightgrey', opacity=0.4, symbol='circle'),
                text=df_noise['title'], hoverinfo='text'
            ))

        # B. 绘制各个聚类 (包含锚点，保证颜色统一)
        import plotly.colors as pc
        unique_labels = sorted([l for l in set(labels) if l != -1])
        colors = pc.qualitative.Plotly * 10 

        for i, label in enumerate(unique_labels):
            # 取出该类下的普通点
            df_sub = df_plot[(df_plot['label'] == label) & (~df_plot['is_anchor'])]
            color = colors[i % len(colors)]
            
            # 构建图例名称
            legend_name = f"Cluster {label}"
            keywords_str = ""
            if label in cluster_keywords_map:
                kws = cluster_keywords_map[label][:5]
                keywords_str = " ".join(kws)
                legend_name = f"C{label}: {keywords_str}"
            
            # 绘制普通点
            if not df_sub.empty:
                fig.add_trace(go.Scatter3d(
                    x=df_sub['x'], y=df_sub['y'], z=df_sub['z'],
                    mode='markers', 
                    name=legend_name,
                    marker=dict(size=6, color=color, opacity=0.8),
                    text=df_sub['title'], 
                    customdata=[f"关键词: {keywords_str}"] * len(df_sub),
                    hovertemplate="<b>%{text}</b><br>%{customdata}<extra></extra>"
                ))
            
            # [新增] 绘制该类对应的锚点 (高亮显示)
            df_anchor_sub = df_plot[(df_plot['label'] == label) & (df_plot['is_anchor'])]
            if not df_anchor_sub.empty:
                # 获取锚点对应的文本描述
                # 假设每个 Label 只有一个锚点，取第一个即可
                anchor_title = df_anchor_sub.iloc[0]['title']
                anchor_short_desc = f"Anchor {label}" # 默认兜底
                anchor_full_desc = "无描述"

                if docs_text_dict and anchor_title in docs_text_dict:
                    # 从 docs_text_dict 中提取内容
                    # 我们之前把锚点文本注入到了 'summary', 'main' 等字段中，取其中一个即可
                    doc_parts = docs_text_dict[anchor_title]
                    # 优先取 summary，没有则取 main
                    raw_text = doc_parts.get('summary') or doc_parts.get('main') or ""
                    
                    if raw_text:
                        anchor_full_desc = raw_text
                        # 截取前 15 个字符作为图例名称，防止图例过长
                        anchor_short_desc = f"🚩 {raw_text[:15]}..."

                        
                fig.add_trace(go.Scatter3d(
                    x=df_anchor_sub['x'], y=df_anchor_sub['y'], z=df_anchor_sub['z'],
                    mode='markers+text',
                    name=anchor_short_desc,   # <--- 图例显示截断后的描述
                    marker=dict(
                        size=12,          
                        color=color,      
                        symbol='diamond', 
                        line=dict(width=2, color='white'), 
                        opacity=1.0
                    ),
                    text=["🚩" for _ in range(len(df_anchor_sub))],
                    textposition="top center",
                    # 鼠标悬停显示完整描述，自动换行
                    hovertext=anchor_full_desc, # <--- 悬停显示完整描述
                    hoverinfo="text",
                    # 如果不想让锚点单独占一个图例行，可以将 showlegend 设为 False
                    # 但通常为了看到那段描述，设为 True 更好
                    showlegend=True 
                ))

        fig.update_layout(
            title=f"多视图加权聚类可视化 ({method})",
            scene=dict(xaxis_title='Dim 1', yaxis_title='Dim 2', zaxis_title='Dim 3'),
            margin=dict(l=0, r=0, b=0, t=40), height=700,
            legend=dict(itemsizing='constant')
        )
        fig.show()

    result_dict = {}
    for i, title in enumerate(titles):
        coords = coords_3d[i].tolist()
        label = int(labels[i])
        
        # 获取该 label 对应的关键词列表
        kws = cluster_keywords_map.get(label, [])    
        # 返回格式: [coords_3d, label, keywords]
        result_dict[title] = [coords, label, kws]
    return result_dict,evaluation_text,cluster_keywords_map

def calculate_balance_std2(results):
    """
    计算聚类结果均衡性的综合指标（越小越均衡）。
    基础指标为标准差 (STD)。
    在此基础上增加惩罚项：如果簇大小偏离舒适区 [6, 15]，则施加惩罚。
    """
    if not results: return float('inf')
    labels = []
    for k, v in results.items():
        lv = -1
        if isinstance(v, dict):
            lv = v.get('label', -1)
        elif isinstance(v, list) and len(v) >= 2:
            lv = v[1]
        
        if lv != -1:
            labels.append(lv)
            
    if not labels: return float('inf')
    
    # 统计各 Label 计数
    counts = list(Counter(labels).values())
    if not counts: return float('inf')

    # 1. 基础标准差
    base_std = np.std(counts)
    
    # 2. 偏离舒适区的惩罚 (Penalty)
    # 设定舒适区间
    MIN_IDEAL = 6
    MAX_IDEAL = 15
    
    penalty_sum = 0.0
    for c in counts:
        if c < MIN_IDEAL:
            # 过小惩罚：平方级惩罚，权重较大 (2.0)，强力避免碎片化
            penalty_sum += ((MIN_IDEAL - c) ** 2) * 2.0
        elif c > MAX_IDEAL:
            # 过大惩罚：线性惩罚，权重较小 (0.5)，稍大是可以容忍的
            penalty_sum += (c - MAX_IDEAL) * 0.5
            
    # 将惩罚均摊到每个簇上，使其量级与 STD 可比
    avg_penalty = penalty_sum / len(counts)
    
    # 综合指标 = 标准差 + 平均惩罚
    final_score = base_std + avg_penalty
    
    return final_score


def calculate_balance_std1(results):
    """
    计算聚类结果均衡性的综合指标（越小越均衡）。
    基础指标为标准差 (STD)。
    在此基础上增加惩罚项：如果簇大小偏离舒适区 [6, 15]，则施加惩罚。
    """
    if not results: return float('inf')
    labels = []
    for k, v in results.items():
        lv = -1
        if isinstance(v, dict):
            lv = v.get('label', -1)
        elif isinstance(v, list) and len(v) >= 2:
            lv = v[1]
        
        if lv != -1:
            labels.append(lv)
            
    if not labels: return float('inf')
    
    # 统计各 Label 计数
    counts = list(Counter(labels).values())
    if not counts: return float('inf')

    # 1. 基础标准差
    base_std = np.std(counts)
    
    # 2. 偏离舒适区的惩罚 (Penalty)
    # 设定舒适区间
    MIN_IDEAL = 20
    MAX_IDEAL = 50
    
    penalty_sum = 0.0
    for c in counts:
        if c < MIN_IDEAL:
            # 过小惩罚：平方级惩罚，权重较大 (2.0)，强力避免碎片化
            penalty_sum += ((MIN_IDEAL - c) ** 2) * 2.0
        elif c > MAX_IDEAL:
            # 过大惩罚：线性惩罚，权重较小 (0.5)，稍大是可以容忍的
            penalty_sum += (c - MAX_IDEAL) * 0.5
            
    # 将惩罚均摊到每个簇上，使其量级与 STD 可比
    avg_penalty = penalty_sum / len(counts)
    
    # 综合指标 = 标准差 + 平均惩罚
    final_score = base_std + avg_penalty
    
    return final_score

def comprehensive_process_function(method = 'KMEANS',weights_config_1=None,weights_config_2=None,keyword_section_weights=None,paper_desc = '暂未提供',**kwargs):



    folder_path = kwargs.get('folder_path', None)
    if folder_path is None:
        results = kwargs.get('results', None)
        label = kwargs.get('label', None)
        eps = kwargs.get('eps', 0.5)
        min_samples = kwargs.get('min_samples', 3)
        min_cluster_size = kwargs.get('min_cluster_size', 3)

        if results is None:
            raise ValueError("Either folder_path or label/results must be provided.")
        elif label is None:
            raise ValueError("Either folder_path or label/results must be provided.")
        else:
            if weights_config_2 is None:
                raise ValueError("weights_config_2 must be provided.")
            
            selected_titles = []
            parent_anchor_text = ''

            for t, item in results.items():
                lv = None
                if isinstance(item, dict):
                    lv = item.get('label', None)
                elif isinstance(item, list) and len(item) >= 2:
                    lv = item[1]
                
                # 找到属于当前 label 的所有对象
                if lv == label:
                    # [关键逻辑] 区分：是上一层的红旗，还是真实文章？
                    if t.startswith("__ANCHOR_"):
                        # 如果是红旗，提取其文本（通常存在 summary 或 main 中）
                        # 假设 results[t] 是字典，取其 summary 作为描述
                        if isinstance(item, dict):
                            desc = item.get('summary', "") or item.get('main', "")
                            if desc:
                                parent_anchor_text=desc
                    else:
                        # 如果是真实文章，加入待处理列表
                        selected_titles.append(t)

            main_doc_data = {}
            summary_doc_data = {}
            map_doc_data = {}
            lineage_doc_data = {}
            year_dict = {}
            for t in selected_titles:
                item = results.get(t)
                if isinstance(item, dict):
                    m = item.get('main', None)
                    s = item.get('summary', None)
                    mp = item.get('map', None)
                    ln = item.get('lineage', None)
                    yr = item.get('year', None)
                else:
                    m = s = mp = ln = yr = None
                if m and s and mp and ln and yr is not None:
                    main_doc_data[t] = m
                    summary_doc_data[t] = s
                    map_doc_data[t] = mp
                    lineage_doc_data[t] = ln
                    try:
                        year_dict[t] = int(yr)
                    except Exception:
                        continue


            # 1. 构造 Prompt 素材 (地图 + 脉络 + 父级背景)
            # 采样前 100 篇，避免 token 溢出
            sub_context_parts = []
            sub_context_parts.append(f"【所属父类别(背景)】: {parent_anchor_text}")
            
            for t in selected_titles[:100]:
                mp_txt = map_doc_data.get(t, "")
                ln_txt = lineage_doc_data.get(t, "")
                if mp_txt or ln_txt:
                    sub_context_parts.append(f"《{t}》\n[地图]: {mp_txt}\n[脉络]: {ln_txt}")
            
            full_sub_context = "\n\n".join(sub_context_parts)
            
            # 2. 调用 AI 生成子红旗 (并行 3 次并择优)
            sub_anchor_prompt = f"""你是一个专注于该细分领域的特邀学术编辑。我们已经将一批文献初步归类到了一个大的父主题下，并且已经整理出每篇文献的【文献定位】和【文献脉络】。现在的任务是在这个父主题内部进行更精细的拆解，发掘并梳理其中的发展脉络与枝桠，将它们进一步划分为2-4类。

---

# 任务书

你是一个专注于该细分领域的特邀学术编辑，你们正在为你们的最新的研究而撰写文献综述。前面的工作流已经将 {len(selected_titles)} 篇文献归类到了同一父主题下，并且已经整理出每篇文献的【文献定位】和【文献脉络】。现在的任务是：你需要在这一父主题内部寻找文献之间的**分裂因子**，将它们进一步细分为 2-4 个具体的类型，有助于后续文献综述中该领域的文献发展脉络与枝桠的梳理。

## 正在撰写的最新研究的大致情况
（你们正在为该最新的研究而撰写文献综述，因此你需要参考该研究的大致内容来规划文献综述的撰写角度与方向，为该研究打下基础）

{paper_desc}

## 细分思路（与初次分类不同）

1. **确立基调**：
   请牢记，该任务的目的是在进行初步的分类之后，对文献进一步的详细分类，从而辅助梳理该父主题下的发展脉络与枝桠，有利于文献综述的撰写，而文献综述的撰写是为了后续正式的研究内容打下基础。
   这些文献已经属于同一个大类了，它们在宏观上是具有一致的特点的。在父类别的颗粒度下，不要重复父类别的描述，不要试图再用大的颗粒度来进一步分类（例如使用学科分类这样的大颗粒度分类来作进一步划分）。你需要寻找的是它们在“同一目标下的不同路径”或“同一领域下的不同切面”，因此此次任务需要更加关注文章的目的/问题/结论/视角/方法/场景等等侧重点。
   所给出的文献中，并不一定都能被包含进你给出的分类方案中，部分文献可被视为噪声文献，你给出的分类也不需要将所有文献都归纳进去，能将大部分的文献归纳进去即可。
   我们需要对文献的分类具有直观性，能体现每一类文献的最突出的、最明显的定位特征，但同时又需要对文献的分类具有逻辑性与互补性，每一类文献之间能被恰当的逻辑联系与组织起来，这样才有利于文献综述的撰写。
   在输出中，定义2-4个分类即可，尤其是当文献数量较少时（例如总的文献数量只有30篇左右），也可以定义为2-3个分类即可（确保文献综述的章节内容足够稠密），若经过缜密思考发现文献内容明显应该被分为逻辑清晰的4类，则也不必拘泥于要求，大胆划分。为为每个子主题撰写一段**详细的、包含丰富专业术语的描述文本。严格遵守输出格式。
   分类时需要保证每一类的”稠密性“，即每一类文献的数量不能过于稀疏，否则会导致文献综述的章节内容不够充实，例如某一类型的文献只有3篇，则不能将这些文章单独归为一类，要么作为噪音舍去，要么融入到其他类型中。

2. **思路步骤**：
   1. 首先，对于大部分的文献，凭借直觉对其进行分类，先不必考虑分类的逻辑性与互补性，此时所分的类能尽量凸显文献的最大的特征，最贴近文献的直观主要内容。
   2. 此时，所分的类可能并未基于同一的维度与标准，没有逻辑性与互补性，此时可以思考该以什么样的逻辑或某种学术上的视角将这些分类串联起来，尤其可以关注那些反复出现的、成对立或互补关系的关键词组。
   3. 若难以不牵强的逻辑将所分类型串联起来，可以尝试站在新的【分裂因子】的视角下梳理分类逻辑，逐步调整所分类型的描述、侧重点等等，调整过程当然会减少分类的直观性，但能增加分类的逻辑性与互补性，最终找到一个不错的平衡点，使分类兼具直观性与逻辑性。

3. **寻找“分裂因子”**：
   你可以从“研究流派”、“核心问题”、“理论与应用”、“聚焦侧重点（此方法几乎通用）”来考虑分类依据，侧重点依据例如：
   * **核心观点**: 这一类的文献持有类似的观点，而另一类文献持有类似的观点。
   * **技术路线**：虽然都解决 X 问题，是一派用了 A 方法，另一派用了 B 方法。
   * **应用场景**：虽然都属于 Y 领域，是一派关注“A场景”，另一派关注“B场景”。
   * **演进阶段**：是一派属于“早期的奠基性理论”，另一派属于“后期的修补或应用”。
   * **核心指标的取舍**：是一派追求“极致的精度”，另一派追求“极致的速度/轻量化”。
   这些视角的加入都能为原本具备直观性的分类中添加逻辑性与互补性，使文献综述逻辑更清晰。

## 输出格式

必须是标准的 JSON 格式，Key 为数字索引（0, 1, 2...），Value 为描述文本。不要附带任何md格式。

{{
    "Key1": "Value1",
    "Key2": "Value2",
    ...
}}

## 描述要求

在这一阶段，描述必须**硬核**和**具体**，模糊的通用词（如“人工智能”、“大数据”）在这里是无效的噪音。
在描述时，可以参考以下逻辑进行描述：
该类文献...（该类文献被分类的突出特点，例如同样聚焦于...角度/同样认为.../同样以...为出发点/同样采用.../同样贡献...），可以以如下学术受控词来进行描述：...（使用一些专业名词、短语甚至语句来描述这一类文章的特点，可以多多参考【文献脉络】部分，中英文均可，描述词越多越好、越凸显特征越好、越独有越好）。例如部分文章针对...问题进行了研究...，部分文章...（重点在此，需要多多举例详细描述该类型文章中有哪些文章做了什么事情，体现出该类的表现，不要详细指出哪篇文章具体做了什么事情，只需描述大概，描述所用的用词以及句子结构可以尽量往原文贴近，例子越多越好）。
注意在描述一类文献时，要突出其独有的特点，也就是在避开共同特征、通用描述词的同时，还要尽量避开其他类文献的独特关键词或独特描述。
这是因为你的描述文本将用于向量检索并匹配相关文献，因此最好包含该类别的**高频特征词**（如特定算法名、特定场景名、特定理论指标），**模仿该类型的文章的主要逻辑进行描述**，你的描述与所给出的文献整理内容在特点上越相似，越能被算法检索出相似度，同时也得避开其他类文献的特征描述，避免出现A类文章与B类文章的描述的相似度高于与A类文章的描述的相似度而被误判为B类文章。


---

# 父级背景（宏观约束，请在此颗粒度下进一步细分，梳理内部发展脉络与枝桠）

【{parent_anchor_text}】

# 文献整理内容

{full_sub_context[:40000]}

---

# 关键提示

请在【父级背景】的约束下，对文献素材进行细颗粒度的拆解，梳理该文献集合的发展脉络与枝桠，并且进行进一步的分类，以此辅助后续文献综述的结构组织与撰写。最后按照格式输出 2-4 个子类，满足任务书的要求。

输出案例如下（仅供参考风格，内容需根据实际素材生成）：
{{
    "0": "该类文献专注于...，研究目标均...，具体...。学术受控词可以描述为...。例如，部分文献...而另一些文献...；...；...；...；...。",
    "1": "该类文献聚焦于...。核心逻辑是通过...。高频词包括...，侧重于架构的搜索效率优化。部分文章针对...进行了研究，提出了...方法；部分文章...；...；...；...。",
    "2": "该类文献属于...流派，文章主要针对...重点解决...。常见关键词为...。具体的，一些文章采用了...架构，旨在优化...指标；另一些...；...；...；...。"
    ...
}}

以上示例仅仅是一个简单的分类示例，你需要做更加详细扎实的工作。
            """
            
            def generate_single_sub_anchors():
                try:
                    # 获取 API 配置
                    api_key = os.environ.get('ARK_API_KEY', '')
                    model_name = os.environ.get('ARK_MODEL', 'deepseek-v3-2-251201')
                    
                    # 调用 AI
                    sub_anchor_resp = AI_call(sub_anchor_prompt, api_key, model_name)
                    
                    # 清洗与解析 JSON
                    clean_json_sub = sub_anchor_resp.strip().replace("```json", "").replace("```", "")
                    sub_anchors_raw = json.loads(clean_json_sub)
                    sub_anchors_parsed = {int(k): v.lstrip("该类") for k, v in sub_anchors_raw.items()}
                    return sub_anchors_parsed
                except Exception as e:
                    print(f"⚠️ [AI架构师] 子锚点生成单次失败，错误: {e}")
                    return None

            # 并行调用 3 次
            print(f"🚀 [AI架构师] 正在并行生成 3 套子锚点方案以择优...")
            sub_anchors_candidates = []
            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = [executor.submit(generate_single_sub_anchors) for _ in range(3)]
                for f in futures:
                    res = f.result()
                    if res:
                        sub_anchors_candidates.append(res)
            
            if not sub_anchors_candidates:
                print("❌ 所有子锚点生成均失败，回退到空锚点。")
                sub_anchors_candidates = [None] # 确保至少跑一次无监督

            # 择优循环
            best_results2 = None
            best_sub_anchors = None
            best_evaluation_text = ""
            best_cluster_keywords_map = {}
            min_balance_score = float('inf')
            
            # 原始数据备份（因为注入会修改字典）
            # 注意：main_doc_data 等是局部变量，为了在循环中不互相污染，我们需要在循环内使用 copy
            
            for idx, candidate_anchors in enumerate(sub_anchors_candidates):
                print(f"\n--- 正在评估第 {idx+1}/{len(sub_anchors_candidates)} 套子分类方案 ---")
                if candidate_anchors:
                    print(f"   锚点数量: {len(candidate_anchors)}")
                
                # 深拷贝数据字典，防止上一轮的注入影响这一轮
                curr_main_doc_data = copy.deepcopy(main_doc_data)
                curr_summary_doc_data = copy.deepcopy(summary_doc_data)
                curr_map_doc_data = copy.deepcopy(map_doc_data)
                curr_lineage_doc_data = copy.deepcopy(lineage_doc_data)
                curr_year_dict = copy.deepcopy(year_dict)
                
                # 注入锚点
                if candidate_anchors:
                    for k, v in candidate_anchors.items():
                        anchor_title = f"__ANCHOR_{k}__"
                        curr_main_doc_data[anchor_title] = v
                        curr_summary_doc_data[anchor_title] = v
                        curr_map_doc_data[anchor_title] = v
                        curr_lineage_doc_data[anchor_title] = v
                        curr_year_dict[anchor_title] = 2025

                # 向量化
                if method == 'DBSCAN':
                    main_vec = analyze_documents_to_vec(curr_main_doc_data, n_dim_reduce=20, method=method, eps=eps, min_samples=min_samples)
                    summary_vec = analyze_documents_to_vec(curr_summary_doc_data, n_dim_reduce=20, method=method, eps=eps, min_samples=min_samples)
                    map_vec = analyze_documents_to_vec(curr_map_doc_data, n_dim_reduce=20, method=method, eps=eps, min_samples=min_samples)
                    lineage_vec = analyze_documents_to_vec(curr_lineage_doc_data, n_dim_reduce=20, method=method, eps=eps, min_samples=min_samples)
                elif method == 'KMEANS':
                    n_clusters = kwargs.get('n_clusters', 3)
                    main_vec = analyze_documents_to_vec(curr_main_doc_data, n_dim_reduce=20, method=method, n_clusters=n_clusters)
                    summary_vec = analyze_documents_to_vec(curr_summary_doc_data, n_dim_reduce=20, method=method, n_clusters=n_clusters)
                    map_vec = analyze_documents_to_vec(curr_map_doc_data, n_dim_reduce=20, method=method, n_clusters=n_clusters)
                    lineage_vec = analyze_documents_to_vec(curr_lineage_doc_data, n_dim_reduce=20, method=method, n_clusters=n_clusters)
                elif method == 'HDBSCAN':
                    main_vec = analyze_documents_to_vec(curr_main_doc_data, n_dim_reduce=20, method=method, min_cluster_size=min_cluster_size, min_samples=min_samples)
                    summary_vec = analyze_documents_to_vec(curr_summary_doc_data, n_dim_reduce=20, method=method, min_cluster_size=min_cluster_size, min_samples=min_samples)
                    map_vec = analyze_documents_to_vec(curr_map_doc_data, n_dim_reduce=20, method=method, min_cluster_size=min_cluster_size, min_samples=min_samples)
                    lineage_vec = analyze_documents_to_vec(curr_lineage_doc_data, n_dim_reduce=20, method=method, min_cluster_size=min_cluster_size, min_samples=min_samples)
                else:
                    raise ValueError(f"Unsupported method: {method}")

                common_titles = set(main_vec.keys()) & set(summary_vec.keys()) & set(map_vec.keys()) & set(lineage_vec.keys()) & set(curr_year_dict.keys())
                five_view_data = {}
                for t in common_titles:
                    v_main = main_vec[t][0] if isinstance(main_vec.get(t), list) and len(main_vec[t]) >= 1 else None
                    v_sum = summary_vec[t][0] if isinstance(summary_vec.get(t), list) and len(summary_vec[t]) >= 1 else None
                    v_map = map_vec[t][0] if isinstance(map_vec.get(t), list) and len(map_vec[t]) >= 1 else None
                    v_lin = lineage_vec[t][0] if isinstance(lineage_vec.get(t), list) and len(lineage_vec[t]) >= 1 else None
                    yr = curr_year_dict.get(t)
                    if v_main is None or v_sum is None or v_map is None or v_lin is None or yr is None:
                        continue
                    five_view_data[t] = [v_main, v_sum, v_map, v_lin, yr]

                if weights_config_2 is None:
                    weights_config_2 = {
                        'main': 0.25,
                        'summary': 0.3,
                        'map': 0.1,
                        'lineage': 0.25,
                        'year': 0.1
                    }
                if keyword_section_weights is None:
                    keyword_section_weights = {
                        'main': 0.15,
                        'summary': 0.2,    
                        'map': 0.35,
                        'lineage': 0.3
                    }

                # 构建结构化数据 (注入后的)
                curr_full_docs_struct = {} 
                for t in common_titles:
                    curr_full_docs_struct[t] = {
                        'main': curr_main_doc_data.get(t, ""),
                        'summary': curr_summary_doc_data.get(t, ""),
                        'map': curr_map_doc_data.get(t, ""),
                        'lineage': curr_lineage_doc_data.get(t, "")
                    }
                    
                results2, evaluation_text, cluster_keywords_map = multi_view_clustering_and_visualize(
                    five_view_data,
                    weights_config_2,
                    method='ANCHOR',
                    docs_text_dict=curr_full_docs_struct,
                    visualize=False,
                    keyword_section_weights=keyword_section_weights,
                    **kwargs
                )
                
                # 转换格式以便计算 Score (同时也为了最终返回)
                for t in list(results2.keys()):
                    item = results2[t]
                    if isinstance(item, list) and len(item) >= 2:
                        results2[t] = {
                            'coords_3d': item[0], 
                            'label': item[1], 
                            'keywords': item[2] if len(item) > 2 else []
                        }
                    if isinstance(results2.get(t), dict):
                        if t in curr_full_docs_struct:
                            results2[t].update(curr_full_docs_struct[t])
                        results2[t]['year'] = curr_year_dict.get(t)

                # 计算均衡性指标
                score = calculate_balance_std2(results2)
                print(f"   -> 方案均衡性得分 (Std): {score:.4f}")
                
                if score < min_balance_score:
                    min_balance_score = score
                    best_results2 = results2
                    best_sub_anchors = candidate_anchors
                    best_evaluation_text = evaluation_text
                    best_cluster_keywords_map = cluster_keywords_map
                    print("   -> ⭐ 当前最优方案")

            # 返回最优结果
            return best_results2, best_sub_anchors, best_evaluation_text, best_cluster_keywords_map
    else:
        if weights_config_1 is None:
            raise ValueError("weights_config_1 must be provided.")
        # 1. 提取用于生成锚点的核心素材 (地图 + 综述句)
        # 注意：这里假设md中对应的标题是 "## 标准化领域地图" 和 "## 综述写作专用句"
        # extract_sections_to_dict 会自动匹配
        ref_map_data = extract_sections_to_dict(folder_path, "标准化领域地图")
        ref_review_data = extract_sections_to_dict(folder_path, "综述写作专用句")

        sample_titles = sorted(list(ref_map_data.keys()))[:200] 
        context_parts = []
        for t in sample_titles:
            map_txt = ref_map_data.get(t, "")
            review_txt = ref_review_data.get(t, "")
            # 只保留有效内容
            if len(map_txt) > 10 or len(review_txt) > 10:
                context_parts.append(f"《{t}》\n[文献定位]: {map_txt}\n[内容简述]: {review_txt}")
        
        full_anchor_context = "\n\n".join(context_parts)
        # 3. 调用 AI 生成锚点 (并行 3 次并择优)
        # 这里的 prompt 专门设计用于生成区分度高的分类标准
        anchor_prompt = f"""你是一个负责文献综述架构的资深编辑，你们正在为你们的最新的研究而撰写文献综述。这里有 {len(sample_titles)} 篇文献的【领域定位】和【内容简述】，你需要阅读这些内容，并最终提出应当如何分类这些文献。

---

# 任务书

你是一个负责文献综述架构的资深编辑，你们正在为你们的最新的研究而撰写文献综述。前面的工作流已经整理出 {len(sample_titles)} 篇文献的【领域定位】和【内容简述】，你需要阅读这些内容，并最终提出应当如何将这些文献进行大致的分类，注意此次分类是初步的分类，分类的颗粒度大致到一级学科下的几类二级学科、或同一领域下几类具体方向、亦或按照某种学术视角下某种具有对比性的分类，最终划分为2-4类即可。

## 正在撰写的最新研究的大致情况
（你们正在为该最新的研究而撰写文献综述，因此你需要参考该研究的大致内容来规划文献综述的撰写角度与方向，为该研究打下基础）

{paper_desc}

## 分类思路

1. 牢记此次分类的任务目的是为了辅助后续文献综述的撰写，而文献综述的撰写是为了后续正式的研究内容打下基础。此次分类是初步的分类，虽然分类颗粒度不需要很细，但依旧需要在分类的时候考虑到后续进一步细分每一类型中的文章时的分类思路。
2. 所给出的文献中，并不一定都能被包含进你给出的分类方案中，部分文献可被视为噪声文献，你给出的分类也不需要将所有文献都归纳进去，能将大部分的文献归纳进去即可。
3. 我们需要对文献的分类具有直观性，能体现每一类文献的最突出的、最明显的定位特征，但同时又需要对文献的分类具有逻辑性与互补性，每一类文献之间能被恰当的逻辑联系与组织起来，这样才有利于文献综述的撰写。
4. 为达成以上目标，分类的思路可参考如下：
   1. 首先，对于大部分的文献，凭借直觉对其进行分类，先不必考虑分类的逻辑性与互补性，此时所分的类能尽量凸显文献的最大的特征，最贴近文献的直观主要内容。
   2. 此时，所分的类可能并未基于同一的维度与标准，没有逻辑性与互补性，此时可以思考该以什么样的逻辑或某种学术上的视角将这些分类串联起来。
   3. 若难以不牵强的逻辑将所分类型串联起来，可以逐步调整所分类型的描述、视角，调整过程当然会减少分类的直观性，但能增加分类的逻辑性，最终找到一个不错的平衡点，使分类兼具直观性与逻辑性。
5. 分类逻辑可以从“研究流派”、“核心问题”、“理论与应用”、“聚焦侧重点（此方法几乎通用）”来考虑。
6. 分类时需要保证每一类的”稠密性“，即每一类文献的数量不能过于稀疏，否则会导致文献综述的章节内容不够充实，例如某一类型的文献只有3篇，则不能将这些文章单独归为一类，要么作为噪音舍去，要么融入到其他类型中。
7. 在输出中，定义2-4个分类即可，尤其是当文献数量较少时（例如总的文献数量只有70篇左右），也可以定义为2-3个分类即可（确保文献综述的章节内容足够稠密），若经过缜密思考发现文献内容明显应该被分为逻辑清晰的4类甚至5类，则也不必拘泥于要求，大胆划分。为为每个子主题撰写一段**详细的、包含丰富专业术语的描述文本。严格遵守输出格式。

## 输出格式

必须是标准的 JSON 格式，Key 为数字索引（0, 1, 2...），Value 为描述文本。不要附带任何md格式，示例如下：

{{
    "Key1": "Value1",
    "Key2": "Value2",
    ...
}}

## 描述要求
在描述时，可以参考以下逻辑进行描述：
该类文献...（该类文献被分类的突出特点，例如同属于...领域/同样聚焦于...角度/同样关注...），可以以如下学术受控词来进行描述：...（使用一些专业名词、短语甚至语句来描述这一类文章的特点，可以多多参考【文献定位】部分，中英文均可，描述词越多越好、越凸显特征越好、越独有越好）。例如部分文章针对...问题进行了研究...，部分文章...（重点在此，需要多多举例详细描述该类型文章中有哪些文章做了什么事情，体现出该类的表现，不要详细指出哪篇文章具体做了什么事情，只需匿名描述大概，描述所用的用词以及句子结构可以尽量往原文贴近，例子越多越好）。
注意在描述一类文献时，要突出其独有的特点，也就是在避开共同特征、通用描述词的同时，还要尽量避开其他类文献的独特关键词或独特描述。
这是因为你的描述文本将用于向量检索并匹配相关文献，因此最好包含该类别的**高频特征词**（如特定算法名、特定场景名、特定理论指标），**模仿该类型的文章的主要逻辑进行描述**，你的描述与所给出的文献整理内容在特点上越相似，越能被算法检索出相似度，同时也得避开其他类文献的特征描述，避免出现A类文章与B类文章的描述的相似度高于与A类文章的描述的相似度而被误判为B类文章。

---

# 文献整理内容

{full_anchor_context[:50000]} 

---

# 关键提示

请阅读文献整理内容，并按照任务书的要求，提出应当如何将这些文献进行大致的、初步的分类，注意此次分类是初步的分类，划分为2-4类即可。并且遵循描述要求，按照输出格式进行输出。输出案例如下（仅供参考风格，内容需根据实际素材生成）：

{{
    "0": "该类文献主要聚焦于...领域，关注...问题。学术受控词可以描述为...。具体的，部分文章针对...进行了研究，提出了...方法；...；...；...。总体而言，这类文献体现了在...场景下的...趋势。",
    "1": "该类文献属于...流派，核心在于...理论的探讨。学术受控词...。例如，有研究指出...，并验证了...；还有研究...；...；...。",
    "2": "该类文献集中讨论了...的应用落地，特别是在...方面。特征词包括...。具体的，一些文章采用了...，旨在...；另一些...；...；...；..."
    ...
}}

以上示例仅仅是一个简单的分类示例，你需要做更加详细扎实的工作。
"""
        
        def generate_single_anchors():
            try:
                # 获取 API 配置
                api_key = os.environ.get('ARK_API_KEY', '')
                model_name = os.environ.get('ARK_MODEL', 'deepseek-v3-2-251201')
                res = AI_call(anchor_prompt, api_key, model_name)
                clean_json = res.strip().replace("```json", "").replace("```", "")
                anchor_docs_raw = json.loads(clean_json)
                return {int(k): v.lstrip("该类") for k, v in anchor_docs_raw.items()}
            except Exception as e:
                print(f"⚠️ [AI架构师] 锚点生成单次失败，错误: {e}")
                return None

        # 并行调用 3 次
        print(f"🚀 [AI架构师] 正在并行生成 3 套父级锚点方案以择优...")
        anchor_candidates = []
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(generate_single_anchors) for _ in range(3)]
            for f in futures:
                res = f.result()
                if res:
                    anchor_candidates.append(res)
        
        if not anchor_candidates:
            print("❌ 所有锚点生成均失败，回退到空锚点。")
            anchor_candidates = [None]
        
        # 择优循环
        best_results = None
        best_anchor_docs = None
        best_evaluation_text = ""
        best_cluster_keywords_map = {}
        min_balance_score = float('inf')

        for idx, anchor_docs in enumerate(anchor_candidates):
            print(f"\n--- 正在评估第 {idx+1}/{len(anchor_candidates)} 套父级分类方案 ---")
            if anchor_docs:
                print(f"   锚点数量: {len(anchor_docs)}")

            # 注意：process_and_classify_target_section 内部会注入 anchor_docs
            # 这里虽然会多次读取 IO，但为了不修改原有函数签名，保持逻辑稳定，我们接受这个开销
            
            target_section = "## 论文主要内容"
            if method == 'DBSCAN':
                eps = kwargs.get('eps', 0.5)
                min_samples = kwargs.get('min_samples', 3)
                main_vec,main_doc_data = process_and_classify_target_section(folder_path, target_section, method=method,anchor_docs=anchor_docs, eps=eps, min_samples=min_samples)
            elif method == 'KMEANS':
                n_clusters = kwargs.get('n_clusters', 3)
                main_vec,main_doc_data = process_and_classify_target_section(folder_path, target_section, method=method,anchor_docs=anchor_docs, n_clusters=n_clusters)
            elif method == 'HDBSCAN':
                min_cluster_size = kwargs.get('min_cluster_size', 3)
                cluster_selection_epsilon=kwargs.get('cluster_selection_epsilon', 0.3)
                main_vec,main_doc_data = process_and_classify_target_section(folder_path, target_section, method=method,anchor_docs=anchor_docs, min_cluster_size=min_cluster_size, cluster_selection_epsilon=cluster_selection_epsilon)
            else:
                raise ValueError(f"Unknown method: {method}")

            
            target_section = "## 论文核心内容概括"
            if method == 'DBSCAN':
                eps = kwargs.get('eps', 0.5)
                min_samples = kwargs.get('min_samples', 3)
                summary_vec,summary_doc_data = process_and_classify_target_section(folder_path, target_section, method=method,anchor_docs=anchor_docs, eps=eps, min_samples=min_samples)
            elif method == 'KMEANS':
                n_clusters = kwargs.get('n_clusters', 3)
                summary_vec,summary_doc_data = process_and_classify_target_section(folder_path, target_section, method=method,anchor_docs=anchor_docs, n_clusters=n_clusters)
            elif method == 'HDBSCAN':
                min_cluster_size = kwargs.get('min_cluster_size', 3)
                cluster_selection_epsilon=kwargs.get('cluster_selection_epsilon', 0.3)
                summary_vec,summary_doc_data = process_and_classify_target_section(folder_path, target_section, method=method,anchor_docs=anchor_docs, min_cluster_size=min_cluster_size, cluster_selection_epsilon=cluster_selection_epsilon)
            else:
                raise ValueError(f"Unknown method: {method}")

            target_section = "标准化领域地图"
            if method == 'DBSCAN':
                eps = kwargs.get('eps', 0.5)
                min_samples = kwargs.get('min_samples', 3)
                map_vec,map_doc_data = process_and_classify_target_section(folder_path, target_section, method=method,anchor_docs=anchor_docs, eps=eps, min_samples=min_samples)
            elif method == 'KMEANS':
                n_clusters = kwargs.get('n_clusters', 3)
                map_vec,map_doc_data = process_and_classify_target_section(folder_path, target_section, method=method,anchor_docs=anchor_docs, n_clusters=n_clusters)
            elif method == 'HDBSCAN':
                min_cluster_size = kwargs.get('min_cluster_size', 3)
                cluster_selection_epsilon=kwargs.get('cluster_selection_epsilon', 0.3)
                map_vec,map_doc_data = process_and_classify_target_section(folder_path, target_section, method=method,anchor_docs=anchor_docs, min_cluster_size=min_cluster_size, cluster_selection_epsilon=cluster_selection_epsilon)
            else:
                raise ValueError(f"Unknown method: {method}")

            target_section = "谱系背景与脉络"
            if method == 'DBSCAN':
                eps = kwargs.get('eps', 0.5)
                min_samples = kwargs.get('min_samples', 3)
                lineage_vec,lineage_doc_data = process_and_classify_target_section(folder_path, target_section, method=method,anchor_docs=anchor_docs, eps=eps, min_samples=min_samples)
            elif method == 'KMEANS':
                n_clusters = kwargs.get('n_clusters', 3)
                lineage_vec,lineage_doc_data = process_and_classify_target_section(folder_path, target_section, method=method,anchor_docs=anchor_docs, n_clusters=n_clusters)
            elif method == 'HDBSCAN':
                min_cluster_size = kwargs.get('min_cluster_size', 3)
                cluster_selection_epsilon=kwargs.get('cluster_selection_epsilon', 0.3)
                lineage_vec,lineage_doc_data = process_and_classify_target_section(folder_path, target_section, method=method,anchor_docs=anchor_docs, min_cluster_size=min_cluster_size, cluster_selection_epsilon=cluster_selection_epsilon)
            else:
                raise ValueError(f"Unknown method: {method}")

            target_section = "## 发表年份"
            if method == 'DBSCAN':
                eps = kwargs.get('eps', 0.5)
                min_samples = kwargs.get('min_samples', 3)
                year_dict = process_and_classify_target_section(folder_path, target_section, method=method,anchor_docs=anchor_docs, eps=eps, min_samples=min_samples)
            elif method == 'KMEANS':
                n_clusters = kwargs.get('n_clusters', 3)
                year_dict = process_and_classify_target_section(folder_path, target_section, method=method,anchor_docs=anchor_docs, n_clusters=n_clusters)
            elif method == 'HDBSCAN':
                min_cluster_size = kwargs.get('min_cluster_size', 3)
                cluster_selection_epsilon=kwargs.get('cluster_selection_epsilon', 0.3)
                year_dict = process_and_classify_target_section(folder_path, target_section, method=method,anchor_docs=anchor_docs, min_cluster_size=min_cluster_size, cluster_selection_epsilon=cluster_selection_epsilon)
            else:
                raise ValueError(f"Unknown method: {method}")

            common_titles = set(main_vec.keys()) & set(summary_vec.keys()) & set(map_vec.keys()) & set(lineage_vec.keys()) & set(year_dict.keys())
            five_view_data = {}
            for t in common_titles:
                # 若任一视图缺失则跳过该文献
                if (t not in main_vec or not main_vec[t] or
                    t not in summary_vec or not summary_vec[t] or
                    t not in map_vec or not map_vec[t] or
                    t not in lineage_vec or not lineage_vec[t] or
                    t not in year_dict or year_dict[t] is None):
                    continue
                five_view_data[t] = [
                    main_vec[t][0],
                    summary_vec[t][0],
                    map_vec[t][0],
                    lineage_vec[t][0],
                    int(year_dict[t])
                ]
            if keyword_section_weights is None:
                keyword_section_weights = {
                    'main': 0.15,
                    'summary': 0.2,    
                    'map': 0.35,
                    'lineage': 0.3
                }

            # 2. 构建结构化数据
            full_docs_struct = {} 
            for t in common_titles:
                full_docs_struct[t] = {
                    'main': main_doc_data.get(t, ""),
                    'summary': summary_doc_data.get(t, ""),
                    'map': map_doc_data.get(t, ""),
                    'lineage': lineage_doc_data.get(t, "")
                }
            if weights_config_1 is None:
                weights_config_1 = {
                    'main': 0.15,
                    'summary': 0.15,
                    'map': 0.45,
                    'lineage': 0.15,
                    'year': 0.1
                }
            results,evaluation_text,cluster_keywords_map = multi_view_clustering_and_visualize(
                five_view_data,
                weights_config_1,
                method='ANCHOR',
                docs_text_dict=full_docs_struct,
                visualize=False,
                keyword_section_weights=keyword_section_weights,
                **kwargs
                
            )

            #将原文本数据也添加进results（稳健处理：检测存在性与形态）
            for t in common_titles:
                if t not in results:
                    continue
                item = results[t]
                if isinstance(item, list) and len(item) >= 2:
                    results[t] = {'coords_3d': item[0], 'label': item[1], 'keywords': item[2]}
                elif not isinstance(item, dict):
                    continue
                results[t]['main'] = main_doc_data.get(t, "")
                results[t]['summary'] = summary_doc_data.get(t, "")
                results[t]['map'] = map_doc_data.get(t, "")
                results[t]['lineage'] = lineage_doc_data.get(t, "")
                results[t]['year'] = year_dict.get(t, None)
            
            # 计算均衡性指标
            score = calculate_balance_std1(results)
            print(f"   -> 方案均衡性得分 (Std): {score:.4f}")
            
            if score < min_balance_score:
                min_balance_score = score
                best_results = results
                best_anchor_docs = anchor_docs
                best_evaluation_text = evaluation_text
                best_cluster_keywords_map = cluster_keywords_map
                print("   -> ⭐ 当前最优方案")

        labels_in_results = []
        if best_results:
            for v in best_results.values():
                lv = None
                if isinstance(v, dict):
                    lv = v.get('label', None)
                elif isinstance(v, list) and len(v) >= 2:
                    lv = v[1]
                if lv is not None:
                    labels_in_results.append(lv)
            labels_in_results = sorted(set(labels_in_results))
            print("所有label：", labels_in_results)
        return best_results,best_anchor_docs,best_evaluation_text,best_cluster_keywords_map


if __name__ == '__main__':
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

    folder_path = "C:\\文献整理合集"

    results,anchor,evaluation_text,cluster_keywords_map = comprehensive_process_function(method = 'KMEANS', weights_config_1 = weights_config_1,keyword_section_weights=keyword_section_weights_1 ,folder_path = folder_path,n_components=20,k_penalty=0.02,similarity_threshold=0.75)
    results2,anchor2,evaluation_text2,cluster_keywords_map2 = comprehensive_process_function(method = 'KMEANS', weights_config_2 = weights_config_2,keyword_section_weights=keyword_section_weights_2 ,label = 1,results = results,n_components=20,k_penalty=0.01,similarity_threshold=0.75)


    anchor
    results
    cluster_keywords_map

    import pprint
    pp = pprint.PrettyPrinter(indent=2)

    print("\n=== VARIABLE INSPECTION ===")
    print(">>> anchor:")
    pp.pprint(anchor)

    print("\n>>> results (First 2 items):")
    # 为了防止输出太长，只展示前两个
    pp.pprint(dict(list(results.items())[:2]))

    print("\n>>> cluster_keywords_map:")
    pp.pprint(cluster_keywords_map)

    print("\n>>> Cluster Counts (Paper Distribution):")
    from collections import Counter
    # 提取所有文章的 label (results[title]['label'])
    # 注意: results 的 value 是一个 dict，其中包含 'label' 键
    labels_list = [v['label'] for v in results.values()]
    counts = Counter(labels_list)
    
    # 按 Label 排序输出
    for label in sorted(counts.keys()):
        count = counts[label]
        label_name = f"Cluster {label}" if label != -1 else "Noise (-1)"
        print(f"  {label_name}: {count} papers")
        
    print("===========================\n")





    # 第一轮：全局聚类
    print("\n\n======== Round 1: Global Clustering ========")
    results, anchor, evaluation_text, cluster_keywords_map = comprehensive_process_function(
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
    labels_found = sorted(list(set(v['label'] for v in results.values() if v['label'] != -1)))
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
                results=results,      # 传入第一轮的完整结果
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
    pp.pprint(anchor)
    
    print("\n>>> Round 2 Sub-clustering Stats:")
    for pid, data in sub_results_storage.items():
        print(f"  Parent Label {pid}: {len(data['results'])} papers processed")
        print(f"    Sub-anchors: {list(data['anchor'].keys())}")
        print(f"    Sub-anchors values: {data['anchor']}")