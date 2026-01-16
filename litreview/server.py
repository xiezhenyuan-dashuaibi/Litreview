import os
import json
import threading
import webbrowser
import sys
import subprocess
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi import WebSocket, WebSocketDisconnect
from starlette.responses import StreamingResponse
import asyncio
import uvicorn

from .services import SystemService, UploadService, SummaryService, ClusterService, GenerateService
from .services.system_service import AI_call, pdf2markdown, pick_working_dir, check_working_dir

def _config_path() -> str:
    return os.path.join(os.getcwd(), "litreview_config.json")

def _load_config_env():
    try:
        p = _config_path()
        if os.path.isfile(p):
            with open(p, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            for k in ("ARK_API_KEY", "LITREVIEW_WORKDIR", "VOLC_ACCESS_KEY", "VOLC_SECRET_KEY"):
                v = cfg.get(k)
                if v:
                    os.environ[k] = v
    except Exception:
        pass

def _save_config_env(payload: dict):
    try:
        data = {
            "ARK_API_KEY": payload.get("apiKey") or os.environ.get("ARK_API_KEY", ""),
            "LITREVIEW_WORKDIR": payload.get("workingDirectory") or os.environ.get("LITREVIEW_WORKDIR", ""),
            "VOLC_ACCESS_KEY": payload.get("accessKeyId") or os.environ.get("VOLC_ACCESS_KEY", ""),
            "VOLC_SECRET_KEY": payload.get("secretAccessKey") or os.environ.get("VOLC_SECRET_KEY", ""),
        }
        with open(_config_path(), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        print("[CONFIG_SAVE]", data)
    except Exception:
        pass

def create_app(static_dir: Optional[str] = None) -> FastAPI:
    _load_config_env()
    app = FastAPI()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    if static_dir and os.path.isdir(static_dir):
        assets_dir = os.path.join(static_dir, "assets")
        if os.path.isdir(assets_dir):
            app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    system_service = SystemService()
    upload_service = UploadService()
    summary_service = SummaryService()
    cluster_service = ClusterService()
    generate_service = GenerateService()

    @app.post("/api/system/start")
    async def system_start(payload: dict):
        try:
            # 设置环境变量，便于后续服务直接读取
            try:
                print("[SYSTEM_START]", payload)
                os.environ['ARK_API_KEY'] = payload.get("apiKey", "") or ""
                os.environ['LITREVIEW_WORKDIR'] = payload.get("workingDirectory", "") or ""
                if payload.get("accessKeyId"):
                    os.environ['VOLC_ACCESS_KEY'] = payload.get("accessKeyId")
                if payload.get("secretAccessKey"):
                    os.environ['VOLC_SECRET_KEY'] = payload.get("secretAccessKey")
                _save_config_env(payload)
            except Exception:
                pass
            data = system_service.start(
                api_key=payload.get("apiKey"),
                working_directory=payload.get("workingDirectory"),
                access_key_id=payload.get("accessKeyId"),
                secret_access_key=payload.get("secretAccessKey")
            )
            return JSONResponse({"status": "success", "message": "系统启动成功", "data": data})
        except Exception as e:
            return JSONResponse({"status": "error", "message": str(e)}, status_code=400)

    @app.get("/api/system/status")
    async def system_status():
        try:
            workdir = os.environ.get('LITREVIEW_WORKDIR') or ''
            pdf_root = os.environ.get('LITREVIEW_PDF_ROOT') or ''
            return JSONResponse({"status": "success", "data": {"workdir": workdir, "pdfRoot": pdf_root, "cwd": os.getcwd()}})
        except Exception as e:
            return JSONResponse({"status": "error", "message": str(e)}, status_code=400)

    @app.get("/api/system/config")
    async def system_config():
        try:
            data = {
                "ARK_API_KEY": os.environ.get('ARK_API_KEY') or '',
                "VOLC_ACCESS_KEY": os.environ.get('VOLC_ACCESS_KEY') or '',
                "VOLC_SECRET_KEY": os.environ.get('VOLC_SECRET_KEY') or '',
                "RESEARCH_TOPIC": os.environ.get('RESEARCH_TOPIC') or '',
                "RESEARCH_DESCRIPTION": os.environ.get('RESEARCH_DESCRIPTION') or ''
            }
            return JSONResponse({"status": "success", "data": data})
        except Exception as e:
            return JSONResponse({"status": "error", "message": str(e)}, status_code=400)

    @app.post("/api/system/save-config")
    async def api_save_config(payload: dict):
        try:
            if not isinstance(payload, dict):
                payload = {}
            # 优先使用前端提交的表单数据；缺失字段用当前环境补齐
            merged = {
                "apiKey": payload.get("apiKey") or os.environ.get("ARK_API_KEY", ""),
                "workingDirectory": payload.get("workingDirectory") or os.environ.get("LITREVIEW_WORKDIR", ""),
                "accessKeyId": payload.get("accessKeyId") or os.environ.get("VOLC_ACCESS_KEY", ""),
                "secretAccessKey": payload.get("secretAccessKey") or os.environ.get("VOLC_SECRET_KEY", ""),
            }
            # 同步更新进程环境，保证后续 /api/system/print-env 输出一致
            try:
                os.environ['ARK_API_KEY'] = merged.get('apiKey', '') or ''
                os.environ['LITREVIEW_WORKDIR'] = merged.get('workingDirectory', '') or ''
                os.environ['VOLC_ACCESS_KEY'] = merged.get('accessKeyId', '') or ''
                os.environ['VOLC_SECRET_KEY'] = merged.get('secretAccessKey', '') or ''
            except Exception:
                pass
            _save_config_env(merged)
            return JSONResponse({"status": "success", "data": merged})
        except Exception as e:
            return JSONResponse({"status": "error", "message": str(e)}, status_code=400)

    @app.post("/api/system/print-env")
    async def system_print_env():
        try:
            vals = {
                "ARK_API_KEY": os.environ.get('ARK_API_KEY') or '',
                "LITREVIEW_WORKDIR": os.environ.get('LITREVIEW_WORKDIR') or '',
                "VOLC_ACCESS_KEY": os.environ.get('VOLC_ACCESS_KEY') or '',
                "VOLC_SECRET_KEY": os.environ.get('VOLC_SECRET_KEY') or ''
            }
            print("[ENV]", vals)
            return JSONResponse({"status": "success", "data": vals})
        except Exception as e:
            return JSONResponse({"status": "error", "message": str(e)}, status_code=400)


    @app.websocket("/ws/system/test-connections")
    async def ws_test_connections(ws: WebSocket):
        await ws.accept()
        try:
            payload = await ws.receive_json()
            api_key = payload.get("apiKey")
            access_key_id = payload.get("accessKeyId")
            secret_access_key = payload.get("secretAccessKey")
            model = payload.get("model", "deepseek-v3-2-251201")
            prompt = payload.get("prompt", "这是一个测试，请简单回复。")
            file_path = payload.get("filePath") or os.path.join(os.getcwd(), "测试用例", "测试用例1.pdf")
            page_num = int(payload.get("pageNum", 32))
            parse_mode = payload.get("parseMode", "ocr")

            loop = asyncio.get_event_loop()
            model_task = loop.run_in_executor(None, AI_call, prompt, api_key, model)
            ocr_task = loop.run_in_executor(None, pdf2markdown, access_key_id, secret_access_key, file_path, page_num, parse_mode)

            tasks = {"model": model_task, "ocr": ocr_task}
            for name, task in tasks.items():
                try:
                    res = await task
                    ok = bool(res and isinstance(res, str) and len(res.strip()) > 0)
                    await ws.send_json({"type": name, "ok": ok})
                except Exception as e:
                    await ws.send_json({"type": name, "ok": False, "error": str(e)})
            await ws.send_json({"type": "done"})
        except Exception as e:
            await ws.send_json({"type": "error", "message": str(e)})
        finally:
            await ws.close()

    @app.get("/api/system/pick-working-dir")
    async def api_pick_working_dir():
        try:
            path = pick_working_dir()
            return JSONResponse({"status": "success", "data": {"path": path}})
        except Exception as e:
            return JSONResponse({"status": "error", "message": str(e)}, status_code=400)

    @app.post("/api/system/check-working-dir")
    async def api_check_working_dir(payload: dict):
        try:
            ok = check_working_dir(
                payload.get("path", ""), 
                expect_collection=payload.get("expect_collection", False)
            )
            return JSONResponse({"status": "success", "data": {"ok": ok}})
        except Exception as e:
            return JSONResponse({"status": "error", "message": str(e)}, status_code=400)

    @app.post("/api/system/open-raw-content-folder")
    async def api_open_raw_content_folder():
        try:
            work_dir = os.environ.get('LITREVIEW_WORKDIR')
            if not work_dir:
                return JSONResponse({"status": "error", "message": "未找到工作目录配置 (LITREVIEW_WORKDIR)"}, status_code=400)

            target_dir = os.path.join(work_dir, "最终文献综述")
            os.makedirs(target_dir, exist_ok=True)

            try:
                if os.name == 'nt':
                    os.startfile(target_dir)
                elif sys.platform == 'darwin':
                    subprocess.Popen(['open', target_dir])
                else:
                    subprocess.Popen(['xdg-open', target_dir])
            except Exception:
                try:
                    webbrowser.open(f"file:///{target_dir}")
                except Exception:
                    pass

            return JSONResponse({"status": "success", "data": {"path": target_dir}})
        except Exception as e:
            return JSONResponse({"status": "error", "message": str(e)}, status_code=400)

    @app.post("/api/upload/zip")
    async def upload_zip(file: UploadFile = File(...)):
        print("正在保存与解析")
        # 保存到临时路径
        try:
            print("[UPLOAD_ENV]", {"LITREVIEW_WORKDIR": os.environ.get('LITREVIEW_WORKDIR')})
            suffix = os.path.splitext(file.filename)[1].lower()
            if suffix != '.zip':
                return JSONResponse({"status": "error", "message": "仅支持ZIP文件"}, status_code=400)
            import tempfile
            fd, tmp_path = tempfile.mkstemp(suffix='.zip')
            with os.fdopen(fd, 'wb') as f:
                try:
                    file.file.seek(0)
                except Exception:
                    pass
                import shutil as _sh
                _sh.copyfileobj(file.file, f, length=1024 * 1024)
            try:
                file.file.close()
            except Exception:
                pass
            data = upload_service.process_zip(tmp_path)
            if not data.get('ok'):
                return JSONResponse({"status": "error", "message": data.get('message')}, status_code=400)
            try:
                os.environ['LITREVIEW_PDF_ROOT'] = data["extractPath"]
            except Exception:
                pass
            print("[UPLOAD_RESULT]", {"extractPath": data["extractPath"]})
            return JSONResponse({"status": "success", "message": "文件上传成功", "data": {"taskId": data["taskId"], "fileCount": data["fileCount"], "extractPath": data["extractPath"]}})
        except Exception as e:
            return JSONResponse({"status": "error", "message": str(e)}, status_code=400)

    @app.post("/api/research/save")
    async def research_save(payload: dict):
        try:
            topic = payload.get('topic', '') or ''
            desc = payload.get('description', '') or ''
            os.environ['RESEARCH_TOPIC'] = topic
            os.environ['RESEARCH_DESCRIPTION'] = desc
            vals = {
                "ARK_API_KEY": os.environ.get('ARK_API_KEY') or '',
                "LITREVIEW_WORKDIR": os.environ.get('LITREVIEW_WORKDIR') or ''
            }
            print("[ENV]", vals)
            try:
                print("[ENV_ALL]", dict(os.environ))
            except Exception:
                pass
            return JSONResponse({"status": "success", "data": {"saved": True}})
        except Exception as e:
            return JSONResponse({"status": "error", "message": str(e)}, status_code=400)

    @app.websocket("/ws/summary/run")
    async def ws_summary_run(ws: WebSocket):
        await ws.accept()
        try:
            try:
                payload = await ws.receive_json()
            except Exception:
                # 客户端断开或未提供有效数据
                return
            task_id = payload.get("taskId")
            root = os.environ.get('LITREVIEW_PDF_ROOT') or ''
            if not task_id or not root or not os.path.isdir(root):
                try:
                    await ws.send_json({"type": "error", "message": "任务或原文目录不存在"})
                except Exception:
                    pass
                return
            pdfs = []
            for name in os.listdir(root):
                p = os.path.join(root, name)
                if os.path.isfile(p) and name.lower().endswith('.pdf'):
                    pdfs.append(p)
            pdfs.sort()
            try:
                await ws.send_json({"type": "init", "files": [os.path.basename(p) for p in pdfs]})
            except Exception:
                return

            from .services.summary_service import SummaryService
            svc = SummaryService()
            idx = 0
            while idx < len(pdfs):
                batch = pdfs[idx: idx + 5]
                try:
                    await ws.send_json({"type": "batch_start", "files": [os.path.basename(p) for p in batch]})
                except Exception:
                    break
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
                    futs = [ex.submit(svc._retry_one, p) for p in batch]
                    for _ in concurrent.futures.as_completed(futs):
                        pass
                try:
                    await ws.send_json({"type": "batch_done", "files": [os.path.basename(p) for p in batch]})
                except Exception:
                    break
                idx += 5
            try:
                await ws.send_json({"type": "done"})
            except Exception:
                pass
        except Exception as e:
            try:
                await ws.send_json({"type": "error", "message": str(e)})
            except Exception:
                pass
        finally:
            try:
                await ws.close()
            except Exception:
                pass

    @app.post("/api/summary/start")
    async def summary_start(payload: dict):
        if not payload.get("taskId"):
            return JSONResponse({"status": "error", "message": "缺少 taskId"}, status_code=400)
        data = summary_service.start(payload["taskId"])
        return JSONResponse({"status": "success", "message": "摘要任务已启动", "data": data})

    @app.get("/api/summary/status/{task_id}")
    async def summary_status(task_id: str):
        data = summary_service.status(task_id)
        return JSONResponse({"status": "success", "data": data})

    @app.post("/api/cluster/start")
    async def cluster_start(payload: dict):
        # 1. 尝试从环境变量获取 LITREVIEW_WORKDIR
        work_dir = os.environ.get('LITREVIEW_WORKDIR')
        
        # 2. 如果环境变量没有，尝试从配置文件读取
        if not work_dir:
            try:
                config_path = _config_path()
                if os.path.isfile(config_path):
                    with open(config_path, "r", encoding="utf-8") as f:
                        cfg = json.load(f)
                        work_dir = cfg.get("LITREVIEW_WORKDIR")
            except Exception:
                pass
        
        if not work_dir:
            return JSONResponse({"status": "error", "message": "未找到工作目录配置 (LITREVIEW_WORKDIR)"}, status_code=400)

        # 3. 构造新的 payload 传给 service
        # 前端传来的 payload 可能为空，我们在这里注入 folder_path (直接传根目录，由 Service 内部处理)
        service_payload = payload.copy()
        service_payload['folder_path'] = work_dir
        
        # 注入用户研究背景 (paper_desc)
        # 从环境变量获取 Topic 和 Description
        res_topic = os.environ.get('RESEARCH_TOPIC', '')
        res_desc = os.environ.get('RESEARCH_DESCRIPTION', '')
        # 拼接成一个字符串
        combined_paper_desc = f"研究题目：{res_topic}\n研究内容描述：{res_desc}"
        service_payload['paper_desc'] = combined_paper_desc
        
        print(f"[CLUSTER] Starting analysis on root: {work_dir}")
        
        # 5. 调用 Service
        try:
            data = cluster_service.start(service_payload)
            if "error" in data:
                 return JSONResponse({"status": "error", "message": data["error"]}, status_code=500)
            return JSONResponse({"status": "success", "message": "聚类任务已启动", "data": data})
        except Exception as e:
            return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

    @app.get("/api/cluster/status/{task_id}")
    async def cluster_status(task_id: str):
        data = cluster_service.status(task_id)
        return JSONResponse({"status": "success", "data": data})

    @app.websocket("/ws/cluster/monitor")
    async def ws_cluster_monitor(ws: WebSocket):
        await ws.accept()
        try:
            # 接收客户端发送的 taskId
            payload = await ws.receive_json()
            task_id = payload.get("taskId")
            if not task_id:
                await ws.send_json({"type": "error", "message": "Missing taskId"})
                return

            import time
            while True:
                status_data = cluster_service.status(task_id)
                status = status_data.get("status")
                
                if status == "completed":
                    # 发送完成消息和数据
                    await ws.send_json({
                        "type": "cluster_complete", 
                        "payload": {
                            "graph": status_data.get("data", {}).get("graph")
                        }
                    })
                    break
                elif status == "failed":
                    # 发送失败消息
                    await ws.send_json({
                        "type": "cluster_failed", 
                        "message": status_data.get("message", "Unknown error")
                    })
                    break
                elif status == "not_found":
                     await ws.send_json({
                        "type": "error", 
                        "message": "Task not found"
                    })
                     break
                else:
                    # 发送进度更新
                    await ws.send_json({
                        "type": "cluster_progress",
                        "progress": status_data.get("progress", 0),
                        "message": status_data.get("message", "")
                    })
                
                await asyncio.sleep(1) # 每秒轮询一次
                
        except WebSocketDisconnect:
            print(f"[WS] Client disconnected for {generation_id}")
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"WS Error: {type(e).__name__}: {e}")
        finally:
            try:
                await ws.close()
            except:
                pass

    @app.post("/api/generate/start")
    async def generate_start(payload: dict):
        # 1. 尝试从环境变量获取 LITREVIEW_WORKDIR
        work_dir = os.environ.get('LITREVIEW_WORKDIR')
        
        # 2. 如果环境变量没有，尝试从配置文件读取
        if not work_dir:
            try:
                config_path = _config_path()
                if os.path.isfile(config_path):
                    with open(config_path, "r", encoding="utf-8") as f:
                        cfg = json.load(f)
                        work_dir = cfg.get("LITREVIEW_WORKDIR")
            except Exception:
                pass
        
        if not work_dir:
            return JSONResponse({"status": "error", "message": "未找到工作目录配置 (LITREVIEW_WORKDIR)"}, status_code=400)

        # 构造新的 payload 传给 service
        service_payload = payload.copy()
        service_payload['folder_path'] = work_dir
        
        # 注入用户研究背景 (paper_desc)
        res_topic = os.environ.get('RESEARCH_TOPIC', '')
        res_desc = os.environ.get('RESEARCH_DESCRIPTION', '')
        combined_paper_desc = f"研究题目：{res_topic}\n研究内容描述：{res_desc}"
        service_payload['paper_desc'] = combined_paper_desc
        
        data = generate_service.start(service_payload)
        return JSONResponse({"status": "success", "message": "综述生成任务已启动", "data": data})

    @app.get("/api/generate/status/{generation_id}")
    async def generate_status(generation_id: str):
        data = generate_service.status(generation_id)
        return JSONResponse({"status": "success", "data": data})

    @app.websocket("/ws/generate/monitor")
    async def ws_generate_monitor(ws: WebSocket):
        await ws.accept()
        try:
            payload = await ws.receive_json()
            generation_id = payload.get("generationId")
            if not generation_id:
                await ws.send_json({"type": "error", "message": "Missing generationId"})
                return

            import asyncio
            retry_count = 0
            while True:
                status_data = generate_service.status(generation_id)
                status = status_data.get("status")
                
                if status == "completed":
                    # 按照指定逻辑排序并拼接内容
                    raw_content = status_data.get("content", {})
                    sorted_content_str = ""



                    if isinstance(raw_content, dict):
                        # 新的排序逻辑：基于内容中的标题序号排序
                        import re
                        from collections import Counter

                        def _extract_first_chapter_num(content: str):
                            if not content:
                                return None
                            m = re.search(r'^\s*#{1,6}\s+(\d+)(?:\.\d+)*', content, re.MULTILINE)
                            if not m:
                                return None
                            try:
                                return int(m.group(1))
                            except Exception:
                                return None

                        def _rewrite_first_header_chapter_num(content: str, expected: int):
                            if not content:
                                return content
                            lines = content.splitlines()
                            for i, ln in enumerate(lines[:10]):
                                m = re.match(r'^(\s*#{1,6}\s+)(\d+)(\s*[\.、]?\s*)(.*)$', ln)
                                if m:
                                    lines[i] = f"{m.group(1)}{expected}{m.group(3)}{m.group(4)}".rstrip()
                                    return "\n".join(lines)
                                m2 = re.match(r'^(\s*#{1,6}\s+)(.+)$', ln)
                                if m2:
                                    lines[i] = f"{m2.group(1)}{expected}. {m2.group(2).strip()}".rstrip()
                                    return "\n".join(lines)
                            return content

                        nums_by_parent = {}
                        for k, v in raw_content.items():
                            mk = re.match(r'^(\d+)-\d+$', str(k))
                            if not mk:
                                continue
                            p = mk.group(1)
                            n = _extract_first_chapter_num(v)
                            if n is None:
                                continue
                            nums_by_parent.setdefault(p, []).append(n)

                        expected_by_parent = {}
                        for p, nums in nums_by_parent.items():
                            c = Counter(nums)
                            best = max(c.values())
                            candidates = [n for n, cnt in c.items() if cnt == best]
                            expected_by_parent[p] = min(candidates)

                        normalized = dict(raw_content)
                        for k, v in raw_content.items():
                            if not re.match(r'^\d+$', str(k)):
                                continue
                            expected = expected_by_parent.get(str(k))
                            if expected is None:
                                continue
                            cur = _extract_first_chapter_num(v)
                            if cur != expected:
                                normalized[k] = _rewrite_first_header_chapter_num(v, expected)

                        raw_content = normalized

                        def content_sort_key(item):
                            key, content = item
                            str_key = str(key)
                            
                            # 1. 特殊 Key 处理
                            if str_key == 'start':
                                return (0, ) # 最前
                            if str_key == 'end':
                                return (3, ) # 最后
                            
                            # 2. 尝试从内容中提取标题序号 (如 "## 1.1", "### 2.1.3")
                            # 匹配以 # 开头，后跟空格，再跟数字.数字...
                            match = re.search(r'^\s*#{1,6}\s+(\d+(?:\.\d+)*)', content, re.MULTILINE)
                            if match:
                                num_str = match.group(1)
                                try:
                                    parts = [int(p) for p in num_str.split('.')]
                                    return (1, tuple(parts)) # 中间，按序号排
                                except ValueError:
                                    pass
                            
                            # 3. 如果没提取到序号，回退到使用 Key 排序，但放在有序号的后面
                            # 尝试解析 Key 中的数字
                            try:
                                key_parts = [int(p) for p in str_key.split('-')]
                                return (2, tuple(key_parts))
                            except:
                                return (2, str_key)

                        # 将 dict 转为 items 列表进行排序
                        sorted_items = sorted(raw_content.items(), key=content_sort_key)
                        
                        # 打印排序结果供调试
                        debug_order = []
                        for k, v in sorted_items:
                            # 提取标题用于日志
                            title_match = re.search(r'^\s*#{1,6}\s+(.*)', v, re.MULTILINE)
                            title = title_match.group(1) if title_match else "No Title"
                            debug_order.append(f"{k}: {title}")
                        print(f"[GENERATE] Sorted by content headers: {debug_order}")

                        try:
                            work_dir = os.environ.get('LITREVIEW_WORKDIR')
                            if work_dir:
                                save_dir = os.path.join(work_dir, "最终文献综述")
                                os.makedirs(save_dir, exist_ok=True)
                                with open(os.path.join(save_dir, "raw_content_dict.json"), "w", encoding="utf-8") as f:
                                    json.dump(dict(sorted_items), f, ensure_ascii=False, indent=2)
                                print(f"[GENERATE] Saved raw content dict to {save_dir}")
                        except Exception as e:
                            print(f"[GENERATE] Failed to save raw content: {e}")

                        sorted_values = [v for k, v in sorted_items]
                        sorted_content_str = "\n\n".join(sorted_values)
                        
                        # 移除所有的星号 (*)
                        sorted_content_str = sorted_content_str.replace('*', '')

                        # --- Save final markdown to file ---
                        try:
                            work_dir = os.environ.get('LITREVIEW_WORKDIR')
                            if work_dir:
                                save_dir = os.path.join(work_dir, "最终文献综述")
                                os.makedirs(save_dir, exist_ok=True)
                                with open(os.path.join(save_dir, "literature_review.md"), "w", encoding="utf-8") as f:
                                    f.write(sorted_content_str)
                                print(f"[GENERATE] Saved final markdown to {save_dir}")
                        except Exception as e:
                            print(f"[GENERATE] Failed to save final markdown: {e}")
                        # -----------------------------------
                    else:
                        sorted_content_str = str(raw_content)
                        # 移除所有的星号 (*)
                        sorted_content_str = sorted_content_str.replace('*', '')

                    await ws.send_json({
                        "type": "generate_complete", 
                        "payload": {
                            "content": sorted_content_str
                        }
                    })
                    break
                elif status == "failed":
                    await ws.send_json({
                        "type": "generate_failed", 
                        "message": status_data.get("message", "Unknown error")
                    })
                    break
                elif status == "not_found":
                     await ws.send_json({
                        "type": "error", 
                        "message": "Generation task not found"
                    })
                     break
                else:
                    await ws.send_json({
                        "type": "generate_progress",
                        "progress": status_data.get("progress", 0),
                        "message": status_data.get("message", ""),
                        "currentSection": status_data.get("currentSection", ""),
                        "content": status_data.get("content", "")
                    })
                
                await asyncio.sleep(2) # Poll every 2 seconds
                
        except Exception as e:
            print(f"WS Error: {e}")
        finally:
            try:
                await ws.close()
            except:
                pass



    # 放在所有 API 路由之后，避免拦截 /api/*
    if static_dir and os.path.isdir(static_dir):
        @app.get("/")
        async def index_html():
            return FileResponse(os.path.join(static_dir, "index.html"))

        @app.exception_handler(404)
        async def spa_fallback(request: Request, exc):
            # 非 /api 的 GET 请求：优先按静态文件返回，否则回退到 index.html，实现 SPA 路由
            if request.method == "GET" and not request.url.path.startswith("/api/"):
                candidate = os.path.join(static_dir, request.url.path.lstrip("/"))
                if os.path.isfile(candidate):
                    return FileResponse(candidate)
                return FileResponse(os.path.join(static_dir, "index.html"))
            return JSONResponse({"detail": "Not Found"}, status_code=404)

    return app

def open_browser(url: str):
    threading.Timer(0.8, lambda: webbrowser.open(url)).start()

def run_app(static_dir: Optional[str] = None, host: str = "127.0.0.1", port: int = 8000, open_ui: bool = True):
    app = create_app(static_dir)
    if open_ui:
        open_browser(f"http://{host}:{port}/")
    uvicorn.run(app, host=host, port=port, log_level="info")