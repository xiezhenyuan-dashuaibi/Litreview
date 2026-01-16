import os
import time
import hashlib
import hmac
import base64
from urllib.parse import urlencode
import re
import requests
from volcenginesdkarkruntime import Ark
import subprocess
try:
    from tkinter import Tk
    from tkinter.filedialog import askdirectory
except Exception:
    Tk = None
    askdirectory = None


class SystemService:
    def start(self, api_key: str, working_directory: str, access_key_id: str = None, secret_access_key: str = None):
        if not api_key or not working_directory:
            raise ValueError("API密钥和工作目录不能为空")
        try:
            working_directory = os.path.abspath(working_directory)
        except Exception:
            pass
        # 设置环境变量供后续调用使用
        try:
            os.environ['ARK_API_KEY'] = api_key
            os.environ['LITREVIEW_WORKDIR'] = working_directory
            if access_key_id:
                os.environ['VOLC_ACCESS_KEY'] = access_key_id
            if secret_access_key:
                os.environ['VOLC_SECRET_KEY'] = secret_access_key
        except Exception:
            pass
        return {"sessionId": f"session_{os.getpid()}", "workingPath": working_directory}

        


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _hmac_sha256(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()


def _utc_now_xdate() -> str:
    return time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())


def volc_sign(ak: str, sk: str, host: str, region: str, service: str,
              method: str, canonical_uri: str, query: dict, headers: dict, body: bytes) -> str:
    signed_header_keys = sorted([k.lower() for k in headers.keys()])
    canonical_headers = ''.join([f"{k.lower()}:{headers[k]}\n" for k in signed_header_keys])
    canonical_query = urlencode(sorted(query.items()))
    payload_hash = _sha256_hex(body)
    canonical_request = '\n'.join([
        method,
        canonical_uri,
        canonical_query,
        canonical_headers,
        ';'.join(signed_header_keys),
        payload_hash,
    ])

    x_date = headers.get('x-date')
    short_date = x_date[:8]
    credential_scope = f"{short_date}/{region}/{service}/request"
    string_to_sign = '\n'.join([
        'HMAC-SHA256',
        x_date,
        credential_scope,
        _sha256_hex(canonical_request.encode('utf-8')),
    ])

    k_date = _hmac_sha256(sk.encode('utf-8'), short_date)
    k_region = hmac.new(k_date, region.encode('utf-8'), hashlib.sha256).digest()
    k_service = hmac.new(k_region, service.encode('utf-8'), hashlib.sha256).digest()
    k_signing = hmac.new(k_service, b'request', hashlib.sha256).digest()
    signature = hmac.new(k_signing, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()
    return f"HMAC-SHA256 Credential={ak}/{credential_scope}, SignedHeaders={';'.join(signed_header_keys)}, Signature={signature}"


def pdf2markdown(ak: str, sk: str, file_path: str, page_num: int, parse_mode: str) -> str:
    host = 'visual.volcengineapi.com'
    region = 'cn-north-1'
    service = 'cv'

    query = {
        'Action': 'OCRPdf',
        'Version': '2021-08-23',
    }

    with open(file_path, 'rb') as f:
        b64 = base64.b64encode(f.read()).decode('ascii')
    file_type = 'pdf' if file_path.lower().endswith('.pdf') else 'image'
    body_dict = {
        'image_base64': b64,
        'version': 'v3',
        'file_type': file_type,
        'page_start': 0,
        'page_num': page_num,
        'parse_mode': parse_mode,
        'table_mode': 'markdown',
        'filter_header': 'false',
    }
    body_encoded = urlencode(body_dict).encode('utf-8')

    headers = {
        'content-type': 'application/x-www-form-urlencoded',
        'host': host,
        'x-date': _utc_now_xdate(),
    }

    auth = volc_sign(
        ak=ak, sk=sk, host=host, region=region, service=service,
        method='POST', canonical_uri='/', query=query, headers=headers, body=body_encoded,
    )

    url = f"https://{host}/"
    req_headers = {
        'Content-Type': headers['content-type'],
        'Host': headers['host'],
        'X-Date': headers['x-date'],
        'Authorization': auth,
    }
    resp = requests.post(url, params=query, data=body_encoded, headers=req_headers, timeout=60)
    data = resp.json()
    md = data['data']['markdown']
    md = re.sub(r'!\[[^\]]*\]\([^\)]+\)', lambda m: m.group(0)[2:m.group(0).find(']')], md)
    md = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', md)
    return md


def AI_call(text: str, api_key: str, model: str) -> str:
    api_key = api_key or ''
    model = model or 'deepseek-v3-2-251201'
    client = Ark(api_key=api_key, timeout=1800)
    # 最多重试3次
    for attempt in range(1, 4):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": text}],
                thinking={"type": "enabled"},
                temperature=0.1,
                top_p=0.7
            )
            return resp.choices[0].message.content
        except Exception as e:
            if attempt == 3:
                # 第三次仍然失败，直接抛出异常
                raise
            # 否则静默重试，也可以加短暂延迟
            time.sleep(1)


def pick_working_dir():
    if Tk is not None and askdirectory is not None:
        root = Tk()
        try:
            root.attributes('-topmost', True)
            root.lift()
            root.focus_force()
            root.update()
        except Exception:
            pass
        root.withdraw()
        try:
            path = askdirectory(parent=root)
        finally:
            try:
                root.destroy()
            except Exception:
                pass
        return path or ''
    # Fallback to PowerShell FolderBrowserDialog on Windows
    try:
        ps_script = (
            "Add-Type -AssemblyName System.Windows.Forms; " +
            "Add-Type -TypeDefinition '[System.Runtime.InteropServices.DllImport(\"user32.dll\")] public static extern System.IntPtr FindWindow(string lpClassName, string lpWindowName); [System.Runtime.InteropServices.DllImport(\"user32.dll\")] public static extern bool SetForegroundWindow(System.IntPtr hWnd); [System.Runtime.InteropServices.DllImport(\"user32.dll\")] public static extern bool SetWindowPos(System.IntPtr hWnd, System.IntPtr hWndInsertAfter, int X, int Y, int cx, int cy, uint uFlags);' -Name 'Win32' -Namespace 'Native'; " +
            "$form = New-Object System.Windows.Forms.Form; $form.TopMost = $true; $form.StartPosition = 'CenterScreen'; $form.ShowInTaskbar = $false; $form.Opacity = 0; $form.Show(); $form.BringToFront(); $form.Activate(); " +
            "$HWND_TOPMOST = [System.IntPtr]::op_Explicit(-1); $SWP_NOSIZE = 0x0001; $SWP_NOMOVE = 0x0002; $SWP_SHOWWINDOW = 0x0040; " +
            "$timer = New-Object System.Timers.Timer; $timer.Interval = 250; $timer.add_Elapsed({ $h = [Native.Win32]::FindWindow('#32770',$null); if($h -ne [System.IntPtr]::Zero){ [Native.Win32]::SetWindowPos($h, $HWND_TOPMOST, 0, 0, 0, 0, $SWP_NOSIZE -bor $SWP_NOMOVE -bor $SWP_SHOWWINDOW) | Out-Null; [Native.Win32]::SetForegroundWindow($h) | Out-Null } }); $timer.Start(); " +
            "$fb = New-Object System.Windows.Forms.FolderBrowserDialog; $fb.Description = '请选择空目录'; " +
            "$null = $fb.ShowDialog($form); $timer.Stop(); $timer.Dispose(); $form.Close(); " +
            "Write-Output $fb.SelectedPath"
        )
        result = subprocess.run([
            "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script
        ], capture_output=True, text=True, timeout=120)
        path = (result.stdout or "").strip()
        if path:
            return path
        raise RuntimeError('未选择目录或选择失败')
    except Exception as e:
        raise RuntimeError(f'目录选择失败: {e}')


def check_working_dir(path: str, expect_collection: bool = False) -> bool:
    if not path or not os.path.isdir(path):
        return False
    
    if expect_collection:
        # Check if "文献整理合集" exists inside
        collection_path = os.path.join(path, '文献整理合集')
        return os.path.isdir(collection_path)
    
    # Default behavior: check if empty
    with os.scandir(path) as it:
        for _ in it:
            return False
    return True
