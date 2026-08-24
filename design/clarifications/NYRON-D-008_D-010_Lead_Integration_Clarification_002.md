# NYRON-D-008 / NYRON-D-010 — Lead Integration Clarification 002

**Status:** NORMATIVE INTEGRATED CANDIDATE CLARIFICATION / PRE-FREEZE
**Applies to:**
- `design/Nyron_External_Interfaces_Workspace_Boundary_Design_Candidate_v0.1.md`
- `design/Nyron_Project_Workspace_Policy_Context_Design_Candidate_v0.1.md`

**Authority:** Nyron Lead Design Authority

This clarification closes D-008 open ownership questions using the Lead-integrated D-010 design and the resolved generic workflow ingress contract.

---

## 1. WorkspaceIdentityDescriptor Ownership

The durable logical Workspace identity/configuration metadata referenced by D-008 belongs to **Project / Workspace Context Owner (PWP Owner)**.

PWP owns:
- `workspace_ref`;
- Workspace lifecycle/governance;
- `WorkspaceConfigRevision`;
- logical root declarations;
- portability descriptors;
- `EnvironmentBindingRevision` configuration;
- policy-context references relevant to workspace access.

D-008 External Interface layer does not own these records.

Resource Manager continues to own live Workspace Handle Resource/Lease state.

Therefore:

```text
PWP Workspace identity/config
!= Workspace Handle Resource
!= ResourceLease
!= host absolute path
```

External workspace adapters consume PWP configuration and Resource Manager live handle/lease truth; they own neither.

### Added external-interface invariant

**EIW-INV-29 — Workspace Logical Context Is PWP-Owned**

External Interface adapters may resolve and enforce PWP-owned Workspace/config/binding descriptors but cannot mutate their canonical identity/configuration or treat them as live Resource/Lease truth.

---

## 2. IngressRoute Ownership

`IngressRoute` and immutable `IngressRouteRevision` configuration belong to **PWP Owner**.

PWP route configuration defines/reference-binds:
- source adapter profile;
- authentication policy/profile;
- schema/version contract;
- deduplication contract;
- canonicalization contract;
- canonical target Owner/event family;
- Project/Workspace policy context;
- Graph ingress binding where applicable.

The External Interface/adapter layer executes the configured transport/auth/validation/canonicalization work but does not become route Owner.

### Added external-interface invariant

**EIW-INV-30 — Adapter Executes Route Contract But Does Not Own Route**

Transport listeners/adapters may enforce an exact IngressRouteRevision, but canonical route identity/revision/configuration remains PWP-owned.

---

## 3. Generic Workflow-Start Route Target

For an external input whose only canonical Nyron meaning is workflow-start intent:

```text
PWP IngressRouteRevision
-> adapter authentication/validation/canonicalization
-> Runtime-owned ExecutionIngressFact
-> Runtime admission
-> Trigger Packet
-> Delivery
-> Activation
```

Runtime Orchestration is the canonical target Owner for the generic execution-ingress fact.

D-008 adapter does not create Activation or Run.

D-008 adapter does not own ExecutionIngressFact.

Duplicate non-repeatable ingress delivery is deduplicated through the route-defined stable identity and Runtime admission contract.

---

## 4. Domain-Specific Route Targets

If the external input has independent domain meaning, the target remains the domain Owner, for example:
- Human response -> Human Interaction Owner;
- billing/usage callback -> Accounting Owner;
- effect evidence -> Effect Authority;
- Resource/Lease callback -> Resource Manager.

Such canonical domain facts may later initiate Runtime execution through a separate ingress/admission transition, but their business truth is not reclassified as generic Runtime ingress truth.

---

## 5. Environment Binding vs Live Availability

PWP `EnvironmentBindingRevision` describes selected logical environment configuration only.

D-008 adapters must still validate live conditions at use time, including as applicable:
- actual workspace root/handle resolution;
- Resource compatibility;
- ResourceLease validity;
- CapabilityGrant/current Attempt/fencing;
- effective network/process/browser/provider boundary state.

A valid EnvironmentBindingRevision is not proof that a live Resource, mount, provider session, browser session or remote worker currently exists.

### Added external-interface invariant

**EIW-INV-31 — Environment Binding Is Not Live Boundary Evidence**

Adapters cannot treat PWP environment-binding configuration as proof of current live Resource availability, Lease authority or external-effect safety.

---

## 6. Import / Rebinding Boundary

D-008 portability rules and D-010 rebinding rules align as follows:
- export may preserve logical requirements and portability descriptors;
- live Resource refs, Grants, PIDs/sessions and raw credentials are not portable definition/context authority;
- rebinding creates a new PWP EnvironmentBindingRevision;
- rebinding does not silently widen Capability scope;
- adapters re-evaluate local live boundary conditions after rebinding;
- historical executions keep their original pinned context refs.

---

## 7. Lead Disposition

D-008 open questions concerning:
- durable Workspace identity/config Owner; and
- external ingress route registry/config Owner

are **RESOLVED** by D-010/PWP integration.

Generic workflow-trigger target ownership is **Runtime Orchestration** through the `ExecutionIngressFact` contract defined by `NYRON-D-010_D-001_Lead_Integration_Clarification_001.md`.

No Frozen Module or Frozen Graph/Composite amendment is required.
