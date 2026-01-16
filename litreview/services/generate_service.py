import os
import json
import threading
from .gen_final_LR import (
    extract_md_to_dict,
    inject_labels_to_dict,
    gen_outline,
    gen_all_section_plans,
    gen_full_article_content,
    analyze_article_stats
)

class GenerateService:
    def __init__(self):
        self._status = {}

    def start(self, payload: dict):
        folder_path = payload.get('folder_path')
        if not folder_path:
             folder_path = os.environ.get('LITREVIEW_WORKDIR')

        if not folder_path or not os.path.exists(folder_path):
             return {"error": "Invalid or missing folder_path"}
        
        # 1. 构造文件路径
        base_folder = folder_path
        # 注意：这里我们假设上一步聚类已经把中间数据存在了 "分类流程数据"
        process_data_dir = os.path.join(base_folder, "分类流程数据")
        round1_path = os.path.join(process_data_dir, "round1_results.json")
        round2_path = os.path.join(process_data_dir, "round2_results.json")
        
        # 原文md文件夹
        md_folder_path = os.path.join(base_folder, "文献整理合集")

        if not os.path.exists(round1_path) or not os.path.exists(round2_path):
             return {"error": "Clustering results not found. Please run Cluster Analysis first."}

        # 生成唯一ID
        generation_id = f"gen_{os.getpid()}_{int(os.times().system)}"
        self._status[generation_id] = {
            "status": "starting",
            "progress": 0,
            "currentSection": "初始化...",
            "content": ""
        }

        # 异步启动生成任务
        paper_desc = payload.get('paper_desc', '暂未提供')
        threading.Thread(target=self._run_generation, args=(generation_id, md_folder_path, round1_path, round2_path, paper_desc)).start()

        return {"generationId": generation_id, "estimatedTime": 600}

    def _run_generation(self, generation_id, md_folder_path, round1_path, round2_path, paper_desc):
        try:
            self._update_status(generation_id, "loading_data", 5, "正在加载聚类数据...")
            print("请等待...")
            # 2. 读取聚类数据
            with open(round1_path, 'r', encoding='utf-8') as f:
                r1_data = json.load(f)
                results1 = r1_data['results']
                anchor1 = r1_data['anchor']
                # keywords1 = r1_data['keywords'] # 暂时没用到

            with open(round2_path, 'r', encoding='utf-8') as f:
                sub_results_storage = json.load(f)
            
            # 注意：JSON加载后的key是字符串，如果原始key是数字，需要转换
            # anchor1 的 key 是父类ID (int)，需要转回 int
            anchor1 = {int(k) if k != '-1' and k.lstrip('-').isdigit() else k: v for k,v in anchor1.items()}
            
            # sub_results_storage 的 key 是父类ID (int)
            # sub_results_storage 内部 structure: {p_id: { 'results': { title: { 'label': s_id } }, 'anchor': {s_id: desc} }}
            # 同样需要把 key 转回 int
            new_sub_storage = {}
            for k, v in sub_results_storage.items():
                p_id = int(k) if k.lstrip('-').isdigit() else k
                
                # 处理 anchor 里的 s_id
                if 'anchor' in v:
                     v['anchor'] = {int(sk) if str(sk).lstrip('-').isdigit() else sk: sv for sk, sv in v['anchor'].items()}
                
                # 处理 results 里的 label
                if 'results' in v:
                    for title, info in v['results'].items():
                        if 'label' in info:
                            info['label'] = int(info['label'])
                            
                new_sub_storage[p_id] = v
            sub_results_storage = new_sub_storage

            # 提取关键词Map (gen_outline需要)
            # 这里的 cluster_keywords_map1 在 round1_results.json 里是 'keywords'
            cluster_keywords_map1 = {int(k) if k.lstrip('-').isdigit() else k: v for k,v in r1_data['keywords'].items()}

            self._update_status(generation_id, "generating_outline", 10, "正在生成大纲...")
            
            # 3. 生成大纲
            outline_resp, outline_dict = gen_outline(anchor1, cluster_keywords_map1, sub_results_storage, paper_desc=paper_desc)

            # 保存大纲产物，便于调试 start/end 错配
            try:
                base_folder = os.path.dirname(md_folder_path)
                save_dir = os.path.join(base_folder, "最终文献综述")
                os.makedirs(save_dir, exist_ok=True)
                with open(os.path.join(save_dir, "outline_resp.md"), "w", encoding="utf-8") as f:
                    f.write(outline_resp or "")
                with open(os.path.join(save_dir, "outline_dict.json"), "w", encoding="utf-8") as f:
                    json.dump(outline_dict or {}, f, ensure_ascii=False, indent=2)
                print(f"[GENERATE] Saved outline to {save_dir}")
            except Exception as e:
                print(f"[GENERATE] Failed to save outline: {e}")

            self._update_status(generation_id, "processing_docs", 20, "正在处理本地文档...")

            # 4. 提取本地 Markdown
            raw_docs_dict = extract_md_to_dict(md_folder_path)
            
            # 5. 注入标签
            main_info_dict = inject_labels_to_dict(raw_docs_dict, results1, sub_results_storage)
            
            self._update_status(generation_id, "planning_sections", 30, "正在规划章节思路...")

            # 6. 生成章节规划
            section_plans = gen_all_section_plans(main_info_dict, outline_dict, outline_resp)
            
            self._update_status(generation_id, "writing_content", 50, "正在撰写正文 (可能需要较长时间)...")

            # 7. 生成全文
            # gen_full_article_content 返回的是 {label: text} 字典
            final_sections_dict = gen_full_article_content(outline_dict, section_plans, main_info_dict, outline_resp)
            
            # [Modified] 直接返回字典，不再拼接全文
            self._update_status(generation_id, "completed", 100, "生成完成", final_sections_dict)
            
        except Exception as e:
            print(f"Generation failed: {e}")
            self._update_status(generation_id, "failed", 0, f"Error: {str(e)}")

    def _update_status(self, generation_id, status, progress, current_section, content=None):
        if generation_id in self._status:
            self._status[generation_id].update({
                "status": status,
                "progress": progress,
                "currentSection": current_section
            })
            if content:
                self._status[generation_id]["content"] = content

    def status(self, generation_id: str):
        return self._status.get(generation_id, {"status": "not_found"})