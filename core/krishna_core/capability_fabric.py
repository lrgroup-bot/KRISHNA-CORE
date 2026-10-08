from __future__ import annotations

from dataclasses import dataclass, asdict
from threading import RLock
from typing import Any


@dataclass(frozen=True)
class CapabilityProvider:
    provider_id: str
    capability: str
    location: str
    free_only: bool
    resident: bool = False
    enabled: bool = True
    sensitive_allowed: bool = False
    heavy: bool = False
    notes: str = ""

    def as_dict(self): return asdict(self)


class CapabilityFabric:
    """Provider/consumer seam for KRISHNA.

    Providers are metadata until invoked by their owning adapter. Registration
    never starts a model or background process, preventing capability discovery
    from increasing KRISHNA's idle memory/CPU load.
    """

    VERSION="capability-fabric-v2"

    def __init__(self, system_one=None):
        self.system_one=system_one
        self._lock=RLock()
        self._providers:dict[str,CapabilityProvider]={}
        self._rishi_gyan_sagar=None
        self._rishi_deep_sources=None
        # RISHI GYAN-SAGAR is a routing/rights fabric, not another resident
        # crawler. Registering these capabilities therefore adds no idle worker
        # or network load. Actual browsing/API calls remain behind KRISHNA's
        # action, permission and browser/connector gates.
        self.register(
            "rishi-gyan-sagar","knowledge.research","hybrid",free_only=True,
            resident=False,sensitive_allowed=False,heavy=False,
            notes="rights-aware scholarly/books/standards/patents/code/source routing for BRAHMAGYAN",
        )
        self.register(
            "rishi-rights-gate","knowledge.rights","local",free_only=True,
            resident=False,sensitive_allowed=True,heavy=False,
            notes="separates read/index/archive/train permissions before Gyan-Bhandar ingestion",
        )

    def register(self, provider_id, capability, location, *, free_only,
                 resident=False, enabled=True, sensitive_allowed=False,
                 heavy=False, notes=""):
        row=CapabilityProvider(
            str(provider_id),str(capability),str(location),bool(free_only),
            bool(resident),bool(enabled),bool(sensitive_allowed),bool(heavy),str(notes),
        )
        with self._lock:self._providers[row.provider_id]=row
        return row.as_dict()

    def list(self, capability=None):
        with self._lock:rows=list(self._providers.values())
        if capability:
            rows=[x for x in rows if x.capability==str(capability)]
        return [x.as_dict() for x in sorted(rows,key=lambda x:(x.capability,x.provider_id))]

    def route(self, capability, *, sensitive=False, mobile=False, prefer_free=True,
              heavy=False, context=None):
        context=dict(context or {})
        rows=[
            x for x in self._providers.values()
            if x.enabled and x.capability==str(capability)
            and (not sensitive or x.sensitive_allowed)
            and (not prefer_free or x.free_only)
        ]
        if mobile:
            preferred=[x for x in rows if x.location in {"mobile","cloud"}]
            if preferred: rows=preferred
        if not heavy:
            light=[x for x in rows if not x.heavy]
            if light: rows=light
        if not rows:
            return {"selected":None,"candidates":[],"reason":"no eligible provider"}
        options=[x.provider_id for x in rows]
        if self.system_one and len(options)>1:
            decision=self.system_one.choose({
                **context,"capability":capability,"sensitive":sensitive,
                "mobile":mobile,"heavy":heavy,
            },options)
            selected=decision["choice"]
        else:
            decision=None
            selected=options[0]
        result={
            "selected":selected,
            "provider":next(x.as_dict() for x in rows if x.provider_id==selected),
            "candidates":[x.as_dict() for x in rows],
            "decision":decision,
            "authority":"provider recommendation only; Sudarshan/PolicyKernel governs execution",
        }
        # Existing Shared Action Bus `capability.route` already passes a context
        # object. Enrich that response for knowledge capabilities instead of
        # adding a second privileged API/action surface.
        if str(capability)=="knowledge.research" and str(context.get("topic") or "").strip():
            kinds=context.get("kinds")
            if kinds is not None and not isinstance(kinds,(list,tuple,set)):
                raise ValueError("knowledge context kinds must be an array")
            result["knowledge_plan"]=self._merged_knowledge_plan(
                str(context["topic"]),
                rishi_id=context.get("rishi_id"),
                kinds=kinds or (),
                max_sources=int(context.get("max_sources") or 12),
            )
            if str(context.get("source_id") or "").strip() and str(context.get("query") or "").strip():
                result["request_plan"]=self._knowledge_request_plan(
                    context["source_id"],context["query"],
                    email=str(context.get("email") or ""),
                    api_key_ref=str(context.get("api_key_ref") or ""),
                )
            result["execution"]="plan/request contract only; network/browser work remains behind Shared Action Bus and approved adapters"
        elif str(capability)=="knowledge.rights" and str(context.get("requested_mode") or "").strip():
            base=self._gyan_sagar().rights_decision(
                context["requested_mode"],
                license_id=str(context.get("license_id") or ""),
                source_default_max_mode=str(context.get("source_default_max_mode") or "read"),
                commercial_context=bool(context.get("commercial_context",True)),
                explicit_permission=bool(context.get("explicit_permission",False)),
            ).public()
            result["rights_decision"]=self._apply_training_policy(
                context["requested_mode"],base,
                license_id=str(context.get("license_id") or ""),
                explicit_permission=bool(context.get("explicit_permission",False)),
            )
        return result

    @staticmethod
    def _apply_training_policy(requested_mode,decision,*,license_id="",explicit_permission=False):
        if str(requested_mode or "").strip().lower()!="train":
            return dict(decision or {})
        from .rishi_training_policy import training_policy
        return training_policy(decision,license_id=license_id,explicit_permission=explicit_permission)

    def _gyan_sagar(self):
        # Lazy import/instantiation prevents source-catalog discovery from adding
        # start-up work to KRISHNA. The object itself is pure policy/planning and
        # performs no network I/O.
        if self._rishi_gyan_sagar is None:
            from .rishi_gyan_sagar import RishiGyanSagar
            self._rishi_gyan_sagar=RishiGyanSagar()
        return self._rishi_gyan_sagar

    def _deep_sources(self):
        if self._rishi_deep_sources is None:
            from .rishi_deep_sources import RishiDeepSourceExpansion
            self._rishi_deep_sources=RishiDeepSourceExpansion()
        return self._rishi_deep_sources

    def _merged_knowledge_plan(self,topic,*,rishi_id=None,kinds=(),max_sources=12):
        limit=max(1,min(int(max_sources),30))
        base=self._gyan_sagar().research_plan(topic,rishi_id=rishi_id,kinds=kinds,max_sources=limit)
        extra=self._deep_sources().research_plan(
            topic,rishi_id=base.get("lead_rishi") or rishi_id,kinds=kinds,max_sources=limit,
        )
        merged=[];seen=set()
        for row in sorted(list(base.get("sources") or [])+list(extra),key=lambda x:(-int(x.get("score") or 0),str(x.get("priority") or "P9"),str(x.get("name") or ""))):
            sid=str(row.get("id") or "")
            if not sid or sid in seen:continue
            seen.add(sid);merged.append(row)
            if len(merged)>=limit:break
        out=dict(base)
        out["sources"]=merged
        out["source_fabrics"]=["rishi-gyan-sagar","rishi-deep-sources"]
        out["available_source_count"]=self._gyan_sagar().source_status()["source_count"]+self._deep_sources().status()["source_count"]
        return out

    def _knowledge_request_plan(self,source_id,query,*,email="",api_key_ref=""):
        try:
            return self._gyan_sagar().request_plan(source_id,query,email=email,api_key_ref=api_key_ref)
        except KeyError:
            return self._deep_sources().request_plan(source_id,query,email=email,api_key_ref=api_key_ref)

    def knowledge_plan(self, topic, *, rishi_id=None, kinds=None, max_sources=12):
        route=self.route("knowledge.research")
        if not route.get("selected"):
            return {"route":route,"plan":None}
        plan=self._merged_knowledge_plan(topic,rishi_id=rishi_id,kinds=kinds or (),max_sources=max_sources)
        return {"route":route,"plan":plan,
                "execution":"source plan only; execute selected requests through Shared Action Bus/browser/connectors"}

    def knowledge_request(self, source_id, query, *, email="", api_key_ref=""):
        route=self.route("knowledge.research")
        if not route.get("selected"):
            return {"route":route,"request":None}
        request=self._knowledge_request_plan(source_id,query,email=email,api_key_ref=api_key_ref)
        return {"route":route,"request":request,
                "execution":"request contract only; network execution remains permission-gated"}

    def knowledge_rights(self, requested_mode, *, license_id="", source_default_max_mode="read",
                         commercial_context=True, explicit_permission=False):
        route=self.route("knowledge.rights",sensitive=True)
        if not route.get("selected"):
            return {"route":route,"decision":None}
        base=self._gyan_sagar().rights_decision(
            requested_mode,license_id=license_id,source_default_max_mode=source_default_max_mode,
            commercial_context=commercial_context,explicit_permission=explicit_permission,
        ).public()
        decision=self._apply_training_policy(
            requested_mode,base,license_id=license_id,explicit_permission=explicit_permission,
        )
        return {"route":route,"decision":decision}

    def knowledge_status(self):
        base=self._gyan_sagar().source_status()
        deep=self._deep_sources().status()
        return {
            "route":self.route("knowledge.research"),
            "rights_route":self.route("knowledge.rights",sensitive=True),
            "sagar":base,
            "deep_sources":deep,
            "total_source_count":int(base["source_count"])+int(deep["source_count"]),
            "policy":"one Rishi knowledge capability; multiple curated source catalogs; no duplicate authority plane; training is stricter than ordinary reuse",
        }

    def status(self):
        rows=self.list()
        return {
            "component":"KRISHNA Capability Fabric",
            "version":self.VERSION,
            "providers":rows,
            "provider_count":len(rows),
            "resident_provider_count":sum(bool(x["resident"]) for x in rows),
            "idle_load_policy":"registration never starts provider runtimes",
        }