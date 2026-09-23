"""Zero-vendor-lock adapters for Sudarshan UI tooling."""
from dataclasses import dataclass
import shutil,subprocess
@dataclass
class ToolResult:
 tool:str;available:bool;ok:bool;output:str=""
class LocalToolAdapter:
 def __init__(self,command):self.command=command
 def available(self):return shutil.which(self.command) is not None
 def run(self,args,timeout=120):
  if not self.available():return ToolResult(self.command,False,False,"not installed")
  p=subprocess.run([self.command,*args],capture_output=True,text=True,timeout=timeout)
  return ToolResult(self.command,True,p.returncode==0,(p.stdout+p.stderr)[-12000:])
class PlaywrightCLI(LocalToolAdapter):
 def __init__(self):super().__init__("playwright-cli")
class StagehandAdapter:
 """Optional agentic-browser adapter. Disabled unless explicitly configured."""
 def __init__(self,enabled=False):self.enabled=enabled
 def available(self):return self.enabled
class StorybookAdapter:
 """Component-state test contract; project supplies its own runner command."""
 def required_states(self):return ("default","hover","focus","disabled","loading","error","empty","long-text","mobile")
