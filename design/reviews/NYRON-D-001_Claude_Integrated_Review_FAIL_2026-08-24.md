# NYRON-D-001 — Claude Integrated Adversarial Review FAIL Record

**Date:** 2026-08-24  
**Reviewer:** Claude  
**Authority:** independent review evidence only; no freeze authority  
**Lead disposition:** findings evaluated individually below

## Review result

`INTEGRATED REVIEW RESULT: FAIL`

## Finding F01 — Static AccountingScope Reference Resolution

Claude identified that immutable `ModuleInstanceRevision.static_accounting_scope_ref` may be present while no explicit cross-owner execution-eligibility rule requires the referenced AccountingScope to resolve before execution.

### Lead disposition

**VALID BLOCKING FINDING.**

The existing Accounting candidate fails closed when a reservation request encounters `ACCOUNTING_SCOPE_INVALID` / policy-resolution failure, but the integrated architecture does not make the foreign reference itself an execution-eligibility prerequisite comparable to unresolved Module dependencies.

The correction must preserve ownership:
- Graph stores immutable `static_accounting_scope_ref` only;
- Accounting Owner remains sole owner of AccountingScope identity/ancestry;
- Graph may remain persistable/importable even when the foreign reference is unresolved;
- Runtime execution admission MUST fail closed unless every required static accounting reference resolves and its Accounting-owned ancestry is structurally valid for the pinned immutable definition.

Frozen baseline impact: **YES**. A cross-domain Amendment is required for Graph/Accounting execution eligibility.

## Finding F02 — PWP Historical Revision Retention

Claude stated that PWP did not guarantee retention/resolvability of pinned Project/Workspace/policy/environment/route revisions.

### Lead disposition

**PARTIALLY VALID / OVERSTATED PREMISE.**

The frozen D-010 bundle already contains the intended rule. The frozen Candidate states, among other things:
- `ARCHIVED` preserves historical resolution;
- a Project referenced by historical executions MUST remain resolvable through pinned revisions;
- historical consumers pin exact revisions;
- superseded revisions remain resolvable while referenced by canonical history;
- historical executions retain exact pinned Workspace and revision references.

Therefore the architecture did not omit historical retention entirely.

However, the coverage is distributed across Project/Workspace/config wording and does not enumerate every PWP revision class (`PolicyContextRevision`, `EnvironmentBindingRevision`, `IngressRouteRevision`) in one explicit retention invariant. That ambiguity is correctness-relevant enough to remove before Overall freeze.

Frozen baseline impact: **YES, clarification-strength Amendment**. Add an explicit PWP Amendment stating that every PWP-owned immutable revision referenced by durable canonical history remains resolvable until no retained history references it; archival/supersession is not deletion.

## Lead next action

1. Create Graph/Accounting Amendment for static AccountingScope reference resolution before execution admission.
2. Create PWP Amendment making retention protection explicit for all pinned PWP revision classes.
3. Update Overall Manifest and STATUS.
4. Reuse the same Claude review conversation for targeted re-review of F01/F02 corrections.
