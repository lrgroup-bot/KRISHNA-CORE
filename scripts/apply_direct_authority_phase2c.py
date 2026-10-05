from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def patch(path,replacements):
    p=ROOT/path
    text=p.read_text(encoding="utf-8")
    original=text
    for old,new in replacements:
        if old in text:
            text=text.replace(old,new)
        elif new not in text:
            raise RuntimeError(f"patch anchor missing in {path}: {old[:160]!r}")
    if text != original:
        p.write_text(text,encoding="utf-8")
        print(f"patched {path}")
    else:
        print(f"already patched {path}")


patch(Path("core/krishna_core/orchestrator.py"),[
("""        self.authority = AuthorityLeaseGate(runtime_state / \"authority\", audit=self.memory.audit, initially_locked=True)\n""",
 """        self.authority = AuthorityLeaseGate(runtime_state / \"authority\", audit=self.memory.audit, initially_locked=True)\n        self.direct_authority_actions=frozenset({\n            \"software_factory.workers.approve\",\n            \"gyan.archive.restore\",\n            \"gyan.archive.remove_original\",\n        })\n"""),
("""    def request_ephemeral_workers(self,project,manager,role,count,reason,hr_snapshot=None,approve=False):\n        if project!=\"KRISHNA\" and not self.projects.get(project):raise KeyError(project)\n        return self.software_factory.worker_request(project,manager,role,count,reason,hr_snapshot or {},bool(approve))\n""",
 """    def request_ephemeral_workers(self,project,manager,role,count,reason,hr_snapshot=None,approve=False,authority_lease=None):\n        if project!=\"KRISHNA\" and not self.projects.get(project):raise KeyError(project)\n        snapshot=hr_snapshot or {}\n        if approve:\n            self.authority.consume(\n                authority_lease,action=\"software_factory.workers.approve\",\n                payload={\"project\":project,\"manager\":manager,\"role\":role,\"count\":int(count),\"reason\":reason,\"hr_snapshot\":snapshot},\n                project=project,source=\"pc\",actor=\"software-factory-http\",\n            )\n        return self.software_factory.worker_request(project,manager,role,count,reason,snapshot,bool(approve))\n"""),
("""    def gyan_archive_file(self, project, source_path, topic=\"\", remove_original=False):\n        root=self._gyan_scope_root(project)\n        source=Path(source_path).resolve()\n        try:source.relative_to(root)\n        except ValueError as exc:raise PermissionError(\"Gyan archive source is outside the selected project/runtime scope\") from exc\n        if remove_original:\n            if project!=\"KRISHNA\":self.projects.assert_mutable(project,\"gyan_archive_remove_original\")\n            if not settings.allow_actions:raise PermissionError(\"KRISHNA_ALLOW_ACTIONS is disabled\")\n        return self.gyan_bhandar.archive_file(project,source,topic,remove_original)\n""",
 """    def gyan_archive_file(self, project, source_path, topic=\"\", remove_original=False, authority_lease=None):\n        raw_source=str(source_path)\n        root=self._gyan_scope_root(project)\n        source=Path(source_path).resolve()\n        try:source.relative_to(root)\n        except ValueError as exc:raise PermissionError(\"Gyan archive source is outside the selected project/runtime scope\") from exc\n        if remove_original:\n            if project!=\"KRISHNA\":self.projects.assert_mutable(project,\"gyan_archive_remove_original\")\n            if not settings.allow_actions:raise PermissionError(\"KRISHNA_ALLOW_ACTIONS is disabled\")\n            self.authority.consume(\n                authority_lease,action=\"gyan.archive.remove_original\",\n                payload={\"project\":project,\"source_path\":raw_source,\"topic\":topic,\"remove_original\":True},\n                project=project,source=\"pc\",actor=\"gyan-http\",\n            )\n        return self.gyan_bhandar.archive_file(project,source,topic,remove_original)\n"""),
("""    def gyan_restore_file(self, sha256, destination, project=\"KRISHNA\", approved=False):\n        root=self._gyan_scope_root(project)\n        destination=Path(destination).resolve()\n""",
 """    def gyan_restore_file(self, sha256, destination, project=\"KRISHNA\", approved=False, authority_lease=None):\n        raw_destination=str(destination)\n        self.authority.consume(\n            authority_lease,action=\"gyan.archive.restore\",\n            payload={\"sha256\":str(sha256),\"destination\":raw_destination,\"project\":project},\n            project=project,source=\"pc\",actor=\"gyan-http\",\n        )\n        approved=True\n        root=self._gyan_scope_root(project)\n        destination=Path(destination).resolve()\n"""),
("""    def development_commit(self, project, message, files, approved=False):\n        receipt=self.dispatch_action(\"development.git.commit\",{\"project\":project,\"message\":message,\"files\":files},project=project,source=\"pc\",actor=\"developer-ui\",approved=approved)\n        return receipt[\"result\"]\n""",
 """    def development_commit(self, project, message, files, approved=False, authority_lease=None):\n        receipt=self.dispatch_action(\"development.git.commit\",{\"project\":project,\"message\":message,\"files\":files},project=project,source=\"pc\",actor=\"developer-ui\",approved=approved,authority_lease=authority_lease)\n        return receipt[\"result\"]\n"""),
("""    def development_push(self, project, approved=False):\n        receipt=self.dispatch_action(\"development.git.push\",{\"project\":project},project=project,source=\"pc\",actor=\"developer-ui\",approved=approved)\n        return receipt[\"result\"]\n""",
 """    def development_push(self, project, approved=False, authority_lease=None):\n        receipt=self.dispatch_action(\"development.git.push\",{\"project\":project},project=project,source=\"pc\",actor=\"developer-ui\",approved=approved,authority_lease=authority_lease)\n        return receipt[\"result\"]\n"""),
("""    def development_sync(self, project, approved=False):\n        receipt=self.dispatch_action(\"development.sync\",{\"project\":project},project=project,source=\"pc\",actor=\"developer-ui\",approved=approved)\n        return receipt[\"result\"]\n""",
 """    def development_sync(self, project, approved=False, authority_lease=None):\n        receipt=self.dispatch_action(\"development.sync\",{\"project\":project},project=project,source=\"pc\",actor=\"developer-ui\",approved=approved,authority_lease=authority_lease)\n        return receipt[\"result\"]\n"""),
])

patch(Path("core/krishna_core/server.py"),[
("""            if action not in {x.get(\"name\") for x in orch.action_bus.list()}:\n                return self._json(404,{\"error\":\"shared action not registered\"})\n""",
 """            allowed_actions={x.get(\"name\") for x in orch.action_bus.list()} | set(getattr(orch,\"direct_authority_actions\",()))\n            if action not in allowed_actions:\n                return self._json(404,{\"error\":\"authority action not registered\"})\n"""),
("""        if post_path == \"/api/software-factory/workers/approve\":\n            try:return self._json(200,orch.request_ephemeral_workers(str(data.get(\"project\") or \"\"),str(data.get(\"manager\") or \"\"),str(data.get(\"role\") or \"\"),int(data.get(\"count\") or 1),str(data.get(\"reason\") or \"\"),data.get(\"hr_snapshot\"),True))\n            except (ValueError,KeyError,TypeError) as exc:return self._json(400,{\"error\":str(exc)})\n""",
 """        if post_path == \"/api/software-factory/workers/approve\":\n            try:return self._json(200,orch.request_ephemeral_workers(str(data.get(\"project\") or \"\"),str(data.get(\"manager\") or \"\"),str(data.get(\"role\") or \"\"),int(data.get(\"count\") or 1),str(data.get(\"reason\") or \"\"),data.get(\"hr_snapshot\"),True,authority_lease=data.get(\"authority_lease\")))\n            except PermissionError as exc:return self._json(403,{\"error\":str(exc)})\n            except (ValueError,KeyError,TypeError) as exc:return self._json(400,{\"error\":str(exc)})\n"""),
("""            try:return self._json(200,orch.development_commit(project,str(data.get(\"message\",\"KRISHNA verified change\")),data.get(\"files\") or [],bool(data.get(\"approved\",False))))\n""",
 """            try:return self._json(200,orch.development_commit(project,str(data.get(\"message\",\"KRISHNA verified change\")),data.get(\"files\") or [],bool(data.get(\"approved\",False)),authority_lease=data.get(\"authority_lease\")))\n"""),
("""            try:return self._json(200,orch.development_push(project,bool(data.get(\"approved\",False))))\n""",
 """            try:return self._json(200,orch.development_push(project,bool(data.get(\"approved\",False)),authority_lease=data.get(\"authority_lease\")))\n"""),
("""            try:return self._json(200,orch.development_sync(project,bool(data.get(\"approved\",False))))\n""",
 """            try:return self._json(200,orch.development_sync(project,bool(data.get(\"approved\",False)),authority_lease=data.get(\"authority_lease\")))\n"""),
("""            try:return self._json(201,orch.gyan_archive_file(project,source_path,str(data.get(\"topic\") or \"\"),bool(data.get(\"remove_original\",False))))\n""",
 """            try:return self._json(201,orch.gyan_archive_file(project,source_path,str(data.get(\"topic\") or \"\"),bool(data.get(\"remove_original\",False)),authority_lease=data.get(\"authority_lease\")))\n"""),
("""            try:return self._json(200,orch.gyan_restore_file(digest,destination,project,bool(data.get(\"approved\",False))))\n""",
 """            try:return self._json(200,orch.gyan_restore_file(digest,destination,project,bool(data.get(\"approved\",False)),authority_lease=data.get(\"authority_lease\")))\n"""),
])

print("Direct authority Phase 2C patch complete")
