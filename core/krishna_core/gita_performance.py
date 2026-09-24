from __future__ import annotations

from copy import deepcopy


class GitaPerformanceEngine:
    """Deterministic verse -> KRISHNA performance compiler.

    This class never rewrites scripture.  It derives behavioral/rendering metadata
    from the canonical Gita corpus, chapter context and a small set of explicit
    high-priority overrides.  Animation choices are labelled as design decisions
    rather than historical/scriptural facts.
    """

    VERSION = "gita-performance-v1"

    FAMILIES = (
        "BATTLEFIELD_CHARIOTEER",
        "SMILING_TEACHER",
        "COMPASSIONATE_GUIDE",
        "DHARMA_TEACHER",
        "KARMA_YOGA_TEACHER",
        "DHYANA_KRISHNA",
        "BHAKTI_KRISHNA",
        "DIVINE_REVEALER",
        "ROYAL_KRISHNA",
        "PROTECTOR_KRISHNA",
        "VISHVARUPA_TRANSITION",
        "VISHVARUPA",
        "REASSURING_PERSONAL_FORM",
        "VRINDAVAN_KRISHNA",
        "FLUTE_KRISHNA",
        "SILENT_WISDOM",
        "FIRM_COUNSEL",
        "LOVING_COUNSEL",
        "CLOSING_COUNSEL",
    )

    SCENES = (
        "KURUKSHETRA_CHARIOT",
        "BATTLEFIELD_WIDE",
        "BATTLEFIELD_INTIMATE",
        "VRINDAVAN_FOREST",
        "YAMUNA",
        "MEDITATION_SPACE",
        "DIVINE_LIGHT",
        "COSMIC_VISHVARUPA",
        "ROYAL_DVARAKA",
        "NEUTRAL_CONVERSATION",
    )

    CAMERAS = (
        "CLOSE_COUNSEL",
        "FACE_TEACHING",
        "HALF_BODY_TEACHING",
        "PARTHA_POV",
        "CHARIOT_TWO_SHOT",
        "BATTLEFIELD_WIDE",
        "DEVOTIONAL_CLOSEUP",
        "COSMIC_REVEAL",
        "RETURN_TO_HUMAN_FORM",
    )

    REQUIRED_FIELDS = (
        "chapter", "verse", "verse_id", "sanskrit", "transliteration",
        "meaning_or", "meaning_hi", "meaning_en", "theme", "secondary_themes",
        "emotional_context", "krishna_form", "avatar_family", "face_expression",
        "eye_expression", "brow_expression", "smile_level", "head_pose",
        "body_pose", "left_hand_gesture", "right_hand_gesture",
        "movement_intensity", "camera_profile", "lighting_profile",
        "background_profile", "aura_profile", "prop_profile", "voice_profile",
        "recitation_profile", "pause_profile", "explanation_profile",
        "partha_dialogue_profile", "scriptural_evidence", "confidence",
        "manual_override",
    )

    CHAPTER_ARCS = {
        1: ("Partha's crisis; Krishna listens with protective calm.", "BATTLEFIELD_CHARIOTEER", "crisis_and_listening"),
        2: ("Teacher awakening; composed, compassionate instruction.", "DHARMA_TEACHER", "self_knowledge_and_steadiness"),
        3: ("Disciplined action and duty.", "KARMA_YOGA_TEACHER", "karma_yoga"),
        4: ("Knowledge, action and divine teaching lineage.", "DIVINE_REVEALER", "knowledge_and_action"),
        5: ("Renunciation integrated with action.", "KARMA_YOGA_TEACHER", "renunciation_and_action"),
        6: ("Meditation, self-mastery and returning the mind.", "DHYANA_KRISHNA", "meditation_and_self_mastery"),
        7: ("Knowledge of Krishna and the nature of reality.", "DIVINE_REVEALER", "divine_knowledge"),
        8: ("Remembrance, impermanence and the supreme destination.", "DIVINE_REVEALER", "remembrance_and_destination"),
        9: ("Royal knowledge, devotion and divine immanence.", "ROYAL_KRISHNA", "royal_knowledge_and_devotion"),
        10: ("Divine manifestations and growing majesty.", "DIVINE_REVEALER", "divine_manifestations"),
        11: ("Universal-form revelation and return to reassurance.", "VISHVARUPA_TRANSITION", "universal_form"),
        12: ("Bhakti; warmer face, softer eyes and loving counsel.", "BHAKTI_KRISHNA", "devotion"),
        13: ("Field/knower discrimination.", "DHARMA_TEACHER", "field_and_knower"),
        14: ("Three gunas and discrimination.", "DHARMA_TEACHER", "three_gunas"),
        15: ("Supreme person and the living being's relation to the divine.", "DIVINE_REVEALER", "supreme_person"),
        16: ("Divine and destructive qualities.", "FIRM_COUNSEL", "ethical_qualities"),
        17: ("Faith, discipline and discernment.", "DHARMA_TEACHER", "faith_and_discernment"),
        18: ("Synthesis, intimate final guidance and preserved agency.", "CLOSING_COUNSEL", "synthesis_and_choice"),
    }

    FAMILY_PROFILE = {
        "BATTLEFIELD_CHARIOTEER": dict(face_expression="protective calm", eye_expression="attentive gaze toward Partha", brow_expression="relaxed attentive", smile_level=0.05, head_pose="slight orientation toward Partha", body_pose="stable charioteer posture", left_hand_gesture="rest/reins", right_hand_gesture="minimal", movement_intensity="low", camera_profile="CHARIOT_TWO_SHOT", lighting_profile="natural_battlefield_soft", background_profile="KURUKSHETRA_CHARIOT", aura_profile="subtle", prop_profile="chariot_reins", voice_profile="KRISHNA_TO_PARTHA: calm listener"),
        "SMILING_TEACHER": dict(face_expression="small composed reassuring smile", eye_expression="direct compassionate", brow_expression="soft composed", smile_level=0.22, head_pose="centered with slight compassionate tilt", body_pose="stable seated charioteer teaching posture", left_hand_gesture="minimal", right_hand_gesture="small opening teaching gesture", movement_intensity="low", camera_profile="FACE_TEACHING", lighting_profile="warm_natural", background_profile="BATTLEFIELD_INTIMATE", aura_profile="subtle", prop_profile="chariot_reins", voice_profile="GITA_EXPLANATION: soft opening then clear teaching"),
        "COMPASSIONATE_GUIDE": dict(face_expression="gentle concern", eye_expression="compassionate steady", brow_expression="softened", smile_level=0.08, head_pose="slight reassuring tilt", body_pose="open grounded posture", left_hand_gesture="rest", right_hand_gesture="gentle reassurance", movement_intensity="low", camera_profile="CLOSE_COUNSEL", lighting_profile="soft_warm", background_profile="BATTLEFIELD_INTIMATE", aura_profile="subtle", prop_profile="none", voice_profile="KRISHNA_TO_PARTHA: compassionate and composed"),
        "DHARMA_TEACHER": dict(face_expression="calm serious warmth", eye_expression="steady teaching gaze", brow_expression="composed", smile_level=0.08, head_pose="centered", body_pose="upright relaxed teaching posture", left_hand_gesture="rest", right_hand_gesture="controlled explanatory gesture", movement_intensity="low", camera_profile="HALF_BODY_TEACHING", lighting_profile="clear_neutral", background_profile="BATTLEFIELD_INTIMATE", aura_profile="subtle", prop_profile="chariot_reins", voice_profile="GITA_EXPLANATION: measured teacher"),
        "KARMA_YOGA_TEACHER": dict(face_expression="composed", eye_expression="steady", brow_expression="focused calm", smile_level=0.04, head_pose="centered", body_pose="upright grounded", left_hand_gesture="rest", right_hand_gesture="controlled explanatory hand", movement_intensity="low", camera_profile="HALF_BODY_TEACHING", lighting_profile="clear_neutral", background_profile="BATTLEFIELD_INTIMATE", aura_profile="subtle", prop_profile="chariot_reins", voice_profile="GITA_EXPLANATION: clear and firm, not severe"),
        "DHYANA_KRISHNA": dict(face_expression="deep serenity", eye_expression="soft focused", brow_expression="fully relaxed", smile_level=0.04, head_pose="still centered", body_pose="aligned meditative teaching posture", left_hand_gesture="rest/mudra", right_hand_gesture="small teaching mudra", movement_intensity="very_low", camera_profile="DEVOTIONAL_CLOSEUP", lighting_profile="soft_meditative", background_profile="MEDITATION_SPACE", aura_profile="low", prop_profile="none", voice_profile="GITA_EXPLANATION: slow, quiet, measured"),
        "BHAKTI_KRISHNA": dict(face_expression="warm gentle", eye_expression="affectionate smiling eyes", brow_expression="soft", smile_level=0.16, head_pose="gentle conversational tilt", body_pose="open relaxed", left_hand_gesture="rest", right_hand_gesture="soft welcoming gesture", movement_intensity="low", camera_profile="DEVOTIONAL_CLOSEUP", lighting_profile="warm_devotional", background_profile="DIVINE_LIGHT", aura_profile="low", prop_profile="none", voice_profile="GITA_EXPLANATION: warm, clear, devotional without theatrics"),
        "DIVINE_REVEALER": dict(face_expression="serene majesty", eye_expression="steady luminous focus", brow_expression="calm", smile_level=0.05, head_pose="centered", body_pose="upright composed", left_hand_gesture="rest", right_hand_gesture="measured revelation gesture", movement_intensity="low", camera_profile="HALF_BODY_TEACHING", lighting_profile="divine_soft", background_profile="DIVINE_LIGHT", aura_profile="medium", prop_profile="none", voice_profile="GITA_EXPLANATION: quiet authority"),
        "ROYAL_KRISHNA": dict(face_expression="serene confidence", eye_expression="direct composed", brow_expression="calm", smile_level=0.08, head_pose="centered", body_pose="dignified relaxed", left_hand_gesture="rest", right_hand_gesture="measured teaching gesture", movement_intensity="low", camera_profile="HALF_BODY_TEACHING", lighting_profile="royal_soft", background_profile="DIVINE_LIGHT", aura_profile="medium", prop_profile="none", voice_profile="GITA_EXPLANATION: dignified and intimate"),
        "PROTECTOR_KRISHNA": dict(face_expression="calm serious reassurance", eye_expression="firm protective", brow_expression="focused", smile_level=0.0, head_pose="centered", body_pose="stable protective", left_hand_gesture="rest", right_hand_gesture="open protective emphasis", movement_intensity="low", camera_profile="CLOSE_COUNSEL", lighting_profile="clear_neutral", background_profile="BATTLEFIELD_INTIMATE", aura_profile="low", prop_profile="none", voice_profile="KRISHNA_TO_PARTHA: firm but controlled"),
        "VISHVARUPA_TRANSITION": dict(face_expression="familiar form becoming transcendent", eye_expression="expanding nonordinary focus", brow_expression="neutral", smile_level=0.0, head_pose="centered", body_pose="transition from personal form", left_hand_gesture="transition", right_hand_gesture="transition", movement_intensity="medium", camera_profile="COSMIC_REVEAL", lighting_profile="growing_cosmic", background_profile="COSMIC_VISHVARUPA", aura_profile="rising", prop_profile="none", voice_profile="SHLOKA_RECITATION: spacious controlled"),
        "VISHVARUPA": dict(face_expression="cosmic/nonordinary; no familiar cheerful softness", eye_expression="cosmic rendering", brow_expression="nonordinary", smile_level=0.0, head_pose="cosmic", body_pose="vast multi-scale cosmic presence", left_hand_gesture="cosmic", right_hand_gesture="cosmic", movement_intensity="controlled_high", camera_profile="COSMIC_REVEAL", lighting_profile="cosmic_high_dynamic_range", background_profile="COSMIC_VISHVARUPA", aura_profile="high", prop_profile="cosmic_symbolism_only", voice_profile="SHLOKA_RECITATION: deep spatial controlled pacing"),
        "REASSURING_PERSONAL_FORM": dict(face_expression="beautiful reassuring personal form", eye_expression="compassionate direct", brow_expression="soft", smile_level=0.10, head_pose="gentle return to eye level", body_pose="normal two-armed composed form", left_hand_gesture="rest", right_hand_gesture="reassuring open hand", movement_intensity="very_low", camera_profile="RETURN_TO_HUMAN_FORM", lighting_profile="rapidly_softening_warm", background_profile="BATTLEFIELD_INTIMATE", aura_profile="low", prop_profile="none", voice_profile="KRISHNA_TO_PARTHA: soft calming"),
        "VRINDAVAN_KRISHNA": dict(face_expression="peaceful warmth", eye_expression="soft", brow_expression="relaxed", smile_level=0.12, head_pose="graceful", body_pose="graceful standing", left_hand_gesture="contextual", right_hand_gesture="contextual", movement_intensity="low", camera_profile="DEVOTIONAL_CLOSEUP", lighting_profile="soft_natural", background_profile="VRINDAVAN_FOREST", aura_profile="subtle", prop_profile="flute_contextual", voice_profile="KRISHNA_TO_PARTHA: warm"),
        "FLUTE_KRISHNA": dict(face_expression="peaceful joy", eye_expression="soft", brow_expression="relaxed", smile_level=0.12, head_pose="graceful", body_pose="Venugopala-inspired graceful stance", left_hand_gesture="flute hold", right_hand_gesture="flute hold", movement_intensity="very_low", camera_profile="DEVOTIONAL_CLOSEUP", lighting_profile="soft_natural", background_profile="VRINDAVAN_FOREST", aura_profile="subtle", prop_profile="flute", voice_profile="silent unless conversation resumes"),
        "SILENT_WISDOM": dict(face_expression="serene attentive", eye_expression="steady reflective", brow_expression="relaxed", smile_level=0.03, head_pose="centered", body_pose="still grounded", left_hand_gesture="rest", right_hand_gesture="minimal", movement_intensity="very_low", camera_profile="FACE_TEACHING", lighting_profile="clear_neutral", background_profile="BATTLEFIELD_INTIMATE", aura_profile="subtle", prop_profile="none", voice_profile="GITA_EXPLANATION: measured with longer pauses"),
        "FIRM_COUNSEL": dict(face_expression="serious composed", eye_expression="firm focused", brow_expression="focused", smile_level=0.0, head_pose="centered", body_pose="centered upright", left_hand_gesture="rest", right_hand_gesture="deliberate emphasis", movement_intensity="low", camera_profile="CLOSE_COUNSEL", lighting_profile="clear_neutral", background_profile="BATTLEFIELD_INTIMATE", aura_profile="subtle", prop_profile="none", voice_profile="GITA_EXPLANATION: firm dharma, never aggressive"),
        "LOVING_COUNSEL": dict(face_expression="serious warmth", eye_expression="warm direct", brow_expression="soft", smile_level=0.08, head_pose="gentle", body_pose="open steady", left_hand_gesture="rest", right_hand_gesture="gentle emphasis", movement_intensity="very_low", camera_profile="CLOSE_COUNSEL", lighting_profile="warm_soft", background_profile="BATTLEFIELD_INTIMATE", aura_profile="subtle", prop_profile="none", voice_profile="KRISHNA_TO_PARTHA: intimate but dignified"),
        "CLOSING_COUNSEL": dict(face_expression="calm serious warmth", eye_expression="steady intimate focus", brow_expression="composed", smile_level=0.04, head_pose="centered", body_pose="steady", left_hand_gesture="rest", right_hand_gesture="minimal deliberate emphasis", movement_intensity="very_low", camera_profile="CLOSE_COUNSEL", lighting_profile="warm_clear", background_profile="BATTLEFIELD_INTIMATE", aura_profile="subtle", prop_profile="none", voice_profile="KRISHNA_TO_PARTHA: quiet authority preserving Partha's agency"),
    }

    def __init__(self, gita):
        self.gita = gita

    @staticmethod
    def _id(chapter: int, verse: int) -> str:
        return f"{int(chapter)}.{int(verse)}"

    def _family(self, chapter: int, verse: int) -> tuple[str, bool]:
        c, v = int(chapter), int(verse)
        if (c, v) == (2, 10):
            return "SMILING_TEACHER", True
        if (c, v) in {(2, 47), (2, 48), (3, 19)}:
            return "KARMA_YOGA_TEACHER", True
        if c == 2 and 55 <= v <= 72:
            return "SILENT_WISDOM", True
        if (c, v) in {(6, 5), (6, 6), (6, 26)}:
            return "DHYANA_KRISHNA", True
        if c == 11 and 8 <= v <= 49:
            return "VISHVARUPA", True
        if c == 11 and v in {50, 51}:
            return "REASSURING_PERSONAL_FORM", True
        if c == 12 and 13 <= v <= 20:
            return "LOVING_COUNSEL", True
        if (c, v) in {(18, 61), (18, 63), (18, 65), (18, 66)}:
            return "CLOSING_COUNSEL", True
        arc = self.CHAPTER_ARCS[c]
        return arc[1], False

    def _theme(self, chapter: int, verse: int) -> tuple[str, list[str]]:
        c, v = int(chapter), int(verse)
        exact = {
            (2, 7): ("seeking guidance", ["confusion", "discernment"]),
            (2, 10): ("compassionate beginning of instruction", ["grief", "teaching"]),
            (2, 13): ("continuity through bodily change", ["self", "change"]),
            (2, 14): ("enduring changing sensations", ["steadiness", "duality"]),
            (2, 20): ("the unborn and undying self", ["self", "death"]),
            (2, 47): ("action without attachment to results", ["work", "duty", "nonattachment"]),
            (2, 48): ("equanimity in action", ["work", "balance"]),
            (3, 19): ("duty without attachment", ["work", "discipline"]),
            (4, 7): ("dharma and divine manifestation", ["dharma", "decline"]),
            (4, 8): ("protection and restoration of dharma", ["dharma", "protection"]),
            (4, 34): ("learning through inquiry and humility", ["teacher", "knowledge"]),
            (6, 5): ("self-elevation", ["mind", "self-mastery"]),
            (6, 6): ("mind as friend or obstacle", ["mind", "self-mastery"]),
            (6, 26): ("returning the wandering mind", ["meditation", "attention"]),
            (7, 7): ("dependence of all on the divine", ["divine_nature"]),
            (8, 5): ("remembrance at death", ["remembrance", "death"]),
            (9, 22): ("single-minded devotion", ["devotion", "trust"]),
            (9, 26): ("simple devotional offering", ["devotion", "offering"]),
            (10, 8): ("source of all", ["divine_nature"]),
            (10, 20): ("indwelling self", ["self", "divine_nature"]),
            (10, 41): ("splendor as a manifestation", ["divine_manifestations"]),
            (11, 32): ("time and destruction in the universal form", ["time", "cosmic_scale"]),
            (15, 7): ("living being as an enduring portion", ["self", "divine_relation"]),
            (18, 61): ("the divine present in the heart", ["agency", "divine_presence"]),
            (18, 63): ("reflect fully and choose", ["agency", "discernment"]),
            (18, 65): ("loving remembrance and devotion", ["devotion", "relationship"]),
            (18, 66): ("final surrender teaching", ["surrender", "trust"]),
        }
        if (c, v) in exact:
            return exact[(c, v)]
        base = self.CHAPTER_ARCS[c][2]
        return base.replace("_", " "), [base]

    def _evidence(self, chapter: int, verse: int, source: dict | None, family: str) -> list[dict]:
        ref = self._id(chapter, verse)
        evidence = [{
            "kind": "TEXTUAL_FACT",
            "reference": f"Bhagavad Gita {ref}",
            "detail": "Canonical Sanskrit and verse reference come from the pinned local corpus.",
            "source": dict(source or {}),
        }]
        special = {
            (2, 10): ("TEXTUAL_FACT", "Bhagavad Gita 2.10", "The verse explicitly describes Krishna as prahasann iva before speaking."),
            (11, 50): ("TEXTUAL_FACT", "Bhagavad Gita 11.50", "The passage describes return to Krishna's own gentle form and reassurance."),
            (11, 51): ("TEXTUAL_FACT", "Bhagavad Gita 11.51", "Partha reports restored composure after seeing the gentle humanlike form."),
            (18, 63): ("TEXTUAL_FACT", "Bhagavad Gita 18.63", "Krishna asks the listener to reflect fully and then act as chosen."),
        }
        if (chapter, verse) in special:
            kind, reference, detail = special[(chapter, verse)]
            evidence.append({"kind": kind, "reference": reference, "detail": detail})
        evidence.append({
            "kind": "ANIMATION_DESIGN_DECISION",
            "reference": f"KRISHNA {self.VERSION}",
            "detail": f"{family} maps textual/chapter context into restrained animation; it is not claimed as historically exact movement.",
        })
        return evidence

    def record(self, chapter: int, verse: int) -> dict:
        row = self.gita.verse(chapter, verse)
        c, v = int(row["chapter"]), int(row["verse"])
        family, manual = self._family(c, v)
        profile = deepcopy(self.FAMILY_PROFILE[family])
        theme, secondary = self._theme(c, v)
        arc = self.CHAPTER_ARCS[c][0]
        krishna_form = "vishvarupa_cosmic" if family == "VISHVARUPA" else (
            "personal_form_return" if family == "REASSURING_PERSONAL_FORM" else "personal_two_armed"
        )
        recitation = {
            "mode": "SHLOKA_RECITATION",
            "language": "sa",
            "tempo": "slow_controlled",
            "melodic": False,
            "preserve_sanskrit": True,
        }
        pause = {
            "after_sanskrit_ms": 850 if family != "VISHVARUPA" else 1200,
            "between_ideas": "measured",
        }
        explanation = {
            "mode": "GITA_EXPLANATION",
            "default_language": "or",
            "available_languages": ["or", "hi", "en"],
            "separate_literal_traditional_practical": True,
            "preserve_interpretive_differences": True,
        }
        partha = {
            "mode": "KRISHNA_TO_PARTHA",
            "address": "Partha",
            "natural_not_every_sentence": True,
            "preserve_agency": True,
            "forbidden_direct_addresses": ["Arjuna", "Arjun", "Sir", "Boss", "Master"],
        }
        return {
            "chapter": c,
            "verse": v,
            "verse_id": self._id(c, v),
            "sanskrit": row["sanskrit"],
            "transliteration": row.get("transliteration"),
            "meaning_or": row.get("meaning_or"),
            "meaning_hi": row.get("meaning_hi"),
            "meaning_en": row.get("summary_en") or row.get("meaning_en"),
            "theme": theme,
            "secondary_themes": list(secondary),
            "emotional_context": arc,
            "krishna_form": krishna_form,
            "avatar_family": family,
            **profile,
            "recitation_profile": recitation,
            "pause_profile": pause,
            "explanation_profile": explanation,
            "partha_dialogue_profile": partha,
            "scriptural_evidence": self._evidence(c, v, row.get("source"), family),
            "confidence": {
                "scripture_identity": "high",
                "chapter_arc": "high",
                "verse_specific_animation": "high" if manual else "derived",
            },
            "manual_override": bool(manual),
            "chapter_arc": arc,
        }

    def all_records(self) -> list[dict]:
        return [self.record(row["chapter"], row["verse"]) for row in self.gita._load_corpus()]

    def validate_record(self, record: dict) -> list[str]:
        errors = []
        for field in self.REQUIRED_FIELDS:
            if field not in record:
                errors.append("missing:" + field)
        family = record.get("avatar_family")
        if family not in self.FAMILIES:
            errors.append("invalid_avatar_family")
        if record.get("camera_profile") not in self.CAMERAS:
            errors.append("invalid_camera_profile")
        if record.get("background_profile") not in self.SCENES:
            errors.append("invalid_background_profile")
        if not str(record.get("sanskrit") or "").strip():
            errors.append("missing_sanskrit")
        c, v = int(record.get("chapter") or 0), int(record.get("verse") or 0)
        if family == "VISHVARUPA" and not (c == 11 and 8 <= v <= 49):
            errors.append("vishvarupa_outside_supported_passage")
        if c == 11 and v in {50, 51} and family != "REASSURING_PERSONAL_FORM":
            errors.append("missing_post_vishvarupa_return")
        if record.get("partha_dialogue_profile", {}).get("address") != "Partha":
            errors.append("owner_address_not_partha")
        return errors

    def qc_report(self) -> dict:
        records = self.all_records()
        failures = []
        refs = set()
        for record in records:
            ref = record["verse_id"]
            if ref in refs:
                failures.append({"verse_id": ref, "errors": ["duplicate_verse"]})
                continue
            refs.add(ref)
            errors = self.validate_record(record)
            if errors:
                failures.append({"verse_id": ref, "errors": errors})
        return {
            "version": self.VERSION,
            "record_count": len(records),
            "unique_verse_count": len(refs),
            "expected_verse_count": self.gita.EXPECTED_VERSE_COUNT,
            "valid": len(records) == self.gita.EXPECTED_VERSE_COUNT and not failures,
            "failures": failures[:100],
            "families": list(self.FAMILIES),
            "scenes": list(self.SCENES),
            "cameras": list(self.CAMERAS),
        }
