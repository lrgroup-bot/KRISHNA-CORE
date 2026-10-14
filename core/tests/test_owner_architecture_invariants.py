from krishna_core.router import ModelRouter
from krishna_core.autonomy_supervisor import AutonomySupervisor

def test_owner_no_qwen_policy_is_non_bypassable_by_defaults():
    assert ModelRouter.DISABLED_LOCAL_MODEL_PREFIXES
    assert not ModelRouter.local_model_allowed("qwen3.5:4b")
    assert not ModelRouter.local_model_allowed("qwen2.5-coder:7b")
    assert all("qwen" not in x.lower() for x in ModelRouter.local_model_candidates("general"))
    assert all("qwen" not in x.lower() for x in ModelRouter.local_model_candidates("coding"))

def test_krishna_autonomy_does_not_own_lr_business_operations():
    assert "vanijya_plan" not in AutonomySupervisor.SAFE_OPERATIONS
    assert "manibhadra" not in {x.lower() for x in AutonomySupervisor.SAFE_OPERATIONS}
