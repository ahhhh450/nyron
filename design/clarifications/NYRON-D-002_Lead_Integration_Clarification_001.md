# NYRON-D-002 — Lead Integration Clarification 001

**Status:** NORMATIVE CANDIDATE CLARIFICATION / PRE-FREEZE
**Applies to:** `design/Nyron_Graph_Composite_Design_Candidate_v0.1.md`
**Authority:** Lead Design Authority integration decision

This clarification incorporates the valid DeepSeek targeted re-review findings without changing the frozen Module execution path or introducing new Runtime primitives.

## C1 — Deterministic Ordinal Scope

For executable `GraphRevision`:

- `edge_ordinal` MUST be a committed immutable definition fact and MUST be unique within the owning `GraphRevision`.
- each concrete input `port_ref` MUST have one stable immutable `ordinal` within its owning `ModuleInstanceRevision`; no two concrete input ports of the same instance may share the same ordinal.
- Runtime Delivery projection ordering MUST depend only on committed canonical definition/runtime facts such as `source_packet_seq`, frozen `edge_ordinal`, and frozen target-port ordinal as defined by the frozen Module contract.
- DB row order, insertion order, UI coordinates, wall-clock time, worker arrival order, hash-map iteration order, or other transient ordering MUST NOT affect semantic Delivery ordering.

This is a tightening of deterministic projection semantics, not a new scheduling primitive.

### Added invariant

**G-INV-20 — Deterministic Delivery Projection Inputs**

Any deterministic ordering used to project a Packet across Graph edges into Deliveries MUST be a function only of committed immutable GraphRevision facts and committed Runtime packet identity/order facts. Definition ordinals used by that function MUST have a collision-free scope sufficient to prevent ordering ambiguity.

## C2 — Concrete Port Single Source of Truth

The `input_port_contract` / `output_port_contract` fields of `ModuleInstanceRevision` and the Graph Candidate's concrete instance Port objects are not two independent authorities.

Normative interpretation:

> The concrete immutable Port objects owned by a `ModuleInstanceRevision` are the materialized representation of that revision's `input_port_contract` / `output_port_contract`.

Edges reference those concrete Port identities. Runtime validation reads the same materialized contracts. No second mutable or independently authoritative port-contract store may diverge from them.

## C3 — Composite Instance Binding Identity

Each materialized Composite placement in an executable GraphRevision MUST have a stable immutable binding identity:

`composite_instance_ref`

A `CompositeInstanceBinding` MUST at minimum identify:

- `composite_instance_ref`
- exact `composite_revision_ref`
- owning `graph_revision_ref`
- optional parent `composite_instance_ref`
- immutable parameter/config binding references required to reproduce provenance
- exposed-interface mapping identity sufficient for deterministic inspection/import/export

`static_composite_path` uses these stable composite instance identities.

The binding is Definition-layer provenance and materialization authority only; it does not create Composite runtime state.

## C4 — Deterministic Composite Materialization

Composite materialization MUST be deterministic with respect to the complete immutable definition inputs used by the materializer.

For the same:

- `CompositeRevision`
- composite instance binding identity/context
- immutable parameter/config bindings
- nested exact revision closure
- materialization algorithm/version contract where relevant

materialization MUST produce the same semantic leaf module/port/edge structure.

The resulting leaf identities/topology are then persisted as authoritative `GraphRevision` facts. Runtime never re-materializes them for execution correctness.

### Added invariant

**G-INV-21 — Deterministic Composite Materialization**

Given identical immutable materialization inputs under the same materialization contract, Composite expansion MUST produce the same semantic leaf definition structure. Once persisted into a GraphRevision, that persisted structure is the execution authority and MUST NOT be recomputed by Runtime.

## C5 — Overall Architecture Owner Table Follow-up

The DeepSeek review correctly noted that the current DRAFT Overall Architecture Owner table omits `EffectOperation`.

This is not a D-002 issue. D-001 integration MUST add:

`EffectOperation -> Effect Authority`

consistent with Frozen Amendment 001 and D-004.

## Lead Disposition

DeepSeek targeted re-review result: **VALID PASS**.

Non-blocking clarifications C1-C4 are accepted as normative pre-freeze refinements to D-002. C5 is assigned to D-001 integration.

No blocking Architecture Finding against the frozen Module baseline or Amendment 001 is open for D-002.
