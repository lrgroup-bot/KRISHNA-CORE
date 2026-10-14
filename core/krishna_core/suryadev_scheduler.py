from __future__ import annotations

"""SURYDEV logical-slot scheduler and adaptive media-learning policy."""

DEFAULT_LOGICAL_SLOTS=50
SLOT_KINDS=("api","text","document","repository","transcript","audio","video","rendered_web")

def media_speed_plan(*,speech_density=.5,technical_density=.5,visual_change=.5,
                     transcript_confidence=.8,evidence_criticality=.5):
    vals=[max(0,min(1,float(x))) for x in
          (speech_density,technical_density,visual_change,transcript_confidence,evidence_criticality)]
    speech,technical,visual,transcript,critical=vals
    complexity=.30*speech+.30*technical+.20*visual+.20*critical
    if transcript<.55 or critical>=.85 or complexity>=.78: speed=1.0
    elif complexity>=.60: speed=1.5
    elif complexity>=.42: speed=2.0
    elif complexity>=.25: speed=3.0
    else: speed=4.0
    return {
        "speed":speed,"sample_first":True,"adaptive":True,
        "rewind_on_low_confidence":True,"slow_critical_segments":True,
        "skip_policy":"skip only low-value/repetitive segments after transcript/index evidence",
        "rule":"maximize evidence throughput, never playback speed at the expense of comprehension",
    }

def slot_plan(*,requested=DEFAULT_LOGICAL_SLOTS,active=0,resource_decision=None,
              media_requested=0,media_cap=None):
    requested=max(0,int(requested));active=max(0,int(active))
    decision=dict(resource_decision or {})
    worker_target=max(0,int(decision.get("target_workers",requested)))
    logical=min(requested,worker_target)
    if media_cap is None: media_cap=max(1,logical//5) if logical else 0
    media=min(max(0,int(media_requested)),max(0,int(media_cap)),logical)
    return {
        "requested_slots":requested,"logical_slots":logical,"media_slots":media,
        "lightweight_slots":max(0,logical-media),"benchmark_target":DEFAULT_LOGICAL_SLOTS,
        "not_a_ceiling":True,
        "rule":"50 is a logical-session benchmark; actual rendered/video concurrency is measured and resource-governed",
    }

def source_adapter_policy():
    return {
        "order":["official_public_api","direct_http_text","document_or_feed","repository",
                 "transcript_or_audio","media_stream","isolated_rendered_web"],
        "browser_context":"isolated non-persistent context per stateful job where supported",
        "media":"prefer dedicated hardware-decoded player when permitted and useful",
        "extractors":"pluggable; no single unofficial extractor is a critical dependency",
        "access":"public/permitted sources only; do not bypass DRM, paywalls, authentication or access controls",
        "privacy":"local metadata/history; minimum cookies; no account unless explicitly required and authorized",
    }

def evidence_quality_gate(*,authority,relevance,independence,transcript_confidence,
                          contradiction_checked=False,timestamped=False):
    score=(.30*authority+.25*relevance+.20*independence+.15*transcript_confidence+
           .05*bool(contradiction_checked)+.05*bool(timestamped))
    return {
        "score":round(max(0,min(1,float(score))),4),
        "route_to_rishi":score>=.60,
        "needs_review":score<.75,
        "rule":"video popularity/view count is discovery metadata, never evidence authority",
    }
