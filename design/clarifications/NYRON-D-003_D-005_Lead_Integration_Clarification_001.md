# NYRON-D-003 / NYRON-D-005 Lead Integration Clarification 001

Status: **LEAD-ACCEPTED PRE-FREEZE CLARIFICATION**
Authority: Nyron Lead Design Authority
Applies to:
- `design/Nyron_Runtime_Orchestration_Design_Candidate_v0.1.md`
- `design/Nyron_Accounting_Recovery_Design_Candidate_v0.1.md`

This clarification resolves integration questions without changing the Frozen Module Architecture Baseline or Amendment 001.

## 1. Top-Level Execution Ingress Must Preserve Packet -> Delivery -> Activation

Nyron MUST NOT introduce a second direct-Activation admission path for workflow start, external ingress, API invocation, human trigger, timer trigger, webhook trigger, or any other top-level execution source.

Every admitted execution ingress must be deterministically converted into a Runtime-owned Trigger Packet and ordinary Delivery path against an immutable GraphRevision ingress binding.

The exact future Graph interface object may be a Graph Input Port or equivalent immutable ingress binding, but it MUST identify the concrete execution-facing destination(s) without resolving mutable `latest/current` state.

Normative rule:

```text
External/API/Product Start Intent
-> validated/admitted ingress fact
-> Runtime-owned Trigger Packet
-> immutable GraphRevision Edge/Ingress projection
-> Delivery
-> Activation readiness/binding
-> Activation
-> Run / Attempt
```

Forbidden:

```text
External/API/Product Start Intent
-> direct Activation creation bypassing Packet/Delivery semantics
```

This closes `OQ-RT-01` at the architectural level while leaving the exact Graph input-interface schema for its owning definition contract.

## 2. ReconciliationCase State Is Not Runtime or Effect Clearance

`ReconciliationCase.RESOLVED` means the Recovery Owner has committed a durable case disposition. It does NOT mean:
- an EffectOperation is no longer UNKNOWN;
- a ResourceLease is known released;
- conflicting external-effect authority is safe to grant;
- Accounting truth became equal to Effect truth;
- Runtime may infer unknown external history.

Therefore Runtime and foreign authorities MUST NOT treat `ReconciliationCase.RESOLVED` alone as a universal clearance token.

## 3. Recovery Disposition Is Scope-Specific

When Runtime termination/administrative closure is blocked by an UNKNOWN foreign subject, Recovery may produce a durable scope-specific disposition that states whether the Runtime execution may close while the underlying subject remains unresolved.

Conceptual minimum:

```text
RecoveryDisposition
- disposition_ref
- reconciliation_case_ref
- subject_ref
- disposition_scope
- permits_runtime_closure: bool
- evidence_refs[]
- policy_ref
- caused_by_ref
```

The exact schema is implementation-level, but the semantic distinction is frozen:

- **Runtime administrative closure permission** may be granted by a Recovery policy disposition while a subject remains UNKNOWN.
- **Conflicting new effect/resource/capability clearance** may only be granted by the authoritative Effect / Resource / Capability owner according to its own canonical safety state and evidence.

Recovery cannot convert an UNKNOWN EffectOperation into effect-conflict clearance by policy alone.

## 4. AccountingScope Reference vs Accounting Ownership

Graph / ModuleInstanceRevision may pin immutable `static_accounting_scope_ref` membership as definition truth.

Accounting Owner owns:
- AccountingScope accounting metadata;
- BudgetPolicyRevision;
- BudgetReservation;
- UsageFact / settlement truth.

Graph subsystem does not gain accounting mutation authority merely because GraphRevision stores the static scope reference.

Changing static containment creates a new definition/revision affiliation for future execution; changing budget policy does not rewrite historical GraphRevision or Activation membership.

## 5. Cross-Owner Terminal Rule

Runtime terminal commitment MUST distinguish:

1. Runtime-owned quiescence/terminal conditions;
2. foreign safety blockers that require authoritative owner clearance;
3. Recovery administrative disposition that may permit Runtime closure without fabricating foreign truth.

A Runtime execution may close administratively while an external EffectOperation remains UNKNOWN only when the applicable policy explicitly permits that closure and the unresolved subject remains durably trackable/recoverable outside the closed Runtime execution.

## 6. Integration Result

With this clarification:
- `NYRON-D-003` is Lead-review PASS;
- `NYRON-D-005` is Lead-review PASS;
- no Frozen Module baseline amendment is required;
- both candidates are ready for bounded independent consistency review before freeze consideration.
