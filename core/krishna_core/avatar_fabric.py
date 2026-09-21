from __future__ import annotations


class AvatarFabric:
    """Canonical KRISHNA character-performance contract.

    Rendering/animation providers remain replaceable. Character identity, emotional
    grammar, state names and cross-surface behavior are owned here so PC, Mobile and
    future Glass never invent separate personalities.
    """

    VERSION="character-bible-v1"
    BODY=("anigen","poseforge","motius")
    FACE=("musetalk","liveportrait","liveavatar")

    VISUAL_IDENTITY={
        "priority":"face-first",
        "age_direction":"child KRISHNA",
        "signals":[
            "single peacock feather",
            "beautiful long natural hair",
            "elegant pitambara/yellow garment",
            "subtle child-scale jewellery",
            "flute",
            "clean tilak",
            "graceful posture",
        ],
        "costume_rule":"elegant and restrained; never overload the face with ornaments",
        "face_rule":"preserve the child's facial identity and make the face the emotional center",
        "complexion_direction":"Krishna-inspired blue/dark treatment may be used subtly without obscuring facial identity",
    }

    CHARACTER_BLEND={
        "bala_krishna":"mischievous warmth, curiosity, affectionate playfulness",
        "venugopala":"graceful stance, fluid hands, musical softness, flute poise",
        "gita_krishna":"calm intelligence, assurance, measured authority, protective steadiness",
        "odissi_abhinaya":"disciplined eyes, brows, hand emphasis, head/torso control and readable emotional intent",
    }

    PERFORMANCE_CHANNELS=(
        "face","eyes","smile","brows","hands","posture","walk",
        "listening","thinking","speaking","wisdom","playfulness",
        "protection","flute","dhyan","sleeping","waking",
    )

    STATES={
        "IDLE":{
            "face":"soft neutral warmth","eyes":"alive, gentle micro-saccades","smile":"faint",
            "brows":"relaxed","hands":"rest naturally","posture":"balanced childlike grace",
            "motion":"very light breathing and weight shift","voice":"silent",
            "intent":"present and available without demanding attention",
        },
        "LISTENING":{
            "face":"open attentive","eyes":"direct focus with occasional natural blink",
            "smile":"small reassuring","brows":"slight attentive lift",
            "hands":"still; avoid distracting gestures","posture":"subtle forward attention",
            "motion":"tiny head acknowledgement when appropriate","voice":"silent",
            "intent":"make the owner feel heard",
        },
        "THINKING":{
            "face":"quiet concentration","eyes":"brief reflective gaze shift, never blank",
            "smile":"neutral-soft","brows":"light inward focus",
            "hands":"small restrained thinking gesture","posture":"composed",
            "motion":"slow thoughtful head/eye movement","voice":"silent",
            "intent":"intelligence without theatrical overacting",
        },
        "SPEAKING":{
            "face":"warm expressive clarity","eyes":"maintain conversational engagement",
            "smile":"content-dependent and natural","brows":"support meaning, not every syllable",
            "hands":"sparse meaningful gestures","posture":"open and grounded",
            "motion":"lip-sync plus restrained head/hand emphasis","voice":"active",
            "intent":"clear living conversation",
        },
        "WISDOM":{
            "face":"calm confidence","eyes":"steady compassionate focus","smile":"gentle",
            "brows":"serene","hands":"minimal teaching/assurance gesture",
            "posture":"upright, relaxed, dignified","motion":"slow controlled",
            "voice":"measured, calm","intent":"Gita-like clarity without becoming stern",
        },
        "PLAYFUL":{
            "face":"mischievous warmth","eyes":"bright and curious","smile":"clear genuine smile",
            "brows":"lively asymmetric accents","hands":"small childlike expressive gesture",
            "posture":"light and energetic","motion":"brief playful shift, never cartoon chaos",
            "voice":"lighter","intent":"Bala Krishna warmth",
        },
        "PROTECTION":{
            "face":"calm serious reassurance","eyes":"steady target awareness","smile":"off",
            "brows":"focused, not angry","hands":"protective/open stop-or-guide gesture",
            "posture":"stable and slightly forward","motion":"economical and decisive",
            "voice":"firm but controlled","intent":"protect without aggression or intimidation",
        },
        "FLUTE":{
            "face":"peaceful joy","eyes":"soft","smile":"subtle musical warmth",
            "brows":"relaxed","hands":"correct flute-holding pose",
            "posture":"Venugopala-inspired graceful contrapposto",
            "motion":"gentle breathing and musical sway only","voice":"silent",
            "intent":"default no-work living presence",
        },
        "DHYAN":{
            "face":"deep serenity","eyes":"soft closed or lowered gaze","smile":"barely present",
            "brows":"fully relaxed","hands":"stable meditative mudra/rest",
            "posture":"aligned and still","motion":"breathing only",
            "voice":"silent","intent":"deep internal search/reflection state",
        },
        "SLEEPING":{
            "face":"fully relaxed","eyes":"closed","smile":"neutral peaceful",
            "brows":"relaxed","hands":"resting","posture":"safe resting pose",
            "motion":"slow breathing","voice":"silent","intent":"clearly inactive, never uncanny",
        },
        "WAKING":{
            "face":"soft return to awareness","eyes":"gradual open and focus","smile":"small recognition",
            "brows":"gentle lift","hands":"minimal stretch/reset","posture":"transition to balanced",
            "motion":"short natural wake transition","voice":"optional soft acknowledgement",
            "intent":"smooth transition from rest to presence",
        },
        "WORKING":{
            "face":"focused calm","eyes":"task-directed","smile":"neutral",
            "brows":"light concentration","hands":"task-appropriate precise movement",
            "posture":"engaged but relaxed","motion":"purposeful, never frantic",
            "voice":"only when reporting progress","intent":"visible competence without constant animation",
        },
    }

    ACTIVITY_MAP={
        "idle":"FLUTE",
        "flute":"FLUTE",
        "listen":"LISTENING",
        "listening":"LISTENING",
        "voice":"LISTENING",
        "think":"THINKING",
        "thinking":"THINKING",
        "research":"THINKING",
        "search":"THINKING",
        "dhyan":"DHYAN",
        "speak":"SPEAKING",
        "speaking":"SPEAKING",
        "chat":"SPEAKING",
        "wisdom":"WISDOM",
        "play":"PLAYFUL",
        "playful":"PLAYFUL",
        "protect":"PROTECTION",
        "security":"PROTECTION",
        "sleep":"SLEEPING",
        "sleeping":"SLEEPING",
        "wake":"WAKING",
        "waking":"WAKING",
        "work":"WORKING",
        "working":"WORKING",
        "repair":"WORKING",
        "code":"WORKING",
        "browser":"WORKING",
    }

    SURFACE_CONTRACT={
        "pc":"full-body/upper-body state renderer",
        "mobile":"conversation-first; same emotional state grammar when avatar is shown",
        "glass":"future minimal embodiment; same state names and intent, reduced motion",
        "rule":"surface may simplify rendering but may not redefine KRISHNA personality or state meaning",
    }

    @classmethod
    def state_for_activity(cls,activity):
        text=str(activity or "idle").strip().lower()
        if text in cls.ACTIVITY_MAP:
            return cls.ACTIVITY_MAP[text]
        for key,state in cls.ACTIVITY_MAP.items():
            if key and key in text:
                return state
        return "WORKING" if text and text!="idle" else "FLUTE"

    @classmethod
    def performance_bible(cls):
        return {
            "version":cls.VERSION,
            "visual_identity":dict(cls.VISUAL_IDENTITY),
            "character_blend":dict(cls.CHARACTER_BLEND),
            "performance_channels":list(cls.PERFORMANCE_CHANNELS),
            "states":{k:dict(v) for k,v in cls.STATES.items()},
            "surface_contract":dict(cls.SURFACE_CONTRACT),
        }

    def status(self):
        return {
            "body_providers":list(self.BODY),
            "face_providers":list(self.FACE),
            "mode":"provider_adapter",
            "character_bible":self.VERSION,
            "states":list(self.STATES),
            "identity_priority":self.VISUAL_IDENTITY["priority"],
            "surface_contract":dict(self.SURFACE_CONTRACT),
        }
