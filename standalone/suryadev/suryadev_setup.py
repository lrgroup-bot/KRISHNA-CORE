"""First-run free local component setup. No credentials, sources or resets.

Only the packaged Windows launcher opts into automatic provisioning. Existing
Python installations remain unchanged. Downloading a model is not learning.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import shutil
import subprocess
import threading
import time
from urllib.request import Request, build_opener, ProxyHandler
from suryadev_liveops import atomic_json, _safe_read
from suryadev_lock import worker_lock
from suryadev_model_router import installed_small_model, decide_model, SMALL_MODEL
from suryadev_resources import snapshot

STATE = 'component-setup.json'
def tesseract_path():
    return shutil.which('tesseract') or next((str(path) for path in (
        Path(os.environ.get('ProgramFiles',r'C:\Program Files'))/'Tesseract-OCR'/'tesseract.exe',
        Path(os.environ.get('LOCALAPPDATA',''))/'Programs'/'Tesseract-OCR'/'tesseract.exe')
        if path.is_file()), None)
def status(root):
    value = _safe_read(root, STATE)
    return value or {'state':'not_requested', 'model':SMALL_MODEL,
                     'note':'Python/PDF/browser components are bundled in the Windows EXE.'}

def _local(path, payload=None, timeout=5):
    data = None if payload is None else json.dumps(payload).encode()
    request = Request('http://127.0.0.1:11434'+path, data=data,
                      headers={'Content-Type':'application/json'})
    return build_opener(ProxyHandler({})).open(request, timeout=timeout)

def provision(root, app, *, measure=snapshot, installed=installed_small_model):
    root, app = Path(root).resolve(), Path(app).resolve()
    def save(state, note):
        result = {'state':state,'note':note,'model':SMALL_MODEL,
                  'updated_at':time.time(),'learning_verified':False,
                  'ocr_available':bool(tesseract_path())}
        atomic_json(root, STATE, result)
        return result
    # A different lock file prevents duplicate installers across dashboards;
    # never acquire or interfere with the actual learning-worker lock.
    control = root.parent / (root.name + '-components')
    control.mkdir(exist_ok=True)
    try:
        with worker_lock(control):
            # OCR is separate from model inference. Missing OCR must remain
            # visible even on a PC that already has the local language model.
            if os.name == 'nt' and not tesseract_path():
                reading=measure(root)
                if not reading.get('available') or reading.get('cpu_percent',100)>=85 or reading.get('ram_percent',100)>=85 or reading.get('disk_free_gb',0)<2:
                    return save('deferred_hardware','OCR setup waits for safe CPU/RAM and disk headroom.')
                powershell=str(Path(os.environ.get('SystemRoot',r'C:\Windows'))/'System32'/'WindowsPowerShell'/'v1.0'/'powershell.exe')
                save('installing_ocr','Installing free Tesseract through the Windows package manager.')
                subprocess.run([powershell,'-NoProfile','-NonInteractive','-File',
                    str(app/'INSTALL_LOCAL_COMPONENTS.ps1'),'-ComponentDir',str(control),'-OCR'],
                    check=True,timeout=900,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0),
                    stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                if not tesseract_path(): raise RuntimeError('Installed Tesseract could not be located')
            if installed():
                return save('ready','Existing local model is available; nothing downloaded.')
            reading = measure(root)
            decision = decide_model(reading, installed=True)
            if decision['model'] == 'collector' or reading.get('disk_free_gb',0) < 10:
                return save('deferred_hardware','Component setup deferred until safe CPU/RAM and 10 GiB disk headroom. Collector remains available.')
            try:
                with _local('/api/version') as response:
                    if not json.loads(response.read(8192)).get('version'):
                        raise ValueError('Invalid local Ollama response')
            except (OSError, ValueError):
                if os.name != 'nt':
                    return save('needs_local_runtime','Automatic runtime installation currently supports Windows only.')
                save('installing_runtime','Downloading official signed Ollama installer.')
                powershell = str(Path(os.environ.get('SystemRoot',r'C:\Windows')) /
                    'System32' / 'WindowsPowerShell' / 'v1.0' / 'powershell.exe')
                subprocess.run([powershell,'-NoProfile','-NonInteractive','-File',
                    str(app/'INSTALL_LOCAL_COMPONENTS.ps1'),'-ComponentDir',str(control)],
                    check=True, timeout=1800, creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0),
                    stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                binary = shutil.which('ollama') or str(Path(os.environ.get('LOCALAPPDATA','')) /
                    'Programs'/'Ollama'/'ollama.exe')
                if not Path(binary).is_file():
                    raise RuntimeError('Installed Ollama executable not found')
                # Reuse the installed service if the installer already started it.
                try:
                    with _local('/api/version'): pass
                except OSError:
                    env = dict(os.environ, OLLAMA_HOST='127.0.0.1:11434',
                               OLLAMA_NO_CLOUD='1', OLLAMA_NUM_PARALLEL='1')
                    subprocess.Popen([binary,'serve'],env=env,stdin=subprocess.DEVNULL,
                        stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                        creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                for _ in range(30):
                    try:
                        with _local('/api/version'): break
                    except OSError: time.sleep(1)
                else: raise RuntimeError('Local Ollama service did not become ready')
            if decide_model(measure(root),installed=True)['model']=='collector':
                return save('deferred_hardware','Runtime installed; model download waits for safe hardware.')
            save('downloading_model','Downloading qwen3.5:2b through local Ollama. No cloud inference.')
            with _local('/api/pull',{'model':SMALL_MODEL,'stream':True},timeout=120) as response:
                finished=False
                for raw in response:
                    if len(raw)>65536: raise RuntimeError('Oversized model progress response')
                    value=json.loads(raw)
                    if value.get('error'): raise RuntimeError(str(value['error'])[:200])
                    if value.get('status')=='success': finished=True
                if not finished or not installed():
                    raise RuntimeError('Downloaded model could not be verified locally')
            return save('ready','Local components ready. Auto model selection uses hardware measured at worker start.')
    except (OSError,ValueError,RuntimeError,subprocess.SubprocessError) as exc:
        return save('blocked',type(exc).__name__+': '+str(exc)[:200])

def start(root, app):
    thread=threading.Thread(target=provision,args=(root,app),daemon=True,
                            name='suryadev-component-setup')
    thread.start()
    return thread
