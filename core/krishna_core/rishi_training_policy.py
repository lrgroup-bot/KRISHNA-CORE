from __future__ import annotations


_AUTO_TRAIN_LICENSES={"cc0","cc0-1.0","public-domain","publicdomain","pd"}


def _key(value):
    return str(value or "").strip().lower().replace("_","-").replace(" ","-")


def training_policy(base_decision: dict, *, license_id="", explicit_permission=False) -> dict:
    """Apply KRISHNA's stricter corpus-training rule on top of reuse rights.

    A content licence can permit copying/adaptation without KRISHNA treating that
    as automatic permission to place the material into a model-training corpus.
    Automatic promotion is limited to public-domain/CC0 material or a recorded
    explicit permission. Other licences remain usable for READ/INDEX/ARCHIVE as
    their terms allow, but training requires a separate rights review.
    """
    row=dict(base_decision or {})
    if bool(explicit_permission):
        row.update({
            "allowed":True,"training_allowed":True,"review_required":False,
            "training_policy":"explicit permission recorded",
        })
        return row
    key=_key(license_id)
    if key in _AUTO_TRAIN_LICENSES and bool(row.get("allowed")):
        row.update({
            "training_allowed":True,"review_required":False,
            "training_policy":"public-domain/CC0 automatic training eligibility",
        })
        return row
    row.update({
        "allowed":False,"training_allowed":False,"review_required":True,
        "training_policy":"non-CC0/public-domain material requires separate model-training rights review",
    })
    reason=str(row.get("reason") or "").strip()
    suffix="model-training promotion is not automatically authorized by the reuse licence"
    row["reason"]=(reason+"; "+suffix) if reason else suffix
    return row


def is_auto_train_license(license_id: str) -> bool:
    return _key(license_id) in _AUTO_TRAIN_LICENSES
