from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
from threading import RLock
import time
import uuid


_SLUG = re.compile(r"^[a-z][a-z0-9_-]{1,63}$")
_KINDS = {"builtin", "local", "http", "mcp", "connector", "custom"}
_AUTH = {"none", "token", "api_key", "oauth", "device", "local"}
_RISKS = {"low", "medium", "high", "critical"}
_RETIRED_PLUGIN_IDS = {
    "amazon-sp-api", "amazon-associates", "flipkart-seller", "flipkart-affiliate",
    "meesho-seller", "alibaba-global", "shopify",
}
_RETIRED_PROVIDER_WORDS = ("amazon", "flipkart", "meesho", "alibaba", "shopify")
_BUILTIN_RUNTIME = {
    "pc": ("native_ready", "krishna-pc", "KRISHNA PC capabilities are provided by the local core and remain permission-gated."),
    "github": ("native_ready", "github-core", "GitHub research and PR-review capabilities exist in KRISHNA; account write access remains separately authorized."),
    "ollama": ("native_ready", "model-router", "Local Ollama execution is handled by KRISHNA ModelRouter."),
    "mcp-servers": ("setup_required", "mcp-gateway", "KRISHNA's authenticated MCP gateway is ready; each external MCP server still needs an approved client/transport registration."),
    "activepieces": ("setup_required", "narad-activepieces", "NARAD has an Activepieces webhook adapter; connect a verified self-hosted endpoint/token before enabling."),
    "gmail": ("setup_required", "narad-gmail", "The Gmail API adapter is implemented; provider OAuth authorization must be connected before enabling."),
    "google-drive": ("setup_required", "narad-google", "Drive/Sheets adapters are implemented; provider OAuth authorization must be connected before enabling."),
    "agentmarkup": ("setup_required", "local-skill", "Install/verify the AgentMarkup local skill in the KRISHNA runtime before enabling."),
    "windsurf": ("setup_required", "device-local", "Requires an explicitly authorized local IDE/device integration."),
    "blackbox-ai": ("policy_blocked", "http", "Paid/non-free provider is blocked by KRISHNA zero-spend policy."),
    "metricool": ("policy_blocked", "connector", "Paid/non-free provider is blocked by KRISHNA zero-spend policy."),
    "canva": ("policy_blocked", "connector", "Paid/non-free provider is blocked by KRISHNA zero-spend policy."),
    "windsor-ai": ("setup_required", "connector", "Free-plan connector requires a verified provider adapter and account authorization."),
    "semrush": ("policy_blocked", "connector", "Paid/non-free provider is blocked by KRISHNA zero-spend policy."),
    "agentmail": ("setup_required", "connector", "Requires a verified AgentMail connector and account authorization."),
    "superhuman-mail": ("policy_blocked", "connector", "Paid/non-free provider is blocked by KRISHNA zero-spend policy."),
}


def _runtime_info(item) -> dict:
    if item.builtin:
        state, adapter, hint = _BUILTIN_RUNTIME.get(item.id, ("setup_required", item.kind, "A dedicated adapter must be verified before enabling."))
    elif item.kind == "http":
        if not item.endpoint:
            state, adapter, hint = "setup_required", "http", "Add a valid HTTP(S) endpoint before enabling."
        elif item.auth_type in {"oauth", "device"}:
            state, adapter, hint = "setup_required", "http", "OAuth/device authentication requires a dedicated provider connector."
        elif item.auth_type in {"token", "api_key"} and not item.credential_ref:
            state, adapter, hint = "setup_required", "http", "Connect the API token/key before enabling."
        else:
            state, adapter, hint = "ready", "http", "Generic bounded HTTP execution is available."
    else:
        state, adapter, hint = "setup_required", item.kind, "Custom connector/local/MCP plugins require a registered adapter before enabling."
    if not item.free:
        state = "policy_blocked"
        hint = "Paid/non-free plugin is blocked by KRISHNA zero-spend policy."
    return {"runtime_state": state, "adapter": adapter, "setup_hint": hint, "can_enable": state in {"ready", "native_ready"}}


@dataclass(slots=True)
class PluginManifest:
    id: str
    name: str
    description: str = ""
    kind: str = "custom"
    endpoint: str = ""
    auth_type: str = "none"
    permissions: tuple[str, ...] = ()
    project_scope: tuple[str, ...] = ("*",)
    risk: str = "medium"
    enabled: bool = False
    builtin: bool = False
    source_url: str = ""
    license: str = ""
    free: bool = False
    credential_ref: str = ""
    created_at: float = 0.0
    updated_at: float = 0.0

    def public(self) -> dict:
        data = asdict(self)
        data["permissions"] = list(self.permissions)
        data["project_scope"] = list(self.project_scope)
        data.update(_runtime_info(self))
        return data


class PluginRegistry:
    """Persistent, provider-neutral plugin catalog.

    A manifest declares what a plugin *wants*. It does not grant execution
    authority, expose credentials, or bypass project/action policy.
    """

    def __init__(self, state_dir: str | Path):
        self.root = Path(state_dir).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "plugins.json"
        self.lock = RLock()
        self._items: dict[str, PluginManifest] = {}
        self._load()
        self._purge_retired()
        self._seed()

    def _load(self):
        if not self.path.exists():
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise RuntimeError(f"plugin registry unreadable: {self.path.name}: {type(exc).__name__}") from exc
        if not isinstance(raw,list):
            raise RuntimeError("plugin registry unreadable: expected JSON array")
        for row in raw if isinstance(raw, list) else []:
            try:
                item = self._coerce(row, preserve_times=True)
                self._items[item.id] = item
            except ValueError:
                continue

    def _save(self):
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps([x.public() for x in self._items.values()], indent=2), encoding="utf-8")
        tmp.replace(self.path)

    def _purge_retired(self):
        removed=False
        for plugin_id in tuple(self._items):
            if plugin_id in _RETIRED_PLUGIN_IDS:
                self._items.pop(plugin_id, None)
                removed=True
        if removed:
            self._save()

    @staticmethod
    def _assert_not_retired(data):
        combined=" ".join(str(data.get(key) or "") for key in ("id","name","source_url","endpoint")).lower()
        if any(word in combined for word in _RETIRED_PROVIDER_WORDS):
            raise PermissionError("this marketplace/provider is intentionally excluded from KRISHNA plugins")

    def _seed(self):
        defaults = [
            {"id":"pc","name":"PC","description":"Local registered projects, browser inspection, logs and approved PC actions.","kind":"local","auth_type":"local","permissions":["projects.read","files.read","browser.inspect","logs.read"],"risk":"high","builtin":True,"source_url":"local://krishna-pc","license":"KRISHNA-local","free":True},
            {"id":"github","name":"GitHub","description":"Repositories, issues, pull requests and CI workflows through an authorized connector.","kind":"connector","auth_type":"oauth","permissions":["repos.read","issues.read","pull_requests.read","actions.read"],"risk":"medium","builtin":True,"source_url":"https://github.com","license":"service-connector","free":True},
            {"id":"ollama","name":"Ollama","description":"Free local model runtime already supported by KRISHNA; no cloud credential required.","kind":"local","auth_type":"local","permissions":["models.local","models.invoke"],"risk":"low","builtin":True,"source_url":"https://github.com/ollama/ollama","license":"MIT","free":True},
            {"id":"mcp-servers","name":"MCP Servers","description":"Free reference MCP servers from the Model Context Protocol project. Install only the servers KRISHNA explicitly approves.","kind":"mcp","auth_type":"local","permissions":["tools.discover","tools.connect"],"risk":"medium","builtin":True,"source_url":"https://github.com/modelcontextprotocol/servers","license":"Apache-2.0/MIT transition","free":True},
            {"id":"activepieces","name":"Activepieces Community","description":"Free self-hosted community automation connector. Enterprise-only code is excluded from KRISHNA's free catalog.","kind":"connector","auth_type":"token","permissions":["workflows.read","workflows.run"],"risk":"medium","builtin":True,"source_url":"https://github.com/activepieces/activepieces","license":"MIT core / separate EE","free":True},
            {"id":"gmail","name":"Gmail","description":"Owner-authorized Gmail read, triage, draft, send, label and trash operations through NARAD; permanent delete is not an unattended operation.","kind":"connector","auth_type":"oauth","permissions":["mail.read","mail.draft","mail.send","mail.modify"],"risk":"high","builtin":True,"source_url":"https://developers.google.com/workspace/gmail/api/guides","license":"service-connector","free":True},
            {"id":"google-drive","name":"Google Drive / Sheets","description":"Owner-authorized Drive and Sheets workflows for project files, reports, product feeds and operating data.","kind":"connector","auth_type":"oauth","permissions":["drive.read","drive.write","sheets.read","sheets.write"],"risk":"high","builtin":True,"source_url":"https://developers.google.com/workspace","license":"service-connector","free":True},
            {"id":"agentmarkup","name":"AgentMarkup","description":"MIT web-project skill for llms.txt, JSON-LD, markdown mirrors, AI crawler policy, headers and machine-readable site validation.","kind":"local","auth_type":"local","permissions":["web.metadata.read","web.metadata.write","build.run"],"risk":"medium","builtin":True,"source_url":"https://github.com/agentmarkup/agentmarkup","license":"MIT","free":True},
            {"id":"windsurf","name":"Windsurf / Devin Desktop","description":"Optional local IDE/agent surface. KRISHNA may learn workflow patterns from it, but it never becomes KRISHNA authority.","kind":"local","auth_type":"device","permissions":["code.read","code.suggest"],"risk":"medium","builtin":True,"source_url":"https://windsurf.com/editor","license":"proprietary-service","free":True},
            {"id":"blackbox-ai","name":"BLACKBOX AI","description":"Optional coding-agent API adapter. Disabled by default because current Agents API requires a paid/enterprise credential; KRISHNA must not silently spend.","kind":"http","auth_type":"api_key","permissions":["code.read","code.suggest","agent.run"],"risk":"high","builtin":True,"source_url":"https://www.blackbox.ai/agents","license":"proprietary-service","free":False},
            {"id":"metricool","name":"Metricool","description":"Optional social scheduling and analytics connector candidate for multiple brand/social channels.","kind":"connector","auth_type":"oauth","permissions":["social.read","social.schedule","social.publish"],"risk":"high","builtin":True,"source_url":"https://metricool.com","license":"proprietary-service","free":False},
            {"id":"canva","name":"Canva","description":"Optional creative connector for product images, social assets and campaign designs; KRISHNA approval policy still governs publishing.","kind":"connector","auth_type":"oauth","permissions":["design.read","design.write"],"risk":"medium","builtin":True,"source_url":"https://www.canva.com","license":"proprietary-service","free":False},
            {"id":"windsor-ai","name":"Windsor.ai","description":"Optional cross-channel marketing/analytics connector with a free plan; writes stay owner-approved and only supported provider actions may run.","kind":"connector","auth_type":"oauth","permissions":["marketing.read","marketing.write"],"risk":"high","builtin":True,"source_url":"https://windsor.ai","license":"proprietary-service","free":True},
            {"id":"semrush","name":"Semrush","description":"Optional SEO/keyword/backlink research connector; never used as a paid fallback without owner approval.","kind":"connector","auth_type":"oauth","permissions":["seo.read"],"risk":"medium","builtin":True,"source_url":"https://www.semrush.com","license":"proprietary-service","free":False},
            {"id":"agentmail","name":"AgentMail","description":"Optional dedicated agent email inbox connector for two-way agent communication; separate from the owner's Gmail.","kind":"connector","auth_type":"oauth","permissions":["mail.read","mail.send","mail.modify"],"risk":"high","builtin":True,"source_url":"https://agentmail.to","license":"proprietary-service","free":True},
            {"id":"superhuman-mail","name":"Superhuman Mail","description":"Optional mail/calendar productivity connector candidate; owner account connection required.","kind":"connector","auth_type":"oauth","permissions":["mail.read","mail.draft","mail.send","calendar.read","calendar.write"],"risk":"high","builtin":True,"source_url":"https://superhuman.com","license":"proprietary-service","free":False},
        ]
        changed = False
        for row in defaults:
            if row["id"] not in self._items:
                row.setdefault("enabled", False)
                self._items[row["id"]] = self._coerce(row)
                changed = True
        if changed:
            self._save()

    def _coerce(self, data: dict, preserve_times: bool = False) -> PluginManifest:
        pid = str(data.get("id") or "").strip().lower()
        if not pid:
            pid = re.sub(r"[^a-z0-9_-]+", "-", str(data.get("name") or "").strip().lower()).strip("-")
        if not _SLUG.fullmatch(pid):
            raise ValueError("plugin id must use lowercase letters, numbers, _ or -")
        name = str(data.get("name") or pid).strip()[:100]
        if not name:
            raise ValueError("plugin name is required")
        kind = str(data.get("kind") or "custom").strip().lower()
        if kind not in _KINDS:
            raise ValueError("unsupported plugin kind")
        auth = str(data.get("auth_type") or "none").strip().lower()
        if auth not in _AUTH:
            raise ValueError("unsupported auth type")
        risk = str(data.get("risk") or "medium").strip().lower()
        if risk not in _RISKS:
            raise ValueError("unsupported risk")
        perms = tuple(sorted({str(x).strip() for x in data.get("permissions") or [] if str(x).strip()}))
        scope = tuple(sorted({str(x).strip() for x in data.get("project_scope") or ["*"] if str(x).strip()})) or ("*",)
        now = time.time()
        created = float(data.get("created_at") or now) if preserve_times else now
        updated = float(data.get("updated_at") or now) if preserve_times else now
        return PluginManifest(
            id=pid, name=name, description=str(data.get("description") or "")[:800],
            kind=kind, endpoint=str(data.get("endpoint") or "")[:1000],
            auth_type=auth, permissions=perms, project_scope=scope, risk=risk,
            enabled=bool(data.get("enabled", False)), builtin=bool(data.get("builtin", False)),
            source_url=str(data.get("source_url") or "")[:1000], license=str(data.get("license") or "")[:120],
            free=bool(data.get("free", False)), credential_ref=str(data.get("credential_ref") or "")[:160],
            created_at=created, updated_at=updated,
        )

    def list(self) -> list[dict]:
        with self.lock:
            return [x.public() for x in sorted(self._items.values(), key=lambda p: (not p.builtin, p.name.lower()))]

    def add(self, data: dict) -> dict:
        self._assert_not_retired(data)
        item = self._coerce(data)
        with self.lock:
            if item.id in self._items:
                raise ValueError("plugin already exists")
            self._items[item.id] = item
            self._save()
        return item.public()

    def set_enabled(self, plugin_id: str, enabled: bool) -> dict:
        with self.lock:
            item = self._items.get(plugin_id)
            if not item:
                raise KeyError(plugin_id)
            if bool(enabled):
                info=_runtime_info(item)
                if not bool(item.free):
                    raise PermissionError("zero-spend policy blocks paid/non-free plugins")
                if not info["can_enable"]:
                    raise RuntimeError("plugin setup is incomplete: "+info["setup_hint"])
            item.enabled = bool(enabled)
            item.updated_at = time.time()
            self._save()
            return item.public()

    def set_credential(self, plugin_id: str, credential_ref: str) -> dict:
        ref=str(credential_ref or "").strip()
        if not ref:
            raise ValueError("credential_ref is required")
        with self.lock:
            item=self._items.get(plugin_id)
            if not item:
                raise KeyError(plugin_id)
            item.credential_ref=ref
            item.updated_at=time.time()
            self._save()
            return item.public()

    def clear_credential(self, plugin_id: str) -> dict:
        with self.lock:
            item=self._items.get(plugin_id)
            if not item:
                raise KeyError(plugin_id)
            item.credential_ref=""
            item.updated_at=time.time()
            self._save()
            return item.public()

    def remove(self, plugin_id: str) -> bool:
        with self.lock:
            item = self._items.get(plugin_id)
            if not item:
                return False
            if item.builtin:
                raise PermissionError("builtin plugins cannot be removed")
            del self._items[plugin_id]
            self._save()
            return True
