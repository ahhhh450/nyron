# NYRON-D-004 — Lead Integration Clarification 002

**Status:** NORMATIVE INTEGRATED CANDIDATE CLARIFICATION / PRE-FREEZE
**Applies to:** `design/Nyron_Capability_Resource_Effect_Authority_Design_Candidate_v0.1.md`
**Authority:** Nyron Lead Design Authority

This clarification incorporates later subsystem ownership decisions into the D-004 authority model without changing Frozen Amendment 001.

---

## 1. Capability Policy Context vs Grant Decision

PWP Owner may supply immutable Project/Workspace policy-context references used by Capability Authority.

Capability Authority remains sole Owner of:
- CapabilityType authority vocabulary/registration semantics;
- Capability policy evaluation result as used for Grant issuance;
- CapabilityGrant lifecycle.

PWP policy/config records are decision inputs, never Grants.

```text
PWP policy context
-> Capability Authority evaluation
-> GRANTED / DENIED / REQUIRES_APPROVAL
-> CapabilityGrant only if Capability Authority commits it
```

### Added authority invariant

**ARE-INV-14 — Policy Context Is Not Capability Authority**

Project/Workspace policy-context ownership does not transfer CapabilityGrant issuance/revocation/narrowing authority away from Capability Authority.

---

## 2. Human Approval Evidence Boundary

Human Interaction Owner owns:
- HumanRequest;
- accepted HumanResponse;
- HumanDecisionEvidence.

Capability Authority may return `REQUIRES_APPROVAL`, and later consume exact HumanDecisionEvidence during re-evaluation.

Human approval evidence:
- must bind to exact protected subject/scope/operation/context;
- may be rejected as stale/insufficient under current pinned Capability policy;
- cannot override a higher-priority system-security deny unless that policy explicitly permits delegation;
- cannot directly create CapabilityGrant;
- cannot revive stale Attempt authority.

### Added authority invariant

**ARE-INV-15 — Human Approval Is Evidence, Not Grant**

Canonical human approval/decision evidence may satisfy a Capability policy requirement, but only Capability Authority may commit Grant truth and must independently validate evidence applicability.

---

## 3. Recovery Disposition vs Effect Conflict Clearance

Recovery Owner may resolve a ReconciliationCase or issue a scoped administrative disposition while the underlying EffectOperation remains UNKNOWN.

Such Recovery disposition may permit Runtime administrative closure according to policy, but does not itself prove Effect conflict clearance.

Effect Authority remains the Owner that may establish EffectOperation completion/fencing/UNKNOWN/conflict-clearance truth.

Resource Manager similarly owns Resource/Lease conflict clearance.

Capability Authority owns Grant validity/revocation.

### Added authority invariant

**ARE-INV-16 — Recovery Cannot Fabricate Authority Clearance**

ReconciliationCase state or Recovery administrative disposition cannot be substituted for Effect/Resource/Capability Owner-specific clearance required to authorize conflicting future work.

---

## 4. Package Trust Is Not Capability

Module Registry / Distribution Owner owns PackageTrustDecision.

Package trust/install/enable state may be a prerequisite for Module loading/admission but never grants operation authority.

```text
Package TRUSTED
!= CapabilityGrant
!= ResourceLease
!= Effect authority
!= Runtime admission
```

A trusted package executing under a current Attempt must still receive and pass actual scoped Capability checks at the relevant boundary.

### Added authority invariant

**ARE-INV-17 — Distribution Trust Cannot Grant Runtime Authority**

Package install/trust/enable decisions cannot create, widen or substitute CapabilityGrant, ResourceLease, EffectOperation authority or Runtime current-Attempt authority.

---

## 5. CapabilityType Extensibility

`CapabilityType` remains a versioned authority vocabulary owned by Capability Authority and opaque to Kernel Foundation.

Product-visible classes such as:
- Browser control;
- Tool invocation;
- Remote execution;
- provider-specific operations

may be represented by registered/versioned CapabilityTypes without becoming Kernel primitives.

D-008's examples such as `BROWSER_CONTROL`, `TOOL_INVOKE` and `REMOTE_EXEC` are permitted extension vocabulary. They do not need to be hardcoded as Kernel primitives or necessarily frozen as mandatory initial v0.1 types unless implementation/product scope selects them.

CapabilityType registration/declaration never implies a Grant.

---

## 6. Workspace Scope Input

Capability scope may reference PWP-owned `workspace_ref`, exact WorkspaceConfig/PolicyContext revisions or related immutable scope descriptors.

That reference does not make Capability Authority owner of Workspace identity/configuration.

At actual external boundary:
- Capability scope/current Attempt/fencing is revalidated;
- ResourceLease is validated where applicable;
- adapter resolves/enforces PWP workspace/binding constraints;
- EffectOperation is used where consequential/crash-ambiguous.

No single reference collapses these Owners.

---

## 7. Lead Disposition

Later D-005/D-007/D-009/D-010 integration introduces no contradiction requiring a new Frozen Module amendment.

D-004 remains **LEAD REVIEW PASS**, now with:
- Frozen Amendment 001; and
- this integration clarification.

It remains pending bounded independent review/freeze consolidation.
