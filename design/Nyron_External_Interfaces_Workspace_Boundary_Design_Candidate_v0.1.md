# Nyron External Interfaces / Workspace Boundary Design Candidate v0.1

Task ID: `NYRON-D-008`
Status: **CANDIDATE — FOR LEAD REVIEW**
Authority: delegated design candidate; not frozen
Depends on:
- `Universal_Runtime_Module_Design_Report_v0.1.md` — FROZEN MODULE ARCHITECTURE BASELINE
- `amendments/Module_Architecture_Amendment_001_EffectOperation_Prepared.md` — FROZEN MODULE ARCHITECTURE AMENDMENT
- `Nyron_Overall_System_Architecture_v0.1.md` — DRAFT
- `Nyron_Capability_Resource_Effect_Authority_Design_Candidate_v0.1.md` — D-004 authority foundation

## 1. Purpose

This design defines Nyron's external-world boundary model for workspace/filesystem, processes, network, browser, provider/model adapters, remote workers and external-event ingress.

It maps those domains onto the generic Capability / Resource / Effect model without turning user-visible integrations into Kernel primitives.

This document consumes D-004. It does **not** redefine CapabilityGrant, Resource, ResourceLease, EffectOperation, Attempt fencing, Accounting, Recovery or Graph topology.

The core rule is:

> External integrations are adapter-mediated uses of generic authority, resource and effect mechanisms. Browser, Shell, File, HTTP, Provider, Tool, Remote Worker and External Event are product/runtime integration families, not Kernel primitives.

## 2. Scope

In scope:
- external-world boundary taxonomy;
- workspace identity and Workspace Handle semantics;
- filesystem containment, symlink and mount boundary requirements;
- read versus write effect classification;
- process execution containment and kill/confirm semantics;
- network destination scope and mediated requests;
- browser observation versus consequential actions;
- provider/model adapter semantics;
- remote worker/job mapping;
- credential/secret usage boundary at architecture level;
- external-event ingress authentication, validation and canonicalization;
- adapter trust and TCB responsibilities;
- host isolation claims and profiles;
- durable external IDs, idempotency and lookup requirements;
- portability implications of environment-bound resources;
- unsafe raw-access prohibitions;
- cross-owner contracts to Runtime, Capability Authority, Resource Manager, Effect Authority and Recovery.

Out of scope:
- secret-store internals;
- provider-specific API schemas;
- concrete browser engine;
- concrete process sandbox implementation;
- concrete VM/container/WASM technology;
- Runtime retry/replacement policy;
- Accounting settlement mechanics;
- ReconciliationCase state machine;
- Graph topology;
- Product Node taxonomy.

## 3. External World Boundary Taxonomy

Nyron treats an external-world boundary as any mediated point at which execution observes, depends on, or changes state that is not owned as canonical Nyron state by the executing Module.

The boundary is classified by operation semantics, not by product label.

### 3.1 Boundary families

1. **Workspace / Filesystem Boundary**
   - file/directory observation;
   - persistent file mutations;
   - workspace mount/handle lifecycle.

2. **Process Boundary**
   - process start;
   - stdin/stdout/stderr interaction;
   - process-group lifecycle;
   - signal/terminate/kill/confirm-stop.

3. **Network Boundary**
   - DNS/name resolution under policy;
   - outbound connection/request;
   - upload/download;
   - protocol-specific request mediation.

4. **Browser Boundary**
   - Browser Session lifecycle;
   - DOM/screenshot/navigation observation;
   - state-changing page interactions.

5. **Provider / Model / Tool Boundary**
   - provider request dispatch;
   - provider sessions;
   - streaming;
   - cancellation;
   - external request identity and lookup.

6. **Remote Worker Boundary**
   - remote job dispatch;
   - remote execution/resource lifecycle;
   - cancellation/fencing/lookup.

7. **External Event Ingress Boundary**
   - webhook/event/message reception;
   - authentication;
   - schema validation;
   - canonicalization into trusted owner-local facts/events.

### 3.2 No Kernel hardcoding

Kernel Foundation must not contain dedicated Browser, Shell, HTTP, Claude, Codex, GitHub, filesystem or remote-worker primitives.

The Kernel only supplies generic identity, canonical persistence, owner enforcement, fencing, causal references and transaction foundations.

Adapter families are registered/configured above that foundation and are mapped to CapabilityTypes, Resources and EffectOperations.

## 4. Generic Operation Classification

Each external operation independently answers:

1. Which CapabilityGrant is required?
2. Which Resource / ResourceLease is required, if any?
3. Is an EffectOperation required?
4. What external identity/evidence is available for lookup, cancellation or reconciliation?
5. Can the operation be replayed/idempotently retried, or can duplicate dispatch create harm?

No external family is assumed to require all three generic mechanisms.

### 4.1 Observation versus consequence

A useful architecture-level split is:

- **Observation operation** — obtains external state without intentionally creating externally persistent change.
- **Consequential operation** — may create, modify, delete, send, publish, submit, execute, allocate, charge or otherwise create persistent/externally meaningful change.

Observation is not automatically safe. It may still require Capability and Resource controls, may expose secrets, and may trigger provider-side logging/cost. However, an observation normally does not require an EffectOperation unless its external semantics are independently retryable/cancellable/ambiguous or otherwise require external-history tracking.

A consequential operation normally requires an EffectOperation.

## 5. Workspace Identity versus Workspace Handle

### 5.1 Workspace identity

`workspace_ref` identifies a logical workspace/project boundary in Nyron configuration or policy.

It is not itself a Resource and does not imply an active filesystem mount, open directory descriptor, network share, checkout, container volume or local path.

A workspace identity may include immutable or canonical metadata such as:

```text
WorkspaceIdentityDescriptor
- workspace_ref
- policy_scope_ref
- portability_class
- declared_roots[]
- environment_binding_descriptor?
```

The exact storage owner of product/project metadata is outside this document.

### 5.2 Workspace Handle

A live mounted or otherwise stateful filesystem access handle may be represented as a D-004 `Resource` with a ResourceLease.

Examples:
- local directory capability broker;
- mounted repository checkout;
- remote filesystem mount;
- container workspace mount;
- ephemeral job working directory.

The Workspace Handle is opaque to Modules. Modules receive broker/proxy access, not unrestricted host paths or raw OS handles.

### 5.3 Identity and live handle are distinct

The following must never be conflated:

```text
workspace_ref != host_absolute_path
workspace_ref != mount_id
workspace_ref != Resource.resource_ref
workspace_ref != raw file descriptor
```

A Workspace Handle may be replaced or rehydrated while preserving the same logical workspace identity only if Resource Manager policy can prove the handle still satisfies the same workspace scope and compatibility constraints.

## 6. Path Containment Requirements

Workspace access must be resolved against an Authority-approved workspace scope.

### 6.1 Canonical containment rule

A request path must be interpreted relative to an approved workspace root or another explicitly scoped root. Access outside the effective root is denied.

Containment must be checked on the resolved filesystem target, not only on the lexical request string.

Therefore lexical checks such as rejecting `..` are necessary but insufficient.

### 6.2 Required defenses

The mediation layer must account for:
- `..` traversal;
- absolute-path injection;
- path separator variants;
- symlink traversal;
- junction/reparse-point traversal where applicable;
- bind mounts / mount points;
- case sensitivity/case folding differences;
- Unicode/path normalization differences;
- TOCTOU between path validation and use;
- replacement of an ancestor directory after validation.

### 6.3 Symlink policy

Capability scope must be able to express whether symlink traversal is:
- forbidden;
- allowed only when the final resolved target remains inside the approved root;
- allowed to explicitly enumerated external targets.

A symlink must never expand authority beyond the CapabilityGrant scope.

### 6.4 Mount boundary policy

Crossing a filesystem mount boundary is not implicitly permitted merely because the mount is lexically nested under an approved directory.

IsolationProfile / workspace policy must define whether nested mounts are:
- denied by default;
- allowed if mounted before lease creation and included in scope evidence;
- explicitly allowlisted by mount identity/path policy.

### 6.5 Race-safe access

Where the host OS permits it, implementations should prefer directory-handle-relative APIs and no-follow / handle-based resolution so containment and use refer to the same object identity.

If the platform cannot provide race-safe guarantees, the IsolationProfile must disclose the weaker claim rather than presenting lexical containment as hostile-code isolation.

## 7. Workspace Read versus Write Classification

### 7.1 Read

Typical workspace reads:
- open/read file;
- stat/list directory;
- compute hash;
- inspect metadata.

Requirements:
- `WORKSPACE_READ` CapabilityGrant;
- optional Workspace Handle Resource/Lease;
- usually no EffectOperation.

A read that itself triggers externally consequential behavior through a special filesystem or device path must not be treated as a normal workspace read.

### 7.2 Write

Typical writes:
- create;
- overwrite;
- append;
- rename/move;
- delete;
- chmod/permission change;
- symlink creation;
- persistent extraction/unpack;
- checkout/update that mutates the workspace.

Requirements:
- `WORKSPACE_WRITE` CapabilityGrant;
- Workspace Handle Resource/Lease when a managed live handle is used;
- EffectOperation for persistent consequential mutation.

### 7.3 Atomic file operations

OS-level atomic rename/write does not create atomicity with Nyron's canonical store.

The EffectOperation exists because a crash can occur between external filesystem mutation and Nyron's canonical recording of the result.

Recovery evidence may include:
- deterministic destination identity;
- content hash;
- file ID/inode where portable enough;
- expected old/new revision hash;
- temp-file identity;
- external journal identity.

If reliable history cannot be determined, the EffectOperation becomes UNKNOWN.

## 8. Process Boundary

### 8.1 Process start

Process start is consequential and requires:
- `PROCESS_EXEC` CapabilityGrant;
- an EffectOperation;
- optional Resource when a reusable managed process/session abstraction exists.

The EffectOperation must be PREPARED before external spawn when crash ambiguity is possible.

### 8.2 Process identity

A raw PID is weak evidence because PIDs may be reused.

The adapter should use the strongest available external identity, such as:
- process-group/job-object identity;
- PID plus process start identity;
- cgroup/container/job identity;
- adapter-generated launch token bound to durable launch metadata.

The identity must support lookup where the platform allows it.

### 8.3 Child-process containment

The host must not claim process containment if it can only track the parent PID.

An IsolationProfile claiming contained execution must provide a mechanism that captures descendants, such as:
- process group/session;
- OS Job Object;
- cgroup;
- container boundary;
- equivalent enforceable descendant ownership mechanism.

Children must not escape scope merely because they were spawned indirectly.

### 8.4 Inherited authority

`PROCESS_EXEC` does not automatically grant arbitrary filesystem or network authority to child processes.

If untrusted code can directly access host filesystem/network outside Nyron's mediation, the host cannot claim those authority boundaries are enforced.

The IsolationProfile must state whether child access is:
- fully mediated;
- OS-sandbox restricted;
- broadly trusted/unrestricted.

### 8.5 Kill / confirm semantics

Attempt replacement or cancellation may cause Effect Authority to request process revocation.

Expected semantics:

```text
ACTIVE
→ REVOKE_REQUESTED
→ terminate/kill process group
→ confirm all owned descendants stopped
   ├─ yes → FENCED
   └─ cannot confirm → UNKNOWN
```

Sending a kill signal is not proof of FENCED.

Timeout while waiting for termination is not proof of termination.

If descendant escape cannot be excluded, the operation cannot be represented as safely fenced.

## 9. Network Boundary

### 9.1 Mediated request rule

Network access must occur through a controlled adapter/proxy or through an IsolationProfile that enforces equivalent destination restrictions.

Modules must not receive unrestricted raw sockets by default.

### 9.2 Destination scope

`NETWORK_ACCESS` scope must be machine-checkable and may include:
- protocol/scheme;
- hostname/domain pattern;
- resolved IP/CIDR class;
- port range;
- request method/class;
- endpoint/path restrictions where meaningful;
- TLS requirements;
- private/link-local/loopback policy;
- redirect policy.

### 9.3 DNS rebinding / resolution

Host authorization based only on an original hostname string is insufficient when the resolved destination may change authority meaning.

Adapters must define how policy applies across DNS resolution and connection establishment.

Where private-network access is not allowed, the adapter must prevent an allowlisted public hostname from resolving/redirecting to disallowed private/link-local/loopback destinations.

### 9.4 Redirects

Redirects are new destination decisions. The adapter must re-evaluate destination policy for each redirect hop unless policy explicitly authorizes the full redirect class.

### 9.5 Observation versus mutation

Examples usually treated as observation:
- GET/HEAD to approved endpoints;
- read-only API query.

Examples usually consequential:
- POST/PUT/PATCH/DELETE;
- message send;
- upload;
- transaction submission;
- remote job creation.

HTTP method alone is not definitive. Adapter metadata or registered operation semantics may classify a nominal GET as consequential if the external service behaves that way.

Consequential network operations normally require EffectOperation.

## 10. Browser Boundary

### 10.1 Browser Session Resource

A browser session/profile/page-set may be a Resource.

The Resource may carry continuity such as cookies, authenticated session state, open pages or browser context, but it must not become the sole canonical source of workflow truth.

### 10.2 Capability composition

Browser operations may require a dedicated registered CapabilityType such as `BROWSER_CONTROL` plus destination restrictions through `NETWORK_ACCESS`, depending on policy.

The exact capability vocabulary remains D-004 territory; this document only requires that browser authority be expressible as scoped generic grants.

### 10.3 Observation operations

Typical browser observations:
- DOM read;
- accessibility tree read;
- screenshot;
- page title/URL query;
- local element lookup.

These normally require browser capability and Browser Session lease but no EffectOperation.

### 10.4 Consequential actions

Typical consequential actions:
- form submit;
- send message;
- upload;
- purchase/transaction confirmation;
- account-setting change;
- deletion;
- publication;
- navigation that intentionally triggers a state-changing endpoint;
- download whose persistent placement mutates an approved workspace.

Each action that can independently be retried, cancelled, produce ambiguity or create externally meaningful state should receive its own EffectOperation.

### 10.5 UI ambiguity

The adapter must not infer that a click is harmless solely from UI presentation. A click on a button labeled "View" can still trigger a consequential endpoint.

Where adapter semantics cannot classify the action reliably, policy should default to the more restrictive consequential classification or require explicit user/module declaration validated by the adapter.

## 11. Provider / Model Adapter Boundary

### 11.1 Adapter responsibility

Provider/model adapters translate generic model invocation requests into provider-specific APIs while preserving Nyron's authority and external-history semantics.

Adapters may hold controlled provider credentials as TCB components but do not own Runtime Attempt, BudgetReservation, CapabilityGrant, ResourceLease or EffectOperation canonical truth.

### 11.2 Provider Session Resource

Conversation/session/thread/cache handles may be modeled as Resources when they are stateful and managed.

A provider session is not workflow canonical truth. If a provider session disappears, Nyron must still be able to explain committed history.

### 11.3 Invocation

A provider invocation normally requires:
- `MODEL_INVOKE` CapabilityGrant;
- optional Provider Session ResourceLease;
- EffectOperation.

EffectOperation PREPARED must exist before dispatch if dispatch can become ambiguous across crash.

### 11.4 Streaming

Streaming does not create a series of separate external invocation effects by default.

One provider request is normally one EffectOperation whose state remains ACTIVE while the request is externally active.

Stream chunks may be:
- transient transport observations;
- durable evidence/events if another contract requires durable chunk semantics;
- accumulated into a final Module output.

Provider token-stream memory is not a substitute for Nyron Continuation.

### 11.5 Cancellation

Cancellation is a request, not proof.

```text
ACTIVE → REVOKE_REQUESTED
→ provider cancel
→ provider confirms terminal cancellation/no further effect
   ├─ reliable confirmation → FENCED
   └─ uncertain → UNKNOWN
```

A local HTTP connection close alone is not proof that provider computation stopped.

### 11.6 Timeout ambiguity

Client timeout means only that Nyron did not obtain a timely result.

It must not be automatically mapped to external failure.

If the provider may have accepted or completed the request and no reliable lookup/idempotency evidence exists, EffectOperation becomes UNKNOWN.

### 11.7 Retry safety

Safe redispatch requires one of:
- proof old operation was never dispatched;
- proof old operation is FENCED;
- proof old operation completed and policy intentionally starts a new distinct operation;
- provider-supported idempotency identity that safely deduplicates duplicate dispatch;
- explicit policy accepting duplicate consequences.

## 12. Remote Worker / Remote Job Mapping

### 12.1 Remote worker session

A reusable remote worker connection/agent/session may be a Resource.

### 12.2 Remote job

Creating a remote job is consequential and requires an EffectOperation.

The external job ID should be recorded as `external_operation_ref` or equivalent evidence.

If the remote platform itself exposes a long-lived job handle useful beyond effect tracking, it may additionally be modeled as a Resource, but the Resource must not replace EffectOperation history.

### 12.3 Fencing

Remote job cancellation follows the same generic semantics:

```text
ACTIVE → REVOKE_REQUESTED
→ remote cancel
→ remote lookup/terminal evidence
   ├─ stopped → FENCED
   ├─ completed → COMPLETED
   └─ uncertain → UNKNOWN
```

A disconnected worker channel is not proof that the remote job stopped.

### 12.4 Result acceptance

Remote results remain subject to Runtime current-Attempt/commit fencing. A stale remote job may return data, but stale Attempt output cannot canonical-commit.

## 13. Credential / Secret Usage Boundary

This design does not define secret-store internals.

Architecture requirements are:

1. Modules should not receive raw long-lived credentials unless a specifically trusted execution profile requires it.
2. Preferred model is credential use inside a trusted adapter/broker.
3. Capability scope governs allowed operation/destination/provider; possession of a secret does not replace authorization.
4. Resource existence does not imply credential authority.
5. Credentials must not be embedded into Packet, Continuation, Module config, logs or durable canonical history unless the owning secret system explicitly defines a safe reference representation.
6. Durable records should store secret references/credential binding identities, not secret values.
7. Adapter error messages and telemetry must avoid secret leakage.
8. Exported workflows must not silently export environment secrets.

If a future secret subsystem provides short-lived delegated credentials, those credentials must still remain subordinate to current Attempt and Capability fencing at the actual effect boundary.

## 14. External Event Ingress

### 14.1 External input is not canonical internal truth

An event arriving from webhook, queue, email, provider callback, filesystem watcher, browser callback or remote worker begins as untrusted external input.

It becomes trusted canonical truth only after an authoritative ingress/target Owner performs validation and commits an internal canonical fact/event.

### 14.2 Ingress stages

```text
receive bytes/message
→ establish transport/source context
→ authenticate source where required
→ validate freshness/replay controls
→ validate schema
→ normalize/canonicalize representation
→ bind external identity and source identity
→ apply deduplication/idempotency rules
→ target Owner decides whether to commit canonical fact
→ durable canonical Event/record
```

### 14.3 Authentication

Ingress adapters may validate:
- signature/HMAC;
- mTLS/client identity;
- OAuth/provider identity;
- queue/topic identity;
- source IP only as weak supplementary evidence;
- secret token;
- provider lookup confirmation.

Authentication policy is explicit per ingress type and must not be inferred from network reachability alone.

### 14.4 Validation

Validation must cover:
- schema/version;
- required identifiers;
- payload size limits;
- freshness/time window when relevant;
- replay nonce/event ID where available;
- source-to-target binding;
- allowed event type.

### 14.5 Canonicalization

Canonicalization must remove transport-dependent ambiguity before owner commit.

Examples:
- normalize provider event type/version;
- extract stable external event ID;
- normalize encoding;
- establish source identity;
- compute canonical payload hash;
- preserve raw evidence reference when required for audit/recovery.

### 14.6 Duplicate ingress

Transport exactly-once delivery is not assumed.

The target Owner or ingress owner must deduplicate using stable event identity or an explicitly defined canonicalization key.

Same external event ID with conflicting payload must be rejected/escalated; it must not silently overwrite earlier meaning.

## 15. Adapter Trust and TCB Responsibilities

Adapters that mediate external effects are part of the Trusted Computing Base for the authority they enforce.

A trusted adapter must:
- accept only broker-issued operation requests;
- revalidate current Attempt/fencing/Capability scope at the actual boundary;
- validate applicable ResourceLease;
- avoid widening scope during translation;
- preserve operation identity/idempotency metadata;
- surface external IDs and acknowledgements;
- support lookup/cancel where promised by the adapter profile;
- distinguish timeout from confirmed failure;
- avoid fabricating completion/fencing evidence;
- redact credentials/secrets;
- report evidence to the owning Nyron subsystems through cross-owner interfaces.

Adapters do not receive authority to mutate arbitrary canonical state.

## 16. Host Isolation Claims and Profiles

Nyron must describe isolation as an explicit profile/claim set rather than a vague `sandboxed=true` boolean.

Candidate conceptual profile:

```text
IsolationProfile
- profile_ref
- module_code_trust_class
- filesystem_enforcement_claim
- network_enforcement_claim
- process_descendant_containment_claim
- credential_exposure_claim
- raw_os_api_access_claim
- host_escape_assumptions
- supported_adapter_boundaries[]
- verification_evidence / implementation_profile_ref
```

Examples of claims:
- trusted builtin, unrestricted host APIs;
- OS process with filesystem broker but unrestricted outbound network;
- container with scoped mounts and egress proxy;
- hostile-plugin isolation with enforced process/filesystem/network boundaries.

A trusted builtin profile may intentionally grant broad access, but it must not be presented as hostile-code containment.

Implementation acceptance tests must validate the exact claims made by each profile.

## 17. Durable External IDs, Idempotency and Lookup

### 17.1 External IDs

Where an external system offers a stable operation ID, job ID, request ID, message ID, transaction ID, process identity or artifact identity, adapters should persist it as EffectOperation or ingress evidence.

### 17.2 Idempotency identity

Nyron's internal `operation_ref` is stable canonical identity.

When the external system supports idempotency keys, the adapter should derive or bind a stable external idempotency key to the Nyron operation identity in a way that survives retry/recovery.

Reusing the same idempotency key for a semantically different operation is forbidden.

### 17.3 Lookup requirement

Adapters that claim crash-safe ambiguity resolution should provide lookup by durable external identity or equivalent evidence.

If no lookup/idempotency/evidence exists, the system must admit the weaker semantics: crash after dispatch may produce UNKNOWN.

### 17.4 Never guess from absence

No response, missing stream, disconnected socket, missing process listing or provider timeout is not automatically proof that an operation never occurred.

## 18. Import / Export and Portability

### 18.1 Definitions versus environment bindings

Exportable workflow/Module definitions may reference logical requirements such as:
- workspace requirement;
- provider class/model capability;
- browser capability;
- remote worker class;
- network destination policy class.

They should not silently embed environment-specific live Resource references.

### 18.2 Non-portable data

Typically non-portable unless explicitly re-bound:
- live Workspace Handle `resource_ref`;
- absolute host path;
- Browser Session ID;
- Provider Session ID;
- process PID/group;
- remote job ID;
- credential value/reference bound to local secret store;
- local container/VM identity.

### 18.3 Import semantics

Import may preserve unresolved logical bindings for user repair, but execution must remain non-executable until required environment bindings, capabilities and resources can be resolved.

Import must not silently map a logical workspace/provider/resource requirement to a broader local authority scope.

### 18.4 Rebinding

Environment rebinding is an explicit operation performed by the appropriate product/configuration/authority layers.

Rebinding creates new local bindings; it does not mutate historical external identities in prior execution history.

## 19. Unsafe Raw-Access Prohibitions

For untrusted or restricted Module execution, the following are forbidden unless an IsolationProfile explicitly declares the execution trusted and policy allows it:

- raw unrestricted filesystem APIs;
- arbitrary host absolute path access;
- direct subprocess spawning outside the process adapter;
- raw unrestricted sockets;
- direct browser automation session handles that bypass broker checks;
- raw provider credentials;
- direct provider SDK use that bypasses EffectOperation preparation;
- direct remote-worker protocol access;
- raw canonical DB/StateStore access;
- direct mutation of CapabilityGrant/ResourceLease/EffectOperation records;
- hidden durable semantic state in adapter-local files/databases that Nyron canonical history cannot interpret.

A broker API that merely wraps a raw unsafe object without enforcing authority is not mediation.

## 20. Cross-Owner Interfaces

This section defines required interaction directions, not concrete transport APIs.

### 20.1 Runtime ↔ External Interface Layer

Runtime supplies:
- Activation/Run/Attempt identity;
- current fencing context;
- requested operation intent;
- cancellation/replacement facts through canonical interfaces.

External adapters must not decide which Attempt is current.

External adapters return observations/evidence; Runtime remains owner of Attempt lifecycle and output commit eligibility.

### 20.2 Capability Authority

Before each actual external boundary crossing, adapter/host must validate:
- required CapabilityGrant exists;
- Grant is ACTIVE/current under D-004 semantics;
- Attempt/fencing token remains current;
- requested operation is within scope.

External layer may Query/Validate grants or consume durable authority evidence through the D-004 contract but does not mutate CapabilityGrant directly.

### 20.3 Resource Manager

Adapters request/consume managed resources through Resource Manager contracts.

Before resource use, validate:
- Resource compatibility;
- ResourceLease belongs to current holder/Attempt;
- fencing token matches;
- lease state permits use.

Adapter may report external loss, hydration evidence, detach result or destroy evidence; Resource Manager remains canonical owner.

### 20.4 Effect Authority

Consequential operations use Effect Authority:

```text
PrepareEffect
→ PREPARED committed
→ adapter revalidates authority
→ dispatch
→ report dispatch/ack/external ID
→ ACTIVE/COMPLETED or later revoke/UNKNOWN evidence
```

Adapter never directly changes EffectOperation canonical state.

### 20.5 Recovery

When external history cannot be reliably determined, the responsible owner transitions/requests transition to UNKNOWN under D-004 rules and hands evidence to Recovery/Reconciliation.

External adapters provide evidence and lookup capability; they do not resolve Recovery policy.

## 21. Crash and UNKNOWN Case Matrix

### 21.1 Workspace write

Crash after PREPARED but before write:
- use temp/destination/hash evidence where possible;
- if proven absent and no dispatch occurred, operation may safely fence/retry according to owner policy;
- if ambiguous, UNKNOWN.

Crash after write before completion commit:
- inspect destination identity/hash/revision evidence;
- if exact expected mutation proven, complete;
- if conflicting/uncertain, UNKNOWN.

### 21.2 Process start

Crash after spawn before ACTIVE commit:
- lookup using durable launch/process-group identity;
- if matching process exists, ACTIVE;
- if reliable evidence proves no spawn, safe non-dispatch path;
- otherwise UNKNOWN.

### 21.3 HTTP/provider mutation

Timeout/disconnect after dispatch:
- lookup by external request/idempotency key;
- complete/active if proven;
- retry only if dedupe semantics prove safe;
- otherwise UNKNOWN.

### 21.4 Browser action

Crash after click/submit before result:
- inspect external/application evidence if the action has stable transaction identity;
- DOM state alone may be insufficient;
- unresolved consequence → UNKNOWN.

### 21.5 Remote job

Connection lost after job creation:
- query by remote job ID;
- map reliable terminal state to COMPLETED/FENCED;
- unknown remote state → UNKNOWN.

## 22. Product Mapping

Future user-visible nodes map as follows:

| Product concept | Generic execution mapping |
| --- | --- |
| File Read | Module + WORKSPACE_READ + optional Workspace Handle |
| File Write | Module + WORKSPACE_WRITE + Workspace Handle + EffectOperation |
| Shell | Module + PROCESS_EXEC + EffectOperation + optional process Resource |
| HTTP Read | Module + NETWORK_ACCESS + optional no EffectOperation |
| HTTP Mutation | Module + NETWORK_ACCESS + EffectOperation |
| Browser Observe | Module + Browser Session Resource + scoped browser/network capability |
| Browser Action | Module + Browser Session Resource + scoped capability + EffectOperation |
| Claude/Codex/model call | Module + MODEL_INVOKE + optional Provider Session + EffectOperation |
| Tool call | Module + registered tool capability + optional Tool Session + EffectOperation if consequential |
| Remote Worker | Module + remote execution capability + Remote Worker Resource + Remote Job EffectOperation |
| External Event | ingress adapter → authenticated/validated/canonicalized Event/Packet path |

None of these require a new Kernel primitive.

## 23. Architecture Invariants

### EIW-INV-01 — No Product Integration Becomes Kernel Primitive
Browser, Shell, File, HTTP, Provider/Model, Tool, Remote Worker and External Event integrations are expressed through generic Module + Capability + Resource + Effect mechanisms.

### EIW-INV-02 — Workspace Identity Is Not a Live Handle
`workspace_ref` must not be treated as a raw path, mount, file descriptor or ResourceLease.

### EIW-INV-03 — Resolved Containment
Workspace scope enforcement must validate the resolved target and must not rely only on lexical path checks.

### EIW-INV-04 — Symlink Cannot Widen Authority
Symlink/junction/reparse traversal must never grant access outside the effective approved scope.

### EIW-INV-05 — Mount Crossing Is Explicit
Nested mount/bind boundaries are denied or explicitly authorized by policy/profile; lexical nesting alone does not authorize them.

### EIW-INV-06 — Persistent Workspace Mutation Is Consequential
Persistent filesystem mutation requires write authority and external-effect tracking when crash ambiguity can affect history.

### EIW-INV-07 — Process Start Is an Effect
Process creation is represented as an EffectOperation; parent PID alone is insufficient containment evidence.

### EIW-INV-08 — Kill Request Is Not Fencing Evidence
A process/job/provider/browser cancellation request does not prove the external effect is stopped. FENCED requires reliable confirmation.

### EIW-INV-09 — Descendants Remain Inside Claimed Process Boundary
An isolation profile claiming process containment must control relevant child/descendant processes, not only the parent.

### EIW-INV-10 — Process Capability Does Not Imply Child I/O Authority
`PROCESS_EXEC` must not be interpreted as implicit unrestricted filesystem/network authority.

### EIW-INV-11 — Network Scope Is Revalidated at Effective Destination
DNS resolution and redirects must not silently widen network authority.

### EIW-INV-12 — Browser Observation and Consequence Are Distinct
Browser reads may be observation operations; consequential actions require appropriate effect tracking.

### EIW-INV-13 — Timeout Is Not External Failure
Network/provider/browser/remote-worker timeout or disconnect must not be treated as proof that an external operation failed or never occurred.

### EIW-INV-14 — External Cancellation Is a Request Until Proven
Cancellation transitions to FENCED only with reliable external evidence.

### EIW-INV-15 — Provider Streaming Does Not Replace Continuation
Provider token-stream state must not be used as hidden Run Continuation or workflow truth.

### EIW-INV-16 — External Event Is Untrusted Until Canonicalized
Ingress data becomes internal canonical truth only after authentication/validation/canonicalization and authoritative owner commit.

### EIW-INV-17 — Duplicate External Events Are Safe
Ingress must support stable deduplication/idempotent handling; duplicate transport delivery must not create duplicate canonical facts.

### EIW-INV-18 — Adapter Cannot Widen Authority
Adapter translation must preserve or narrow Capability scope and must never infer broader authority from credentials, resource possession or provider session state.

### EIW-INV-19 — Credentials Are Not Authority
Possession of a credential does not replace Capability validation, Attempt fencing or ResourceLease checks.

### EIW-INV-20 — External Identity Is Preserved When Available
Stable external operation/event identities and idempotency keys must be durably bound to Nyron canonical operation/evidence identity when required for recovery safety.

### EIW-INV-21 — Absence Is Not Proof
Missing response, connection loss, absent stream or unconfirmed process listing must not be converted into guessed non-dispatch/non-completion.

### EIW-INV-22 — Live Environment Resources Are Not Portable Definition State
Exports must not silently embed live Workspace Handle, Browser Session, Provider Session, PID/process-group, remote job or credential bindings as portable executable truth.

### EIW-INV-23 — Raw Restricted Access Is Forbidden
Restricted Modules must not bypass mediated filesystem, process, network, browser, provider, remote-worker or canonical-state boundaries.

### EIW-INV-24 — Isolation Claims Are Explicit and Testable
Nyron must not claim hostile-code isolation unless the selected IsolationProfile can enforce and test the claimed filesystem, network, process and credential boundaries.

### EIW-INV-25 — Resource Is Not Effect History
Browser/provider/workspace/remote Resources may preserve continuity but must not replace EffectOperation or canonical workflow history.

### EIW-INV-26 — Effect Authority Remains Owner
External adapters/hosts report evidence but must not directly mutate EffectOperation canonical state.

### EIW-INV-27 — Capability Authority Remains Owner
External adapters/hosts validate and consume Grants but must not directly mutate CapabilityGrant canonical state.

### EIW-INV-28 — Resource Manager Remains Owner
External adapters/hosts use and report on Resources/Leases but must not directly mutate their canonical lifecycle.

## 24. Implementation Gates

### Gate EIW-G1 — Generic Broker Contracts
Before external adapters are implementation-authoritative:
- generic host/broker request envelope is defined;
- current Attempt/fencing context is carried;
- Capability validation occurs at actual boundary;
- ResourceLease validation occurs where applicable;
- EffectOperation PREPARED-before-dispatch path is implemented for consequential operations.

### Gate EIW-G2 — Workspace Safety
Before untrusted Modules receive workspace access:
- resolved containment implemented;
- symlink/junction policy enforced;
- mount-boundary policy implemented;
- TOCTOU posture documented/tested;
- read/write distinction tested;
- no raw host path escape in claimed isolation profile.

### Gate EIW-G3 — Process Safety
Before claiming process isolation:
- descendant containment exists;
- external process identity supports reliable lookup as claimed;
- terminate/kill/confirm semantics implemented;
- stale Attempt cannot spawn new process;
- child filesystem/network authority matches profile claims.

### Gate EIW-G4 — Network Safety
Before granting restricted network access:
- destination scope enforced;
- DNS resolution policy defined;
- private/link-local/loopback protections where required;
- redirects revalidated;
- raw socket bypass blocked in profiles that claim mediation.

### Gate EIW-G5 — Provider / Browser / Remote Recovery
Before crash-safe retry claims:
- external IDs/idempotency/lookup support documented per adapter;
- timeout ambiguity maps to UNKNOWN where necessary;
- cancellation confirmation semantics tested;
- adapters do not blind-retry uncertain non-idempotent PREPARED operations.

### Gate EIW-G6 — External Event Ingress
Before external events can drive Runtime:
- source authentication policy exists;
- schema/version validation exists;
- stable deduplication exists;
- canonicalization contract exists;
- canonical owner commit is separated from transport reception.

### Gate EIW-G7 — Isolation Claim Verification
Before third-party hostile code is supported:
- one concrete IsolationProfile is implemented;
- filesystem/network/process/credential claims have adversarial tests;
- bypass channels are explicitly reviewed;
- trusted builtin mode is not used as evidence for hostile-plugin safety.

### Gate EIW-G8 — Portability
Before workflow export/import is advertised as portable:
- environment-bound resources are classified;
- live Resource refs are excluded or marked unresolved;
- explicit rebinding flow exists;
- import cannot widen local authority implicitly.

## 25. Open Questions for Lead Review / Later Designs

1. Which subsystem owns durable `WorkspaceIdentityDescriptor` product/project metadata: a dedicated Workspace subsystem, Product/Project owner, or another definition/config owner?
2. Should `BROWSER_CONTROL`, `TOOL_INVOKE` and `REMOTE_EXEC` be standardized initial CapabilityTypes or remain registry-defined examples until product requirements stabilize?
3. Which external observations should require EffectOperation because of cost/side-channel/provider semantics even when they are read-only from the user's perspective?
4. What minimum isolation profile is required for third-party Modules in the first implementation release: trusted-only, OS-process brokered, containerized, or stronger?
5. Should network policy canonicalize hostnames at authorization time, connection time, or both for long-lived connections?
6. Which workspace filesystems/platforms are in the first supported security envelope, given cross-platform differences in symlinks, junctions, mount namespaces and handle-relative APIs?
7. What durable external evidence schema should be common across adapters versus adapter-specific metadata referenced by EffectOperation?
8. Which subsystem owns external ingress route registration/configuration before a future public API/Event Ingress design is frozen?
9. Should persistent browser downloads be modeled only as browser EffectOperation plus subsequent workspace EffectOperation, or as a composed operation with two separately tracked effects? The default in this candidate favors separate effects when both external state transitions are independently ambiguous.
10. What formal compatibility descriptor is required for rebinding Provider Session / Browser Session / Remote Worker Resources after restart?

These questions do not require changing D-004 authority ownership and therefore are not blocking Architecture Findings at this stage.

## 26. Architecture Findings

**None.**

D-004's Capability / Resource / Effect authority model is sufficient to express the external-world safety rules required by this candidate.

No change is proposed to CapabilityGrant ownership/lifecycle, Resource/ResourceLease ownership/lifecycle, EffectOperation ownership/lifecycle, Attempt fencing, Accounting, Recovery or Graph topology.

## 27. Candidate Conclusion

Nyron can support File, Shell, HTTP, Browser, provider/model, Tool, Remote Worker and External Event integrations without hardcoding them into the Kernel.

The safe boundary is achieved by combining:
- scoped Capability validation at the real external boundary;
- optional managed Resource/ResourceLease for stateful handles;
- EffectOperation for consequential or crash-ambiguous external history;
- adapter TCB responsibilities;
- explicit IsolationProfile claims;
- durable external identity/idempotency/lookup where available;
- UNKNOWN rather than guessed history when evidence is insufficient;
- explicit ingress authentication/validation/canonicalization before external inputs become canonical truth.

This document is a design candidate only. It does not freeze architecture and does not authorize implementation to reinterpret the frozen Module baseline or D-004 ownership model.