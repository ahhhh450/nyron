# Nyron Graph / Composite Frozen Baseline v0.1

**Task ID:** `NYRON-D-002`
**Status:** **FROZEN GRAPH / COMPOSITE ARCHITECTURE BASELINE**
**Freeze Authority:** Nyron Lead Design Authority

## 1. Baseline Composition

This frozen baseline is the normative composition of the following exact repository artifacts:

1. `design/Nyron_Graph_Composite_Design_Candidate_v0.1.md`
   - frozen content blob SHA: `f0c7f875c1bb233c9ef1c8ff3f8c6c39d2eef22b`
2. `design/clarifications/NYRON-D-002_Lead_Integration_Clarification_001.md`
   - frozen content blob SHA: `67e0d14602d698a9968c096a915a0e85d98611b6`

If the working-tree version of either source file later differs from these exact blobs, that later content is NOT part of this baseline unless an explicit amendment or superseding frozen baseline says so.

The source Candidate header may still say Candidate; this freeze manifest is the authoritative status declaration for the exact blobs above.

## 2. Review Evidence

Lead integration review: PASS.

Independent targeted review:
- `design/reviews/NYRON-D-002_DeepSeek_Targeted_ReReview.md`
- result accepted by Lead Design Authority as VALID PASS.

The first earlier DeepSeek PASS was explicitly rejected as review-invalid due to material misreads and is not freeze evidence.

## 3. Frozen Clarifications Included

The baseline includes the following normative refinements from Lead Clarification 001:

1. `edge_ordinal` has collision-free normative scope sufficient for deterministic Delivery projection; in v0.1 it is unique within GraphRevision.
2. Concrete input-port ordinals are stable and collision-free within the owning ModuleInstanceRevision.
3. Runtime projection ordering cannot depend on DB row order, UI position, worker arrival, wall clock, hash iteration, or other transient ordering.
4. Concrete immutable Port objects are the materialized single source of truth for ModuleInstanceRevision input/output port contracts.
5. Every Composite placement has stable immutable `composite_instance_ref` binding identity.
6. Composite materialization is deterministic for identical immutable materialization inputs under the same materialization contract.
7. Persisted materialized leaf ModuleInstanceRevision/Port/Edge topology in GraphRevision is execution authority; Runtime never re-flattens or regenerates it.
8. `G-INV-20` and `G-INV-21` are frozen as part of this baseline.

## 4. Frozen Architectural Conclusions

The following are frozen:

- Graph is logical identity; GraphRevision is immutable execution definition.
- Runtime pins exact GraphRevision and exact ModuleDefinition versions; no mutable latest/current resolution.
- GraphDraft may be broken/incomplete and remains non-executable until validation passes.
- Concrete Ports and Edges are immutable definition facts.
- FEEDBACK is an intentional-cycle Edge role only and introduces no special Runtime semantics.
- Directed Graph cycles are allowed when each cycle contains explicit FEEDBACK; CompositeRevision dependency recursion is forbidden.
- Loop/Branch/Join are not Kernel/Runtime primitives.
- Composite is a versioned Definition-layer reusable subgraph/template and never a second Runtime.
- Composite materialization produces GraphRevision-owned ordinary leaf ModuleInstanceRevision + Port + Edge facts.
- DependencyManifest is derived metadata using the frozen recursive exact-version formula and is never authority.
- Unresolved/broken definitions may be preserved/imported but cannot enter Runtime execution admission.
- Validation and execution eligibility are derived; publication/archive governance is orthogonal.
- Import/export preserves exact versions and grants no trust, Capability, Resource, or execution authority.
- Product Node taxonomy cannot change Graph/Runtime/Kernel primitive taxonomy.

## 5. Open Questions That Remain Non-Blocking

The following remain intentionally open for owning designs without reopening this baseline unless they require semantic change:

- global Schema/Value compatibility contract;
- ModuleInstance logical identity tooling rules across copy/fork/merge/import;
- exact top-level Graph input/output interface schema;
- product governance details for Deprecated vs Retired;
- loop liveness/termination/budget policy;
- terminology alignment for Composite internal reusable member definitions.

Top-level execution ingress is constrained by later Lead integration clarification: it must preserve the ordinary Trigger Packet -> Delivery -> Activation path and may not introduce direct Activation admission.

## 6. Change Control

This frozen baseline MUST NOT be silently edited or reinterpreted.

Any semantic change requires one of:
- an explicit Graph/Composite Architecture Amendment identifying affected invariants/contracts; or
- a superseding frozen Graph/Composite baseline.

Implementation may refine schemas, storage layout and APIs only where the refinement does not weaken or change the frozen semantics above and in the exact baseline artifacts.
