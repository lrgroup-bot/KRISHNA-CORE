from __future__ import annotations

from .avatar_fabric import AvatarFabric


class AvatarRuntime:
    """Provider-neutral animation command bus for KRISHNA's canonical character states.

    The runtime can express the complete state machine before a final rigged GLB is
    installed. Body/facial commands still declare their asset requirements so a
    fallback sprite can never be reported as production skeletal animation.
    """

    STATE_ACTIONS={
        "IDLE":"idle",
        "LISTENING":"listen",
        "THINKING":"think",
        "SPEAKING":"talk",
        "WISDOM":"wisdom",
        "PLAYFUL":"playful",
        "PROTECTION":"protection",
        "FLUTE":"flute",
        "DHYAN":"dhyan",
        "SLEEPING":"sleep",
        "WAKING":"wake",
        "WORKING":"work",
    }
    ALLOWED=set(STATE_ACTIONS.values())|{"walk","smile","wave"}
    BODY_ACTIONS={"walk","wave","flute","dhyan","sleep","wake","work","wisdom","playful","protection","idle","listen","think","talk"}
    FACE_ACTIONS={"smile","talk","listen","think","wisdom","playful","protection","flute","dhyan","sleep","wake","work","idle"}

    def __init__(self):
        self.state="FLUTE"

    def command(self,action,**params):
        action=str(action or "").strip().lower()
        if action not in self.ALLOWED:raise ValueError("unsupported avatar action")
        for state,mapped in self.STATE_ACTIONS.items():
            if mapped==action:self.state=state;break
        return {
            "action":action,
            "state":self.state,
            "params":params,
            "requires_rigged_glb":action in self.BODY_ACTIONS,
            "requires_morph_targets":action in self.FACE_ACTIONS,
            "character_bible":AvatarFabric.VERSION,
        }

    def set_state(self,state,**params):
        state=str(state or "").strip().upper()
        if state not in self.STATE_ACTIONS:raise ValueError("unsupported avatar state")
        self.state=state
        return self.command(self.STATE_ACTIONS[state],**params)

    def for_activity(self,activity,**params):
        return self.set_state(AvatarFabric.state_for_activity(activity),**params)

    def lip_sync(self,phonemes):
        self.state="SPEAKING"
        return {
            "action":"talk","state":"SPEAKING","phonemes":list(phonemes),
            "requires_rigged_glb":True,"requires_morph_targets":True,
            "required_channels":"Oculus visemes or provider-equivalent verified viseme mapping",
            "character_bible":AvatarFabric.VERSION,
        }

    def status(self):
        return {
            "state":self.state,
            "states":sorted(self.STATE_ACTIONS),
            "actions":sorted(self.ALLOWED),
            "asset_policy":"commands may exist before the final asset, but body/facial animation is not VERIFIED until the GLB inspector passes",
            "character_bible":AvatarFabric.VERSION,
        }
