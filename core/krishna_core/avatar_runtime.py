from __future__ import annotations

from .avatar_fabric import AvatarFabric
from .lip_sync import KrishnaLipSyncPlanner


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

    GITA_FAMILY_STATE={
        "BATTLEFIELD_CHARIOTEER":"LISTENING",
        "SMILING_TEACHER":"WISDOM",
        "COMPASSIONATE_GUIDE":"WISDOM",
        "DHARMA_TEACHER":"WISDOM",
        "KARMA_YOGA_TEACHER":"WISDOM",
        "DHYANA_KRISHNA":"DHYAN",
        "BHAKTI_KRISHNA":"WISDOM",
        "DIVINE_REVEALER":"WISDOM",
        "ROYAL_KRISHNA":"WISDOM",
        "PROTECTOR_KRISHNA":"PROTECTION",
        "VISHVARUPA_TRANSITION":"WISDOM",
        "VISHVARUPA":"WISDOM",
        "REASSURING_PERSONAL_FORM":"WISDOM",
        "VRINDAVAN_KRISHNA":"FLUTE",
        "FLUTE_KRISHNA":"FLUTE",
        "SILENT_WISDOM":"WISDOM",
        "FIRM_COUNSEL":"WISDOM",
        "LOVING_COUNSEL":"WISDOM",
        "CLOSING_COUNSEL":"WISDOM",
    }

    def __init__(self):
        self.state="FLUTE"
        self.current_performance=None

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
            "current_performance":dict(self.current_performance) if self.current_performance else None,
        }

    def set_state(self,state,**params):
        state=str(state or "").strip().upper()
        if state not in self.STATE_ACTIONS:raise ValueError("unsupported avatar state")
        self.state=state
        return self.command(self.STATE_ACTIONS[state],**params)

    def for_activity(self,activity,**params):
        return self.set_state(AvatarFabric.state_for_activity(activity),**params)

    def apply_performance(self,performance):
        if not isinstance(performance,dict):
            raise ValueError("performance must be an object")
        family=str(performance.get("avatar_family") or "").strip().upper()
        if family not in self.GITA_FAMILY_STATE:
            raise ValueError("unsupported Gita avatar family")
        previous_family=(self.current_performance or {}).get("avatar_family")
        self.current_performance=dict(performance)
        base_state=self.GITA_FAMILY_STATE[family]
        command=self.set_state(
            base_state,
            source="gita-performance",
            performance_family=family,
            face_expression=performance.get("face_expression"),
            eye_expression=performance.get("eye_expression"),
            brow_expression=performance.get("brow_expression"),
            smile_level=performance.get("smile_level"),
            head_pose=performance.get("head_pose"),
            body_pose=performance.get("body_pose"),
            left_hand_gesture=performance.get("left_hand_gesture"),
            right_hand_gesture=performance.get("right_hand_gesture"),
            movement_intensity=performance.get("movement_intensity"),
            camera_profile=performance.get("camera_profile"),
            lighting_profile=performance.get("lighting_profile"),
            background_profile=performance.get("background_profile"),
            aura_profile=performance.get("aura_profile"),
            prop_profile=performance.get("prop_profile"),
        )
        command.update({
            "performance_family":family,
            "verse_id":performance.get("verse_id"),
            "renderer_mode":"cosmic_vishvarupa" if family=="VISHVARUPA" else "personal_krishna",
            "requires_cosmic_layer":family=="VISHVARUPA",
            "transition_from":previous_family,
            "transition_to":family,
            "performance":dict(performance),
        })
        return command

    def lip_sync(self,phonemes):
        self.state="SPEAKING"
        return {
            "action":"talk","state":"SPEAKING","phonemes":list(phonemes),
            "requires_rigged_glb":True,"requires_morph_targets":True,
            "required_channels":"Oculus visemes or provider-equivalent verified viseme mapping",
            "character_bible":AvatarFabric.VERSION,
            "current_performance":dict(self.current_performance) if self.current_performance else None,
        }

    def plan_lip_sync(self,text,language="or",mode="GITA_EXPLANATION"):
        """Build a truthful fallback viseme timeline for renderer consumption."""
        plan=KrishnaLipSyncPlanner.plan(text,language,mode)
        self.state="SPEAKING"
        return {
            "action":"talk","state":"SPEAKING",
            "lip_sync":plan,
            "requires_rigged_glb":True,
            "requires_morph_targets":True,
            "acoustic_alignment_verified":False,
            "character_bible":AvatarFabric.VERSION,
            "current_performance":dict(self.current_performance) if self.current_performance else None,
        }

    def status(self):
        return {
            "state":self.state,
            "states":sorted(self.STATE_ACTIONS),
            "actions":sorted(self.ALLOWED),
            "asset_policy":"commands may exist before the final asset, but body/facial animation is not VERIFIED until the GLB inspector passes",
            "character_bible":AvatarFabric.VERSION,
            "current_performance":dict(self.current_performance) if self.current_performance else None,
            "gita_family_states":dict(self.GITA_FAMILY_STATE),
        }
