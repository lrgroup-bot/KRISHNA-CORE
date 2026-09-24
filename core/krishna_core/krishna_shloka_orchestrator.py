from __future__ import annotations

from .gita_performance import GitaPerformanceEngine


class KrishnaShlokaOrchestrator:
    """Coordinate scripture, continuous navigation, avatar intent and explanation."""

    VERSION="krishna-shloka-orchestrator-v1"

    def __init__(self,gita,avatar,explain=None):
        self.gita=gita
        self.avatar=avatar
        self.explain=explain
        self.performance_engine=GitaPerformanceEngine()

    def _explain(self,row,language,depth):
        if not self.explain:
            return None
        prompt=self.gita.lesson_prompt(row,language,depth)
        text=str(self.explain(prompt) or "").strip()
        return text or None

    def _present(self,row,language="or",depth="deep",include_explanation=True,session=None):
        language=str(language or "or").strip().lower()
        if language not in self.gita.LANGUAGES:
            raise ValueError("language must be one of: or, hi, en")
        performance=self.performance_engine.performance(row["chapter"],row["verse"])
        avatar=self.avatar.set_state(
            performance["base_avatar_state"],
            source="gita-session",
            performance_id=performance["performance_id"],
            performance_family=performance["family"],
        )
        explanation=self._explain(row,language,depth) if include_explanation else None
        speech_sequence=[
            {
                "kind":"shloka",
                "language":"sa",
                "text":row["sanskrit"],
                "voice_profile":"SHLOKA_RECITATION",
            }
        ]
        if explanation:
            speech_sequence.append({
                "kind":"explanation",
                "language":language,
                "text":explanation,
                "voice_profile":"KRISHNA_TO_PARTHA",
            })
        return {
            "reference":f"Bhagavad Gita {row['chapter']}.{row['verse']}",
            "chapter":row["chapter"],
            "verse":row["verse"],
            "sanskrit":row["sanskrit"],
            "transliteration":row.get("transliteration"),
            "trusted_summary_en":row.get("summary_en"),
            "source":row.get("source"),
            "language":language,
            "depth":depth,
            "explanation":explanation,
            "performance":performance,
            "avatar":avatar,
            "speech_sequence":speech_sequence,
            "session":session,
            "navigation":{
                "completion_required_for_next":False,
                "controls":["repeat","previous","next","forward","skip","goto"],
                "owner_controls_progression":True,
            },
        }

    def start(self,chapter=1,verse=1,language="or",depth="deep",include_explanation=True):
        state,row=self.gita.start_session(chapter,verse,language,depth)
        return self._present(row,language,depth,include_explanation,state)

    def control(self,action,count=1,chapter=None,verse=None,include_explanation=True):
        state,row=self.gita.navigate_session(action,count,chapter,verse)
        return self._present(
            row,
            state.get("language") or "or",
            state.get("depth") or "deep",
            include_explanation,
            state,
        )

    def goto(self,chapter,verse,language=None,depth=None,include_explanation=True):
        state=self.gita.session_status()
        if language or depth:
            self.gita.configure_session(language=language,depth=depth)
        state,row=self.gita.navigate_session("goto",1,chapter,verse)
        return self._present(
            row,
            language or state.get("language") or "or",
            depth or state.get("depth") or "deep",
            include_explanation,
            state,
        )

    def verse(self,chapter,verse,language="or",depth="deep",include_explanation=True):
        row=self.gita.verse(chapter,verse)
        return self._present(row,language,depth,include_explanation,self.gita.session_status())

    def performance(self,chapter,verse):
        row=self.gita.verse(chapter,verse)
        return {
            "reference":f"Bhagavad Gita {row['chapter']}.{row['verse']}",
            "performance":self.performance_engine.performance(row["chapter"],row["verse"]),
        }

    def status(self):
        return {
            "version":self.VERSION,
            "default_conversation_language":"or",
            "global_odia_default":True,
            "session":self.gita.session_status(),
            "performance":self.performance_engine.status(self.gita._load_corpus()),
        }
