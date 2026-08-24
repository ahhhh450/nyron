# Nyron Graph / Composite Design Candidate v0.1

Status: CANDIDATE — FOR INDEPENDENT REVIEW
Task: NYRON-D-002
Authority: Lead Design Authority integration candidate
Depends on:
- `Nyron_Overall_System_Architecture_v0.1.md` — DRAFT
- `Universal_Runtime_Module_Design_Report_v0.1.md` — FROZEN MODULE ARCHITECTURE BASELINE

## 1. Purpose

Graph describes what the executable definition is; Runtime decides when execution occurs. Graph / Composite remain Definition-Layer concepts and MUST NOT create a second Runtime or product-node primitive taxonomy.

The subsystem supports immutable executable definitions, Port/Edge topology, versioned Composite reuse, broken/incomplete workflow preservation, dependency diagnostics, import/export, and exact Runtime pinning.

## 2. Scope

Owned design scope:
- Graph / GraphDraft / GraphRevision
- ModuleInstance logical identity and ModuleInstanceRevision placement in GraphRevision
- concrete Port contracts
- Edge topology
- Composite / CompositeRevision / materialization
- dependency manifest
- structural validation and execution eligibility
- definition lifecycle
- import/export/sharing
- Graph canonical ownership and Runtime boundary

Non-scope:
- Runtime scheduling/readiness implementation
- retry/replacement/cancellation policy
- workflow terminal state machine
- Capability/Resource/Accounting semantics
- Module Host
- product Node taxonomy and UX
- complete schema/type-system design
- registry installation/signing/trust policy

## 3. Ownership Model

Graph subsystem canonical truth includes:
- `graph_ref` and Graph identity
- revision lineage
- immutable `GraphRevision`
- `module_instance_ref`
- immutable `ModuleInstanceRevision`
- concrete revision-owned Port identities/contracts
- immutable Edge topology
- Composite identity and immutable `CompositeRevision`
- Composite instance bindings and static Composite provenance/path
- publication/deprecation/retirement/archive governance facts

GraphDraft may be durable authoring state, but is never Runtime execution authority.

Graph subsystem does not own ModuleDefinition semantics, Registry installation state, Packet, Delivery, Activation, Run, Scheduler, CapabilityGrant, Resource, BudgetReservation, Runtime retry state, or product UI Node taxonomy.

Derived, rebuildable state includes dependency manifests, validation reports, missing-dependency diagnostics, execution eligibility, editor/search indexes, UI layout caches and flattened summaries.

## 4. Graph / GraphDraft / GraphRevision

`Graph` is long-lived logical identity. It is not executable.

`GraphDraft` is mutable authoring state and may be incomplete, invalid, missing modules/config, or contain temporarily invalid topology. It never enters Runtime directly.

`GraphRevision` is an immutable definition snapshot. Runtime pins `graph_revision_ref`, never `graph_ref -> current/latest`.

GraphRevision semantic payload is immutable from creation. Any semantic change creates a new GraphRevision.

A revision snapshot freezes:
- exact ModuleDefinition versions
- immutable config references
- concrete Port contracts
- Edge topology and stable ordinals
- exact CompositeRevision bindings
- fully materialized leaf execution topology
- static Composite paths

Publication is a governance fact over an immutable revision, not a rewrite of the revision payload.

Publication, validation/execution eligibility, and archive status are orthogonal axes.

Deprecation is advisory for new use. Retirement blocks ordinary new admission by default but cannot break historical resolution/replay. Archive is storage/listing policy only and cannot invalidate referenced history.

Validated immutable but unpublished GraphRevision may be admitted for test/preview when policy allows.

## 5. ModuleInstance / ModuleInstanceRevision

`module_instance_ref` is a logical placement identity that may persist across Graph revisions.

Each executable placement in a GraphRevision is an immutable `ModuleInstanceRevision` belonging to exactly one GraphRevision and pinning exactly one immutable `ModuleDefinition@version` and immutable `config_ref`.

Frozen Module fields remain authoritative:
- `module_instance_revision_ref`
- `graph_revision_ref`
- `module_instance_ref`
- `module_definition_ref@version`
- `config_ref`
- `config_hash`
- `input_port_contract`
- `output_port_contract`
- `static_composite_path`
- `static_accounting_scope_ref`

Runtime MUST NOT resolve `latest/current/compatible latest` module/config values.

`config_hash` is integrity evidence only; `config_ref` remains addressable immutable authority.

## 6. Port Model

Three layers are distinct:
1. Module Port Definition — capability contract owned by ModuleDefinition@version.
2. Concrete Instance Port — immutable GraphRevision-owned contract referenced by Edge.
3. UI Port — product presentation only.

Every concrete Port has stable `port_ref`; label/name is not identity.

Input contract minimally includes direction, schema, activation mode, connection policy and ordinal. Frozen activation modes remain:
- TRIGGER
- REQUIRED_NEXT
- REQUIRED_LATEST
- OPTIONAL_LATEST

Graph MUST NOT introduce a second required/optional execution authority conflicting with activation mode. UI required/optional presentation is derived from the contract.

Output contract declares schema, ordinal and output-presence semantics; output presence never changes Activation readiness.

Dynamic Port families may exist only at authoring/definition creation time. Before GraphRevision creation they are materialized to concrete frozen Ports. Runtime cannot add/remove/change Ports.

Input connection policy may distinguish SINGLE_SOURCE and MULTI_SOURCE. Fan-in requires the target to permit it.

Schema compatibility must be deterministic. Graph does not perform implicit conversions/casts/adapters. Until a global Schema/Value Contract exists, safe default is exact-compatible schema only.

## 7. Edge Model

Edge is immutable Definition Fact, never Packet/Delivery/Runtime connection state.

An Edge binds one concrete source Output Port to one concrete target Input Port and has stable `edge_ref` plus stable `edge_ordinal`.

`edge_ordinal` is a frozen definition fact used by deterministic projection and MUST NOT depend on DB row order, UI position, creation time or wall clock.

Fan-out is allowed. Fan-in is allowed only when target connection policy permits it.

Exact duplicate source-endpoint -> target-endpoint edges are illegal.

Edge role:
- NORMAL
- FEEDBACK

Self-loop requires FEEDBACK.

Every directed cycle must contain at least one explicit FEEDBACK edge; otherwise validation returns `UNDECLARED_GRAPH_CYCLE`.

FEEDBACK is only an explicit definition-layer declaration of intentional cyclic topology. It MUST NOT alter Packet/Delivery ordering, activation modes, attempt identity, or other Runtime execution semantics. Loop iterations remain new Packet -> Delivery -> Activation -> Run chains; old Activation cannot be reused.

## 8. Composite Model

Composite is a versioned reusable Definition-Layer subgraph/template. It is not ModuleDefinition, Module, Activation, Run, Scheduler, Runtime or Kernel primitive.

`Composite` is logical identity; `CompositeRevision` is immutable semantic definition. Immutable executable definitions pin exact `composite_revision_ref`, never latest.

CompositeRevision may define:
- interface input/output Ports
- internal Module member definitions
- nested Composite members
- internal Edges
- definition-time config schema/parameter binding rules

When a Composite is instantiated into a GraphRevision, its closure is deterministically and finitely materialized into GraphRevision-owned leaf `ModuleInstanceRevision + Edge` objects.

The materialized leaf identities and topology written into GraphRevision are canonical definition facts. Runtime MUST NOT re-flatten Composite or regenerate leaf identities during execution.

`static_composite_path` records immutable static provenance/grouping from root Graph to leaf. It is not a call stack, scheduler nesting or execution authority.

Composite dependency closure must be finite and acyclic. Direct or indirect recursive CompositeRevision references are invalid.

Composite exposed input may map to one or more compatible internal input Ports. Composite output maps to exactly one internal Output Port in v0.1; multi-source merge requires an explicit Module rather than hidden Composite runtime semantics.

Composite config, if supported, is definition-time parameterization only. It must fully resolve into concrete leaf config/topology/Ports before an executable GraphRevision exists.

Product Layer may display a Composite as one collapsible Node without changing Runtime primitives.

## 9. Loop / Branch / Join

v0.1 adds no Loop, Branch or Join Kernel/Runtime primitive.

Branch is expressed by Module output semantics plus Ports and topology.

Join/barrier/snapshot behavior is expressed by Modules with multiple Input Ports and frozen activation modes.

Any-source merge may use MULTI_SOURCE TRIGGER semantics; actual data aggregation requires explicit Merge/Join Module behavior.

Loop is Graph cycle plus explicit FEEDBACK edge. Iteration limits, budgets, cancellation and liveness are not Graph primitives and remain Runtime/Accounting concerns.

## 10. Dependency Manifest

For GraphRevision and CompositeRevision, dependency manifest is derived definition metadata:

`sorted(unique(all referenced module_ref@version recursively))`

It is generated automatically from immutable definitions, may be cached, and is never user-maintained authority.

Unresolved references remain present in the manifest and produce diagnostics rather than being omitted.

Manifest supports import preflight, export, missing-module diagnostics, package resolution, offline bundle inspection, compatibility inspection and sharing UX. It does not install/trust modules, grant Capability or authorize execution.

## 11. Validation Model

Validation is staged and derived.

V0 — Envelope / identity integrity:
- malformed/corrupt object
- invalid reference format
- ambiguous identity collision
- impossible revision ownership
- integrity failure

Failure at V0 prevents acceptance as structured GraphRevision; raw imported artifact may still be quarantined/preserved.

V1 — Internal referential integrity:
- missing ModuleInstance/Port
- invalid Edge endpoint
- invalid interface mapping
- duplicate Edge
- invalid static Composite path

V2 — Module resolution:
- every `module_definition_ref@version` resolves exactly one immutable ModuleDefinition
- otherwise `UNRESOLVED_MODULE_REFERENCE`

V3 — Composite resolution:
- exact revision exists and is immutable
- nested refs resolve
- closure is finite and acyclic
- otherwise `UNRESOLVED_COMPOSITE_REFERENCE` / `CYCLIC_COMPOSITE_REFERENCE`

V4 — Port validation:
- direction
- existence
- materialization
- cardinality
- schema compatibility
- ordinal integrity

V5 — Config validation:
- immutable config_ref exists
- required config present
- schema-valid
- Composite parameterization fully resolved

V6 — Topology validation:
- duplicate Edge
- invalid self-loop
- undeclared cycle
- illegal fan-in
- invalid Composite boundary
- ambiguous hidden merge

V7 — Execution eligibility:
Only when all correctness-affecting definition constraints pass may derived `EXECUTION_ELIGIBLE = true`.

## 12. Saveable vs Executable

GraphDraft may preserve unresolved modules/composites, missing config, broken endpoints, schema mismatch, cyclic Composite references, invalid feedback declarations and other repairable authoring errors.

Broken imported definitions may be preserved and inspected, but cannot enter Runtime execution admission.

Corrupt/ambiguous data that cannot form a trustworthy structured identity/revision is preserved only as raw imported artifact, not canonical GraphRevision.

Executable means all Runtime-correctness definition constraints are satisfied; warnings may still exist.

## 13. Lifecycle Axes

Do not collapse authoring, validation, publication and archival into one state machine.

Authoring: mutable GraphDraft.
Revision: immutable GraphRevision.
Validation: derived INVALID / VALID_NON_EXECUTABLE / EXECUTION_ELIGIBLE (names non-normative).
Publication: canonical UNPUBLISHED / PUBLISHED / DEPRECATED / RETIRED governance facts.
Archive: independent ACTIVE_STORAGE / ARCHIVED policy.

Published is not required for Runtime correctness; immutable + execution eligible + admission policy is sufficient.

## 14. Import / Export / Sharing

Graph bundle preserves at minimum:
- bundle format version
- Graph identity and GraphRevision payload
- exact CompositeRevision closure
- dependency manifest
- immutable config/schema references required for interpretation
- provenance metadata
- bundle content hash

Composite bundle equivalently preserves CompositeRevision closure and dependencies.

Exact module/composite versions MUST be preserved. Import never silently upgrades a version; user-requested upgrade creates a new revision.

Missing modules/composites are importable and inspectable but non-executable, with explicit unresolved diagnostics.

Embedding a Module package does not install or trust it. Import provenance is evidence, not authority.

Portability does not guarantee environment executability: secrets, provider accounts, workspace bindings, external resources and policy may remain environment-specific.

Principle: broken definitions may survive; broken definitions may not corrupt Runtime.

## 15. Runtime Boundary

Runtime accepts `graph_revision_ref` and resolves immutable GraphRevision, ModuleInstanceRevision, Port, Edge and config facts.

Runtime MUST NOT read current draft, latest module, latest Composite or mutable editor config.

Executable GraphRevision has already completed Composite materialization, exact module/config pinning, concrete Port materialization and topology freezing.

Runtime never executes Composite nesting. It sees leaf ModuleInstanceRevision + Edge topology.

Execution path remains frozen:
`Packet -> Edge projection -> Delivery -> Activation -> Run`.

Graph subsystem never creates Activation, calls Modules/downstream Modules, retries Modules or schedules Modules.

Composite creates no CompositeRun, CompositeActivation, CompositeScheduler or execution stack. Composite progress/observability is derived from leaf Runtime facts.

## 16. Architecture Invariants

G-INV-01 — Graph is logical identity; Runtime execution pins exactly one immutable GraphRevision.

G-INV-02 — GraphRevision semantic payload is immutable from creation; semantic changes require a new revision.

G-INV-03 — Runtime cannot resolve current/latest/mutable definitions for an existing execution.

G-INV-04 — Every ModuleInstanceRevision belongs to exactly one GraphRevision and pins exactly one immutable ModuleDefinition@version and config_ref.

G-INV-05 — Executable GraphRevision contains fully materialized immutable concrete Port contracts; Runtime cannot mutate Ports.

G-INV-06 — Every Edge references existing source Output and target Input Ports and passes direction/cardinality/schema validation.

G-INV-07 — Exact duplicate source endpoint -> target endpoint Edge is illegal.

G-INV-08 — Every directed cycle contains at least one explicit FEEDBACK Edge; every self-loop is FEEDBACK.

G-INV-09 — FEEDBACK changes no Runtime execution semantics; cycles create new Packet/Delivery/Activation/Run facts and never reuse an old Activation.

G-INV-10 — Composite is Definition only and is never Module/Runtime/Scheduler/Kernel primitive.

G-INV-11 — CompositeRevision dependency closure is finite and free of direct/indirect recursive Composite references.

G-INV-12 — Composite materialization produces ordinary GraphRevision-owned leaf ModuleInstanceRevision + Edge facts. Materialized leaf identities/topology are stored as authoritative definition facts and are never regenerated by Runtime.

G-INV-13 — DependencyManifest is automatically derived from immutable definition references and is not authority.

G-INV-14 — Unresolved ModuleDefinition/CompositeRevision references may be preserved but cannot enter executable Runtime admission.

G-INV-15 — ValidationReport, dependency diagnostics, manifest and execution eligibility are rebuildable derived state, not canonical authority.

G-INV-16 — GraphRevision, ModuleInstanceRevision, CompositeRevision and immutable semantic dependencies referenced by durable execution history remain resolvable through deprecation/retirement/archive.

G-INV-17 — Import/provenance/embedded packages grant no Module trust, Capability, Resource or execution authority.

G-INV-18 — Graph/Composite never bypass Packet -> Delivery -> Activation -> Run or enable direct downstream Module calls.

G-INV-19 — Product Node taxonomy cannot alter Graph/Runtime/Kernel primitive taxonomy; product concepts are expressed through generic Module/Config/Port/Edge/Composite/Topology/Capability/Resource mechanisms.

## 17. Open Questions

OQ-01 — Global Schema/Value Compatibility Contract. Graph requires a deterministic compatibility function but must not invent a private type system. Exact-compatible-only is the safe interim rule.

OQ-02 — Logical ModuleInstance identity rules across copy/paste/duplicate/merge/import/fork. This affects diff/tooling rather than Runtime correctness.

OQ-03 — Whether top-level Graph formally exposes Graph Input/Output Ports. Likely yes, but Workflow Start / External Event -> Trigger Packet belongs to Runtime/External Interface design.

OQ-04 — Whether product governance needs both Deprecated and Retired statuses. Historical resolution must remain unaffected either way.

OQ-05 — Loop liveness/termination/iteration limits/budget/deadlock policies belong to Runtime/Accounting.

OQ-06 — Composite internal-member terminology should be aligned with the frozen Module document without changing semantics: reusable internal member definitions materialize into GraphRevision-owned ModuleInstanceRevision facts.

## 18. Architecture Findings

None. This candidate does not require reopening the frozen Module architecture baseline.

## 19. Recommended Implementation Gates

G1 — Definition Identity Foundation: Graph/Draft/Revision, ModuleInstance/Revision persistence, Port/Edge and Composite identities. No Scheduler.

G2 — Validation + Dependency: module/composite resolution, Port/Edge/config/topology validation, dependency manifest, diagnostics and execution eligibility.

G3 — Composite Materialization: nesting, interface maps, parameterization, deterministic flatten, static Composite paths, persisted leaf identities/topology.

G4 — Import/Export: bundles, provenance, missing dependency preservation, roundtrip fidelity; no silent version upgrade.

G5 — Runtime Definition Integration: only after Runtime Orchestration contract is compatible; connect GraphRevision -> Packet Edge Projection -> Delivery without redesigning Scheduler/retry/lifecycle.

G6 — Product Node / Visual Graph: only after foundational Graph contract is stable; product nodes remain wrappers over generic primitives.

## 20. Lead Integration Review Notes

Lead Design Authority integration review found no blocking conflict with the frozen Module baseline.

Two clarifications are incorporated before independent review:
1. Composite materialization output (leaf identities and topology) becomes authoritative immutable GraphRevision content; Runtime never re-flattens/re-identifies it.
2. FEEDBACK is only an explicit intentional-cycle marker and does not create special delivery ordering, activation, attempt or scheduling semantics.

Candidate is ready for independent architecture review, but is not FROZEN.