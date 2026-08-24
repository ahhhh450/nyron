# NYRON-D-009 — Lead Integration Clarification 001

**Status:** NORMATIVE INTEGRATED CANDIDATE CLARIFICATION / PRE-FREEZE
**Applies to:** `design/Nyron_Human_Interaction_Approval_Authority_Design_Candidate_v0.1.md`
**Authority:** Nyron Lead Design Authority

This clarification tightens policy ownership and response acceptance semantics without changing Runtime, Capability, Recovery or External Ingress ownership.

---

## 1. Response Contract Semantics vs Responder Authorization Policy

Nyron distinguishes two different policy classes.

### 1.1 Human Interaction-owned response contract semantics

Human Interaction Owner owns the immutable semantics that determine how canonical responses satisfy one HumanRequest.

This includes the request-bound `ResponsePolicyRevision` / response-contract semantics for:
- accepted response cardinality;
- first-valid / single / N-of-M / unanimous / threshold behavior;
- duplicate-principal counting rule;
- deny-veto / conflict aggregation rule;
- terminal satisfaction rule;
- whether late/post-terminal amendment semantics exist;
- how accepted HumanResponse refs aggregate into canonical `HumanDecisionEvidence`.

These rules are part of Human Interaction canonical request interpretation and therefore must be immutable/revisioned and pinned by the HumanRequest.

### 1.2 Project/Workspace/Identity policy remains foreign

Human Interaction does NOT own:
- principal identity;
- organization/team/role membership;
- workspace/project responder assignments;
- security policy deciding whether a principal may respond;
- product visibility/routing roles.

Those come from the authoritative Project/Workspace/Identity/policy owners as pinned evidence/references.

Therefore:

```text
ResponsePolicyRevision
= how valid responses are counted/interpreted

Responder authorization policy
= who is allowed to provide a valid response
```

The two may reference each other but must not collapse ownership.

### Added invariant

**HI-INV-21 — Response Aggregation And Responder Authority Are Separate**

Human Interaction owns immutable request-response aggregation semantics, while principal/role/membership/authorization policy remains owned by the appropriate foreign policy/identity Owner. Human Interaction cannot create responder authority merely by defining a quorum or selector.

---

## 2. Invalid External Input Is Not HumanResponse Truth

Normative v0.1 rule:

`HumanResponse` means an accepted immutable canonical response fact.

Untrusted, unauthenticated, schema-invalid, unauthorized, late, cancelled-request, superseded-request or identity-conflicting external inputs MUST NOT be represented as accepted HumanResponse truth merely with a `REJECTED_AS_INVALID` state.

They may be represented by:
- ingress rejection/audit fact;
- security event;
- telemetry;
- protected raw evidence reference;

according to the owning ingress/security/audit contract.

This removes ambiguity between:
- accepted semantic response history; and
- rejected transport/input evidence.

The canonical HumanResponse state may therefore remain effectively immutable/accepted in v0.1; exact storage schema need not expose a lifecycle state field if no semantic transition exists after acceptance.

### Added invariant

**HI-INV-22 — Rejected Input Does Not Become Accepted Response Truth**

Only successfully authenticated, authorized, schema-valid, deduplicated and request-eligible input may become canonical HumanResponse. Rejected ingress may be durably audited elsewhere but cannot participate in satisfaction/quorum/decision evidence.

---

## 3. Response vs Expiry/Terminal Race

Response acceptance and request terminal transitions (`SATISFIED`, `EXPIRED`, `CANCELLED`, `SUPERSEDED`) MUST serialize within Human Interaction Owner or use equivalent owner-local atomic compare-and-commit semantics.

A response cannot be accepted based on a stale `OPEN` read after a terminal transition already committed.

Likewise, a terminal transition cannot erase a HumanResponse that already committed while the request was eligible.

Wall-clock arrival order outside the Owner is not semantic authority. The Human Interaction Owner's committed transition order plus the pinned expiry contract determines the canonical result.

### Added invariant

**HI-INV-23 — Response/Terminal Race Is Owner-Serialized**

Concurrent response acceptance and request terminal transitions must resolve through deterministic owner-local canonical serialization/atomicity; transport arrival timing cannot create two conflicting terminal interpretations.

---

## 4. Approval Evidence Reuse

`HumanDecisionEvidence` is evidence about one exact HumanRequest response contract and protected subject scope.

Reuse by a replacement Attempt, later execution, broader path, larger amount, different operation class or changed policy is denied unless the consuming Owner's pinned policy explicitly allows that reuse and can machine-check the evidence applicability.

Human Interaction does not decide CapabilityGrant reuse. Capability Authority remains final authority.

---

## 5. Lead Disposition

NYRON-D-009 Lead integration result: **PASS WITH CLARIFICATION 001**.

No Frozen Module, Frozen Graph/Composite, Runtime, Capability/Resource/Effect or Accounting/Recovery amendment is required.

D-009 is ready for bounded independent consistency review before freeze consideration.
