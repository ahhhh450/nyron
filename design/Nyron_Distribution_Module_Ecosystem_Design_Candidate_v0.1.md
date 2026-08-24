# Nyron Distribution / Module Ecosystem Design Candidate v0.1

**Task ID:** `NYRON-D-007`  
**Status:** CANDIDATE — FOR LEAD DESIGN REVIEW  
**Mode:** design only; no implementation authority; no freeze authority  

Depends on:
- `design/Universal_Runtime_Module_Design_Report_v0.1.md` — **FROZEN MODULE ARCHITECTURE BASELINE**
- `design/Nyron_Graph_Composite_Frozen_Baseline_v0.1.md` — **FROZEN GRAPH / COMPOSITE ARCHITECTURE BASELINE**
- `design/Nyron_Overall_System_Architecture_v0.1.md` — integrated system architecture candidate
- `design/Nyron_Capability_Resource_Effect_Authority_Design_Candidate_v0.1.md` — authority-boundary input only where install/trust actions cross controlled host/workspace boundaries

This Candidate MUST NOT silently change frozen Module or Graph/Composite semantics. If implementation or review discovers that distribution requires such a change, it must raise an Architecture Finding rather than reinterpret the frozen baseline.

---

## 1. Purpose

This document defines Nyron's Distribution / Module Ecosystem architecture: package identity, registry semantics, immutable resolution, dependency closure, installation, trust/signing evidence, provenance, offline bundles, mirrors/caches, and the relationship between distributed Module packages and exact Graph/Composite dependencies.

The central separation is:

```text
Import Definition
!= Resolve Package
!= Install Package
!= Trust Package
!= Enable Package
!= Grant Capability
!= Admit Graph Execution
```

Distribution makes immutable artifacts available and interpretable. It does not create Runtime authority.

---

## 2. Scope and Non-Scope

### 2.1 In scope

- Module package identity and immutable package versions;
- package content hashing and integrity;
- ModuleDefinition publication/distribution relationship;
- Registry identity and exact immutable version resolution;
- package manifest and dependency closure;
- exact dependency resolution and missing dependency behavior;
- install / resolve / trust / enable distinction;
- publisher identity, namespace and collision policy;
- signing, provenance and trust evidence;
- package replacement, withdrawal, deprecation and historical resolution;
- Graph / Composite bundle interaction with Module packages;
- schema/config dependency packaging boundaries;
- capability declaration validation without authority granting;
- untrusted/malicious package boundary and Module Host isolation dependency;
- public, private and local Registry semantics;
- cache, mirror and Registry outage behavior;
- canonical versus derived distribution state;
- implementation gates and open questions.

### 2.2 Explicit non-scope

This design does not own or redefine:
- GraphRevision, CompositeRevision or ModuleInstanceRevision semantics;
- Runtime scheduling, readiness, retry, replacement, cancellation or admission state machine;
- CapabilityGrant issuance or policy authority;
- Resource / ResourceLease lifecycle;
- EffectOperation lifecycle;
- product Node taxonomy;
- concrete VM/container/WASM/process isolation technology;
- provider secrets or credential storage architecture;
- package-manager UI details.

---

## 3. Existing Frozen Constraints Consumed by This Design

The Distribution subsystem consumes the following frozen facts without modification:

1. `ModuleDefinition` is a versioned immutable execution capability contract identified by exact `module_ref@version`.
2. An executable `GraphRevision` pins exact immutable `ModuleDefinition` versions and immutable config references.
3. Runtime never resolves `latest`, `current`, or compatible-latest definitions for an existing execution.
4. Graph/Composite `DependencyManifest` is derived metadata using the exact recursive referenced-module formula and is not authority.
5. Unresolved Module references may remain preserved in imported definitions, but such definitions cannot enter executable Runtime admission.
6. Graph/Composite import/export preserves exact versions and grants no trust, Capability, Resource or execution authority.
7. ModuleDefinition declares `effect_classes[]` and `required_capability_types[]`; declaration validation is machine-checkable, but declaration is not authorization.
8. Third-party hostile code requires enforceable Module Host isolation before Nyron may claim safe hostile-plugin execution.

Distribution therefore provides availability, integrity, provenance and trust-policy inputs while leaving execution and authority to their existing Owners.

---

## 4. Distribution Ownership Model

Nyron introduces a **Module Registry / Distribution Owner** as the canonical Owner of distribution-domain facts.

It owns canonical truth for:
- Registry identities known to a Nyron installation/project policy domain;
- package publication records;
- immutable package identities and their content digests;
- publisher/namespace bindings recognized by that Registry;
- package status governance such as published, deprecated or withdrawn;
- local installation records;
- package trust decisions/evidence bindings where trust policy assigns those decisions to the Registry/Distribution domain;
- immutable source/provenance records needed to interpret how an installed package was obtained;
- exact package-to-ModuleDefinition publication bindings.

It does **not** own:
- ModuleDefinition semantic truth itself where that truth is owned by the Module Registry domain contract;
- GraphRevision or CompositeRevision;
- Runtime execution/admission;
- CapabilityGrant;
- ResourceLease;
- EffectOperation;
- Workspace/Project identity;
- Host process isolation state beyond distribution-facing evidence/requirements.

A distribution record referencing another Owner's object does not transfer ownership.

---

## 5. Core Identity Model

Nyron distinguishes four identities:

```text
ModuleDefinition identity: module_ref@version
ModulePackage identity:    package_ref@package_version
Registry identity:         registry_ref
Publisher identity:        publisher_ref
```

These identities MUST NOT be collapsed.

A Module package may contain one or more ModuleDefinitions, schemas, static assets or adapter components. A ModuleDefinition version may be published by exactly one immutable package payload per Registry publication record, but the same byte-identical package may be mirrored by multiple Registries.

### 5.1 ModulePackage

Candidate envelope:

```text
ModulePackage
- package_ref
- package_version
- package_format_version
- publisher_ref
- namespace
- content_digest
- manifest_digest
- module_definitions[]
- package_dependencies[]
- schema_dependencies[]
- bundled_artifacts[]
- declared_capability_types[]
- declared_effect_classes[]
- host_requirements?
- provenance_descriptor?
- signature_envelopes[]
```

`package_ref@package_version` identifies an immutable semantic package release.

`content_digest` is cryptographic integrity evidence over the canonical package payload. Once a package version is published, a different payload MUST NOT be accepted under the same package identity/version.

If the ecosystem wishes to distribute a changed payload, it must publish a new package version or a distinct package identity according to Registry policy.

### 5.2 Package version and Module version are independent

`package_version` and `ModuleDefinition.version` are not assumed equal.

A package release may contain multiple ModuleDefinitions with distinct module versions. Graphs still pin exact `module_ref@version`; they do not pin package latest.

Distribution resolution maps an exact module definition reference to an immutable package artifact containing exactly that definition version.

---

## 6. Package Manifest

Each package contains one immutable, hash-covered manifest.

Minimum semantic fields:

```text
PackageManifest
- package_ref
- package_version
- package_format_version
- publisher_ref
- namespace
- module_definitions[]
    - module_definition_ref@version
    - definition_digest
    - entry_artifact_ref
- package_dependencies[]
    - package_ref@exact_package_version OR exact content_digest binding
- schema_dependencies[]
    - schema_ref@exact_version / immutable schema_ref
- included_artifacts[]
    - artifact_ref
    - artifact_digest
    - media/type metadata
- capability/effect declarations summary
- host/isolation requirements?
- build/provenance references?
```

Manifest dependency references are exact. Version ranges such as `^1.2`, `>=2`, `latest` or floating branches may exist only in authoring/tooling metadata outside the immutable execution closure; they are never the resolved dependency authority for an installed immutable package used to satisfy a Graph's exact dependencies.

---

## 7. ModuleDefinition Publication Relationship

Publishing a Module package does not change ModuleDefinition semantics.

For every exported `module_definition_ref@version`, registration validates:
- the exact ModuleDefinition object is immutable and internally valid;
- its digest matches package manifest evidence;
- its port/config/effect/capability contract is identical to the registered immutable definition under that exact identity;
- no different semantic payload already occupies the same exact ModuleDefinition identity in the target Registry domain;
- package identity/version is not being reused for different content.

A Registry MAY reject a package whose ModuleDefinition identity collides with an existing different payload. It MUST NOT pick one nondeterministically.

If the exact same ModuleDefinition bytes/digest are already registered, the Registry may treat a repeated publication as idempotent evidence rather than creating a second semantic definition.

---

## 8. Registry Model

A `Registry` is a distribution namespace and immutable artifact resolution authority, not Runtime authority.

Candidate identity:

```text
RegistryDescriptor
- registry_ref
- registry_kind
- endpoint/location descriptor
- trust_policy_ref?
- namespace_policy_ref?
- mirror_of_registry_ref?
- metadata
```

Possible registry kinds include PUBLIC, PRIVATE and LOCAL, but these are deployment/governance classes rather than Runtime primitives.

### 8.1 Exact resolution

Normative resolution input:

```text
ResolveModule(module_ref@exact_version)
```

Result is one of:

```text
RESOLVED(package_ref@version, content_digest, registry_ref, evidence)
MISSING
AMBIGUOUS_IDENTITY
WITHDRAWN_FOR_NEW_INSTALL
INTEGRITY_FAILURE
POLICY_DENIED
```

For an exact ModuleDefinition identity, executable resolution MUST produce exactly one accepted immutable semantic payload. Multiple registries/mirrors may provide byte-identical copies; that is not ambiguity if the accepted content digest and immutable definition digest are identical.

Different semantic payloads claiming the same exact identity are a collision and MUST fail closed.

### 8.2 Registry priority is policy, not identity

A workspace/project/system may configure registry search order or allowed registries. Search order may decide where bytes are fetched from, but MUST NOT silently choose between conflicting semantic payloads for one exact identity.

---

## 9. Dependency Closure

There are two distinct dependency closures.

### 9.1 Graph/Composite Module dependency closure

Frozen Graph semantics remain:

```text
dependency_manifest =
sorted(unique(all referenced module_ref@version recursively))
```

This manifest is derived from immutable Graph/Composite definitions.

### 9.2 Package artifact dependency closure

A package may itself depend on exact package/schema/runtime support artifacts needed to load the ModuleDefinition implementation.

Candidate closure:

```text
PackageClosure(root_package)
= root package
+ transitive exact package dependencies
+ exact schema/artifact dependencies required for interpretation/loading
```

This closure is distribution-layer metadata and MUST NOT rewrite the Graph's Module dependency manifest.

### 9.3 Exact-version preserving resolution

For every Graph dependency `module_ref@version`, Distribution resolves only that exact immutable version. Missing dependencies remain explicit; no compatible-latest substitution is allowed.

An upgrade operation is an authoring operation that creates a new immutable GraphRevision/CompositeRevision referencing the new exact ModuleDefinition version.

---

## 10. Missing Dependency Behavior

Missing package bytes or missing Registry availability do not mutate the imported Graph/Composite.

A definition may remain:
- stored;
- inspectable;
- exportable;
- diagnosable;
- repairable.

But if any required exact ModuleDefinition or immutable semantic dependency is unresolved, integrity-invalid or policy-denied, execution eligibility remains false.

Distribution SHOULD return structured diagnostics such as:

```text
MissingDependency
- owner_definition_ref
- module_ref
- required_version
- attempted_registry_refs[]
- reason
- expected_digest? 
```

`MISSING` is not rewritten to a substitute version.

---

## 11. Resolve, Install, Trust, Enable and Execute

These states/operations are intentionally orthogonal.

### 11.1 Resolve

Resolution proves that an exact immutable artifact can be identified under configured Registry policy. It does not imply local presence or trust.

### 11.2 Install

Installation makes the verified package payload locally available to the configured Module Host/package store.

Candidate canonical record:

```text
InstalledPackage
- installation_ref
- package_ref@package_version
- content_digest
- source_registry_ref
- installed_at
- installed_artifact_location_ref
- verification_evidence_ref
- state
```

Installation does not grant Runtime execution or Capability.

### 11.3 Trust

Trust is a policy decision that a package/publisher/signature/provenance set is acceptable for some bounded use context.

Trust may be scoped by:
- package digest;
- package identity/version;
- publisher identity;
- namespace;
- Registry;
- project/workspace/system policy;
- required isolation profile.

Trust never grants a CapabilityGrant.

### 11.4 Enable

Enablement means local policy allows the installed package to be considered by Module loading/admission in a bounded environment.

An installed but disabled package remains present but unavailable for ordinary execution loading.

Enablement MUST NOT bypass Graph exact-version validation or Runtime admission.

### 11.5 Execute

Runtime execution requires, independently:
- execution-eligible immutable GraphRevision;
- exact ModuleDefinition resolution;
- locally usable package/implementation;
- applicable trust/enable policy;
- Module Host capability to satisfy required isolation/runtime profile;
- Runtime admission;
- actual scoped CapabilityGrant(s) where effects require them.

No single Distribution status proves all of these.

---

## 12. Trust, Signing and Provenance Evidence

Nyron treats signatures and provenance as evidence, not automatic authority.

### 12.1 Signature envelope

Candidate model:

```text
SignatureEnvelope
- signature_ref
- subject_content_digest
- signer_identity_ref
- signature_algorithm
- signature_bytes
- signed_at?
- certificate_chain_ref?
- transparency_evidence_ref?
```

Verification answers whether a signature is cryptographically valid for a digest and identity evidence. It does not answer whether the signer is trusted by current policy.

### 12.2 Provenance

Candidate provenance evidence may include:
- source repository identity/ref;
- source commit/tree digest;
- build system identity;
- build recipe digest;
- builder identity;
- dependency lock/closure digest;
- reproducible-build evidence;
- Registry ingestion evidence;
- publisher attestation.

Provenance evidence is immutable evidence. Trust policy interprets it.

### 12.3 Trust decision

A trust decision SHOULD bind to immutable evidence and context:

```text
PackageTrustDecision
- trust_decision_ref
- subject_package_digest
- policy_ref
- policy_revision_ref
- decision
- evidence_refs[]
- scope
- decided_at
```

Candidate decision states:

```text
TRUSTED
UNTRUSTED
QUARANTINED
CONDITIONAL
```

`CONDITIONAL` may require an enforceable IsolationProfile or prohibit selected host adapters.

Trust decisions are policy/governance facts; they do not become Module semantic truth.

---

## 13. Publisher Identity and Namespace Collision Policy

A Registry MUST have an explicit architecture-level rule for publisher and namespace identity.

Minimum properties:
- publisher identity is stable and not inferred solely from display name;
- namespace ownership is explicit under Registry policy;
- exact `package_ref` and `module_ref` bindings cannot be reassigned silently to a different publisher;
- display-name changes do not change identity;
- namespace transfer, if supported, is a canonical governance event with history retained;
- a conflicting claim is rejected/quarantined, never resolved by arrival order.

For public registries, globally unique namespace policy is strongly preferred.

For private/local registries, identical human-readable names MAY exist across distinct `registry_ref` domains, but cross-registry import must retain source Registry/provenance so identity is not accidentally conflated.

Nyron SHOULD prefer globally stable opaque identity underneath human-readable namespace names.

---

## 14. Registration-Time Capability Declaration Validation

The frozen Module baseline requires machine-checkable effect/capability declaration validation.

At package registration/install validation, Distribution/Registry may verify:
- each included ModuleDefinition declares valid known CapabilityType references under current registry vocabulary policy;
- effect-to-required-capability mapping is structurally valid;
- declared CapabilityType schema/version references resolve;
- forbidden undeclared host access requirements are rejected by package policy.

Example:

```text
WORKSPACE_WRITE effect declared
+ no WORKSPACE_WRITE capability requirement
=> CAPABILITY_EFFECT_MISMATCH
```

This validation proves declaration consistency only.

It MUST NOT:
- create a CapabilityGrant;
- widen an existing grant;
- pre-authorize future Runs;
- infer that a trusted package is allowed unrestricted effects.

Actual CapabilityGrant issuance remains Capability Authority responsibility and is Attempt/fencing/scope bound.

---

## 15. Malicious / Untrusted Package Boundary

Package integrity and package trust do not equal sandbox safety.

A package can be:
- byte-integrity-valid yet malicious;
- correctly signed by an untrusted signer;
- trusted for one project but not another;
- trusted only under a constrained IsolationProfile.

Before executing hostile/untrusted third-party code, the Module Host MUST provide enforceable isolation appropriate to the declared threat model. Merely hiding APIs in a language wrapper is insufficient if the package can access raw filesystem, subprocess, sockets, credentials or canonical storage by other means.

Distribution therefore may expose host requirements such as:

```text
HostRequirement
- minimum_isolation_profile
- required_runtime_family
- native_code_allowed?
- network_default
- filesystem_default
- broker_only_external_access
```

But the concrete isolation technology remains outside this design.

If the current Host cannot satisfy required isolation, the package may remain installed/inspectable but MUST NOT be enabled for that execution context.

---

## 16. Schema and Config Packaging Boundaries

GraphRevision pins immutable `config_ref`; `config_hash` remains integrity evidence only.

Distribution may package immutable config/schema objects required to interpret a shared definition, but it MUST preserve their identity and ownership semantics.

Rules:
1. Bundle/package transport does not convert config into mutable package-local defaults if the Graph pins an immutable external config reference.
2. Schema artifacts required to parse/validate ModuleDefinition/config/ports must be exact immutable references or content-addressed immutable artifacts.
3. Secrets, credentials, workspace bindings and environment-specific policy values are not portable config merely because a package needs them.
4. Export may include a redacted/parameter requirement descriptor for environment-specific bindings, but not fabricate values.
5. Import preserves unresolved config/schema references when allowed by Graph validation rules and keeps the definition non-executable until resolved.

---

## 17. Graph / Composite Bundle and Module Package Interaction

A Graph/Composite bundle preserves exact definition identity, dependency manifest, immutable config/schema interpretation dependencies and provenance under the frozen Graph baseline.

A bundle MAY embed Module packages for portability/offline use.

Embedding changes transport availability only:

```text
Embedded Module Package
!= Installed Package
!= Trusted Package
!= Enabled Package
!= CapabilityGrant
```

Import sequence SHOULD be conceptually separated:

```text
1. Verify bundle envelope/hash.
2. Import/preserve Graph/Composite immutable definitions.
3. Derive/verify exact dependency manifest.
4. Inspect embedded package artifacts.
5. Verify package hashes/signatures/provenance.
6. Resolve exact dependencies against embedded/local/allowed Registry sources.
7. Ask Distribution policy whether packages may be installed.
8. Ask trust policy whether installed packages may be trusted/enabled.
9. Re-run definition execution-eligibility validation.
10. Runtime admission remains separate.
```

The Graph import operation MUST NOT silently execute steps 7–10 as one hidden authority escalation.

---

## 18. Offline Bundle Semantics

Nyron supports an offline distribution bundle that can contain:
- Graph/Composite bundle payload;
- exact Module package closure;
- exact schema/artifact closure needed for interpretation;
- package manifests;
- content digests;
- signatures and provenance evidence;
- Registry source metadata;
- bundle format/version metadata.

An offline bundle should be self-inspectable without network access.

Offline import can prove only the evidence present in the bundle plus local trust policy. It MUST NOT claim online revocation/transparency freshness if such checks were not available.

Policy may require one of:
- offline trust allowed with pinned keys/evidence;
- quarantine until online verification;
- private Registry-issued offline attestation.

Offline resolution must still preserve exact versions and content digests.

---

## 19. Replacement, Withdrawal, Deprecation and Historical Resolvability

Published immutable bytes are never silently replaced.

### 19.1 Replacement

A corrected or changed package is a new immutable package version/content identity. A changed Module observable contract requires a new ModuleDefinition version per frozen Module rules.

### 19.2 Deprecation

Deprecation is advisory governance for new selection. It does not invalidate exact historical references.

### 19.3 Withdrawal

Withdrawal means ordinary new installation/resolution policy may refuse the package, for example due to security or legal reasons.

Withdrawal MUST NOT rewrite history or pretend the package never existed.

If durable execution history or a retained immutable GraphRevision references the package/ModuleDefinition, Nyron must retain enough canonical metadata/evidence to interpret the historical reference. Actual executable bytes may be subject to retention/security policy, but loss of bytes must be represented honestly rather than rebound to another version.

### 19.4 Security revocation

A severe security revocation may block new execution even if an old GraphRevision remains structurally valid. That is an admission/trust policy outcome, not mutation of the GraphRevision.

Historical resolution metadata remains available so audit/replay can explain what exact artifact was referenced.

---

## 20. Local, Private and Public Registry Semantics

All Registry classes share the same immutable-resolution semantics.

### Public Registry
- broad publisher population;
- strong namespace ownership and collision controls;
- public signing/transparency/revocation policy expected;
- no automatic trust merely because publication is public.

### Private Registry
- organization/project-controlled publisher set;
- private signing roots and policy may apply;
- exact immutable identity rules remain identical;
- private placement does not itself equal trusted code.

### Local Registry
- machine/user-local immutable package source;
- may contain unpublished development packages;
- may be populated by offline import;
- exact content identity and collision checks still apply;
- local origin does not bypass trust/enable policy.

A package moved or mirrored between registry classes retains immutable content identity and provenance links.

---

## 21. Cache, Mirror and Registry Outage Semantics

Caches and mirrors are distribution accelerators, not semantic Owners.

### 21.1 Cache

A cache may satisfy an exact dependency only when:
- expected exact identity matches;
- content digest verifies;
- immutable definition/package digest matches canonical metadata/evidence;
- applicable trust/policy permits use.

Cache age alone does not make immutable content stale. Revocation/trust freshness may still require current policy evidence.

### 21.2 Mirror

A mirror may serve byte-identical package content under preserved source/provenance metadata. A mirror MUST NOT re-sign/relabel a payload in a way that falsely changes publisher identity unless it is explicitly issuing a distinct mirror attestation rather than replacing original evidence.

### 21.3 Registry outage

If the Registry is unavailable:
- already installed verified packages MAY remain usable if trust/admission policy allows;
- exact cached packages MAY resolve if their integrity and policy evidence are sufficient;
- unavailable dependencies remain unresolved rather than upgraded/substituted;
- no Runtime correctness rule depends on Registry uptime after immutable execution inputs are already resolved and locally usable.

If policy requires fresh revocation/transparency evidence and freshness cannot be obtained, the result is policy-specific deny/quarantine/conditional, not silent trust.

---

## 22. Canonical vs Derived Distribution State

### Canonical distribution facts

Examples:
- immutable Package publication identity/version/digest;
- Registry publication record;
- publisher/namespace binding;
- package withdrawal/deprecation governance event;
- installation record;
- trust decision and evidence bindings where persisted as authoritative policy facts;
- immutable provenance/signature evidence stored for later interpretation;
- ModuleDefinition-to-package publication binding.

### Derived/rebuildable state

Examples:
- local package search index;
- dependency resolution plan;
- available-update suggestions;
- Graph missing-module diagnostics;
- package dependency closure cache;
- mirror ranking;
- download progress;
- UI trust badge;
- dependency-manifest cache;
- compatibility summaries.

Derived state MUST NOT become the sole authority for immutable identity, trust or historical interpretation.

---

## 23. Upgrade Semantics

An upgrade never mutates a frozen GraphRevision or ModuleDefinition reference in place.

Conceptually:

```text
Existing GraphRevision pins module A@1
User/policy proposes A@2
→ authoring validates A@2 contracts/config/ports
→ creates new ModuleInstanceRevision / GraphRevision as required
→ new revision receives exact A@2 reference
→ validation runs
→ optional publication/admission occurs separately
```

Distribution may discover or recommend updates, but it does not rewrite definitions.

Package upgrades likewise create/select a new immutable package version. Existing historical package records remain addressable by exact identity/digest.

---

## 24. Cross-Owner Interaction Vocabulary

Distribution follows the system Query / Command / Event / Proposal model.

Illustrative contracts:

### Graph/Definition → Distribution
- Query: `ResolveExactModule(module_ref@version)`
- Query: `CheckModuleAvailability(module_ref@version)`
- Event consumption: package installed/trust status changed for revalidation trigger
- No direct installation mutation by Graph Owner.

### Distribution → Module Registry domain
- Command/registration request: register immutable ModuleDefinition publication binding
- Query: resolve exact ModuleDefinition identity/digest
- Event: ModuleDefinitionRegistered / RegistrationRejected

### Distribution → Capability Authority
Normally none for semantic authorization. If package installation itself performs controlled external actions, the installer execution environment may require separate ordinary capabilities, but package declarations do not create grants.

### Distribution → Module Host
- Query: supported runtime/isolation profiles
- Command: stage/activate verified installed package under policy
- Event: package staged/activation failed/host profile unavailable

Host remains non-owner of package trust, ModuleDefinition semantics and CapabilityGrant truth.

---

## 25. Failure Semantics

Minimum architectural error vocabulary:

```text
PACKAGE_NOT_FOUND
MODULE_VERSION_NOT_FOUND
PACKAGE_CONTENT_HASH_MISMATCH
MANIFEST_HASH_MISMATCH
MODULE_DEFINITION_HASH_MISMATCH
PACKAGE_IDENTITY_COLLISION
MODULE_IDENTITY_COLLISION
NAMESPACE_COLLISION
SIGNATURE_INVALID
SIGNER_UNTRUSTED
PROVENANCE_POLICY_FAILED
PACKAGE_QUARANTINED
PACKAGE_WITHDRAWN_FOR_NEW_INSTALL
PACKAGE_DISABLED
HOST_REQUIREMENT_UNSATISFIED
UNRESOLVED_PACKAGE_DEPENDENCY
UNRESOLVED_SCHEMA_DEPENDENCY
CAPABILITY_EFFECT_MISMATCH
REGISTRY_UNAVAILABLE
REVOCATION_FRESHNESS_UNAVAILABLE
```

Errors must preserve exact requested identities and reasons. They must not be normalized into a generic "latest package missing" fallback.

---

## 26. Distribution Architecture Invariants

**DIST-INV-01** — `module_ref@version`, `package_ref@package_version`, `registry_ref` and `publisher_ref` are distinct identities and MUST NOT be conflated.

**DIST-INV-02** — A published package version is immutable by content digest. Different content cannot replace the same exact package identity/version.

**DIST-INV-03** — Exact `module_ref@version` resolves to exactly one accepted immutable ModuleDefinition semantic payload; conflicting payloads under the same identity fail closed.

**DIST-INV-04** — Graph/Composite exact dependency manifests remain derived from immutable definition references and are not Registry/Distribution authority.

**DIST-INV-05** — Distribution resolution MUST preserve exact ModuleDefinition versions. It MUST NOT substitute latest/current/range-compatible versions for an exact Graph dependency.

**DIST-INV-06** — Missing/unresolved dependencies may be preserved and diagnosed but cannot become executable through fallback substitution.

**DIST-INV-07** — Importing a Graph/Composite does not install a package.

**DIST-INV-08** — Installing a package does not trust or enable it.

**DIST-INV-09** — Trusting/enabling a package does not grant Capability, Resource, Effect or Runtime execution authority.

**DIST-INV-10** — Embedding a package in a bundle is transport availability only; it grants no installation/trust/enable/Capability authority.

**DIST-INV-11** — Cryptographic signature validity and provenance are evidence; trust remains a policy decision over evidence and context.

**DIST-INV-12** — Publisher/namespace collision is never resolved by arrival order, mutable display name or Registry search priority.

**DIST-INV-13** — Package registration may validate Module effect/capability declarations but MUST NOT create or imply a CapabilityGrant.

**DIST-INV-14** — Resource existence, package installation, package trust and Module loading never bypass the Module Host mediated-effect authority boundary.

**DIST-INV-15** — Host isolation claims for hostile third-party packages must be enforceable; trusted builtin mode is not evidence of hostile-plugin isolation.

**DIST-INV-16** — Withdrawal/deprecation/security revocation may block new install/admission but MUST NOT silently mutate historical immutable references.

**DIST-INV-17** — Historical definitions referenced by durable history retain exact identity/provenance resolution metadata even when new execution is denied.

**DIST-INV-18** — Public, private and local Registries share the same exact immutable identity semantics; locality or privacy does not itself grant trust.

**DIST-INV-19** — Cache/mirror use is valid only when exact identity/content integrity is preserved. Cache/mirror selection is not semantic version resolution authority.

**DIST-INV-20** — Registry outage MUST NOT cause silent version substitution or mutation of already pinned execution definitions.

**DIST-INV-21** — Config/schema packaging preserves immutable references and does not convert environment-specific secrets/policy bindings into portable semantic config.

**DIST-INV-22** — Module/package upgrade creates new immutable references/revisions where semantics change; no frozen GraphRevision or ModuleDefinition reference is rewritten in place.

**DIST-INV-23** — Registry/distribution state does not own Runtime scheduling/admission, CapabilityGrant, ResourceLease or EffectOperation.

**DIST-INV-24** — Derived indexes, dependency plans, update suggestions and diagnostics are reconstructible and cannot be sole correctness authority.

---

## 27. Implementation Gates

### Gate D1 — Identity / Immutable Package Store

Must implement and test:
- package identity/version/digest;
- immutable manifest;
- exact package storage;
- collision rejection;
- canonical publication records.

No trust auto-grant and no Runtime integration.

### Gate D2 — Exact Registry Resolution

Must implement and test:
- `module_ref@exact_version` resolution;
- identical mirror copies versus conflicting identity payloads;
- exact dependency closure;
- missing dependency diagnostics;
- no range/latest fallback.

### Gate D3 — Install / Trust / Enable Separation

Must implement and test distinct state transitions/policies for:
- resolved;
- installed;
- trusted/quarantined;
- enabled/disabled.

CapabilityGrant and Runtime admission remain out of scope.

### Gate D4 — Signing / Provenance / Namespace Governance

Must implement and test:
- signature verification;
- publisher identity;
- namespace collision handling;
- trust evidence binding;
- revocation/withdrawal governance;
- historical metadata retention.

### Gate D5 — Graph / Composite Bundle Integration

Must implement and test:
- exact dependency manifest consumption;
- embedded package inspection;
- unresolved dependency preservation;
- roundtrip exact-version fidelity;
- no implicit install/trust/upgrade;
- offline bundle verification.

### Gate D6 — Module Host Integration

Only after Host isolation/mediation requirements are concrete enough to enforce:
- verified package staging/loading;
- host profile compatibility;
- untrusted package deny/quarantine behavior;
- no raw filesystem/network/process/canonical-store bypass.

### Gate D7 — Cache / Mirror / Outage and Recovery

Must test:
- exact cached resolution;
- mirror byte identity;
- Registry outage;
- stale revocation evidence policy;
- no silent semantic substitution;
- historical resolution after withdrawal/deprecation.

---

## 28. Acceptance Tests Required Before Freeze/Implementation Completion

Architecture-level acceptance scenarios should include at minimum:

1. Graph imports with `module.a@1` missing; graph remains inspectable and non-executable.
2. Registry contains `module.a@2` only; resolver MUST NOT substitute it for `module.a@1`.
3. Two registries return identical bytes/digest for `module.a@1`; resolution succeeds with preserved provenance.
4. Two registries claim different payloads for `module.a@1`; resolution fails with identity collision.
5. Embedded package imports with Graph bundle; Graph import succeeds but package remains uninstalled/untrusted until separate policy actions.
6. Package is validly signed by unknown publisher; signature verifies but trust decision remains untrusted/quarantined.
7. Package is trusted but Host cannot satisfy isolation profile; package cannot be enabled for that context.
8. Package declares WORKSPACE_WRITE effect without required capability declaration; registration rejects with `CAPABILITY_EFFECT_MISMATCH`.
9. Package is installed and trusted; a Runtime Attempt without WORKSPACE_WRITE grant still cannot perform workspace write.
10. Package version is withdrawn after historical execution; historical exact identity/provenance remains explainable and no alternate version is rebound.
11. Registry is offline but exact verified installed package exists; policy may allow use without semantic re-resolution to latest.
12. Registry is offline and dependency is absent; execution remains blocked rather than silently upgraded.
13. Cache contains content under wrong digest; integrity check fails.
14. User upgrades ModuleDefinition version; a new immutable GraphRevision is produced and old revision remains unchanged.
15. Offline bundle lacks required online revocation freshness; result follows explicit policy (deny/quarantine/conditional) rather than fabricated fresh trust.

---

## 29. Open Questions

**OQ-DIST-01 — Package cardinality.** Whether one package should normally contain exactly one ModuleDefinition or may intentionally contain multiple definitions. This Candidate permits multiple while preserving exact ModuleDefinition identity.

**OQ-DIST-02 — Global versus Registry-qualified module identity.** Strong preference is globally stable opaque `module_ref` with Registry as source/provenance, avoiding semantic identity changes when mirrored. Lead review should confirm whether any Registry-qualified namespace is needed.

**OQ-DIST-03 — Trust decision Owner placement.** This Candidate places package trust decisions in the Registry/Distribution policy domain unless the future Project/Workspace Policy Owner centralizes trust policy state. Ownership must remain single and explicit after D-010 integration.

**OQ-DIST-04 — Transparency/revocation freshness.** Exact online freshness requirements are policy-specific and should be finalized with security/operations design.

**OQ-DIST-05 — Content-addressed secondary identity.** The package digest is normative integrity evidence; Lead may choose whether it is also exposed as a first-class package locator.

**OQ-DIST-06 — Native extension threat classes.** Concrete isolation profiles for native code, interpreted code and WASM/containerized modules remain Module Host implementation/design work.

None of these open questions requires changing frozen Module or Graph invariants.

---

## 30. Architecture Findings

**None.**

This Candidate can satisfy the required Distribution / Module Ecosystem semantics while preserving the frozen Module and Graph/Composite architecture. No frozen invariant must be reopened by this design.
