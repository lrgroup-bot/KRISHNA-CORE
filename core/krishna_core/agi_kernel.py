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
from .integrations import CodebaseMemoryAdapter, GraftMemoryAdapter, WebhookAdapter
from .narad import NaradRuntime
from .specialist_registry import SpecialistRegistry
from .context_governor import ContextGovernor
from .media_adapter import OpenMontageAdapter

class AGIKernel:
    VERSION="1.1.0-alpha"
    def __init__(self,runtime_root,memory,gyan,verification_engine,reviewer):
        self.root=Path(runtime_root); self.root.mkdir(parents=True,exist_ok=True)
        self.policy=PolicyKernel(self.root)
        self.executors=ExecutorFabric(self.policy)
        self.memory=MemoryFabric(memory,gyan)
        self.critic=IndependentCriticVerifier(verification_engine,reviewer)
        self.skills=SkillCompiler(self.root/"skills"/"compiled")
        self.benchmarks=BenchmarkLab()
        self.bus=AutomationBus()
        self.workers=WorkerFabric(self.root)
        self.creator=CreatorRuntime(self.workers)
        self.avatar=AvatarFabric()
        self.revenue=RevenueEngine(self.bus)
        self.code_intelligence=CodebaseMemoryAdapter(cache_root=self.root/"cbm-cache")
        self.graft=GraftMemoryAdapter(profile="krishna")
        self.specialists=SpecialistRegistry()
        self.context=ContextGovernor()
        self.narad=NaradRuntime(self.policy,self.bus,{"n8n":WebhookAdapter(),"activepieces":WebhookAdapter(),"webhook":WebhookAdapter()},state_path=self.root/"narad"/"state.json")
        self.media=OpenMontageAdapter(self.workers)
    def status(self):
        return {"name":"KRISHNA AGI CORE","version":self.VERSION,"architecture":"single-control-plane/modular-workers",
        "orchestrator":"KRISHNA Neural Action Graph + durable adapter boundary","executors":self.executors.capabilities(),
        "memory":{**self.memory.adapters(),"graft":self.graft.status()},"code_intelligence":self.code_intelligence.status(),
        "critic":"independent","skill_compiler":"ready","benchmark_lab":"ready","narad":self.narad.status(),
        "specialists":self.specialists.list(),"garudanetra":"BrowserOperator/Garuda integration",
        "creator":self.creator.status(),"avatar":self.avatar.status(),"media":self.media.status(),
        "revenue":self.revenue.status(),"workers":self.workers.status()}
