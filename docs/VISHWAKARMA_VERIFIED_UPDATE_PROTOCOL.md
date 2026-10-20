# VISHWAKARMA Verified Update Protocol

VISHWAKARMA is KRISHNA's builder/update engineer. It is not allowed to edit the live
runtime, merge its own work, or promote an unverified candidate.

Flow:

PLANNED -> IMPLEMENTING -> TESTED -> FRONTEND_READY -> FRONTEND_APPROVED ->
RELEASE_CANDIDATE -> PROMOTION_READY -> DEPLOYED -> VERIFIED

Hard gates:
- implementation occurs in isolated engineering worktrees;
- TESTED requires passing evidence;
- FRONTEND_READY requires real frontend/browser proof;
- FRONTEND_APPROVED requires explicit approval;
- no Windows EXE/package is allowed before FRONTEND_APPROVED;
- PROMOTION_READY requires independent verification;
- DEPLOYED requires a transactional promotion receipt;
- VERIFIED requires post-deployment health evidence;
- auto-merge is false and VISHWAKARMA has no promotion authority.

Existing KRISHNA components remain authoritative:
EngineeringScheduler/EngineeringSwarmManager staff isolated work; IndependentCriticVerifier
judges evidence; PromotionManager performs backup/promotion/rollback; MRITYUNJAY handles
bounded self-heal; Guardian restarts the runtime with crash-loop quarantine; Sudarshan/owner
policy remains promotion authority.

The Windows executable is deliberately outside this change. Frontend acceptance happens first.
