import os
import json
import threading
import plotly
from .core_algorithm import comprehensive_process_function
from .visualize_and_gen_outline import construct_swimlane_data, plot_swimlane

class ClusterService:
    def __init__(self):
        self._status = {}

    def start(self, payload: dict):
        """
        启动异步聚类分析任务
        """
        folder_path = payload.get('folder_path')
        if not folder_path:
             folder_path = os.environ.get('LITREVIEW_ACTIVE_FOLDER')

        if not folder_path or not os.path.exists(folder_path):
             return {"error": "Invalid or missing folder_path"}
        
        # 生成唯一 Task ID
        task_id = f"cluster_{os.getpid()}_{int(os.times().system)}"
        
        # 初始化状态
        self._status[task_id] = {
            "status": "starting",
            "progress": 0,
            "message": "正在初始化聚类任务...",
            "data": None
        }

        # 启动后台线程
        threading.Thread(target=self._run_analysis, args=(task_id, folder_path, payload)).start()

        return {"taskId": task_id}

    def status(self, task_id: str):
        return self._status.get(task_id, {"status": "not_found"})

    def _update_status(self, task_id, status, progress, message, data=None):
        if task_id in self._status:
            update_dict = {
                "status": status,
                "progress": progress,
                "message": message
            }
            if data:
                update_dict["data"] = data
            self._status[task_id].update(update_dict)

    def _run_analysis(self, task_id, folder_path, payload):
        try:
            self._update_status(task_id, "processing", 5, "正在准备文件...")
            
            # [Modified] Append "文献整理合集" to the base path
            base_folder = folder_path
            folder_path = os.path.join(base_folder, "文献整理合集")
            if not os.path.exists(folder_path):
                self._update_status(task_id, "failed", 0, f"Folder not found: {folder_path}")
                return

            # [Modified] Prepare output directory "分类流程数据"
            output_dir = os.path.join(base_folder, "分类流程数据")
            os.makedirs(output_dir, exist_ok=True)

            paper_desc = payload.get('paper_desc','暂未提供')
            
            # 配置权重
            weights_config_1 = {
                'main': 0.05, 'summary': 0.2, 'map': 0.55, 'lineage': 0.2, 'year': 0.0
            }
            weights_config_2 = {
                'main': 0.1, 'summary': 0.2, 'map': 0.4, 'lineage': 0.2, 'year': 0.1
            }
            keyword_section_weights_1 = {
                'main': 0.1, 'summary': 0.2, 'map': 0.35, 'lineage': 0.35
            }
            keyword_section_weights_2 = {
                'main': 0.2, 'summary': 0.3, 'map': 0.2, 'lineage': 0.3
            }

            # 第一轮：全局聚类
            self._update_status(task_id, "processing", 10, "正在执行第一轮全局聚类...")
            print("\n\n======== Round 1: Global Clustering ========")
            
            try:
                results1, anchor1, evaluation_text1, cluster_keywords_map1 = comprehensive_process_function(
                    method='KMEANS', 
                    weights_config_1=weights_config_1,
                    keyword_section_weights=keyword_section_weights_1,
                    paper_desc=paper_desc,
                    folder_path=folder_path,
                    n_components=20,
                    k_penalty=0.02,
                    similarity_threshold=0.75
                )
            except Exception as e:
                print(f"Global clustering failed: {e}")
                self._update_status(task_id, "failed", 0, f"Global clustering failed: {str(e)}")
                return

            # Save Round 1 results
            self._update_status(task_id, "processing", 40, "正在保存第一轮结果...")
            try:
                with open(os.path.join(output_dir, "round1_results.json"), "w", encoding="utf-8") as f:
                    json.dump({
                        "results": results1,
                        "anchor": anchor1,
                        "keywords": cluster_keywords_map1
                    }, f, ensure_ascii=False, indent=2, default=str)
            except Exception as e:
                print(f"Failed to save round1 results: {e}")

            # 提取第一轮发现的 Label
            labels_found = sorted(list(set(
                item['label'] 
                for item in results1.values() 
                if isinstance(item, dict) and 'label' in item and item['label'] != -1
            )))

            # 第二轮：对每个子类进行细分
            self._update_status(task_id, "processing", 50, "正在执行第二轮子类细分...")
            sub_results_storage = {} 
            
            total_labels = len(labels_found)
            for i, label_id in enumerate(labels_found):
                progress = 50 + int((i / total_labels) * 40) # 50% -> 90%
                self._update_status(task_id, "processing", progress, f"正在细分分类 {label_id}...")
                print(f"\n\n======== Round 2: Sub-clustering for Label {label_id} ========")
                try:
                    res2, anc2, eval2, kws2 = comprehensive_process_function(
                        method='KMEANS', 
                        weights_config_2=weights_config_2,
                        keyword_section_weights=keyword_section_weights_2,
                        paper_desc=paper_desc,
                        label=label_id,
                        results=results1,
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
                except Exception as e:
                    print(f"  [ERROR] Failed to process Label {label_id}: {e}")

            # Save Round 2 results
            try:
                with open(os.path.join(output_dir, "round2_results.json"), "w", encoding="utf-8") as f:
                    json.dump(sub_results_storage, f, ensure_ascii=False, indent=2, default=str)
            except Exception as e:
                print(f"Failed to save round2 results: {e}")

            # 生成可视化
            self._update_status(task_id, "processing", 95, "正在生成可视化图表...")
            categories_dict, papers_dict = construct_swimlane_data(anchor1, cluster_keywords_map1, sub_results_storage)
            
            if papers_dict:
                fig = plot_swimlane(categories_dict, papers_dict)
                graph_json = json.loads(fig.to_json())
                
                # 保存图表为HTML
                try:
                    cluster_scheme_dir = os.path.join(base_folder, "文献聚类方案")
                    os.makedirs(cluster_scheme_dir, exist_ok=True)
                    html_path = os.path.join(cluster_scheme_dir, "swimlane_chart.html")
                    fig.write_html(html_path)
                    print(f"Saved swimlane chart to {html_path}")
                except Exception as e:
                    print(f"Failed to save chart HTML: {e}")

                # 完成
                self._update_status(task_id, "completed", 100, "聚类分析完成", {"graph": graph_json})
            else:
                self._update_status(task_id, "failed", 0, "No papers to plot")

        except Exception as e:
            self._update_status(task_id, "failed", 0, f"Unexpected error: {str(e)}")