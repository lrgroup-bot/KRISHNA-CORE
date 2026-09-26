from __future__ import annotations


class GitHubPRReviewer:
    """Build a governed review packet from PR metadata/diff/test evidence."""

    def review(self,pr:dict,diff_files:list[dict],checks:list[dict],security_findings:list[dict]|None=None)->dict:
        concerns=[]
        title=str(pr.get("title") or "").strip()
        body=str(pr.get("body") or "").strip()
        if not title:concerns.append("PR title missing")
        if not body:concerns.append("PR intent/body missing")
        changed=sum(int(x.get("changes") or 0) for x in diff_files)
        if changed>5000:concerns.append("very large diff requires staged review")
        failed=[x for x in checks if str(x.get("conclusion") or "").lower() not in {"success","skipped","neutral"}]
        if failed:concerns.append("required checks are not green")
        high=[x for x in (security_findings or []) if str(x.get("severity") or "").lower() in {"high","critical"}]
        if high:concerns.append("high/critical security finding")
        unrelated=[x.get("filename") for x in diff_files if x.get("unrelated")]
        if unrelated:concerns.append("unrelated changes detected")
        return {
            "accepted":not concerns,
            "intent":{"title":title,"body":body},
            "changed_files":len(diff_files),"changed_lines":changed,
            "failed_checks":failed,"security_findings":security_findings or [],
            "concerns":concerns,
            "auto_merge":False,
            "merge_authority":"Sudarshan/owner policy",
        }
