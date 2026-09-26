from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
MEM=(ROOT/"core"/"krishna_core"/"memory.py").read_text(encoding="utf-8")
ORCH=(ROOT/"core"/"krishna_core"/"orchestrator.py").read_text(encoding="utf-8")
SERVER=(ROOT/"core"/"krishna_core"/"server.py").read_text(encoding="utf-8")
WEB=(ROOT/"core"/"web_validation.html").read_text(encoding="utf-8")
class GyanAvatarContractTests(unittest.TestCase):
    def test_learning_schema_and_api(self):
        self.assertIn("CREATE TABLE IF NOT EXISTS learnings",MEM)
        self.assertIn("def learn(",MEM); self.assertIn("def learnings(",MEM)
        self.assertIn("GyanBhandarAgent",ORCH)
        self.assertIn('/api/gyan-bhandar',SERVER)
        self.assertIn('/api/gyan-bhandar/strengthen',SERVER)
    def test_krishna_remains_authority(self):
        g=(ROOT/"core"/"krishna_core"/"gyan_bhandar.py").read_text(encoding="utf-8")
        self.assertIn('"decision_authority":"KRISHNA"',g)
        self.assertIn('"auto_implementation":False',g)
        self.assertIn('"implementation_executor":"Sudarshan"',g)
    def test_private_avatar_is_local_route(self):
        self.assertIn('/api/avatar/status',SERVER)
        self.assertIn('/api/avatar.glb',SERVER)
        self.assertIn('dashboard" / "assets" / "avatar" / "krishna.glb"',SERVER)
        self.assertIn('id="krishnaModel"',WEB)
        self.assertIn("customElements.get('model-viewer')",WEB)
        self.assertIn("avatar.setAttribute('src','/api/avatar.glb')",WEB)
        self.assertNotIn('src="/api/avatar.glb"',WEB)
        self.assertNotIn('ajax.googleapis.com/ajax/libs/model-viewer',WEB)
    def test_pc_avatar_has_single_frame_animated_fallback(self):
        self.assertIn('id="avatarFallbackStrip"',WEB)
        self.assertIn('class="avatarFallbackStage"',WEB)
        self.assertIn('#avatarFallback .avatarFallbackStrip',WEB)
        self.assertIn('width:800%!important',WEB)
        self.assertIn('krishnaFallbackBreath',WEB)
        self.assertIn("frameMap={IDLE:0",WEB)
        self.assertIn("applyKrishnaAvatarMotion(next)",WEB)

    def test_frozen_exe_uses_private_e_drive_avatar_not_bundle(self):
        self.assertIn('AVATAR_GLB = RUNTIME_ROOT / "dashboard" / "assets" / "avatar" / "krishna.glb"',SERVER)
        self.assertIn('AVATAR_PRODUCTION_GLB = RUNTIME_ROOT / "dashboard" / "assets" / "avatar" / "krishna.production.glb"',SERVER)
        self.assertNotIn('_BUNDLE_ROOT / "avatar" / "krishna.glb"',SERVER)
        self.assertNotIn('_BUNDLE_ROOT / "avatar" / "krishna.production.glb"',SERVER)

    def test_gyan_ui_contract(self):
        self.assertIn('id="gyan"',WEB)
        self.assertIn('Gyan-Bhandar',WEB)
        self.assertIn('strengthenGyan()',WEB)
if __name__=="__main__":unittest.main()
