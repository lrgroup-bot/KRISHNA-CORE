from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]


def text(rel):
    return (ROOT/rel).read_text(encoding="utf-8")


def block(source,start,end):
    i=source.index(start)
    j=source.find(end,i+len(start))
    return source[i:] if j < 0 else source[i:j]


class DirectAuthorityContractTests(unittest.TestCase):
    def test_orchestrator_registers_direct_authority_actions(self):
        src=text("core/krishna_core/orchestrator.py")
        for action in (
            "software_factory.workers.approve",
            "gyan.archive.restore",
            "gyan.archive.remove_original",
        ):
            self.assertIn(f'"{action}"',src)

    def test_worker_approval_consumes_exact_lease(self):
        src=text("core/krishna_core/orchestrator.py")
        section=block(src,"    def request_ephemeral_workers(self,", "    def run_ephemeral_workers(self,")
        self.assertIn("authority_lease=None",section)
        self.assertIn('action="software_factory.workers.approve"',section)
        self.assertIn("self.authority.consume(",section)
        self.assertLess(section.index("self.authority.consume("),section.index("self.software_factory.worker_request"))

    def test_gyan_destructive_archive_and_restore_consume_lease(self):
        src=text("core/krishna_core/orchestrator.py")
        archive=block(src,"    def gyan_archive_file(self,", "    def gyan_restore_file(self,")
        restore=block(src,"    def gyan_restore_file(self,", "    def gyan_archive_status(self,")
        self.assertIn('action="gyan.archive.remove_original"',archive)
        self.assertIn("authority_lease=None",archive)
        self.assertIn('action="gyan.archive.restore"',restore)
        self.assertIn("authority_lease=None",restore)
        self.assertIn("approved=True",restore)
        self.assertLess(restore.index("self.authority.consume("),restore.index("approved=True"))

    def test_development_wrappers_forward_authority_lease(self):
        src=text("core/krishna_core/orchestrator.py")
        for name in ("development_commit","development_push","development_sync"):
            section=block(src,f"    def {name}(self,","\n    def ")
            self.assertIn("authority_lease=None",section,name)
            self.assertIn("authority_lease=authority_lease",section,name)

    def test_authority_request_allows_only_registered_bus_or_direct_actions(self):
        src=text("core/krishna_core/server.py")
        section=block(src,'        if post_path == "/api/authority/lease/request":','        if post_path == "/api/authority/lease/decide":')
        self.assertIn("orch.action_bus.list()",section)
        self.assertIn("direct_authority_actions",section)
        self.assertIn("authority action not registered",section)

    def test_direct_http_routes_forward_lease(self):
        src=text("core/krishna_core/server.py")
        routes=(
            "/api/software-factory/workers/approve",
            "/api/development/git/commit",
            "/api/development/git/push",
            "/api/development/sync",
            "/api/gyan-bhandar/archive",
            "/api/gyan-bhandar/archive/restore",
        )
        for route in routes:
            marker=f'        if post_path == "{route}":'
            self.assertIn(marker,src,route)
            section=block(src,marker,"\n        if post_path == ")
            self.assertIn("authority_lease",section,route)

    def test_known_boolean_only_server_calls_are_gone(self):
        src=text("core/krishna_core/server.py")
        forbidden=(
            'orch.development_push(project,bool(data.get("approved",False))))',
            'orch.development_sync(project,bool(data.get("approved",False))))',
            'orch.gyan_restore_file(digest,destination,project,bool(data.get("approved",False))))',
        )
        for needle in forbidden:
            self.assertNotIn(needle,src)


if __name__ == "__main__":
    unittest.main()
