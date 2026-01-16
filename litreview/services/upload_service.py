import os
import zipfile
import shutil
from datetime import datetime
from typing import Dict, Tuple
import re

from ..state import TASKS


class UploadService:
    def _ensure_workdir(self) -> str:
        workdir = os.environ.get('LITREVIEW_WORKDIR') or os.path.join(os.getcwd(), 'literature_review')
        os.makedirs(workdir, exist_ok=True)
        print(workdir)
        return workdir

    def _build_target_folder(self) -> str:
        workdir = self._ensure_workdir()
        base = os.path.join(workdir, '文献原文合集')
        os.makedirs(base, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        target = os.path.join(base, f'文献集1-上传时间{timestamp}')
        os.makedirs(target, exist_ok=True)
        return target

    def _validate_zip_only_pdfs(self, zf: zipfile.ZipFile) -> Tuple[bool, str, int]:
        count = 0
        for info in zf.infolist():
            if info.is_dir():
                continue
            name = info.filename
            # Skip hidden/system files
            base = os.path.basename(name)
            if base.startswith('.'):
                return False, f'压缩包中含有隐藏文件: {base}，请移除后重试', 0
            if not name.lower().endswith('.pdf'):
                return False, f'压缩包中检测到非PDF文件: {name}，请保证仅包含PDF', 0
            count += 1
        if count == 0:
            return False, '压缩包中未检测到PDF文件', 0
        return True, '', count

    def _recover_name(self, info: zipfile.ZipInfo) -> str:
        decoded = info.filename
        if (info.flag_bits & 0x800):
            return os.path.basename(decoded)
        raw = decoded.encode('cp437', errors='replace')
        for enc in ('gb18030', 'gbk', 'big5', 'shift_jis', 'utf-8', 'latin1'):
            try:
                candidate = raw.decode(enc)
                return os.path.basename(candidate)
            except Exception:
                continue
        return os.path.basename(decoded)

    def _sanitize_filename(self, info: zipfile.ZipInfo) -> str:
        base = self._recover_name(info).strip()
        root, ext = os.path.splitext(base)
        ext = '.pdf' if ext.lower() == '.pdf' else ext
        invalid = '<>:"/\\|?*'
        root = ''.join('_' if (ch in invalid or ord(ch) < 32) else ch for ch in root)
        if re.fullmatch(r'(?i)^(con|prn|aux|nul|com[1-9]|lpt[1-9])$', root):
            root = '_' + root
        if len(root) > 200:
            root = root[:200]
        return f'{root}{ext}'

    def process_zip(self, zip_path: str) -> Dict:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            ok, msg, pdf_count = self._validate_zip_only_pdfs(zf)
            if not ok:
                return {"ok": False, "message": msg}
            target = self._build_target_folder()
            for info in zf.infolist():
                if info.is_dir():
                    continue
                with zf.open(info) as src:
                    fname = self._sanitize_filename(info)
                    out_path = os.path.join(target, fname)
                    i = 1
                    while os.path.exists(out_path):
                        root, ext = os.path.splitext(fname)
                        fname2 = f"{root}_{i}{ext}"
                        out_path = os.path.join(target, fname2)
                        i += 1
                    with open(out_path, 'wb') as dst:
                        shutil.copyfileobj(src, dst, length=1024 * 1024)

        try:
            os.remove(zip_path)
        except Exception:
            pass

        task_id = f"task_{os.getpid()}_{int(datetime.now().timestamp())}"
        TASKS[task_id] = {
            "summary": {
                "total": pdf_count,
                "completed": 0,
                "failed": 0,
                "files": []
            }
        }
        return {"ok": True, "taskId": task_id, "fileCount": pdf_count, "extractPath": target}
