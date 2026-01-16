# AI 文献综述生成器
## 完整产品需求文档（Python CLI 版）

> 版本：v1.0（Python CLI 统一命令版）  
> 作者：SOLO Document  
> 更新：2025-06-25

---

## 项目总览
本工具面向科研人员与知识工作者，提供一条“零数据库、文件即数据”的极简流水线：把含多篇 PDF 的 ZIP 包丢进去，四层自动调用大模型，最终产出可直接投稿的文献综述 Markdown。核心卖点：1. 纯 Python，可 `pip install` 后一行命令跑完；2. 全程本地文件落地，任何环节可人工打断、修正、续跑；3. 前端仅用于“对话协商”，不保存任何状态，真正“后端即全部”。

---

## 应用流程全景（七步闭环）

1. **启动与自检**  
   阶段目标：确认 Python 环境与 LLM 连通性。  
   用户执行 `litreview start`（开发态 `python -m litreview start`），后台自动检测 ≥3.9 解释器、读取 `~/.litreview.conf` 中的 API 密钥，若空则弹窗索要并回写；随后向指定 LLM 端点发送心跳包，返回 200 即绿灯，浏览器自动打开 `http://127.0.0.1:8000` 空白待命页。用户感知：一条命令完成“装依赖-鉴权-心跳”三连，失败信息彩色高亮，成功即浏览器闪出空白页。

2. **上传与落盘**  
   阶段目标：把批量 PDF 收进本地工作区。  
   用户继续 `litreview layer1`，前端出现极简拖拽窗，仅收 `.zip`、MIME 必须为 `application/zip`、上限 200 MB；校验通过后弹出系统文件选择器，让用户指定“工作根目录”。确认后两窗关闭，后台把 ZIP 解压到 `工作根目录/__tmp_unzip__`，随后立即把原始 ZIP 再复制一份到 `工作根目录/__raw_zip__` 作为只读备份。用户感知：两次点击即完成“上传+选目录”，文件树就地可见，可随时手动删改。

3. **解析与摘要**  
   阶段目标：每篇 PDF 生成“背景-方法-结论”三栏 Markdown 表格。  
   Python 异步任务流按文件名顺序逐篇提取文本（兼容可拷贝文本与 OCR），按 2 000 字符滑动窗口切块，调用 LLM 生成表格，回写至 `工作根目录/文献总结/文件名.md`，UTF-8 编码；同时把 LLM 原始返回的 JSON 存入 `工作根目录/文献总结/raw/文件名.json` 方便二次开发。全部完成后系统通知区弹窗，并在终端提示“下一步：litreview layer2”。用户感知：终端实时滚动进度百分条，可随时 Ctrl-C 中断，下次加 `--resume` 续跑。

4. **聚类与分组**  
   阶段目标：自动给出多种“文献组织思路”供挑选。  
   用户执行 `litreview layer2`，后台读取全部摘要，先用 TF-IDF 向量化，再按 `--k` 上限（默认 8 组）做 HDBSCAN 聚类，余弦距离 ≥ `--similarity-threshold`（默认 0.15）即打散；随后让 LLM 为每组生成“组名+研究脉络+可展开方向”，再把组间顺序按“逻辑递进”重排，最终输出 3~5 套不同分组方案到 `工作根目录/多种文献组织思路/组X_方案Y.txt`，每套附“适用场景一句话”。用户感知：终端打印一张“方案对比小表”，一眼看懂哪套更适合自己。

5. **对话与拍板**  
   阶段目标：人机协商出“最终方案”并锁定。  
   用户 `litreview layer3`，本地网页自动刷新成“对话模式”：左侧展示上一步所有方案，右侧聊天框支持自然语言指令，例如“把方案 2 的第三组拆成两块”或“再给我 3 篇对比实验的文章”。后台通过 WebSocket 把指令转发给 LLM，实时返回调整后的分组 JSON，前端即时渲染新分组卡片；用户可继续上传新 ZIP（自动再走 layer1 摘要并合并），也可手动拖拽卡片调整。点“确认”后，前端把最终 JSON POST 到后端，写入 `工作根目录/最终方案/final.json` 并生成人类可读的 `final.md`。用户感知：像聊天一样把“综述骨架”聊到满意，一键锁定。

6. **生成与续写**  
   阶段目标：按锁定骨架逐节生成综述正文。  
   用户 `litreview layer4`，后台按 final.json 中的组顺序，逐组调用 LLM 生成“段落+引用”，流式返回 Markdown；前端逐块渲染，每段结束自动滚动到底，用户可实时编辑或点击“重说”。生成完毕后，后端把全文写入 `工作根目录/最终综述/final_review.md`，同时在 `最终综述/assets/` 内生成一份“引用 BibTeX”与一张“组-文献”对照 CSV 方便投稿。用户感知：像看直播一样看综述一点点长出来，随时喊停改口吻。

7. **交付与复盘**  
   阶段目标：把结果做成“可直接投稿”的完整包。  
   生成完终端提示“可执行 `litreview package`（可选）一键打包”，该命令会把 `最终综述/` 与 `最终方案/` 打成 `工作根目录/__deliver__/综述_YYYYMMDD_HHMM.zip`，内含：final_review.md、final.json、assets/、以及一份 `生成日志.log`。用户感知：一条命令拿到 zip，直接丢给导师或投稿系统，全流程本地文件闭环，可随时回滚任何一步。

---

## 目录
1. 逐层六要素详述  
   1.1 Layer-0 启动与配置  
   1.2 Layer-1 解析与摘要  
   1.3 Layer-2 聚类与分组  
   1.4 Layer-3 对话与拍板  
   1.5 Layer-4 生成与续写  
2. Python CLI 命令入口与参数约定  
3. 数据模型与文件格式  
4. 接口与通信协议  
5. 验收标准  
6. 开发者自测清单  
7. 常见坑提示  
8. 里程碑与度量  
9. 风险与应对  
10. 后续扩展

---

## 1. 逐层六要素详述

### 1.1 Layer-0 启动与配置
- **入口条件**：Python≥3.9 已装，终端可执行 `litreview` 命令。  
- **用户操作**：`litreview start`（或 `python -m litreview start`）。  
- **系统行为**：  
  1) 读取 `~/.litreview.conf`，若无则弹窗索要 API 密钥并回写；  
  2) 向 LLM 端点发 HEAD 心跳，超时 5 s；  
  3) 启动本地服务（默认端口 8000，可 `--port` 改），空白页自动打开。  
- **输出**：控制台彩色日志 + 浏览器空白页。  
- **异常**：心跳失败 → 红色提示并退出码 1；端口占用 → 自动+1 重试三次。  
- **下一步提示**：“下一步：litreview layer1”。

### 1.2 Layer-1 解析与摘要
- **入口条件**：Layer-0 成功，工作根目录已创建。  
- **用户操作**：`litreview layer1 [--zip 路径]`，若缺 `--zip` 则前端弹窗拖拽。  
- **系统行为**：  
  1) 校验 ZIP 头 4 bytes；  
  2) 解压到 `__tmp_unzip__`；  
  3) 逐篇调 `pdfminer.six` 或 `ocrmypdf`（若 `--skip-ocr` 则跳过）；  
  4) 2 000 字符窗口切块，调 LLM 生成三栏表格；  
  5) 写 `文献总结/文件名.md` 与 `raw/文件名.json`。  
- **输出**：终端进度条 + 系统通知。  
- **异常**：任一 PDF 损坏 → 记录到 `__error_pdf__.log` 并继续；LLM 返回非 JSON → 重试三次后写纯文本兜底。  
- **下一步提示**：“下一步：litreview layer2”。

### 1.3 Layer-2 聚类与分组
- **入口条件**：`文献总结/` 下≥2 篇摘要。  
- **用户操作**：`litreview layer2 [--k 8 --similarity-threshold 0.15]`。  
- **系统行为**：  
  1) 读取全部摘要，TF-IDF 向量化（max_features=5 000，ngram_range=1:2）；  
  2) HDBSCAN 聚类，`min_cluster_size=2`，`metric='cosine'`；  
  3) 对噪声篇按“余弦距离>阈值”打散成单篇组；  
  4) 调 LLM 为每组生成“组名+脉络+可展开方向”；  
  5) 按组间逻辑递进重排，输出 3~5 套方案到 `多种文献组织思路/`。  
- **输出**：终端“方案对比小表”+ 文件。  
- **异常**：若摘要过少（<2）→ 退出码 2 并提示“请上传更多文献”。  
- **下一步提示**：“下一步：litreview layer3”。

### 1.4 Layer-3 对话与拍板
- **入口条件**：`多种文献组织思路/` 非空。  
- **用户操作**：`litreview layer3`，浏览器自动跳转对话页。  
- **系统行为**：  
  1) WebSocket 全双工，前端每发一条指令，后端把“当前分组 JSON + 用户指令”喂给 LLM，返回调整后 JSON；  
  2) 支持增量上传新 ZIP（自动调 layer1 摘要并合并到当前会话）；  
  3) 用户点击“确认”后，后端写 `最终方案/final.json` 与 `final.md`。  
- **输出**：实时渲染卡片 + 文件落盘。  
- **异常**：WebSocket 断线 → 前端自动重连三次，仍失败则提示“请刷新”。  
- **下一步提示**：“下一步：litreview layer4”。

### 1.5 Layer-4 生成与续写
- **入口条件**：`最终方案/final.json` 存在。  
- **用户操作**：`litreview layer4 [--model gpt-4 --temperature 0.7]`。  
- **系统行为**：  
  1) 按组顺序逐块调 LLM，流式返回 Markdown；  
  2) 前端每收到 50 token 插入页面，可实时编辑；  
  3) 生成完写 `最终综述/final_review.md`，并输出 `assets/ref.bib` + `mapping.csv`。  
- **输出**：浏览器实时渲染 + 本地文件。  
- **异常**：LLM 中途报错 → 自动重试三次，仍失败则把已生成部分写 `final_review_incomplete.md` 并提示手动续写。  
- **下一步提示**：“可选：litreview package”。

---

## 2. Python CLI 命令入口与参数约定
入口命令：`litreview <phase>`，phase ∈ {start, layer1, layer2, layer3, layer4, package}。  
常用可选参数（自然语言描述，无代码）：
- `--zip`：本地 ZIP 路径，若省略则前端弹窗上传。  
- `--out`：工作根目录，默认弹窗选择。  
- `--lang`：摘要与生成语言，默认 zh。  
- `--concurrency`：并发 LLM 请求数，默认 4。  
- `--k`：聚类最大组数参考，默认 8。  
- `--similarity-threshold`：余弦距离打散阈值，默认 0.15。  
- `--resume`：断点续跑，读取 `__checkpoint__.json`。  
- `--skip-ocr`：强制跳过 OCR，仅对可拷贝文本 PDF 生效。  
- `--port`：本地服务端口，默认 8000。  
- `--model`：LLM 模型名，留空则读配置。  
- `--temperature`：LLM 温度，默认 0.7。  

所有参数支持短写（`-z`、`-o`…）与长写，按标准 argparse 行为解析。

---

## 3. 数据模型与文件格式

### 3.1 目录结构（以工作根目录为锚点）
```
工作根目录/
├─ __raw_zip__/              # 原始 ZIP 备份
├─ __tmp_unzip__/            # 临时解压（可删）
├─ 文献总结/                 # Layer-1 输出
│   ├─ *.md                  # 人读摘要
│   └─ raw/*.json            # LLM 原始返回
├─ 多种文献组织思路/         # Layer-2 输出
│   └─ 组X_方案Y.txt
├─ 最终方案/                 # Layer-3 输出
│   ├─ final.json            # 机器读
│   └─ final.md              # 人读骨架
├─ 最终综述/                 # Layer-4 输出
│   ├─ final_review.md       # 终稿
│   └─ assets/
│       ├─ ref.bib           # BibTeX
│       └─ mapping.csv       # 组-文献对照
└─ __deliver__/              # package 命令产出
    └─ 综述_YYYYMMDD_HHMM.zip
```

### 3.2 核心 JSON 模式（仅列字段，无代码）
- `final.json`：顶层对象含 `version`、`create_time`、`groups` 数组；每项 group 有 `id`、`name`、`description`、`papers` 数组；每项 paper 含 `title`、`summary_md_path`、`bibkey`。  
- `__checkpoint__.json`：记录当前已完成的 layer、已处理 PDF 列表、失败列表、下次续跑的起始偏移。

---

## 4. 接口与通信协议

### 4.1 本地 WebSocket（ws://127.0.0.1:8000/ws）
- 上行：`{"type":"adjust","payload":{"instruction":"把组2拆成两部分"}}`  
- 下行：`{"type":"adjust_result","payload":{"groups":[...],"reason":"..."}}`  
- 心跳：每 30 s 双向 ping/pong，断线前端自动重连。

### 4.2 HTTP（REST，仅用于上传）
- `POST /api/upload`：FormData 含 ZIP 文件，返回 `{"task_id":"...","file_count":12}`。

---

## 5. 验收标准

功能级：  
✅ 一条命令完成七步闭环，中途任意 Ctrl-C 后 `--resume` 可续跑。  
✅ 上传 100 篇 PDF（1 GB ZIP）在 8 核 16 G 环境下，Layer-1 摘要 ≤ 30 min，Layer-2 聚类 ≤ 5 min，Layer-4 生成 8 000 字综述 ≤ 10 min。  
✅ 最终 Markdown 可直接用 Pandoc 转 DOCX，引用格式符合《信息与文献 参考文献著录规则》。  

体验级：  
✅ 全程无数据库，仅依赖本地文件与 Python 库，pip 安装后离线可跑。  
✅ Windows / macOS / Linux 三平台终端颜色一致，中文日志不乱码。  

---

## 6. 开发者自测清单

- [ ] `pip install -e .` 后 `litreview start` 能打开空白页。  
- [ ] 故意写错 API 密钥，程序应红灯提示并退出码 1。  
- [ ] 传 1 篇 PDF，Layer-2 应提示“请上传更多文献”并退出码 2。  
- [ ] 生成中途拔掉网线，前端重连三次后仍可用。  
- [ ] 把 `最终综述/final_review.md` 用 Word 打开，图片与引用不丢失。  
- [ ] 执行 `litreview package` 后，交付 zip 内含生成日志，且解压后路径无中文乱码。

---

## 7. 常见坑提示

1. OCR 依赖 `ocrmypdf`，首次运行会自动下载 `eng+chi_sim` 模型，若网络差可手动 `python -m ocrmypdf --download-cache`。  
2. Windows 路径长度超限 → 建议把工作根目录放在盘符根目录，如 `D:\review`。  
3. 部分高校代理会拦截 WebSocket，若前端一直重连失败，可 `--port` 换成 8080/443 以外端口。  
4. LLM 返回表格若缺少“结论”列，后台会自动补“（LLM 未给出）”占位，避免后续聚类报错。  
5. 若 `--k` 设得过大，HDBSCAN 可能全算噪声，此时自动把 `k` 减半重跑，日志会打印“retry with k=4”。

---

## 8. 里程碑与度量

| 里程碑 | 截止 | 完成标准 |
|--------|------|----------|
| M1 CLI 骨架 | 7-05 | `litreview start/layer1` 可跑通，日志中文 |
| M2 聚类稳定 | 7-15 | 100 篇 PDF 聚类耗时 ≤ 5 min，Silhouette ≥ 0.25 |
| M3 对话上线 | 7-25 | WebSocket 延迟 ≤ 300 ms，10 次指令不崩 |
| M4 综述生成 | 8-05 | 8 000 字输出格式错误 ≤ 3 处/百篇 |
| M5 PyPI 发布 | 8-15 | `pip install litreview` 后示例能跑完七步 |

---

## 9. 风险与应对

| 风险 | 概率 | 应对 |
|------|------|------|
| LLM 端点限速 | 中 | 内置指数退避 + 多 key 轮询 |
| OCR 依赖过大 | 低 | 提供 `--skip-ocr` 降级方案 |
| 用户目录含空格 | 高 | 全路径加双引号 + pathlib 处理 |
| 聚类效果差 | 中 | 允许人工拖拽 + 多方案输出 |
| 投稿格式突变 | 低 | 最终综述采用标准 Markdown，转 Word 由用户侧 Pandoc 负责 |

---

## 10. 后续扩展

- **插件化**：预留 `litreview plugin list/install` 入口，允许社区贡献“引用样式”、“图生成”插件。  
- **增量更新**：支持只上传新增 PDF，自动 diff 摘要并提示“是否合并到当前最终方案”。  
- **多语言**：摘要与生成阶段加 `--lang en/es/fr`，自动切换 prompt 模板。  
- **GUI 独立版**：用 PySide6 打包单文件 exe，双击即跑，服务后台隐藏。  
- **云适配**：提供 `--backend openai-compatible` 参数，可指向任意 OpenAI-API 兼容端点，包括本地 llama.cpp。

---

文档结束。祝开发顺利，早日 `pip install litreview` 一键发综述！