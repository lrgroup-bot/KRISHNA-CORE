from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VersePerformance:
    performance_id: str
    family: str
    base_avatar_state: str
    face_expression: str
    eye_expression: str
    smile_level: str
    head_pose: str
    body_pose: str
    left_hand_gesture: str
    right_hand_gesture: str
    movement_intensity: str
    camera_profile: str
    lighting_profile: str
    background_profile: str
    aura_profile: str
    prop_profile: str
    voice_profile: str
    recitation_profile: str
    pause_profile: str

    def as_dict(self) -> dict:
        return dict(self.__dict__)


class GitaPerformanceEngine:
    """Deterministic verse -> KRISHNA performance mapping.

    There is one KRISHNA identity and 700 verse-specific performance records.
    The record is renderer-neutral. Visible skeletal/facial animation remains
    unverified until the private GLB passes the production rig/morph checks.
    """

    VERSION = "gita-performance-v1"

    FAMILY_DEFAULTS = {
        "BATTLEFIELD_CHARIOTEER": dict(
            base_avatar_state="LISTENING", face_expression="attentive calm",
            eye_expression="steady situational gaze", smile_level="off",
            body_pose="charioteer seated readiness", movement_intensity="low",
            camera_profile="CHARIOT_TWO_SHOT", lighting_profile="battlefield-natural",
            background_profile="KURUKSHETRA_CHARIOT", aura_profile="subtle",
            prop_profile="chariot-reins", voice_profile="quiet-attentive",
        ),
        "SMILING_TEACHER": dict(
            base_avatar_state="WISDOM", face_expression="calm reassuring warmth",
            eye_expression="direct compassionate focus", smile_level="small-composed",
            body_pose="upright relaxed teaching posture", movement_intensity="low",
            camera_profile="FACE_TEACHING", lighting_profile="warm-natural",
            background_profile="BATTLEFIELD_INTIMATE", aura_profile="soft",
            prop_profile="chariot-reins-resting", voice_profile="measured-teacher",
        ),
        "COMPASSIONATE_GUIDE": dict(
            base_avatar_state="WISDOM", face_expression="gentle concern",
            eye_expression="soft compassionate gaze", smile_level="minimal",
            body_pose="slight forward attention", movement_intensity="very-low",
            camera_profile="CLOSE_COUNSEL", lighting_profile="soft-warm",
            background_profile="BATTLEFIELD_INTIMATE", aura_profile="soft",
            prop_profile="none", voice_profile="soft-reassuring",
        ),
        "KARMA_YOGA_TEACHER": dict(
            base_avatar_state="WISDOM", face_expression="composed clarity",
            eye_expression="steady focused gaze", smile_level="faint",
            body_pose="open grounded teaching posture", movement_intensity="low",
            camera_profile="HALF_BODY_TEACHING", lighting_profile="clear-day",
            background_profile="KURUKSHETRA_CHARIOT", aura_profile="subtle",
            prop_profile="reins-and-open-hand", voice_profile="clear-firm",
        ),
        "MEDITATIVE_KRISHNA": dict(
            base_avatar_state="DHYAN", face_expression="deep serenity",
            eye_expression="soft lowered gaze", smile_level="barely-present",
            body_pose="aligned meditative stillness", movement_intensity="very-low",
            camera_profile="DEVOTIONAL_CLOSEUP", lighting_profile="cool-soft",
            background_profile="MEDITATION_SPACE", aura_profile="soft",
            prop_profile="none", voice_profile="slow-contemplative",
        ),
        "DIVINE_REVEALER": dict(
            base_avatar_state="WISDOM", face_expression="majestic calm",
            eye_expression="luminous steady focus", smile_level="subtle",
            body_pose="open authoritative teaching posture", movement_intensity="medium-low",
            camera_profile="HALF_BODY_TEACHING", lighting_profile="divine-gold",
            background_profile="DIVINE_LIGHT", aura_profile="medium",
            prop_profile="symbolic-divine", voice_profile="majestic-measured",
        ),
        "VISHVARUPA": dict(
            base_avatar_state="PROTECTION", face_expression="cosmic-nonordinary",
            eye_expression="cosmic-multiplicity", smile_level="off",
            body_pose="cosmic-expansion", movement_intensity="high-controlled",
            camera_profile="COSMIC_REVEAL", lighting_profile="cosmic-high-dynamic",
            background_profile="COSMIC_VISHVARUPA", aura_profile="maximum",
            prop_profile="cosmic-symbolic", voice_profile="deep-spatial",
        ),
        "REASSURING_PERSONAL_FORM": dict(
            base_avatar_state="WISDOM", face_expression="beautiful reassuring calm",
            eye_expression="compassionate direct gaze", smile_level="gentle",
            body_pose="relaxed personal form", movement_intensity="very-low",
            camera_profile="RETURN_TO_HUMAN_FORM", lighting_profile="soft-restored",
            background_profile="BATTLEFIELD_INTIMATE", aura_profile="low",
            prop_profile="none", voice_profile="soft-calming",
        ),
        "BHAKTI_KRISHNA": dict(
            base_avatar_state="WISDOM", face_expression="affectionate serenity",
            eye_expression="warm smiling eyes", smile_level="gentle",
            body_pose="graceful devotional openness", movement_intensity="low",
            camera_profile="DEVOTIONAL_CLOSEUP", lighting_profile="warm-devotional",
            background_profile="DIVINE_LIGHT", aura_profile="soft",
            prop_profile="flute-optional", voice_profile="warm-devotional",
        ),
        "WISDOM_TEACHER": dict(
            base_avatar_state="WISDOM", face_expression="serene intelligence",
            eye_expression="steady reflective focus", smile_level="faint",
            body_pose="upright balanced teaching posture", movement_intensity="low",
            camera_profile="FACE_TEACHING", lighting_profile="neutral-warm",
            background_profile="BATTLEFIELD_INTIMATE", aura_profile="subtle",
            prop_profile="none", voice_profile="measured-teacher",
        ),
        "CLOSING_COUNSEL": dict(
            base_avatar_state="WISDOM", face_expression="serious warmth",
            eye_expression="steady intimate focus", smile_level="minimal",
            body_pose="still centered counsel posture", movement_intensity="very-low",
            camera_profile="CLOSE_COUNSEL", lighting_profile="late-golden",
            background_profile="KURUKSHETRA_CHARIOT", aura_profile="soft",
            prop_profile="none", voice_profile="quiet-authority",
        ),
        "PROTECTOR_KRISHNA": dict(
            base_avatar_state="PROTECTION", face_expression="calm protective certainty",
            eye_expression="steady protective focus", smile_level="off",
            body_pose="stable protective posture", movement_intensity="low",
            camera_profile="CLOSE_COUNSEL", lighting_profile="warm-strong",
            background_profile="DIVINE_LIGHT", aura_profile="medium",
            prop_profile="open-palm-protection", voice_profile="firm-reassuring",
        ),
    }

    SPECIAL_FAMILY = {
        (2, 7): "COMPASSIONATE_GUIDE",
        (2, 10): "SMILING_TEACHER",
        (2, 47): "KARMA_YOGA_TEACHER",
        (11, 50): "REASSURING_PERSONAL_FORM",
        (11, 51): "REASSURING_PERSONAL_FORM",
        (18, 63): "CLOSING_COUNSEL",
        (18, 65): "BHAKTI_KRISHNA",
        (18, 66): "PROTECTOR_KRISHNA",
    }

    def family_for(self, chapter: int, verse: int) -> str:
        key=(int(chapter),int(verse))
        if key in self.SPECIAL_FAMILY:
            return self.SPECIAL_FAMILY[key]
        chapter, verse=key
        if chapter == 1:
            return "BATTLEFIELD_CHARIOTEER"
        if chapter == 2:
            return "SMILING_TEACHER"
        if chapter in (3,4,5):
            return "KARMA_YOGA_TEACHER"
        if chapter == 6:
            return "MEDITATIVE_KRISHNA"
        if chapter in (7,8,9,10):
            return "DIVINE_REVEALER"
        if chapter == 11:
            if 9 <= verse <= 49:
                return "VISHVARUPA"
            return "DIVINE_REVEALER"
        if chapter == 12:
            return "BHAKTI_KRISHNA"
        if chapter in (13,14,15,16,17):
            return "WISDOM_TEACHER"
        return "CLOSING_COUNSEL"

    def performance(self, chapter: int, verse: int) -> dict:
        chapter,verse=int(chapter),int(verse)
        family=self.family_for(chapter,verse)
        base=dict(self.FAMILY_DEFAULTS[family])
        variant=(chapter * 97 + verse * 31) % 7
        base.update({
            "performance_id":f"gita-{chapter:02d}-{verse:03d}",
            "family":family,
            "head_pose":("centered","slight-left","slight-right","gentle-incline")[variant % 4],
            "left_hand_gesture":("rest","open-explain","soft-assurance","teaching-mudra")[variant % 4],
            "right_hand_gesture":("rest","open-explain","precision-emphasis","protective-open-palm")[variant % 4],
            "recitation_profile":"sanskrit-controlled-clear",
            "pause_profile":("short-reflective","medium-reflective","verse-end-long")[variant % 3],
            "verse_variant":variant,
            "renderer_contract":{
                "one_identity":True,
                "requires_rigged_glb":True,
                "requires_morph_targets":True,
                "visible_animation_verified":False,
            },
        })
        return VersePerformance(
            performance_id=base["performance_id"],
            family=base["family"],
            base_avatar_state=base["base_avatar_state"],
            face_expression=base["face_expression"],
            eye_expression=base["eye_expression"],
            smile_level=base["smile_level"],
            head_pose=base["head_pose"],
            body_pose=base["body_pose"],
            left_hand_gesture=base["left_hand_gesture"],
            right_hand_gesture=base["right_hand_gesture"],
            movement_intensity=base["movement_intensity"],
            camera_profile=base["camera_profile"],
            lighting_profile=base["lighting_profile"],
            background_profile=base["background_profile"],
            aura_profile=base["aura_profile"],
            prop_profile=base["prop_profile"],
            voice_profile=base["voice_profile"],
            recitation_profile=base["recitation_profile"],
            pause_profile=base["pause_profile"],
        ).as_dict() | {
            "verse_variant":variant,
            "renderer_contract":base["renderer_contract"],
        }

    def records_for(self, verses) -> list[dict]:
        return [self.performance(row["chapter"],row["verse"]) for row in verses]

    def status(self, verses=None) -> dict:
        records=self.records_for(verses) if verses is not None else []
        return {
            "version":self.VERSION,
            "family_count":len(self.FAMILY_DEFAULTS),
            "record_count":len(records),
            "unique_performance_ids":len({x["performance_id"] for x in records}),
            "one_krishna_identity":True,
            "verse_specific_performance":True,
            "visible_animation_requires_verified_private_rig":True,
        }
