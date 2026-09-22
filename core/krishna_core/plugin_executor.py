from __future__ import annotations
import ipaddress,json,os,socket,urllib.request,urllib.parse
from dataclasses import dataclass


@dataclass
class PluginCall:
    plugin_id:str
    project:str
    operation:str
    payload:dict


class PluginExecutor:
    """Execution boundary for enabled HTTP plugins.

    Secrets are never stored in plugin manifests. Token/API-key values resolve from
    KRISHNA's encrypted vault (or an explicitly named environment variable). HTTP
    calls are bounded and reject unsafe URL forms/link-local metadata targets.
    Connector/MCP/local providers remain adapter-specific.
    """

    def __init__(self, registry, vault=None):
        self.registry=registry
        self.vault=vault

    def _manifest(self, plugin_id):
        item=next((x for x in self.registry.list() if x["id"]==plugin_id),None)
        if not item: raise KeyError(plugin_id)
        if not item.get("enabled"): raise PermissionError("plugin is disabled")
        return item

    @staticmethod
    def _endpoint(endpoint):
        parsed=urllib.parse.urlparse(str(endpoint or "").strip())
        if parsed.scheme not in {"http","https"} or not parsed.hostname:
            raise ValueError("invalid HTTP plugin endpoint")
        if parsed.username or parsed.password:
            raise ValueError("plugin endpoint must not embed credentials")
        if parsed.fragment:
            raise ValueError("plugin endpoint fragments are not allowed")
        host=parsed.hostname.strip().lower()
        if host in {"metadata.google.internal","metadata","instance-data","instance-data.ec2.internal"}:
            raise PermissionError("link-local/cloud metadata plugin target is blocked")
        addresses=[]
        try:
            literal=ipaddress.ip_address(host.strip("[]"))
            addresses=[literal]
        except ValueError:
            try:
                addresses=list({
                    ipaddress.ip_address(row[4][0].split("%",1)[0])
                    for row in socket.getaddrinfo(host,parsed.port or (443 if parsed.scheme=="https" else 80),type=socket.SOCK_STREAM)
                })
            except OSError as exc:
                raise ValueError("plugin endpoint hostname could not be resolved") from exc
        for addr in addresses:
            if addr.is_link_local or addr.is_unspecified or addr.is_multicast or addr.is_reserved:
                raise PermissionError("link-local/reserved plugin target is blocked")
        is_local=host=="localhost" or bool(addresses and all(a.is_loopback or a.is_private for a in addresses))
        if parsed.scheme!="https" and not is_local:
            raise PermissionError("non-local HTTP plugins require HTTPS")
        return parsed

    def execute(self, plugin_id, project, operation="get", payload=None, auth_env=None):
        item=self._manifest(plugin_id)
        scope=item.get("project_scope") or ["*"]
        if "*" not in scope and project not in scope: raise PermissionError("plugin is outside project scope")
        if item.get("kind")!="http":
            raise ValueError("this runtime executes HTTP plugins only; connector/MCP/local plugins require their registered adapter")
        endpoint=str(item.get("endpoint") or "").strip()
        self._endpoint(endpoint)
        op=str(operation or "get").lower()
        if op not in {"get","post"}: raise ValueError("HTTP plugin operation must be get or post")
        headers={"Accept":"application/json","User-Agent":"KRISHNA-PluginRuntime/1.1"}
        secret=None
        credential_ref=str(item.get("credential_ref") or "").strip()
        if credential_ref:
            if not self.vault: raise PermissionError("plugin credential vault is unavailable")
            secret=self.vault.resolve(credential_ref)
        elif auth_env:
            name=str(auth_env)
            if not name.replace("_","").isalnum(): raise ValueError("invalid auth environment variable")
            secret=os.getenv(name)
            if not secret: raise PermissionError("plugin credential environment variable is unavailable")
        auth=item.get("auth_type")
        if secret is not None:
            if auth=="token": headers["Authorization"]="Bearer "+secret
            elif auth=="api_key": headers["X-API-Key"]=secret
            elif auth not in {"none","local"}: raise ValueError("auth type requires a dedicated adapter")
        elif auth in {"token","api_key"}:
            raise PermissionError("plugin credential is not connected")
        data=None
        if op=="post":
            encoded=json.dumps(payload or {},ensure_ascii=False).encode("utf-8")
            if len(encoded)>1_000_000:raise ValueError("plugin request exceeds 1 MB")
            data=encoded;headers["Content-Type"]="application/json"
        req=urllib.request.Request(endpoint,data=data,headers=headers,method=op.upper())
        with urllib.request.urlopen(req,timeout=30) as response:
            raw=response.read(2_000_001)
            if len(raw)>2_000_000: raise ValueError("plugin response exceeds 2 MB")
            ctype=response.headers.get("Content-Type","")
            text=raw.decode("utf-8",errors="replace")
            body=json.loads(text) if "json" in ctype.lower() and text.strip() else text
            return {"plugin_id":plugin_id,"project":project,"operation":op,"status":response.status,"content_type":ctype,"body":body}
