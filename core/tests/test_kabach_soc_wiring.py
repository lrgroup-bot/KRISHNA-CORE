from krishna_core.durable_event_bus import DurableEventBus
from krishna_core.kabach import KabachAgent

class Memory:
    def __init__(self,db): self.db=db
    def audit(self,*a,**k): return None
    def remember(self,*a,**k): return None

def test_kabach_consumes_lifecycle_events(tmp_path):
    db=str(tmp_path/"k.db")
    bus=DurableEventBus(db)
    memory=Memory(bus.db)
    k=KabachAgent(memory,tmp_path/"privacy",event_bus=None)
    k.bind_security_events(bus)
    bus.publish("TEST_FAILED",{"detail":"failed login","actor":"tester"},source="tests")
    assert k.security_status()["soc"]["events_in_window"]>=1
    assert k.security_status()["event_bus_bound"] is True
