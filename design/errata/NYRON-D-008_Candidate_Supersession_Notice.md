# NYRON-D-008 Candidate Supersession Notice

**Classification:** NON-NORMATIVE DOCUMENTATION HYGIENE NOTICE  
**Applies to:** `design/Nyron_External_Interfaces_Workspace_Boundary_Design_Candidate_v0.1.md`  
**Normative authority remains:** frozen D-008 baseline + accepted Amendments  
**Architecture Finding:** NONE

## Purpose

The historical D-008 Candidate contains wording in §11.7 that was later found unsafe and superseded by a frozen Amendment.

The Candidate is retained as historical design material and is **not a standalone implementation authority**.

## Superseded wording

Historical Candidate §11.7 states:

```text
Safe redispatch requires one of:
- proof old operation was never dispatched;
- proof old operation is FENCED;
- proof old operation completed and policy intentionally starts a new distinct operation;
- provider-supported idempotency identity that safely deduplicates duplicate dispatch;
- explicit policy accepting duplicate consequences.
```

The condition:

```text
proof old operation is FENCED
```

is **insufficient by itself** for semantic retry safety.

## Current authoritative rule

The controlling frozen correction is:

`design/amendments/External_Interfaces_Amendment_001_Fenced_Retry_Semantics.md`

Normative interpretation:

```text
FENCED
!= proof of no prior consequence
!= proof of never-dispatched
!= semantic retry clearance
```

`FENCED` may clear the active/concurrency conflict axis only. Same-semantic non-idempotent redispatch still requires independent evidence such as proven non-dispatch/no relevant consequence, reliable external idempotency/deduplication, an explicitly distinct new semantic operation, or policy that intentionally accepts duplicate consequences.

Historical outcome may remain `UNKNOWN` or `PARTIAL` after active work is FENCED.

## Implementation reading rule

Do **not** implement D-008 retry behavior from the Candidate alone.

Read in this order:

1. `design/Nyron_Overall_System_Architecture_Frozen_Baseline_v0.1.md`
2. `design/Nyron_External_Interfaces_Workspace_Frozen_Baseline_v0.1.md`
3. `design/amendments/External_Interfaces_Amendment_001_Fenced_Retry_Semantics.md`
4. the historical Candidate only for supporting detail not superseded by the frozen bundle.

Where historical Candidate wording conflicts with an accepted Amendment, the Amendment controls.

## Review disposition

This notice records a documentation-hygiene issue only.

It does not reopen `NYRON-D-004-GPT-F01`, does not alter the accepted D-004 targeted re-review PASS, and does not change the frozen architecture semantics.
