# Graph / Accounting Amendment 001 — Static AccountingScope Reference Resolution

**Status:** **FROZEN GRAPH / ACCOUNTING ARCHITECTURE AMENDMENT**  
**Authority:** Nyron Lead Design Authority  
**Applies to:**
- `design/Nyron_Graph_Composite_Frozen_Baseline_v0.1.md`
- `design/Nyron_Accounting_Recovery_Frozen_Baseline_v0.1.md`

**Reason:** Resolve `NYRON-D-001-CLAUDE-F01` from the integrated Claude adversarial review.

## 1. Problem

`ModuleInstanceRevision.static_accounting_scope_ref` is immutable definition-time affiliation, but Graph owns only the reference while Accounting Owner owns the referenced `AccountingScope` and ancestry.

The frozen design already requires unresolved Module dependencies to make a definition non-executable and Accounting already fails closed on invalid scope/policy during reservation. However, no single frozen cross-owner rule explicitly requires every static accounting reference in an admitted GraphRevision to resolve before execution admission.

That leaves an avoidable correctness ambiguity at the Graph/Accounting boundary.

## 2. Ownership remains unchanged

This Amendment does **not** transfer Accounting ownership into Graph or Runtime.

```text
Graph / ModuleInstanceRevision
  owns: immutable static_accounting_scope_ref

Accounting Owner
  owns: AccountingScope identity, ancestry, policy and reservation truth

Runtime
  owns: execution admission
```

A reference never grants mutation authority over the referenced Owner.

## 3. Persistable definition vs executable eligibility

A GraphRevision or imported definition MAY remain durably stored even when a foreign accounting reference is temporarily unresolved.

But unresolved accounting affiliation is not executable.

Therefore:

```text
persistable/importable definition
!= execution eligible definition
```

This mirrors the existing rule for unresolved `module_ref@version` without making Accounting state part of Graph canonical ownership.

## 4. Mandatory execution-eligibility validation

Before Runtime admits a WorkflowExecution for a GraphRevision, the system MUST validate every `ModuleInstanceRevision.static_accounting_scope_ref` in the admitted immutable executable topology.

For each reference, the authoritative Accounting Owner must establish that:

1. the reference resolves to exactly one canonical `AccountingScope`;
2. the scope is valid for the pinned immutable definition anchor / GraphRevision affiliation required by the Accounting contract;
3. the complete Accounting-owned parent ancestry required for reservation is resolvable and structurally valid;
4. no missing/ambiguous parent reference or ownership mismatch exists;
5. any canonical ancestry identity/hash used by the Accounting contract is consistent with the resolved ancestry.

The exact API/query is implementation-local. The correctness result is not.

## 5. Fail-closed rule

If any required static accounting reference is unresolved, ambiguous, mismatched, or has incomplete/invalid ancestry, Runtime MUST NOT admit the GraphRevision for ordinary execution.

A machine-readable reason such as:

```text
UNRESOLVED_ACCOUNTING_SCOPE_REFERENCE
ACCOUNTING_SCOPE_BINDING_INVALID
ACCOUNTING_SCOPE_ANCESTRY_INVALID
```

or an equivalent structured reason MUST be emitted.

No implementation may interpret missing accounting affiliation as:
- no budget policy;
- unlimited budget;
- rootless accounting;
- best-effort attribution;
- permission to defer validation until after an external effect has begun.

## 6. Budget policy resolution remains separate

This Amendment validates static accounting identity/ancestry, not mutable/current budget policy by Graph ownership.

Budget policy remains Accounting-owned and is resolved/pinned under the frozen Accounting contract when authorization/reservation is performed.

Therefore:

```text
static AccountingScope resolution
!= BudgetPolicyRevision ownership
!= BudgetReservation authority
```

## 7. Historical resolvability

Any AccountingScope identity or ancestry information referenced by retained durable execution/accounting history MUST remain resolvable for replay, audit and late settlement while that history is retained.

Archival/supersession may prevent new use but MUST NOT turn a still-referenced canonical accounting identity into a dangling reference.

This does not require retaining derived dashboards/caches; only the canonical identity/ancestry truth needed to interpret history.

## 8. Added invariants

**GA-INV-01 — Static Accounting References Must Resolve Before Execution**  
A GraphRevision is not eligible for ordinary Runtime execution admission while any `static_accounting_scope_ref` in its executable immutable topology cannot be authoritatively resolved and structurally validated by Accounting Owner.

**GA-INV-02 — Missing Accounting Scope Never Means Unbounded Authority**  
An unresolved/invalid AccountingScope reference fails closed and cannot be interpreted as absence of budget/accounting restriction.

**GA-INV-03 — Referenced Accounting Identity Remains Historically Resolvable**  
AccountingScope identity/ancestry still referenced by retained canonical history cannot be hard-deleted or made semantically unresolvable.

## 9. Baseline effect

This Amendment is authoritative wherever the frozen Graph/Accounting bundle was previously silent about cross-owner `static_accounting_scope_ref` execution eligibility.

It does not change:
- Graph topology ownership;
- AccountingScope ownership;
- static accounting membership semantics;
- Packet -> Delivery -> Activation -> Run execution path;
- BudgetReservation lifecycle;
- Runtime current-Attempt ownership.
