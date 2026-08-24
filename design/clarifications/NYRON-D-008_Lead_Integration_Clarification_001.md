# NYRON-D-008 Lead Integration Clarification 001

Status: **LEAD-ACCEPTED PRE-FREEZE CLARIFICATION**
Authority: Nyron Lead Design Authority
Applies to: `design/Nyron_External_Interfaces_Workspace_Boundary_Design_Candidate_v0.1.md`

This clarification resolves ownership and ingress integration boundaries without changing D-004 ownership or the Frozen Module Architecture Baseline.

## 1. Workspace Identity Ownership Is Not Assigned to D-008

`WorkspaceIdentityDescriptor` in D-008 is a conceptual external-boundary descriptor, not a newly claimed canonical state class owned by the External Interface layer.

Until a Workspace / Project / Product configuration Owner is formally frozen:
- D-008 may consume a stable `workspace_ref` and immutable/canonical policy references supplied by the owning subsystem;
- D-008 does not mutate workspace identity metadata;
- a Workspace Handle Resource remains owned by Resource Manager and is distinct from `workspace_ref`;
- Capability scope may reference `workspace_ref` without giving Capability Authority ownership of workspace metadata.

This prevents an unowned or multiply-owned canonical Workspace identity from being introduced implicitly.

## 2. External Event Ingress Does Not Create Activation Directly

An ingress adapter authenticates, validates, canonicalizes and deduplicates external input, but it does not create Runtime Activation directly.

After authoritative ingress canonicalization, execution-triggering input must enter the Runtime through the ordinary execution ingress contract:

```text
External Input
-> authenticated/validated canonical ingress fact
-> admitted immutable GraphRevision ingress binding
-> Runtime-owned Trigger Packet
-> Delivery
-> Activation readiness/binding
-> Activation
-> Run / Attempt
```

The ingress adapter may provide evidence and normalized payload, but Runtime owns Packet/Delivery/Activation execution truth.

## 3. Ingress Canonical Owner Must Be Explicit Per Route

Every external ingress route must identify which subsystem is authoritative for the canonicalized input fact before that fact can drive Runtime.

Transport reception itself is never canonical authority.

A future ingress-route registry/configuration design must therefore pin at least:
- route identity;
- source authentication policy;
- canonical target Owner / event type;
- deduplication identity semantics;
- immutable Graph/execution binding where the route starts workflow execution.

The exact route registry Owner remains an open system-design item and is not claimed by D-008.

## 4. Observation Classification Is Adapter-Declared and Fail-Closed

D-008 statements that an external observation "usually" does not require EffectOperation are not blanket exemptions.

An adapter/profile must classify whether a nominal read/observation is:
- independently billable;
- externally stateful;
- asynchronously active;
- cancellable;
- crash-ambiguous;
- consequential under provider semantics.

If any such property requires durable external-history tracking, the operation must use EffectOperation even if the product UI presents it as a read.

If classification is uncertain, policy fails closed to the stronger consequential/tracked class.

## 5. Environment Rebinding Never Widens Authority Implicitly

Import/rebinding may resolve logical workspace/provider/browser/worker requirements to local environment bindings only through explicit authorized configuration.

Rebinding cannot:
- silently broaden Capability scope;
- import live ResourceLease authority;
- reuse historical external operation identity as current authority;
- mutate prior execution history.

## 6. Integration Result

With this clarification:
- `NYRON-D-008` is Lead-review PASS;
- D-004 Capability / Resource / Effect ownership remains unchanged;
- no Frozen Module baseline amendment is required;
- D-008 is ready for bounded independent consistency review before freeze consideration.
