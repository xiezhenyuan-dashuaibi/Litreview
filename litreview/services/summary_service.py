import os
import threading
import time
from typing import Dict, List
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..state import TASKS
from .system_service import pdf2markdown, AI_call


class SummaryService:
    def _list_pdfs(self, root: str) -> List[str]:
        files = []
        for name in os.listdir(root):
            p = os.path.join(root, name)
            if os.path.isfile(p) and name.lower().endswith('.pdf'):
                files.append(p)
        files.sort()
        return files

    def _ensure_root(self) -> str:
        base = os.environ.get('LITREVIEW_WORKDIR') or os.path.join(os.getcwd(), 'literature_review')
        target = os.path.join(base, '文献整理合集')
        os.makedirs(target, exist_ok=True)
        return target

    def _process_one(self, pdf_path: str) -> str:
        print("[SUMMARY][PROCESS_START]", pdf_path, flush=True)
        out_root = self._ensure_root()
        print("[SUMMARY][OUT_ROOT]", out_root, flush=True)
        base = os.path.splitext(os.path.basename(pdf_path))[0]
        invalid = '<>:"/\\|?*'
        base = ''.join('_' if (ch in invalid or ord(ch) < 32) else ch for ch in base).strip()
        if base == '':
            base = 'untitled'
        if len(base) > 150:
            base = base[:150]
        if base.lower() in ('con','prn','aux','nul') or base.lower().startswith('com') or base.lower().startswith('lpt'):
            base = '_' + base
        print("[SUMMARY][BASENAME]", base, flush=True)
        for name in os.listdir(out_root):
            if name.lower().endswith('.md') and (name.lower() == f"{base.lower()}.md" or name.lower().startswith(f"{base.lower()}_")):
                p = os.path.join(out_root, name)
                print("[SUMMARY][EXISTING_MD]", p, flush=True)
                return p
        lock_path = os.path.join(out_root, f"{base}.lock")
        print("[SUMMARY][LOCK_TRY]", lock_path, flush=True)
        acquired = False
        lock_attempts = 0
        while not acquired:
            try:
                with open(lock_path, 'x', encoding='utf-8') as _:
                    pass
                acquired = True
                print("[SUMMARY][LOCK_ACQUIRED]", lock_path, flush=True)
            except FileExistsError:
                for name in os.listdir(out_root):
                    if name.lower().endswith('.md') and (name.lower() == f"{base.lower()}.md" or name.lower().startswith(f"{base.lower()}_")):
                        p = os.path.join(out_root, name)
                        print("[SUMMARY][LOCK_WAIT_FOUND_MD]", p, flush=True)
                        return p
                print("[SUMMARY][LOCK_WAIT]", lock_path, flush=True)
                time.sleep(0.5)
                lock_attempts += 1
                if lock_attempts >= 3:
                    print("[SUMMARY][LOCK_WAIT_TIMEOUT]", lock_path, flush=True)
                    raise RuntimeError("lock wait exceeded")
        
        try:
            print("[SUMMARY][OCR_BEGIN]", pdf_path, flush=True)
            ak = os.environ.get('VOLC_ACCESS_KEY', '')
            sk = os.environ.get('VOLC_SECRET_KEY', '')
            api_key = os.environ.get('ARK_API_KEY', '')
            page_num = int(os.environ.get('OCR_PAGE_NUM', '32'))
            parse_mode = os.environ.get('OCR_PARSE_MODE', 'ocr')
            ocr_md = ''
            ocr_try = 0
            for _ in range(3):
                try:
                    ocr_try += 1
                    print("[SUMMARY][OCR_TRY]", ocr_try, parse_mode, page_num, flush=True)
                    ocr_md = pdf2markdown(ak, sk, pdf_path, page_num, parse_mode)
                    if ocr_md:
                        print("[SUMMARY][OCR_DONE]", len(ocr_md), flush=True)
                        break
                except Exception as e:
                    print("[SUMMARY][OCR_ERROR]", str(e), flush=True)
                    time.sleep(1)
            if not ocr_md:
                print("[SUMMARY][OCR_MAX_RETRY_EXCEEDED]", pdf_path, flush=True)
                raise RuntimeError("ocr retries exceeded")
            research_topic = os.environ.get('RESEARCH_TOPIC', '')
            research_desc = os.environ.get('RESEARCH_DESCRIPTION', '')
            prompt = f"""你是一个科研助手，你的任务是辅助用户做专业的论文整理工作，这需要你根据用户给出的任务书，在阅读并理解所给出的论文后，做专业的论文总结以及关键信息提取。
---

# 任务书

你是一个专业的科研助手，你的工作是对论文进行专业的总结以及关键信息提取。由于该整理产出将被用户用于自身的论文撰写，因此在整理时你不仅需要关注这篇文章本身讲了什么内容，你还需要重点思考这篇文章与用户所研究的主题有着什么样的关系，你所整理出的结果必须体现出这样的思考，其中的信息必须有利于用户的论文撰写（例如梳理出该文章的论点与用户论文中的某些观点可能存在着相应/相悖/关联/印证，有助于构建与厘清用户研究主题的map与position）。

## 用户的研究主题（重中之重）

{research_topic}

## 用户的研究说明（重中之重）

{research_desc}

## 需要整理出的信息以及相关要求

1. 详细叙述论文的主要内容，应当比论文的摘要更加详细，要求梳理有条理有逻辑，其中需要重点叙述该论文研究的问题（为什么会提出这样的问题、解决/回答这样的问题能有多大意义）。
2. 简述（概括需要周到但干练）论文的研究主题、所研究的问题的由来与研究价值、本研究的主要工作（例如使用怎么样的新方法研究旧问题，或使用了怎么样的新/旧方法研究新问题等等）、本研究的主要结论。
3. 对用户的研究有何帮助，或者说与用户的研究有什么关联，目标文献可能与用户的研究主题以及各种论点有直接的关联，也有可能没有直接的关联，因此在回答该问题前进行思考与揣摩，若文献与用户的某些论点间可能存在着潜在的印证关系，也可以整理出来。当然，该关联也不能牵强。
4. 对该文献进行关联度评分，衡量该文献中的内容对用户研究的帮助有多大。注意关联度评分并不代表该文章的重要程度，它可能在学术领域是一篇很重要的文章，只是对用户的研究帮助不大而已
5. 阐明该文献的map与position，该部分尤其重要，你需要基于严谨的“三层科学计量框架”，对我提供的这篇文献进行精准画像和定位。请忽略通用的摘要总结。请严格执行以下**“三层精准定位协议”**，以确定该文献在学术版图中的精确坐标：
    1. 宏观切分：
    **方法论依据：** 层级分类法 (Hierarchical Taxonomy) & 受控词表 (Controlled Vocabulary)
    * **执行动作：** 请勿使用作者随意列出的关键词。请尝试将该文献映射到通用的标准分类体系中（例如计算机领域的 ACM CCS，经济学的 JEL，或通用的科学分类树）。
    * **输出要求：**
        1.  **一级学科 (Discipline):** （例如：计算机科学 / 社会学）
        2.  **二级子学科 (Sub-discipline):** （例如：自然语言处理）
        3.  **具体领域 (Specific Domain):** （例如：大语言模型 - 对齐技术）
        4.  **核心原子问题 (Core Problem):** 定义这篇论文试图解决的那个最具体的“元问题”是什么。
    2. 中观脉络：
    **方法论依据：** CARS 模型 (Create a Research Space) & 主路径推断 (Main Path Inference)
    * **执行动作：** 分析文章的“引言”和“相关工作”部分，确定其历史地位和演化角色。
    * **CARS 分析 (Gap Definition):**
        * *传承 (The Legacy/Move 1):* 它承认并基于哪个既定的传统或“主路径”？
        * *缺口 (The Gap/Move 2):* 它声称填补了什么具体的空白？（是知识空白 Knowledge Void，方法论缺陷 Methodological Flaw，还是证据冲突 Conflicting Evidence？）
    * **演化地位 (Evolutionary Status):**
        * 它是 **“开创性/奠基性”** 工作（开启了一条新路径）？
        * 它是 **“渐进性/优化性”** 工作（在既有路径上提升效果）？
        * 它是 **“综合性/桥接性”** 工作（连接了两条原本分离的路径）？
    3. 微观对比：
    **方法论依据：** 认识论分类 (Epistemic Classification) & 研究范式
    * **执行动作：** 基于其“探究工具”和贡献方式进行分类。
    * **输出要求：**
        1.  **研究范式 (Research Paradigm):**
        **【范式参考列表 (Paradigm Library)】**
        * **A. 工程与人工科学 (Engineering & CS):**
            * *建构/设计 (Constructive/Design):* 创造了新系统、新架构、新制品。
            * *仿真/模拟 (Simulation):* 基于计算机模拟的实验。
            * *评测/基准 (Benchmarking):* 专注于性能评估和比较。
        * **B. 自然科学 (Natural Sciences):**
            * *理论推导 (Theoretical):* 数学推导、物理模型构建。
            * *实验验证 (Experimental):* 控制变量的实验室研究。
            * *观察发现 (Observational):* 天文、地质等非干预性观察。
        * **C. 社会科学 (Social Sciences):**
            * *实证-定量 (Empirical-Quantitative):* 统计分析、计量经济学。
            * *实证-定性 (Empirical-Qualitative):* 案例研究、民族志、访谈。
            * *规范/概念 (Normative/Conceptual):* 定义概念、探讨“应然”问题。
        * **D. 人文学科 (Humanities):**
            * *阐释/解释 (Hermeneutic):* 文本细读、意义构建。
            * *批判/理论 (Critical):* 揭示权力结构、意识形态批判。
            * *历史/考据 (Historical):* 档案研究、史料考证。
        * **E. 形式科学 (Formal Sciences):**
            * *公理化证明 (Axiomatic):* 纯数学或逻辑学的定理证明。
        * **F. 通用综述 (General Review):**
            * *系统性综述/元分析 (Systematic Review / Meta-analysis)*
        2.  **流派归属 (School/Branch):** 如果该问题存在不同的“思想学派”（例如符号主义 vs. 连接主义），从方法论上看，这篇文章属于哪个阵营？若不存在流派而仅仅是对某一问题不同角度的探讨，也需要描述该文章的大致方向与论点。
6. 该文章中或许还提到了一些重要的文献，较大程度地支撑起了该文章的重要研究内容，罗列出这些文献的标题与作者，有利于用户更深入了解该研究领域的发展脉络。

## 输出格式

请在正式输出中，以md格式输出以下内容，请严格遵守以下格式输出，括号内为填写部分，其他内容请保持不变：
```输出格式
# 论文整理：(此处填写所整理的文献标题)

## 发表年份

(此处填写所整理的文献发表的年份，这通常在文章的页眉或页脚信息中，需要关注文献中被插入在正文中的看似“格式错乱”的部分，若实在没有相关信息，则可以默认其发表年份在其最新的参考文献之后的1年，例如其参考文献中最新的文献是2024年，则默认本文的发表年份为2025年)

## 论文主要内容

(此处填写论文的详细内容，注意此处不是对文章摘要简单的复述，需要详细描述论文的内容，包括但不限于论文的研究问题、研究价值/为什么做这样的研究、研究方法、实验设计、过程与结果、研究结论等，需要进行**详细的讲解与叙述，尤其是要浓墨重彩地说明为什么会提出这样的问题、解决/回答这样的问题能有多大意义**，而非三言两语概括，注意用语尽量符合科研的严谨要求，不可编造或超出原文解释范围)

## 论文核心内容概括

(此处填写论文的核心内容概括（概括需要周到但干练），主要概括出研究主题、所研究的问题的由来与研究价值、本研究的主要工作与方法（例如使用怎么样的新方法研究旧问题，或使用了怎么样的新/旧方法研究新问题等等）、本研究的主要结论。)

## 与用户的研究内容有何关联

(此处罗列该文献对用户的研究有何帮助，不论是直接的关联，还是潜在的关联，甚至是“在经过了深入的思考后，发现该文章的某个论点可能印证了用户研究主题中某个论点的部分逻辑”，都需要进行展示)

## 关联度评分

(此处填写该文献与用户研究主题的关联度评分，范围为0-100，60以下表示该文章不够符合用户研究主题，即便经过思考也没有发现潜在的、对用户研究有有效帮助的论点，60-70表示该文章中某些论点与用户的研究中的某些论点存在着潜在的关联，70-80表示该文章中某些论点与用户的研究中的某些论点存在着直接的关联，80-90表示该文章的研究主题与用户的研究主题高度相似，只是角度或许存在差异，但在众多地方都能为用户的研究提供对比与启发，90-100表示该文章与用户研究的主题几乎一致，用户的研究绕不开该文章，甚至需要基于该文章做出创新或改进，否则研究内容可能重合。注意关联度评分并不代表该文章的重要程度，它可能在学术领域是一篇很重要的文章，只是对用户的研究帮助不大而已)

## 论文map

(此处填写论文的领域地图以及定位，请按照以下结构化格式输出分析结果：)

### 1. 标准化领域地图

(此处定位文献的“宏观切分”，定位方法为[一级学科] - [二级子学科] - [具体领域] - [核心原子问题] - [列出5-10个正式的学术受控词]，在输出时使用一段话清晰描述)

### 2. 谱系背景与脉络

(此处梳理文献的“中观脉络”，以一段话描述三个方面的内容：1. 以一段话详细描述该文献的领域地图：[由一级学科、二级学科到具体领域，并着重介绍该论文所处的具体领域，其研究位于学科领域下什么样的分支]；。2. 前人基础:[简述其基于的“祖先”研究]；3. 识别出Gap并描述本文贡献:[前人工作中存在的具体局限或未解之谜，而本文的贡献在于例如：填补空白 / 纠正错误 / 跨界融合，若该文章仅仅是杂谈或访谈类，不算严谨的研究型论文，则可以指出而不必说明贡献])

### 3. 认识论范式

(此处描述该文章的“微观对比”（认识论范式），首先确定该文献属于什么领域，再参考前文的范式参考列表判断该文献属于什么样的范式，思路为[领域] - [范式] - [简单描述文献范式的表现]，回复时使用一段话清晰描述)

### 4. 综述写作专用句

(*请起草一句适合直接放入文献综述中的学术句子，用于给这篇文章定位：*例如““在 [细分领域] 领域，针对 [核心问题]，[作者] (年份) 采用 [具体范式] 方法，提出了 [核心贡献]。该研究通过 [具体手段] 填补了 [前人Gap]，属于该技术路线中的 [演化角色] 工作。””)

## 该论文关联的、值得额外阅读的论文（选填，若填则必须真实来源于该论文的引用文献）

(此处罗列与该文献相关的、值得额外阅读的论文的标题与作者，选填，若填则必须真实来源于该论文的引用文献，每个标题占一行，标题前不需要序号，重点参考该文献中重点章节中提到的重要参考文献，这有助于帮助用户寻找文献的重要“祖宗”，追根溯源)

```

---

# 待整理文献（重要提示，文献中部分格式的错乱其实是插入的页眉页脚的信息，例如某一段话中间被插入了换行符、数字、日期以及注脚说明等等）

{ocr_md[:50000]}

---

# 关键提示

请根据以上**任务书**以及**待整理文献**，进行详细的分析与总结，输出符合要求的md格式内容。
你的输出的简单示例：
```Markdown
# 论文整理：[xxx论文标题]

## 发表年份

2025年

## 论文主要内容

...本文针对...问题进行了研究。作者首先指出当前...方法存在...局限，随后提出了...实验部分...结果显示...结论认为...。

## 论文核心内容概括

* **研究主题：** ...
* **问题由来与价值：** ...源于...现象，旨在解决...痛点。
* **主要工作：** ...提出了...算法/模型。
* **主要结论：** ...证实了...的有效性。

## 与用户的研究内容有何关联

1. **方法借鉴：** ...文中的...实验设计可以参考用于用户的...部分。
2. **逻辑支撑：** ...其结论...侧面印证了用户关于...的假设。

## 关联度评分

75

## 论文map

### 1. 标准化领域地图

本文所属的一级学科为 xxx与xxx的复合领域，二级子学科为 xxx，具体领域为 xxx，核心原子问题为 xxx，可以使用受控词A, 受控词B...来定位该问题。

### 2. 谱系背景与脉络

1. ...本文的研究领域属于[xxx]与[xxx]复合领域下的[xxx]分支，本文聚焦在[xxx]具体领域上，该领域...
2. ...本文继承了...，前人的研究表明...
3. ...本文指出前人未能解决...问题，本文...。

### 3. 认识论范式

本文属于...大类，范式为...，文中...。

### 4. 综述写作专用句

“在 [xxx] 领域，针对 [xxx] 问题，[作者] (年份) ...，发现了/得出了...”

## 该论文关联的、值得额外阅读的论文（选填，若填则必须真实来源于该论文的引用文献）

* Title of Paper A (Author, Year)
* Title of Paper B (Author, Year)
```

**以上内容仅为格式示例，你需要做更加详细扎实的工作，请按要求完成以上任务**
"""
            content = ''
            ai_try = 0
            for _ in range(3):
                try:
                    ai_try += 1
                    print("[SUMMARY][AI_TRY]", ai_try, flush=True)
                    content = AI_call(prompt, api_key, os.environ.get('ARK_MODEL', 'deepseek-v3-2-251201'))
                    if content:
                        print("[SUMMARY][AI_DONE]", len(content), flush=True)
                        break
                except Exception as e:
                    print("[SUMMARY][AI_ERROR]", str(e), flush=True)
                    time.sleep(1)
            if not content:
                print("[SUMMARY][AI_MAX_RETRY_EXCEEDED]", pdf_path, flush=True)
                raise RuntimeError("ai retries exceeded")
            i = 0
            write_attempts = 0
            written = False
            while write_attempts < 3:
                name = f"{base}.md" if i == 0 else f"{base}_{i}.md"
                out_path = os.path.join(out_root, name)
                try:
                    print("[SUMMARY][WRITE_TRY]", out_path, flush=True)
                    with open(out_path, 'x', encoding='utf-8') as f:
                        f.write(content or '')
                    print("[SUMMARY][WRITE_OK]", out_path, flush=True)
                    written = True
                    break
                except FileExistsError:
                    print("[SUMMARY][WRITE_EXISTS]", out_path, flush=True)
                    i += 1
                    write_attempts += 1
                    continue
                except OSError as e:
                    print("[SUMMARY][WRITE_OSERROR]", out_path, str(e), flush=True)
                    time.sleep(0.5)
                    i += 1
                    write_attempts += 1
                    continue
            if not written:
                print("[SUMMARY][WRITE_MAX_RETRY_EXCEEDED]", base, flush=True)
                raise RuntimeError("write retries exceeded")
            print("[SUMMARY][PROCESS_DONE]", out_path, flush=True)
            return out_path
        finally:
            try:
                if os.path.exists(lock_path):
                    os.remove(lock_path)
                    print("[SUMMARY][LOCK_RELEASE]", lock_path, flush=True)
            except Exception:
                pass

    def _run(self, task_id: str, pdfs: List[str]):
        s = TASKS.setdefault(task_id, {"summary": {"total": len(pdfs), "completed": 0, "failed": 0, "files": [os.path.basename(p) for p in pdfs], "currentFile": None}})["summary"]
        print("[SUMMARY][RUN_START]", task_id, s["total"], flush=True)
        failed_files = []
        idx = 0
        while idx < len(pdfs):
            batch = pdfs[idx: idx + 5]
            print("[SUMMARY][BATCH_START]", idx, [os.path.basename(p) for p in batch], flush=True)
            with ThreadPoolExecutor(max_workers=5) as ex:
                futures = {}
                for p in batch:
                    futures[ex.submit(self._retry_one, p)] = p
                for fut in as_completed(futures):
                    p = futures[fut]
                    try:
                        r = fut.result()
                        s["completed"] += 1
                        s["currentFile"] = os.path.basename(p)
                        print("[SUMMARY][FILE_DONE]", p, r, flush=True)
                    except Exception as e:
                        s["failed"] += 1
                        s["currentFile"] = os.path.basename(p)
                        failed_files.append({"file": os.path.basename(p), "error": str(e)})
                        print("[SUMMARY][FILE_FAIL]", p, str(e), flush=True)
            idx += 5
        print("[SUMMARY][RUN_DONE]", task_id, flush=True)
        if failed_files:
            print("[SUMMARY][FAILED_LIST]", failed_files, flush=True)
        else:
            print("[SUMMARY][FAILED_LIST]", [], flush=True)
        s["currentFile"] = None

    def _retry_one(self, pdf_path: str) -> str:
        print("[SUMMARY][RETRY_START]", pdf_path, flush=True)
        attempts = 0
        while attempts < 3:
            try:
                return self._process_one(pdf_path)
            except Exception as e:
                attempts += 1
                print("[SUMMARY][RETRY_ERROR]", pdf_path, attempts, str(e), flush=True)
                time.sleep(1)
        print("[SUMMARY][RETRY_MAX_RETRY_EXCEEDED]", pdf_path, flush=True)
        raise RuntimeError("file retries exceeded")

    def start(self, task_id: str) -> Dict:
        root = os.environ.get('LITREVIEW_PDF_ROOT') or ''
        pdfs = self._list_pdfs(root) if root and os.path.isdir(root) else []
        print("[SUMMARY][START]", task_id, root, len(pdfs), flush=True)
        TASKS[task_id] = {"summary": {"total": len(pdfs), "completed": 0, "failed": 0, "files": [os.path.basename(p) for p in pdfs], "currentFile": None}}
        t = threading.Thread(target=self._run, args=(task_id, pdfs), daemon=True)
        t.start()
        return {"summaryId": f"summary_{task_id}"}

    def status(self, task_id: str) -> Dict:
        s = TASKS.setdefault(task_id, {"summary": {"total": 0, "completed": 0, "failed": 0, "files": [], "currentFile": None}})["summary"]
        total = s["total"] or 0
        completed = s["completed"] or 0
        done = completed >= total and total > 0
        print("[SUMMARY][STATUS]", task_id, total, completed, done, s.get("currentFile"), flush=True)
        return {
            "status": "completed" if done else "processing",
            "progress": 100 if done else (round(completed / total * 100) if total > 0 else 0),
            "total": total,
            "completed": completed,
            "failed": s["failed"],
            "currentFile": s.get("currentFile")
        }
