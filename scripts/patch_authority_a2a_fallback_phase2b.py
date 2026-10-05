from pathlib import Path

p=Path(__file__).resolve().parents[1]/"core/krishna_core/protocol_gateway.py"
text=p.read_text(encoding="utf-8")
old='''        return self.action_bus.dispatch(\n            action,msg.get("payload") or {},project=str(msg.get("project") or "KRISHNA"),\n            source="a2a",actor=str(msg.get("principal") or "a2a-peer"),\n            permissions=msg.get("permissions") or [],approved=bool(msg.get("approved",False)),\n            idempotency_key=str(msg.get("request_id") or "").strip() or None,\n        )\n'''
new='''        return self.action_bus.dispatch(\n            action,msg.get("payload") or {},project=str(msg.get("project") or "KRISHNA"),\n            source="a2a",actor=str(msg.get("principal") or "a2a-peer"),\n            permissions=msg.get("permissions") or [],approved=bool(msg.get("approved",False)),\n            idempotency_key=str(msg.get("request_id") or "").strip() or None,\n            authority_lease=msg.get("authority_lease"),\n        )\n'''
if old in text:
    p.write_text(text.replace(old,new),encoding="utf-8")
    print("patched A2A direct action-bus fallback authority lease")
elif new in text:
    print("A2A fallback authority lease already patched")
else:
    raise RuntimeError("A2A fallback patch anchor missing; fail closed")
