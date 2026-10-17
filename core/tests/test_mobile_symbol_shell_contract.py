import unittest
from pathlib import Path


class MobileSymbolShellContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.realtime = (cls.root / "mobile_v3" / "realtime-client.js").read_text(encoding="utf-8")
        cls.index = (cls.root / "mobile_v3" / "index.html").read_text(encoding="utf-8")

    def test_main_quick_dock_is_hidden_by_symbol_shell(self):
        self.assertIn(".quickDock{display:none!important}", self.realtime)
        self.assertIn("krishnaTopSymbols", self.realtime)

    def test_required_top_symbols_exist(self):
        for marker in (
            "krishnaBackSymbol",
            "krishnaOmSymbol",
            "krishnaSudarshanSymbol",
            "krishnaBrahmandSymbol",
            "krishnaNotificationSymbol",
            "krishnaHawkeyeSymbol",
            "krishnaVoiceSymbol",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.realtime)

    def test_hawkeye_is_symbol_not_removed_capability(self):
        self.assertIn("startFieldScan", self.realtime)
        self.assertIn("krishnaHawkeyeSymbol", self.realtime)
        self.assertIn('id="cameraLayer"', self.index)

    def test_sudarshan_has_permanent_rooms(self):
        for room in (
            "KRISHNA",
            "Meetings",
            "Projects",
            "Tasks",
            "Hawkeye",
            "Brahmand",
            "Notifications",
        ):
            with self.subTest(room=room):
                self.assertIn(room, self.realtime)
        self.assertIn("createThread", self.realtime)
        self.assertIn("newChat", self.realtime)

    def test_realtime_events_become_chat_messages_and_unread_badges(self):
        self.assertIn("window.onSudarshanRealtimeEvent", self.realtime)
        self.assertIn("ingestEvent", self.realtime)
        self.assertIn("symbolBadge", self.realtime)
        self.assertIn("unreadNotifications", self.realtime)
        self.assertIn("notifications','event'", self.realtime)

    def test_hawkeye_sits_next_to_notifications_in_top_bar(self):
        notice = self.realtime.index("const notice=this.symbol('krishnaNotificationSymbol'")
        hawkeye = self.realtime.index("const hawkeye=this.symbol('krishnaHawkeyeSymbol'")
        voice = self.realtime.index("const voice=this.symbol('krishnaVoiceSymbol'")
        append = self.realtime.index("bar.append(notice,hawkeye,voice)")
        self.assertLess(notice, hawkeye)
        self.assertLess(hawkeye, voice)
        self.assertGreater(append, voice)

    def test_brahmand_is_single_pipeline_surface(self):
        self.assertIn("BRAHMAND · PC PIPELINE", self.realtime)
        for capability in (
            "BRAHMAGYAN",
            "SUDARSHAN",
            "RISHI COUNCIL",
            "NARAD",
            "GARUDA / GARUDANETRA",
            "KABACH",
            "MRITYUNJAY",
            "PROJECT / JOB PIPELINE",
            "HAWKEYE SYNC",
        ):
            with self.subTest(capability=capability):
                self.assertIn(capability, self.realtime)

    def test_hotword_platform_limitation_is_not_injected_into_main_chat(self):
        self.assertIn("continuous\\s+hot\\s*-?word.*unavailable", self.realtime)
        self.assertIn("self.voiceNotice=value;return", self.realtime)

    def test_back_navigation_closes_layers_before_home(self):
        self.assertIn("back(){", self.realtime)
        self.assertIn("cameraLayer", self.realtime)
        self.assertIn("closeBrahmand", self.realtime)
        self.assertIn("showRoomList", self.realtime)
        self.assertIn("closeSudarshan", self.realtime)

    def test_existing_realtime_delivery_is_preserved(self):
        self.assertIn("class KrishnaRealtime", self.realtime)
        self.assertIn("resumeAsync", self.realtime)
        self.assertIn("this.onEvent?.(e)", self.realtime)
        self.assertIn("localStorage.setItem('krishna_seq'", self.realtime)


if __name__ == "__main__":
    unittest.main()
