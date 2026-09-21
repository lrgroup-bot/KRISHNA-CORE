from __future__ import annotations
from pathlib import Path
from .policy_kernel import PolicyKernel
from .executor_fabric import ExecutorFabric
from .memory_fabric import MemoryFabric
from .critic_verifier import IndependentCriticVerifier
from .skill_compiler import SkillCompiler
from .benchmark_lab import BenchmarkLab
from .automation_bus import AutomationBus
from .worker_fabric import WorkerFabric
from .creator_runtime import CreatorRuntime
from .avatar_fabric import AvatarFabric
from .revenue_engine import RevenueEngine

class AGIKernel:
    VERSION='1.0.0-alpha'
    def __init__(self,runtime_root,memory,gyan,verification_engine,reviewer):
        self.root=Path(runtime_root); self.root.mkdir(parents=True,exist_ok=True)
        self.policy=PolicyKernel(self.root)
        self.executors=ExecutorFabric(self.policy)
        self.memory=MemoryFabric(memory,gyan)
        self.critic=IndependentCriticVerifier(verification_engine,reviewer)
        self.skills=SkillCompiler(self.root/'skills'/'compiled')
        self.benchmarks=BenchmarkLab()
        self.bus=AutomationBus()
        self.workers=WorkerFabric(self.root)
        self.creator=CreatorRuntime(self.workers)
        self.avatar=AvatarFabric()
        self.revenue=RevenueEngine(self.bus)
    def status(self):
        return {"name":"KRISHNA AGI CORE","version":self.VERSION,"architecture":"single-control-plane/modular-workers","orchestrator":"KRISHNA Neural Action Graph + LangGraph adapter boundary","executors":self.executors.capabilities(),"memory":self.memory.adapters(),"critic":"independent","skill_compiler":"ready","benchmark_lab":"ready","automation":{"native":"ready","adapters":["n8n","activepieces"]},"garudanetra":"existing BrowserOperator/Garuda integration","creator":self.creator.status(),"avatar":self.avatar.status(),"revenue":self.revenue.status(),"workers":self.workers.status()}
