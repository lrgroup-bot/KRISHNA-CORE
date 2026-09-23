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
from .brahmagyan import BrahmagyanRuntime
from .revenue_engine import RevenueEngine
from .integrations import CodebaseMemoryAdapter, GraftMemoryAdapter, WebhookAdapter
from .narad import NaradRuntime, NaradMessageStore
from .narad.credentials import NaradCredentialVault
from .narad.providers import NaradProviderHub
from .narad.n8n_bridge import N8nBridge
from .specialist_registry import SpecialistRegistry
from .context_governor import ContextGovernor
from .media_adapter import OpenMontageAdapter
from .sudarshan_design_engine import SudarshanDesignEngine
from .sudarshan_ui_pipeline import UIPipeline
from .vishvakarma_learning import VishvakarmaLearning
from .vishvakarma_rishi import VishvakarmaRishi
from .model_scout import ModelScout

class AGIKernel:
    VERSION="1.2.0-alpha"
    def __init__(self,runtime_root,memory,gyan,verification_engine,reviewer,secure_vault=None):
        self.root=Path(runtime_root); self.root.mkdir(parents=True,exist_ok=True)
        self.policy=PolicyKernel(self.root)
        self.executors=ExecutorFabric(self.policy)
        self.code_intelligence=CodebaseMemoryAdapter(cache_root=self.root/"cbm-cache")
        self.graft=GraftMemoryAdapter(profile="krishna")
        self.memory=MemoryFabric(memory,gyan,graft=self.graft,codebase_memory=self.code_intelligence)
        self.critic=IndependentCriticVerifier(verification_engine,reviewer)
        self.skills=SkillCompiler(self.root/"skills"/"compiled")
        self.benchmarks=BenchmarkLab()
        self.bus=AutomationBus()
        self.workers=WorkerFabric(self.root)
        self.creator=CreatorRuntime(self.workers)
        self.avatar=AvatarFabric()
        self.brahmagyan=BrahmagyanRuntime(self.root/"brahmagyan",gyan,memory)
        self.revenue=RevenueEngine(self.bus)
        self.specialists=SpecialistRegistry()
        self.context=ContextGovernor()
        self.narad_credentials=NaradCredentialVault(self.root/"narad"/"credentials.json", secure_vault)
        self.narad_providers=NaradProviderHub()
        self.narad_messages=NaradMessageStore(self.root/"narad"/"messages.json")
        self.narad=NaradRuntime(
            self.policy,self.bus,
            {"n8n":N8nBridge(),"activepieces":WebhookAdapter(),"webhook":WebhookAdapter()},
            state_path=self.root/"narad"/"state.json",
            credentials=self.narad_credentials,
            provider_hub=self.narad_providers,
        )
        self.media=OpenMontageAdapter(self.workers)
        self.vishvakarma=VishvakarmaRishi(self.root/"vishvakarma")
        self.vishvakarma_learning=VishvakarmaLearning(self.root/"vishvakarma"/"learning")
        self.design=SudarshanDesignEngine(self.root/"design",knowledge=self.vishvakarma_learning)
        self.ui_pipeline=UIPipeline(self.design)
        self.model_scout=ModelScout(self.root/"model-scout.json")
    def status(self):
        return {"name":"KRISHNA AGI CORE","version":self.VERSION,"architecture":"single-control-plane/modular-workers",
        "orchestrator":"KRISHNA Neural Action Graph + durable adapter boundary","executors":self.executors.capabilities(),
        "memory":self.memory.adapters(),"code_intelligence":self.code_intelligence.status(),
        "critic":"independent","skill_compiler":"ready","benchmark_lab":"ready",
        "narad":{**self.narad.status(),
            "credential_vault":{"connections":self.narad_credentials.list()["count"],"policy":"environment refs or Windows DPAPI encrypted secrets"},
            "providers":self.narad_providers.providers(),
            "messages":self.narad_messages.status()},
        "specialists":self.specialists.list(),"garudanetra":"BrowserOperator/Garuda integration",
        "creator":self.creator.status(),"avatar":self.avatar.status(),"brahmagyan":self.brahmagyan.status(),"media":self.media.status(),
        "revenue":self.revenue.status(),"workers":self.workers.status(),
        "design":self.design.status(),"vishvakarma":{**self.vishvakarma.status(),"learning":self.vishvakarma_learning.status()},
        "model_scout":self.model_scout.status()}
