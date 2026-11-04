from krishna_core.sudarshan_project_ingress import ProjectIngress, SudarshanProjectIngress


class FakeOrchestrator:
    def start(self, project_id, context):
        return {"state": "DISCOVERY", "project": project_id, "context": context, "owner": "Sudarshan"}


def test_lr_technology_enters_sudarshan_with_approved_versioned_spec():
    gateway = SudarshanProjectIngress(FakeOrchestrator())
    result = gateway.accept(ProjectIngress(
        project_id="customer-app",
        spec_version="1.0",
        source="lr-technology",
        customer_approved=True,
        specification={"requirements": ["AUTH-001"], "architecture": {"kind": "web"}},
    ))
    assert result["state"] == "DISCOVERY"
    assert result["authority"] == "KRISHNA"
    assert result["orchestration"] == "Sudarshan"
    assert result["context"]["project_ingress_source"] == "lr-technology"


def test_lr_technology_cannot_bypass_customer_approval():
    gateway = SudarshanProjectIngress(FakeOrchestrator())
    result = gateway.accept(ProjectIngress(
        project_id="customer-app",
        spec_version="1.0",
        source="lr-technology",
        customer_approved=False,
        specification={"requirements": ["AUTH-001"]},
    ))
    assert result["state"] == "BLOCKED_CUSTOMER_APPROVAL"


def test_unknown_project_source_is_rejected():
    gateway = SudarshanProjectIngress(FakeOrchestrator())
    result = gateway.accept(ProjectIngress(
        project_id="customer-app",
        spec_version="1.0",
        source="unknown-company",
        customer_approved=True,
        specification={"requirements": ["AUTH-001"]},
    ))
    assert result["state"] == "BLOCKED_SOURCE"


def test_sudarshan_authority_request_is_never_self_approved():
    request = SudarshanProjectIngress.authority_request(
        "customer-app", "deploy", reason="release candidate", permissions=("deploy",)
    )
    assert request["requested_by"] == "Sudarshan"
    assert request["authority"] == "KRISHNA"
    assert request["approved"] is False
