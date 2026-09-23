"""Installer orchestration for an already-authorized trusted KRISHNA node."""
from dataclasses import dataclass
@dataclass
class HardwareProfile: cpu:str="unknown"; ram_gb:int=0; gpu:str="unknown"
class NodeInstaller:
 def plan(self, trusted, profile, missing_components=(), missing_models=()):
  if not trusted: return {"state":"AUTHORIZATION_REQUIRED"}
  return {"state":"READY","profile":profile.__dict__,"components":list(missing_components),"models":list(missing_models),"steps":["transfer-delta","regenerate-machine-identity","configure-runtime","install-services","acceptance-test","register-ready"]}
 def accept(self,checks):
  failed=[k for k,v in checks.items() if not v]
  return {"state":"READY" if not failed else "FAILED","failed":failed}
