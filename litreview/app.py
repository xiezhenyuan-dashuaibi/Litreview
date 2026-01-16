import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional

import requests

from .server import run_app

"暂时未更新该启动方法，启动项目可遵照README.md中的说明"

class LitReviewApp:
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = Path(base_dir or Path.home() / ".litreview")
        self.web_dir = self.base_dir / "web"
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def install_web(self, source_url: Optional[str] = None, local_dist: Optional[str] = None):
        self.web_dir.mkdir(parents=True, exist_ok=True)
        if local_dist and Path(local_dist).is_dir():
            shutil.rmtree(self.web_dir, ignore_errors=True)
            shutil.copytree(local_dist, self.web_dir)
            return str(self.web_dir)
        if not source_url:
            raise RuntimeError("缺少前端资源地址，请提供 source_url 或 local_dist")
        tmp_zip = Path(tempfile.gettempdir()) / "litreview_web.zip"
        with requests.get(source_url, stream=True, timeout=60) as r:
            r.raise_for_status()
            with open(tmp_zip, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        shutil.rmtree(self.web_dir, ignore_errors=True)
        self.web_dir.mkdir(parents=True, exist_ok=True)
        shutil.unpack_archive(str(tmp_zip), str(self.web_dir))
        #当安装完各种资源之后，需要构建前端以及下载各种依赖库，以便后面start能直接启动
        return str(self.web_dir)

    def start(self, port: int = 8000, host: str = "127.0.0.1", prefer_local: bool = True):
        static_dir = str(self.web_dir) if (self.web_dir.exists() and any(self.web_dir.iterdir())) else None
        # 尝试自动从本地前端构建产物安装/刷新（开发环境友好）
        if prefer_local:
            candidates = []
            try:
                candidates.append(Path.cwd() / "frontend" / "dist")
                candidates.append(Path(__file__).resolve().parents[2] / "frontend" / "dist")
            except Exception:
                pass
            for cand in candidates:
                if cand.is_dir() and any(cand.iterdir()):
                    self.install_web(local_dist=str(cand))
                    static_dir = str(self.web_dir)
                    break
        run_app(static_dir=static_dir, host=host, port=port, open_ui=True)
