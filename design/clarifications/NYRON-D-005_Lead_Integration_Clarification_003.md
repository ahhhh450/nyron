# NYRON-D-005 — Lead Integration Clarification 003

**Status:** FROZEN NORMATIVE CLARIFICATION  
**Authority:** Nyron Lead Design Authority  
**Task:** `NYRON-T-20260826-084`  
**Resolves:** `NYRON-T-20260826-077-F-002`  
**Coordination Basis:** Epoch `2` / Revision `80`  
**Applies to frozen bundle:**
- `design/Nyron_Accounting_Recovery_Design_Candidate_v0.1.md`
- `design/clarifications/NYRON-D-003_D-005_Lead_Integration_Clarification_001.md`
- `design/clarifications/NYRON-D-005_D-010_Lead_Integration_Clarification_002.md`
- `design/Nyron_Accounting_Recovery_Frozen_Baseline_v0.1.md`

This clarification freezes only the minimum same-scope `BudgetPolicyRevision` publication and current-selection semantics required to make Accounting authorization deterministic. It does not redesign Accounting / Recovery and does not add provider pricing, rolling-window machinery, currency conversion, settlement, Recovery, or new cross-owner authority.

No conflict was found with the frozen Accounting / Recovery baseline. The existing baseline already requires immutable policy revisions, exact policy pinning on reservations, cumulative ancestor restriction, Accounting ownership of publication/authorization, and fail-closed policy resolution. The rules below make the previously unspecified same-scope revision-chain semantics exact.

---

## 1. Applicability Interval Convention

For current-selection purposes, every `BudgetPolicyRevision` uses a half-open applicability interval:

```text
[effective_from, logical_effective_until)
```

The lower bound is inclusive and the upper bound is exclusive.

`effective_until`, when explicitly stored on a revision, MUST be strictly greater than that revision's `effective_from`.

`logical_effective_until` is determined as follows:

1. if the revision has an explicit `effective_until`, that value is its upper bound;
2. otherwise, if the revision has a valid direct successor, the successor's `effective_from` is the predecessor's logical upper bound;
3. otherwise the revision is open-ended for current-selection purposes.

A successor therefore logically bounds an open predecessor without mutating or rewriting the predecessor row.

---

## 2. One Immutable Linear Revision Chain Per Scope

For each `accounting_scope_ref`, Accounting Owner MUST maintain at most one canonical immutable, non-branching `BudgetPolicyRevision` chain.

The chain is append-only:

- the first revision for a scope is the genesis revision;
- every later revision is a direct successor of the existing chain tip;
- insertion into the middle of a committed chain is forbidden;
- rewriting an earlier revision to change history is forbidden.

A publication race targeting the same chain tip MUST serialize inside Accounting Owner so that at most one successor can commit. A losing/stale publication attempt is rejected; committed branches are never resolved by last-arrival, lexical reference ordering, or another tie-break rule.

---

## 3. Exact `supersedes_ref` Invariants

### 3.1 Genesis publication

If no `BudgetPolicyRevision` exists for the target `accounting_scope_ref`:

- `supersedes_ref` MUST be absent.

A genesis revision that names a `supersedes_ref` is invalid.

### 3.2 Successor publication

If one or more revisions already exist for the target scope:

- `supersedes_ref` MUST be present;
- the target revision MUST exist;
- the target revision MUST have the same `accounting_scope_ref`;
- the target revision MUST be the unique current chain tip;
- the new revision MUST become that tip's direct successor.

The following are rejected fail closed at publication:

- self-supersession;
- cross-scope supersession;
- superseding any non-tip historical revision;
- a second successor of an already-superseded revision;
- any cycle;
- any publication that would create a branch or disconnected same-scope history.

Because every successor must point to the exact unique tip, cycle/branch/cross-scope histories cannot be created through a valid publication path.

---

## 4. Effective-Time Ordering

For every valid same-scope successor:

```text
successor.effective_from > predecessor.effective_from
```

Strict increase is mandatory.

Two same-scope revisions with equal `effective_from` are never valid alternatives. Equal-effective publication is rejected; Accounting MUST NOT choose between them using `budget_policy_revision_ref`, creation order, row order, arrival order, or any other secondary tie-break.

---

## 5. Predecessor `effective_until` Consistency and Gaps

When the predecessor has an explicit `effective_until`, a proposed successor is valid only if:

```text
predecessor.effective_until <= successor.effective_from
```

Therefore:

- `predecessor.effective_until == successor.effective_from` gives a contiguous handoff;
- `predecessor.effective_until < successor.effective_from` creates an explicit policy gap and is permitted;
- `predecessor.effective_until > successor.effective_from` would create overlap and is rejected.

When the predecessor is open (`effective_until` absent), a valid successor's `effective_from` becomes the predecessor's logical upper bound for current-selection purposes. The historical predecessor row remains immutable.

A permitted gap is not implicit unlimited authority. If a scope already has a policy chain but decision time falls in a gap, that scope has no uniquely applicable revision and new authorization fails closed under Section 7.

---

## 6. Future Successors May Be Pre-Published

Accounting MAY publish successors whose `effective_from` is in the future.

Future publication does not create a second chain or replace the currently applicable revision early. The same append-only rules apply:

- the future revision MUST directly supersede the exact current chain tip;
- its `effective_from` MUST be strictly greater than the predecessor's `effective_from`;
- explicit predecessor `effective_until` consistency from Section 5 still applies;
- another later future revision may be pre-published only by directly superseding that future chain tip and using a still later `effective_from`.

Committed future revisions cannot be inserted around, reordered, or replaced by an equal-effective revision. Policy administration that needs different future semantics must append another valid later revision; it may not rewrite committed revision history.

The chain order is established solely by valid `supersedes_ref` links plus the strict effective-time invariant, not by arrival order during authorization.

---

## 7. Deterministic Current Selection at Decision Time `t`

Policy resolution remains per `accounting_scope_ref`.

For a scope with at least one canonical policy revision, Accounting MUST first validate that the stored same-scope history satisfies Sections 1–6. It then computes each revision's half-open applicability interval and selects the revision for which:

```text
effective_from <= t < logical_effective_until
```

Current selection MUST produce exactly one applicable revision.

For a scope that already has a policy chain:

- exactly one applicable revision -> use that revision;
- zero applicable revisions, including before the first effective revision, after an explicitly ended terminal revision, or inside a permitted gap -> fail closed for new authorization;
- more than one applicable revision -> fail closed for new authorization.

A scope with no canonical `BudgetPolicyRevision` history contributes no scope-local rules. This does not erase or weaken any ancestor policy.

No `budget_policy_revision_ref` lexical ordering, database row ordering, latest-arrival rule, or wall-clock publication ordering may decide which committed revision governs authorization.

---

## 8. Invalid or Ambiguous Historical Chains Fail Closed

If stored same-scope policy history is malformed or ambiguous, including any branch, cycle, cross-scope supersession, equal-effective conflict, overlap, disconnected duplicate genesis, missing supersession target, or non-tip successor relation, Accounting MUST NOT repair or guess current authority during authorization.

New authorization that depends on that scope fails closed with a machine-readable policy-resolution failure such as `POLICY_NOT_RESOLVABLE` or equivalent frozen implementation reason.

Historical repair/migration, if ever required, is a separate explicitly authorized operation and is outside this clarification.

---

## 9. Historical Reservation Pinning Is Immutable

Every committed `BudgetReservation` remains pinned to the exact `policy_revision_refs[]` used for its canonical authorization decision.

Later policy publication MUST NOT:

- rewrite those refs;
- re-evaluate an already committed reservation as though a newer policy had governed it;
- retroactively invalidate an already granted reservation solely because a stricter successor exists;
- revive a `DENIED` reservation because a later revision is more permissive.

Replay of an already committed identical `request_ref` returns the existing canonical reservation/decision and does not perform a new current-policy selection.

A genuinely new authorization request resolves policy at its own decision time and pins the exact revisions selected then.

---

## 10. Ancestor HARD Rules Compose Cumulatively

Policy resolution is performed independently for every scope in the reservation's pinned AccountingScope ancestry.

For a new authorization at decision time `t`:

1. resolve the applicable revision, if policy history exists, for each governing scope under Section 7;
2. collect every applicable `HARD` rule from every selected ancestor and child revision;
3. evaluate all such rules against the same Accounting Owner atomic reservation snapshot.

A child policy may narrow or add restrictions, but it cannot erase, replace, bypass, or widen an ancestor `HARD` rule. Matching child dimensions or rules do not shadow ancestor authority.

A scope with no local policy history adds no local rule, but ancestor rules remain fully applicable. A scope with an existing but non-resolvable policy chain causes the new authorization to fail closed rather than silently dropping that scope's authority.

---

## 11. Bounded Implementation Consequence

`NYRON-T-20260826-077-F-002` is contractually resolved by this clarification.

The bounded implementation correction may now enforce:

- exact linear-chain publication validation;
- immutable successor publication;
- strict effective-time ordering;
- deterministic half-open interval selection;
- logical truncation of open predecessors without row mutation;
- fail-closed gap/ambiguity/invalid-history behavior;
- exact historical reservation policy pinning;
- cumulative ancestor HARD-rule evaluation.

No production code is changed by this clarification itself. Final Gate-6A acceptance still requires the authorized bounded implementation correction and independent review of the eventual combined content.
