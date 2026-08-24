# NYRON-D-005 / NYRON-D-010 — Lead Integration Clarification 002

**Status:** NORMATIVE INTEGRATED CANDIDATE CLARIFICATION / PRE-FREEZE
**Applies to:**
- `design/Nyron_Accounting_Recovery_Design_Candidate_v0.1.md`
- `design/Nyron_Project_Workspace_Policy_Context_Design_Candidate_v0.1.md`

**Authority:** Nyron Lead Design Authority

This clarification resolves the ownership portion of D-005 `AR-OQ-02` and aligns Project/Workspace budget policy context with static Accounting ownership.

---

## 1. AccountingScope Remains Accounting-Owned

Project/Workspace identity or policy context may participate in accounting attribution/policy selection, but PWP does not own `AccountingScope`, `BudgetPolicyRevision`, `BudgetReservation`, UsageFact or settlement.

Accounting Owner remains the sole canonical Owner of:
- AccountingScope hierarchy used for hard-limit accounting;
- BudgetPolicyRevision semantics/results;
- reservation/settlement counters;
- BudgetReservation;
- usage/adjustment/overrun facts.

PWP supplies immutable context references only.

---

## 2. Static Execution Membership Is Preserved

For Module execution, the frozen static accounting affiliation remains:

```text
Activation
-> immutable ModuleInstanceRevision
-> static_accounting_scope_ref
-> Accounting-owned scope ancestry
```

Dynamic facts MUST NOT change membership:
- current Workspace config pointer;
- current Project policy pointer;
- Packet provenance;
- triggering Edge;
- Runtime Attempt replacement;
- worker/provider identity;
- later PWP rebind/reparent/config update.

PWP changes affect future definition/admission/accounting-context construction according to explicit contracts, not historical affiliation of already-admitted Activations.

### Added Accounting invariant

**AR-INV-23 — PWP Context Cannot Dynamically Reassign Accounting Membership**

Project/Workspace/policy context may select or constrain the Accounting-owned scope/policy context used for new work, but an admitted Activation's static AccountingScope affiliation cannot be recomputed from mutable PWP `current` state.

---

## 3. Project / Workspace / Organization-Level Budget Policy

If v0.1 or later requires Project/Workspace/organization/account budget limits above Graph/Composite-local scopes, those limits must still be represented within the **Accounting Owner's canonical authority domain**.

Permitted architecture shape:

```text
PWP project/workspace identity + exact policy context refs
-> immutable reference/input to Accounting
-> Accounting-owned AccountingScope / BudgetPolicyRevision hierarchy
-> Runtime/Effect requests BudgetReservation
```

The Accounting-owned hierarchy may contain scope records whose `definition_anchor_ref` / context refs point to stable PWP Project/Workspace identities or another immutable policy-domain identity.

That reference does not transfer Accounting ownership to PWP.

A hard reservation that spans such ancestor scopes must still satisfy D-005 full-ancestry atomic reservation semantics inside one logical Accounting Owner transaction domain.

### Added Accounting invariant

**AR-INV-24 — External Context Anchors Do Not Split Budget Ownership**

AccountingScope may reference stable Project/Workspace/organization context identities, but all hard-limit ancestor reservation/settlement truth remains Accounting-owned and cannot be implemented as a best-effort cross-owner partial reserve.

---

## 4. PWP Policy Context Is Input, Not Budget Decision

PWP may own/reference:
- which Project/Workspace policy sources apply;
- immutable policy-context revision identity;
- principal/role context used to authorize budget-policy administration.

Accounting Owner independently owns:
- BudgetPolicyRevision acceptance/publication under its contract;
- reservation allow/deny;
- canonical exposure;
- settlement and overrun.

Therefore:

```text
PWP accounting-policy context
!= BudgetPolicyRevision ownership
!= BudgetReservation authority
```

### Added PWP invariant

**PWP-INV-25 — PWP Does Not Own Budget Truth**

PWP may supply immutable Project/Workspace/accounting policy context references but cannot reserve, release, settle or rewrite Accounting canonical state.

---

## 5. Human Roles for Accounting Administration

D-005 `AR-OQ-05` ownership boundary is also clarified:

- authenticated HumanResponse / HumanDecisionEvidence -> Human Interaction Owner;
- Project/Workspace role/membership policy -> PWP/Identity policy authority;
- decision to publish/change BudgetPolicyRevision -> Accounting Owner under its authorized command contract;
- human evidence/role does not directly mutate budget state.

A human operator may be authorized to request a budget-policy change, but the Accounting Owner commits the policy revision and resulting canonical accounting state.

---

## 6. Lead Disposition

- `AR-OQ-02` Owner placement — **RESOLVED**: higher-level Project/Workspace/organization budget scopes remain Accounting-owned; PWP supplies immutable context anchors/policy inputs.
- `AR-OQ-05` authority boundary — **RESOLVED at architecture level**: Human Interaction owns response evidence, PWP/Identity owns role context, Accounting owns budget-policy/state transitions.

Exact product role names, budget dimensions and conservative UNKNOWN exposure defaults remain non-blocking policy/schema details.

No Frozen Module or Frozen Graph/Composite amendment is required.
