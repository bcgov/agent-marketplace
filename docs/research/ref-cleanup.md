# Obsolete-ref preservation and pending cleanup

Status: **prepared, no remote or tracking refs deleted**. Retained main at inventory was `d9da79c4f5856cb1aaa47f5963d63253efeecbe0`; the integration PR has not established retained-main reachability. [Public inventory](preservation.json) records exact historical local/remote refs and all original/preserved file hashes. Refresh refs/worktrees immediately before cleanup; any changed candidate tip requires reassessment and preservation, never a broader deletion.

| Exact remote candidate | Expected SHA | Deletion |
| --- | --- | --- |
| `refs/heads/prototype/catalogue-personality` | `c6c012a7d8b9a2606cb77c295945da697b0913c1` | Pending |
| `refs/heads/prototype/security-check-flow` | `dd143a4dd2bb779b21b51bd4b3d96bd81f29b879` | Pending |
| `refs/heads/research/codex-patch-inventory` | `acaad6023466cd8fc2d255469aa8420d0f1d4f8a` | Pending |
| `refs/heads/research/extension-level-evidence` | `761c7b5f4840da170e29e3727d11482b528fc066` | Pending |
| `refs/heads/research/fork-pr-automerge` | `5c8e805b58b976de83f09037cc6ef016a51330b1` | Pending |
| `refs/heads/research/native-install-formats` | `af91f4a80e011bfee8061636f9342c4ed7e544b8` | Pending |
| `refs/heads/research/replaceable-skill-scanner` | `3005d63679cab27c99a9461de8a273bf9353340e` | Pending |
| `refs/heads/research/scan-extensibility` | `81dcee04714260754018d351bc0df30e18f253cd` | Pending |

## Post-merge completion gate

1. Verify the merged retained-main commit contains all 17 preserved sources/index/manifest; compare every preserved SHA-256 and original Git blob or documented historical link repair. Verify the complete eight-ref bundle hash/heads and recovery in an isolated repository. Keep the durable backup after cleanup.
2. Add stable retained-main archive references to decisions #9/#10/#11/#13/#18/#21/#22/#23. Preserve historical context and supersession; verify discoverability from each affected decision before deleting its source ref. Until those references exist, retain that remote branch.
3. Re-inventory exact local/remote refs and worktrees, retain unmerged user work, confirm all eight expected tips and no matching active local head/worktree. Keep all `v1/*`, original user branches, main/HEAD, published tags/releases and all PR refs. The local `v1/61-validation-isolation` is protected even though its remote is gone.
4. Run build/internal-file/anchor checks. Delete only the eight named remote heads with per-ref expected-SHA leases. Then delete only corresponding unchanged tracking refs with expected-old-SHA guards. Record actual outcomes and retained evidence/backup location; stop for any changed SHA or failed gate.

No wildcard pruning, user worktree deletion or active implementation-ref cleanup is authorized by this inventory. `working/` was absent and no tracked history was found; original external patch bytes are unavailable, so no deletion/backup claim is made for them. This document is a pending plan, not #53 completion evidence. #43 and #48 external proofs remain independent.
