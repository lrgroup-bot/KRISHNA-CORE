from __future__ import annotations

class GitHubValidationPolicy:
 """Zero-spend GitHub validation gate.

 GitHub-hosted standard runners are zero Actions-minute cost for public repos.
 Private-repo hosted runners are conditional because included minutes/storage can
 be exhausted. Self-hosted is zero Actions-minute cost but must be isolated and trusted.
 """
 def decide(self,*,repo_visibility,runner,zero_cost_proven=False,isolated=False,trusted=False):
  vis=str(repo_visibility or "").lower();run=str(runner or "").lower()
  if vis=="public" and run in {"github-hosted","standard","github-hosted-standard"}:
   return {"allowed":True,"mode":"public-standard-hosted","reason":"standard hosted Actions are free for public repositories"}
  if run in {"self-hosted","self_hosted"}:
   ok=bool(isolated and trusted)
   return {"allowed":ok,"mode":"self-hosted","reason":
    "allowed only on an isolated trusted runner; never expose the main KRISHNA host to untrusted PR workflows"}
  if vis in {"private","internal"} and run in {"github-hosted","standard","github-hosted-standard"}:
   return {"allowed":bool(zero_cost_proven),"mode":"private-hosted-conditional","reason":
    "private hosted Actions use included quota and may bill after allowance; require explicit zero-cost proof"}
  return {"allowed":False,"mode":"blocked","reason":"runner/repository cost or trust state is not proven safe"}

 def validation_order(self):
  return ["local-unit","local-integration","local-ui","local-security","github-independent-build-test-if-zero-cost","sudarshan","promotion"]
