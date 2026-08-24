# Nyron Project / Workspace / Policy Context Design Candidate v0.1

Task ID: `NYRON-D-010`
Status: **CANDIDATE — FOR LEAD REVIEW**
Authority: delegated design candidate only; not frozen

Depends on:
- `design/Nyron_Overall_System_Architecture_v0.1.md` — integrated system architecture candidate
- `design/Nyron_Graph_Composite_Frozen_Baseline_v0.1.md` — **FROZEN GRAPH / COMPOSITE ARCHITECTURE BASELINE**
- `design/Nyron_Capability_Resource_Effect_Authority_Design_Candidate_v0.1.md` — lead-integrated authority candidate
- `design/Nyron_Accounting_Recovery_Design_Candidate_v0.1.md` — lead-integrated accounting/recovery candidate
- `design/Nyron_External_Interfaces_Workspace_Boundary_Design_Candidate_v0.1.md` — lead-integrated external-boundary candidate
- `design/clarifications/NYRON-D-008_Lead_Integration_Clarification_001.md`
- `design/clarifications/NYRON-D-003_D-005_Lead_Integration_Clarification_001.md`

---

## 1. Purpose

This candidate closes the Project / Workspace / Policy Context ownership gap in Nyron.

It defines canonical ownership and lifecycle for:
- Project identity;
- Workspace identity;
- immutable/revisioned ProjectConfig and WorkspaceConfig;
- project/workspace policy-source references and restriction composition;
- logical environment bindings and binding revisions;
- workspace root declarations and portability descriptors;
- execution admission context pinning;
- external ingress route registration/configuration;
- import/export/rebinding semantics;
- archival/deprecation and historical resolvability.

The central rule is:

> Project/Workspace Context owns durable identity and revisioned configuration/policy context. It does not own live Resources, Capability decisions, Runtime execution state, Graph topology, raw secrets, or external adapter state.

This design intentionally separates logical configuration identity from live environment state.

---

## 2. Scope and Hard Boundaries

### 2.1 In scope

- Project and Workspace canonical identity.
- Project/Workspace lifecycle governance at architecture level.
- Project-to-Workspace relationship and nesting rules.
- Revisioned immutable configuration records.
- Revisioned immutable policy-source composition records.
- Logical environment binding declarations.
- Workspace root declarations and portability metadata.
- Binding revision pinning and historical resolution.
- Execution admission context references.
- IngressRoute identity/configuration and target binding.
- Import/export/rebinding of logical configuration.
- Archive/deprecation semantics.
- Cross-owner contracts.

### 2.2 Explicitly out of scope

This candidate MUST NOT own or redefine:
- `Resource` / `ResourceLease` / live Workspace Handle state;
- `CapabilityGrant` or capability authorization decisions;
- Runtime `WorkflowExecution`, Packet, Delivery, Activation, Run or Attempt;
- GraphRevision topology, Ports, Edges or Composite materialization;
- EffectOperation lifecycle;
- Accounting or Reconciliation state;
- HumanRequest/HumanResponse truth;
- raw secrets/credentials;
- provider/browser/process/worker adapter internals;
- account/auth subsystem internals.

If implementation requires this subsystem to own any of those canonical states, that is an Architecture Finding.

---

## 3. Canonical Owner

Nyron introduces one logical **Project / Workspace Context Owner** (`PWP Owner`).

PWP Owner owns canonical truth for:
- `Project`;
- `Workspace`;
- `ProjectConfigRevision`;
- `WorkspaceConfigRevision`;
- `PolicyContextRevision`;
- `EnvironmentBindingRevision`;
- `IngressRoute` logical identity;
- `IngressRouteRevision`;
- archive/deprecation governance facts for those objects.

PWP Owner does not gain authority over any foreign Owner merely because its records contain references to foreign objects.

Examples:
- a WorkspaceConfig may reference `workspace_handle_profile_ref`; Resource Manager still owns actual Resource/Lease truth;
- a PolicyContextRevision may reference security policy; Capability Authority still decides Grant issuance;
- an IngressRouteRevision may reference a GraphRevision ingress binding; Graph owns that immutable topology and Runtime owns resulting execution;
- a config may reference `secret_ref`; secret storage and raw secret value remain outside this design.

---

## 4. Project Identity and Lifecycle

### 4.1 Project meaning

A `Project` is a stable logical product/work unit boundary under which Workspaces, configuration, policy context and ingress routes may be organized.

It is not:
- a Graph;
- a WorkflowExecution;
- an AccountingScope;
- a Resource;
- a CapabilityGrant.

Candidate canonical object:

```text
Project
- project_ref
- state
- created_at
- archived_at?
- display_metadata_ref?
- current_project_config_revision_ref
- current_policy_context_revision_ref?
- supersedes_project_ref?
```

`project_ref` is stable across configuration changes.

### 4.2 Project lifecycle

Candidate states:

```text
ACTIVE
DEPRECATED
ARCHIVED
```

Meaning:
- `ACTIVE` — may receive new mutable governance operations and may be used for new admission subject to applicable policy.
- `DEPRECATED` — remains resolvable and may remain usable where policy allows, but new use should be discouraged or denied by configured policy.
- `ARCHIVED` — no new ordinary execution admission or new workspace creation under the Project; historical resolution remains mandatory.

Archive is governance state, not deletion.

A Project referenced by historical executions MUST remain resolvable through its pinned revisions even after archival.

---

## 5. Workspace Identity and Lifecycle

### 5.1 Workspace meaning

A `Workspace` is a stable logical working-boundary identity used by configuration, policy, capability scope, external adapters and resource compatibility.

Candidate object:

```text
Workspace
- workspace_ref
- project_ref
- parent_workspace_ref?
- state
- created_at
- archived_at?
- current_workspace_config_revision_ref
- current_policy_context_revision_ref?
- current_environment_binding_revision_ref?
```

The following are permanently distinct:

```text
workspace_ref != host_absolute_path
workspace_ref != Resource.resource_ref
workspace_ref != ResourceLease.lease_ref
workspace_ref != mount_id
workspace_ref != checkout/session/browser/worker handle
```

### 5.2 Workspace lifecycle

Candidate states:

```text
ACTIVE
DEPRECATED
ARCHIVED
```

Archival forbids new ordinary admission against the Workspace unless an explicit administrative recovery/export contract permits a bounded non-execution operation.

Historical executions retain exact pinned Workspace and revision references.

### 5.3 Workspace Handle distinction

A live mounted/mutable Workspace Handle remains a Resource Manager concern under D-004/D-008.

PWP Owner may declare what logical binding a compatible Workspace Handle must satisfy. It cannot create, lease, revoke, fence, hydrate or destroy the live Resource by direct mutation.

---

## 6. Project / Workspace Relationship and Nesting

### 6.1 Project ownership relation

Every Workspace belongs to exactly one Project.

`project_ref` on Workspace is immutable after Workspace creation in v0.1.

Moving a Workspace across Projects is represented as export/import or clone/rebind into a new Workspace identity, not in-place identity reassignment.

This avoids rewriting policy ancestry and historical meaning.

### 6.2 Workspace nesting

Workspace nesting is optional and logical.

Rules:
- a Workspace has at most one `parent_workspace_ref`;
- parent and child MUST belong to the same Project;
- cycles are forbidden;
- nesting does not imply filesystem subdirectory containment;
- nesting does not implicitly inherit live ResourceLease authority;
- nesting may participate in policy/config inheritance only through explicit revisioned composition rules.

A child Workspace may declare a filesystem root located below a parent root, but that is an environment-binding fact, not the semantic meaning of parentage.

### 6.3 Stable ancestry

For authority/policy composition that depends on Workspace ancestry, the applicable ancestry must be captured in an immutable revision or snapshot reference used by the decision/admission. Mutable current ancestry cannot be re-resolved for historical executions.

---

## 7. Immutable ProjectConfig / WorkspaceConfig

Configuration changes produce new immutable revisions.

### 7.1 ProjectConfigRevision

```text
ProjectConfigRevision
- project_config_revision_ref
- project_ref
- revision_seq
- previous_revision_ref?
- config_schema_ref
- default_workspace_policy_ref?
- default_runtime_admission_policy_ref?
- default_environment_binding_policy_ref?
- default_ingress_policy_ref?
- user_policy_refs[]
- system_policy_refs[]
- extension_refs[]
- created_at
- caused_by_ref
```

### 7.2 WorkspaceConfigRevision

```text
WorkspaceConfigRevision
- workspace_config_revision_ref
- workspace_ref
- revision_seq
- previous_revision_ref?
- config_schema_ref
- root_declarations[]
- portability_descriptor_ref?
- environment_binding_revision_ref?
- workspace_policy_refs[]
- runtime_admission_policy_refs[]
- security_policy_refs[]
- secret_refs[]
- extension_refs[]
- created_at
- caused_by_ref
```

### 7.3 Revision rules

- revisions are immutable after commit;
- mutable `current_*_revision_ref` pointers may advance only by PWP Owner transition;
- historical consumers pin exact revisions;
- no execution may rely on resolving `latest/current` after admission;
- superseded revisions remain resolvable while referenced by canonical history.

Config revisions may contain references to immutable foreign revisions but may not copy foreign canonical state and claim ownership of it.

---

## 8. Canonical Policy Source Ownership

PWP Owner owns **policy-context composition records and policy-source references**, not all policy semantics in the system.

This distinction is essential.

### 8.1 PolicyContextRevision

```text
PolicyContextRevision
- policy_context_revision_ref
- subject_kind              # PROJECT or WORKSPACE
- subject_ref
- revision_seq
- previous_revision_ref?
- project_policy_refs[]
- workspace_policy_refs[]
- security_policy_refs[]
- runtime_admission_policy_refs[]
- user_policy_refs[]
- system_policy_refs[]
- composition_contract_ref
- created_at
- caused_by_ref
```

PWP Owner canonically records **which immutable policy sources apply as configuration context** and their composition order/relationship.

The owning policy authority for each policy class remains authoritative for that policy's semantics.

Examples:
- security policy source may be system-owned;
- Capability Authority consumes applicable policy sources and owns Grant decisions;
- Runtime consumes admission policy sources and owns execution admission decisions;
- Accounting consumes budget policy according to Accounting's own contract, not this one.

### 8.2 Policy documents are not Grants

A policy reference, policy evaluation input, allow rule or user approval reference is not a CapabilityGrant.

Only Capability Authority may commit Grant truth.

---

## 9. Policy Precedence and Restriction Composition

Nyron uses fail-closed restriction composition.

### 9.1 General rule

Applicable policies compose as the legal intersection of allowed behavior plus the union of applicable restrictions/requirements.

A more local policy may narrow authority but MUST NOT widen an applicable higher-authority restriction unless the higher-authority policy explicitly delegates a bounded widening mechanism.

Default architectural ordering for conflict resolution is by authority class, not UI placement:

```text
System security restrictions
∩ Project restrictions
∩ Workspace restrictions
∩ Runtime-admission restrictions
∩ User policy restrictions
∩ request-specific restrictions
```

This ordering is not a grant algorithm. It determines the immutable policy input set/precedence contract supplied to the actual deciding Owner.

### 9.2 Deny / require / allow semantics

At architecture level:
- hard deny dominates ordinary allow;
- mandatory requirement is cumulative unless mutually exclusive, in which case evaluation fails closed;
- absence of an allow where allowlisting is required means deny;
- unknown/unresolvable required policy input means admission/authority evaluation fails closed;
- human approval evidence cannot override a system-security deny unless that security policy explicitly defines such delegation.

### 9.3 No semantic duplication

PWP Owner MUST NOT independently answer "is this Attempt allowed to execute this capability?".

It only provides pinned policy/config context. Capability Authority or Runtime makes the relevant decision under its own contract.

---

## 10. Environment Binding Identity vs Live Resource

### 10.1 EnvironmentBindingRevision

Environment binding describes how a logical Workspace may be resolved in a particular environment without claiming a live handle exists.

```text
EnvironmentBindingRevision
- environment_binding_revision_ref
- workspace_ref
- revision_seq
- previous_revision_ref?
- environment_ref
- binding_entries[]
- portability_constraints[]
- created_at
- caused_by_ref
```

Candidate binding entry:

```text
EnvironmentBindingEntry
- binding_key
- binding_class
- logical_requirement_ref
- provider/profile_ref?
- local_root_descriptor?
- browser_profile_class_ref?
- worker_class_ref?
- process_profile_ref?
- resource_compatibility_descriptor_ref?
- secret_ref?
```

`binding_class` may identify logical classes such as local root, provider profile, browser profile, worker class or process environment. These are configuration categories, not live Resource types owned here.

### 10.2 No live-state claim

An EnvironmentBindingRevision proves only that a binding configuration was selected.

It does not prove:
- the path currently exists;
- a filesystem mount is live;
- a browser session exists;
- a worker is reachable;
- a provider session is authenticated;
- a ResourceLease has been granted.

Live availability/compatibility is established through Resource Manager/adapters at use time.

---

## 11. Workspace Root Declarations and Portability

### 11.1 Root declarations

WorkspaceConfigRevision may declare logical roots:

```text
WorkspaceRootDeclaration
- root_key
- root_role
- logical_path
- mutability_class
- required
- portability_class
- containment_policy_ref
```

`logical_path` is not necessarily a host absolute path. It may be resolved by the active EnvironmentBindingRevision.

### 11.2 Portability descriptor

A portability descriptor classifies what must be rebound when moving configuration between environments.

Candidate classes:
- `PORTABLE_LOGICAL` — no environment-specific identity required;
- `REBIND_REQUIRED` — logical requirement portable, local realization must be explicitly selected;
- `ENVIRONMENT_PINNED` — meaningful only in the identified environment unless explicitly migrated;
- `NON_EXPORTABLE_REFERENCE` — may be referenced historically but cannot be carried as active authority into another environment.

Portability metadata never transfers secrets, live Resources, leases or Grants.

---

## 12. Binding Revisions and Historical Pinning

Any execution whose correctness depends on project/workspace configuration must pin exact references at admission.

At minimum, a Runtime execution admission context must be able to record:

```text
ExecutionContextRefSet
- project_ref
- project_config_revision_ref
- workspace_ref?
- workspace_config_revision_ref?
- policy_context_revision_ref
- environment_binding_revision_ref?
- ingress_route_revision_ref?
- graph_revision_ref
```

The exact Runtime-owned schema may differ, but the semantic pinning is mandatory.

After admission:
- advancing current ProjectConfig does not alter the execution;
- advancing current WorkspaceConfig does not alter the execution;
- policy updates do not retroactively widen/narrow the already-pinned execution context;
- environment rebinding does not silently migrate the active execution.

Dynamic safety mechanisms remain separate. For example, Capability Authority may revoke an already-issued Grant under its own revocation semantics even though execution config is pinned. Pinning prevents silent mutable-context substitution; it does not disable explicit foreign-owner revocation.

---

## 13. Graph Execution Admission Context

PWP Owner provides revision references; Runtime owns admission.

Normative admission interaction:

```text
Start Intent / canonical ingress fact
→ resolve requested Project/Workspace logical identities
→ PWP Owner resolves exact admissible config/policy/binding revisions
→ Runtime validates immutable GraphRevision execution eligibility
→ Runtime consumes pinned policy context and foreign-owner decisions
→ Runtime commits WorkflowExecution admission with exact context refs
→ Runtime creates Trigger Packet
→ Delivery
→ Activation
```

Forbidden:
- PWP Owner creating Activation;
- PWP Owner selecting current Attempt;
- PWP Owner mutating GraphRevision;
- Runtime re-resolving mutable `current` policy/config for an already-admitted execution.

If Project/Workspace is archived, required revision is unresolved, or required binding is unavailable, admission fails closed unless an explicit owning policy defines a permitted administrative path.

---

## 14. External Ingress Route Registry

D-008 left ingress-route registry ownership open. This candidate assigns it to PWP Owner.

### 14.1 IngressRoute identity

`IngressRoute` is stable logical route identity.

```text
IngressRoute
- ingress_route_ref
- project_ref
- workspace_ref?
- state
- current_revision_ref
- created_at
- archived_at?
```

Candidate states:

```text
ACTIVE
DISABLED
DEPRECATED
ARCHIVED
```

Transport listeners/adapters are not canonical Owners of route identity.

### 14.2 IngressRouteRevision

```text
IngressRouteRevision
- ingress_route_revision_ref
- ingress_route_ref
- revision_seq
- previous_revision_ref?
- source_adapter_profile_ref
- source_auth_policy_ref
- input_schema_ref
- deduplication_contract_ref
- canonical_target_owner_ref
- canonical_event_type_ref
- canonicalization_contract_ref
- graph_ingress_binding_ref?
- graph_revision_ref?
- project_config_revision_ref
- workspace_config_revision_ref?
- policy_context_revision_ref
- enabled_from?
- enabled_until?
- created_at
- caused_by_ref
```

The route revision owns configuration of the route, not the canonicalized external event itself.

### 14.3 Canonical target Owner

Every route MUST identify the Owner that is authoritative for the canonicalized input fact.

Transport reception is never canonical truth by itself.

Examples:
- authenticated human-response route → Human Interaction Owner;
- provider billing callback → Accounting Owner;
- generic workflow trigger route → a designated ingress canonicalization Owner/event contract, then Runtime admission;
- subsystem-specific external callback → that subsystem's canonical Owner where appropriate.

PWP Owner configures this target; it does not mutate target Owner state directly.

### 14.4 Graph ingress binding

A workflow-starting route may pin an immutable GraphRevision ingress binding.

It MUST NOT resolve mutable `latest/current` Graph state when the canonical ingress fact is admitted for execution.

Execution path remains:

```text
External Input
→ adapter authentication/validation
→ target Owner canonical input fact
→ admitted immutable IngressRouteRevision / Graph ingress binding
→ Runtime-owned Trigger Packet
→ Delivery
→ Activation
→ Run / Attempt
```

Direct Activation creation is forbidden.

---

## 15. Route Authentication, Deduplication and Secrets

### 15.1 Authentication policy reference

IngressRouteRevision references an immutable authentication policy/profile. It does not contain raw credentials unless a separate approved secret subsystem contract explicitly allows encrypted material as an opaque foreign object.

Default rule:

```text
route config stores secret_ref, never raw secret value
```

### 15.2 Deduplication

Each route revision must define stable deduplication identity semantics appropriate to the source.

The deduplication contract may use:
- source event ID;
- signed delivery ID;
- provider callback ID;
- deterministic content+source identity where safe.

A duplicate transport delivery must not create duplicate canonical input facts merely because it arrived twice.

PWP Owner owns the revisioned deduplication configuration; the canonical target Owner/admission component performs deduplication according to the applicable contract within its own authority boundary.

---

## 16. Import / Export / Rebinding

### 16.1 Export semantics

Project/Workspace export may contain:
- logical identities or portable remapped identities;
- immutable config revisions;
- policy references where exportable;
- root declarations;
- portability descriptors;
- logical environment requirements;
- ingress route definitions where exportable;
- immutable Graph/package references under their own distribution contracts.

Export MUST NOT include as transferable authority:
- live Resource/ResourceLease;
- CapabilityGrant;
- current Runtime Attempt;
- active EffectOperation authority;
- raw credentials/secrets;
- historical external operation identity as current authority.

### 16.2 Import semantics

Import creates or resolves local logical identities and validates all immutable dependencies.

Importing policy/config does not imply trust or authorization.

A foreign policy reference that cannot be resolved to an accepted local authority remains unresolved and cannot silently become permissive.

### 16.3 Rebinding semantics

Rebinding maps logical environment requirements to a new `EnvironmentBindingRevision`.

Rebinding:
- is explicit and canonical;
- creates a new revision;
- never mutates historical revisions;
- never widens Capability scope implicitly;
- never transfers live ResourceLease authority;
- never copies raw secret values;
- may require new local policy approval.

A successful rebind means configuration is resolved, not that required live Resources are currently available.

---

## 17. Policy / Config Updates During Active Execution

Default v0.1 rule: **active executions remain pinned to the exact Project/Workspace/Policy/Binding revisions captured at admission.**

This prevents non-deterministic behavior where a mutable workspace policy changes the meaning of a running execution without a canonical transition.

Updates affect:
- new admissions after the new revision becomes current;
- explicit re-admission/restart flows;
- explicit foreign-owner safety revocations where that Owner's contract permits dynamic revocation.

Updates do not silently modify:
- the GraphRevision pinned by execution;
- prior CapabilityGrant history;
- already-committed Runtime Attempt identity;
- historical policy/config references.

If future product requirements demand live config adoption by running executions, that requires an explicit architecture contract defining opt-in transition, compatibility, fencing and replay semantics. It is not implicit in v0.1.

---

## 18. User/System Policy References

PWP config may reference user/system policy identities while remaining agnostic to account/auth subsystem internals.

Candidate reference shape:

```text
PolicyPrincipalRef
- principal_kind
- principal_ref
- policy_ref
- authority_domain_ref
```

PWP Owner may verify that references are syntactically/structurally resolvable. It does not authenticate users, issue identities, or define account sessions.

Authenticated identity evidence must come from the appropriate identity/auth authority when required by a policy decision.

---

## 19. Canonical vs Derived State

### 19.1 Canonical PWP state

Canonical:
- Project/Workspace identity and lifecycle state;
- immutable config revisions;
- immutable policy-context revisions;
- immutable environment-binding revisions;
- IngressRoute identity and revisions;
- current revision pointers;
- archive/deprecation transitions;
- explicit import/rebind commits.

### 19.2 Derived state

Derived/reconstructible:
- UI project tree;
- workspace search index;
- effective-policy explanation view;
- flattened config projection;
- route dashboards;
- environment availability dashboard;
- resolved local path cache;
- current "ready to execute" badge;
- compatibility suggestions;
- imported-package convenience mappings.

A derived projection must not become sole correctness authority.

An effective-policy projection may explain a decision input but cannot replace exact pinned policy references and decision evidence.

---

## 20. Cross-Owner Contracts

### 20.1 Graph ↔ PWP

PWP → Graph:
- Query immutable GraphRevision / ingress binding metadata.
- Validate exact references during config/route publication.

Graph → PWP:
- Event/Query evidence that referenced immutable definition exists, is archived/deprecated, or is execution-ineligible.

Boundary:
- PWP never mutates topology;
- Graph never mutates project/workspace identity.

### 20.2 Runtime ↔ PWP

Runtime → PWP:
- `ResolveAdmissionContext(project_ref, workspace_ref?, requested_route_ref?)`
- `GetPinnedConfigRevision`
- `GetPolicyContextRevision`
- `GetEnvironmentBindingRevision`

PWP → Runtime:
- exact immutable revision refs and lifecycle/admissibility facts;
- route binding context;
- durable config/policy revision events.

Boundary:
- Runtime owns final execution admission and all execution state.

### 20.3 Capability Authority ↔ PWP

Capability Authority → PWP:
- query exact applicable Project/Workspace policy context and `workspace_ref` scope metadata.

PWP → Capability Authority:
- immutable policy refs, workspace identity and binding descriptors as decision inputs.

Boundary:
- PWP does not issue/deny Grants;
- policy documents are inputs, not authority tokens.

### 20.4 Resource Manager ↔ PWP

Resource Manager → PWP:
- query logical Workspace identity, environment binding and compatibility requirements.

PWP → Resource Manager:
- binding/config descriptors and root requirements.

Resource Manager → PWP/Event consumers:
- Resource availability/loss/compatibility events as foreign evidence.

Boundary:
- PWP never owns live Resource or Lease state.

### 20.5 Accounting / Recovery ↔ PWP

Accounting may reference Project/Workspace identities for attribution/policy lookup where its own contract allows, but PWP does not own AccountingScope or BudgetPolicyRevision.

Recovery may reference exact config/binding/route revisions as evidence. PWP does not resolve foreign UNKNOWN subject truth.

### 20.6 External Interfaces ↔ PWP

External adapters → PWP:
- query route revision, environment binding, workspace root declaration and policy references.

PWP → adapters:
- immutable route/binding/config descriptors and secret references.

Adapters → target Owners:
- authenticated/validated evidence according to route contract.

Boundary:
- adapters do not mutate PWP identity/config outside PWP Commands.

### 20.7 Human Interaction ↔ PWP

PWP may reference Human Interaction policy/route targets.

Human Interaction owns HumanRequest/HumanResponse truth.

An ingress route targeting Human Interaction configures the boundary but PWP does not authenticate or commit the human response fact itself.

---

## 21. Commands / Queries / Events

Candidate PWP command vocabulary:

```text
CreateProject
CreateWorkspace
PublishProjectConfigRevision
PublishWorkspaceConfigRevision
PublishPolicyContextRevision
PublishEnvironmentBindingRevision
ArchiveProject
ArchiveWorkspace
DeprecateProject
DeprecateWorkspace
CreateIngressRoute
PublishIngressRouteRevision
EnableIngressRoute
DisableIngressRoute
ArchiveIngressRoute
ImportProjectContext
ImportWorkspaceContext
RebindWorkspaceEnvironment
```

Candidate queries:

```text
GetProject
GetWorkspace
GetProjectConfigRevision
GetWorkspaceConfigRevision
GetPolicyContextRevision
GetEnvironmentBindingRevision
ResolveAdmissionContext
GetIngressRouteRevision
ResolveWorkspaceAncestry
GetWorkspaceRootDeclarations
```

Candidate canonical events:

```text
ProjectCreated
ProjectDeprecated
ProjectArchived
WorkspaceCreated
WorkspaceDeprecated
WorkspaceArchived
ProjectConfigRevisionPublished
WorkspaceConfigRevisionPublished
PolicyContextRevisionPublished
EnvironmentBindingRevisionPublished
IngressRouteCreated
IngressRouteRevisionPublished
IngressRouteEnabled
IngressRouteDisabled
IngressRouteArchived
WorkspaceEnvironmentRebound
ContextImported
```

Command acknowledgement is not proof of commit; the corresponding canonical PWP event is evidence of committed state.

---

## 22. Invariants

### PWP-INV-01 — Single canonical owner
Project/Workspace identity, their revisioned configuration context and IngressRoute configuration have exactly one canonical Owner: PWP Owner.

### PWP-INV-02 — Logical Workspace identity is not a live Resource
`workspace_ref` MUST NOT be represented as `Resource`, `ResourceLease`, mount, host path or live handle.

### PWP-INV-03 — Live Resource ownership remains foreign
PWP Owner MUST NOT create, lease, revoke, fence, hydrate or destroy live Resources by direct canonical mutation.

### PWP-INV-04 — Policy input is not Grant authority
No policy/config reference owned by PWP is a CapabilityGrant or proof that an operation is authorized.

### PWP-INV-05 — Runtime execution remains Runtime-owned
PWP MUST NOT own WorkflowExecution, Packet, Delivery, Activation, Run, Attempt, retry, cancellation or terminal truth.

### PWP-INV-06 — Graph topology remains Graph-owned
PWP may pin GraphRevision/ingress references but MUST NOT own or mutate Graph topology.

### PWP-INV-07 — Revisions are immutable
Published ProjectConfig, WorkspaceConfig, PolicyContext, EnvironmentBinding and IngressRoute revisions are immutable.

### PWP-INV-08 — Historical pinning
Canonical executions and canonical ingress admissions that depend on PWP context MUST preserve exact revision refs needed to interpret history.

### PWP-INV-09 — No mutable current re-resolution
An admitted execution MUST NOT silently re-resolve `current/latest` project/workspace/policy/binding revisions.

### PWP-INV-10 — Policy restriction cannot be silently widened
Local/workspace/import/rebinding changes MUST NOT widen higher-authority restrictions except through an explicitly delegated policy mechanism.

### PWP-INV-11 — Import grants no authority
Import/export/rebinding does not import CapabilityGrant, ResourceLease, Runtime Attempt or live Effect authority.

### PWP-INV-12 — Secrets remain references
Raw secrets/credentials are not canonical PWP config values; PWP stores approved secret references only.

### PWP-INV-13 — Environment binding is configuration, not availability
An EnvironmentBindingRevision MUST NOT be interpreted as evidence that any live path, browser, provider, worker or process Resource exists.

### PWP-INV-14 — Workspace nesting is logical
Workspace parentage MUST NOT implicitly mean filesystem containment, Resource sharing, Lease sharing or authority inheritance.

### PWP-INV-15 — Project membership is stable
A Workspace cannot be in-place reassigned to a different Project in v0.1; cross-project move is new identity/import-rebind semantics.

### PWP-INV-16 — Ingress route Owner is explicit
Every IngressRouteRevision MUST identify canonical target Owner/event type before input may become authoritative internal truth.

### PWP-INV-17 — Transport reception is not canonical truth
Receiving a webhook/message/event does not by itself establish canonical system fact.

### PWP-INV-18 — No direct Activation ingress
Ingress routes MUST preserve canonical input -> Runtime Trigger Packet -> Delivery -> Activation. Direct Activation creation is forbidden.

### PWP-INV-19 — Route revisions are pinned
A canonicalized ingress used for execution MUST bind the exact applicable IngressRouteRevision and immutable Graph ingress binding, not a mutable route current pointer.

### PWP-INV-20 — Archive preserves history
Archival/deprecation MUST NOT destroy resolution of revisions referenced by canonical history.

### PWP-INV-21 — Active executions are revision-pinned
Ordinary Project/Workspace/config/policy updates affect future admissions, not existing executions, except explicit foreign-owner revocation/safety mechanisms.

### PWP-INV-22 — Cross-owner references do not transfer ownership
Referencing Capability, Resource, Graph, Accounting, Recovery, External Interface or Human Interaction identities never transfers mutation authority to PWP.

---

## 23. Failure and Resolution Semantics

PWP operations fail closed when required references or composition semantics cannot be resolved.

Examples:
- missing ProjectConfig revision;
- unknown workspace identity;
- archived workspace on new admission;
- unresolved required policy authority;
- invalid GraphRevision ingress reference;
- environment binding missing for required non-portable root;
- imported binding attempts implicit scope widening;
- route target Owner/event type unresolved.

These failures are configuration/admission facts. PWP MUST NOT repair them by fabricating live Resource, Grant, Runtime or Graph state.

---

## 24. Implementation Gates

Before implementation of PWP Owner v0.1 begins, Lead Design Authority should freeze or explicitly accept:

1. canonical PWP Owner assignment;
2. immutable revision model;
3. Workspace identity vs live Workspace Handle distinction;
4. policy-context ownership as input composition, not Grant authority;
5. execution context pinning rule;
6. EnvironmentBindingRevision distinction from live Resource;
7. IngressRoute / IngressRouteRevision ownership;
8. explicit target Owner/event type requirement;
9. no-direct-Activation ingress rule;
10. import/rebinding no-authority-widening rule;
11. archive/historical resolvability rule;
12. PWP-INV-01 through PWP-INV-22.

Implementation may choose storage schema, API naming, indexes and caching only if those choices preserve these semantics.

---

## 25. Open Questions

### OQ-PWP-01 — Exact global policy object taxonomy
This design defines PWP policy-source references/composition but intentionally does not define one universal `PolicyDocument` object or claim ownership of all policy semantics. Lead may later choose a shared policy registry if multiple domains need it.

### OQ-PWP-02 — Generic workflow ingress canonical target
D-008 requires every route to name a canonical target Owner/event type. For subsystem-specific callbacks this is clear. For a generic workflow-trigger webhook, the exact canonical pre-Runtime ingress fact Owner may need an explicit small ingress-domain contract if Runtime is not intended to own the authenticated external fact itself.

This does not block the invariant that transport is not canonical truth and that Runtime execution begins only through Trigger Packet -> Delivery -> Activation.

### OQ-PWP-03 — Project/Workspace policy ancestry mutation
v0.1 freezes Project membership and treats Workspace parentage as logical canonical state. If future requirements allow reparenting an existing Workspace, the operation must define historical ancestry pinning and policy transition semantics rather than editing ancestry in place.

### OQ-PWP-04 — Live policy adoption
v0.1 pins active executions. A future opt-in live-policy-adoption feature would require explicit compatibility/fencing/replay design.

---

## 26. Architecture Finding

**ARCHITECTURE FINDING — AF-PWP-001: Generic workflow-trigger ingress canonical fact ownership remains underspecified at the integrated system level.**

D-008 correctly requires every external route to identify a canonical target Owner/event type before driving Runtime. PWP can own route identity/configuration, but must not become the Owner of arbitrary external business facts merely because it configures routes.

For provider billing, human response and subsystem callbacks, the target Owner is naturally the corresponding subsystem. For a generic external event whose only purpose is to start a workflow, current baselines do not unambiguously state whether:
- Runtime owns a canonical `ExecutionIngressFact` after adapter authentication/canonicalization; or
- a distinct generic Ingress Owner owns that canonical fact and Runtime consumes its event.

This Candidate therefore does **not** invent that Owner. It freezes only the requirement that an IngressRouteRevision name the authoritative target and that no direct Activation path exists.

Lead Design Authority should resolve AF-PWP-001 during integration before generic workflow-trigger ingress implementation is treated as fully specified.

---

## 27. Candidate Result

This candidate assigns durable Project / Workspace / policy-context / environment-binding / ingress-route configuration ownership without crossing into live Resource, CapabilityGrant, Runtime Attempt or Graph topology authority.

No frozen Graph/Composite semantic change is proposed.

The only architecture finding is AF-PWP-001 concerning canonical ownership of a generic external workflow-trigger fact before Runtime Trigger Packet creation.
