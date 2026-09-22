import json
from krishna_core.dependency_audit import DependencyAuditor
from krishna_core.domain_ops import DomainOps
from krishna_core.business_research import BusinessResearch

def test_dependency_inventory_and_sbom(tmp_path):
    (tmp_path/"requirements.txt").write_text("requests==2.32.0\n# comment\n",encoding="utf-8")
    a=DependencyAuditor()
    inv=a.inventory(tmp_path)
    assert inv["count"]==1 and inv["mutated"] is False
    assert a.sbom(tmp_path)["bomFormat"]=="CycloneDX"

def test_domain_change_is_plan_only():
    p=DomainOps().plan_change("example.com","A","www","192.0.2.1")
    assert p["executed"] is False and p["requires_owner_approval"] is True

def test_business_research_drops_unapproved_fields():
    r=BusinessResearch().normalize({"name":"Shop","website":"https://example.com","password":"secret"})
    assert r["name"]=="Shop" and "password" not in r
