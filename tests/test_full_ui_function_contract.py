import re
import unittest
from pathlib import Path


ROOT=Path(__file__).resolve().parents[1]
WEB=ROOT/"core"/"web_validation.html"
SERVER=ROOT/"core"/"krishna_core"/"server.py"


class FullUIFunctionContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html=WEB.read_text(encoding="utf-8")
        cls.server=SERVER.read_text(encoding="utf-8")
        cls.orchestrator=(ROOT/"core"/"krishna_core"/"orchestrator.py").read_text(encoding="utf-8")
        cls.functions=set(re.findall(r"(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(",cls.html))

    def test_every_textbox_select_and_textarea_is_wired(self):
        controls=re.findall(r"<(input|textarea|select)\b([^>]*)>",self.html,flags=re.I)
        missing_id=[]
        dead=[]
        for tag,attrs in controls:
            m=re.search(r'\bid="([^"]+)"',attrs)
            if not m:
                missing_id.append((tag,attrs[:120]))
                continue
            control_id=m.group(1)
            # A live control is referenced after its declaration or has an inline event.
            refs=len(re.findall(re.escape(control_id),self.html))
            inline=bool(re.search(r"\bon(?:input|change|keydown|keyup|click|submit)=",attrs,re.I))
            if refs<2 and not inline:
                dead.append(control_id)
        self.assertEqual(missing_id,[],missing_id)
        self.assertEqual(dead,[],dead)

    def test_every_inline_handler_calls_defined_function_or_browser_builtin(self):
        allowed={
            "preventDefault","stopPropagation","getElementById","click","focus",
            "confirm","alert","prompt","setTimeout","setInterval",
        }
        missing=[]
        handlers=re.findall(r'\bon(?:click|change|input|submit|keydown|keyup)="([^"]+)"',self.html,re.I)
        for handler in handlers:
            for fn in re.findall(r"(?<![.\w$])([A-Za-z_$][\w$]*)\s*\(",handler):
                if fn in {"if","for","while","switch"} or fn in allowed:
                    continue
                if fn not in self.functions:
                    missing.append((fn,handler))
        self.assertEqual(missing,[],missing)

    def test_project_and_chat_context_menus_are_live(self):
        for token in (
            "openProjectActionMenu","executeProjectMenuAction",
            "data-project-action","project.rename","project.unregister",
            "openChatActionMenu","executeChatMenuAction","data-chat-action",
            "renameCurrentChat","moveCurrentChat","deleteCurrentChat",
            "krishnaPinnedChats",
        ):
            self.assertIn(token,self.html)

    def test_every_req_endpoint_exists_in_core_server(self):
        endpoints=set()
        patterns=(
            r"\breq\(\s*['\"](/api/[^'\"?]+)",
            r"\bfetch\(\s*['\"](/api/[^'\"?]+)",
        )
        for pattern in patterns:
            endpoints.update(re.findall(pattern,self.html))
        missing=[ep for ep in sorted(endpoints) if ep not in self.server]
        self.assertEqual(missing,[],missing)

    def test_every_shared_action_called_by_ui_is_registered(self):
        actions=set(re.findall(r"actionReq\(\s*['\"]([^'\"]+)",self.html))
        registration_surface=self.server+"\n"+self.orchestrator
        missing=[action for action in sorted(actions)
                 if f'"{action}"' not in registration_surface and f"'{action}'" not in registration_surface]
        self.assertEqual(missing,[],missing)

    def test_current_owner_surface_and_language_controls(self):
        for token in (
            'data-krishna-ui="2026.09-current"',
            "MAIN MENU","KRISHNA","Sudarshan","MANIBHADRA","Plugins",
            'id="input"','id="krishnaPopupInput"','id="attachInput"',
            'value="en-IN"','value="hi-IN"','value="or-IN"',
        ):
            self.assertIn(token,self.html)
        main=re.search(r'(?s)<div class="section">MAIN MENU</div><div class="nav mainMenuNav">(.*?)</div>\s*<div class="sidebarWorkspace">',self.html)
        self.assertIsNotNone(main)
        menu=main.group(1)
        self.assertEqual(menu.count("<button"),4)
        self.assertNotIn("showView('workingGods')",menu)
        for forbidden in ("KABACH","Garuda","Garudanetra","BRAHMAGYAN","Gyan-Bhandar","NARAD","System"):
            self.assertNotIn(forbidden,menu)

    def test_manibhadra_owner_crm_surface_is_live(self):
        for token in (
            'id="manibhadra"',"MANIBHADRA","Needs your attention","Sales pipeline",
            "manibhadra.crm.dashboard","manibhadra.crm.records","manibhadra.ai.advice",
            "money.investment_scenario","loadManibhadraCRM","manibhadraAddLead",
            "manibhadraAddDeal","manibhadraScoutProduct",
        ):
            self.assertIn(token,self.html)

    def test_vanijya_sales_head_is_live_inside_manibhadra_not_main_menu(self):
        for token in (
            "RISHI VĀṆIJYA · Sales & Marketing Head",
            "Lead Researcher → SDR / Calling → Lead Qualifier",
            "vanijya.dashboard","vanijya.products.sync","vanijya.sales_cycle","vanijya.autopilot.tick",
            "loadVanijyaSales","vanijyaSyncProducts","vanijyaAutopilot","vanijyaSalesCycle",
        ):
            self.assertIn(token,self.html)
        main=re.search(r'(?s)<div class="section">MAIN MENU</div><div class="nav mainMenuNav">(.*?)</div>\s*<div class="sidebarWorkspace">',self.html)
        self.assertIsNotNone(main)
        self.assertEqual(main.group(1).count("<button"),4)
        self.assertNotIn("showView('vanijya')",main.group(1))

    def test_vanijya_backend_actions_are_registered(self):
        for action in (
            "vanijya.status","vanijya.dashboard","vanijya.health","vanijya.health.verify",
            "vanijya.manibhadra.request","vanijya.products.sync","vanijya.sales_cycle","vanijya.autopilot.tick",
            "vanijya.campaign.create","vanijya.hr.request","vanijya.hr.create","vanijya.hr.retire",
            "vanijya.outreach.decide","vanijya.lead.qualify","vanijya.reply.ingest",
            "vanijya.outbound.plan","vanijya.narad.workflow","vanijya.quote.create",
            "vanijya.payment.upi_request","vanijya.payment.verify",
            "manibhadra.expansion.status","manibhadra.expansion.plan",
        ):
            self.assertIn(f'"{action}"',self.orchestrator)

    def test_no_server_fallback_to_legacy_dashboard(self):
        self.assertNotIn("WEB_VALIDATION if WEB_VALIDATION.exists() else DASHBOARD",self.server)
        self.assertIn("stale KRISHNA desktop UI refused",self.server)


if __name__=="__main__":
    unittest.main()
