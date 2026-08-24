# NYRON-D-007 / NYRON-D-010 — Lead Integration Clarification 001

**Status:** NORMATIVE INTEGRATED CANDIDATE CLARIFICATION / PRE-FREEZE
**Applies to:**
- `design/Nyron_Distribution_Module_Ecosystem_Design_Candidate_v0.1.md`
- `design/Nyron_Project_Workspace_Policy_Context_Design_Candidate_v0.1.md`

**Authority:** Nyron Lead Design Authority

This clarification resolves D-007 `OQ-DIST-03` and removes ambiguity between Registry/Distribution trust decisions and Project/Workspace policy-context ownership.

---

## 1. Module Registry / Distribution Owner Is One Logical Owner Domain

For v0.1, `Module Registry / Distribution Owner` is one logical canonical Owner domain for the Registry/distribution state required by Module publication and package availability/trust.

It owns canonical truth for:
- registered immutable `ModuleDefinition` identity/digest records needed for exact resolution;
- ModuleDefinition-to-package publication binding;
- Registry identities and publication records;
- package identity/version/content-digest records;
- publisher/namespace bindings;
- installation records;
- package withdrawal/deprecation governance;
- `PackageTrustDecision` canonical results and their evidence bindings;
- enable/disable distribution state where enablement is modeled canonically.

The immutable semantic contents of a `ModuleDefinition@version` remain governed by the Frozen Module contract. Distribution governance cannot mutate those semantics after registration.

There is no separate competing Owner that may rewrite the same ModuleDefinition registration/publication truth.

### Added invariant

**DIST-INV-25 — Registry/Distribution Has One Canonical Owner Domain**

ModuleDefinition exact registration identity, package publication binding, package installation/trust/governance and Registry resolution records required by v0.1 belong to one logical Module Registry / Distribution Owner domain. Storage may be split physically, but canonical mutation authority is not duplicated across Registry and Distribution services.

---

## 2. PackageTrustDecision Ownership

`PackageTrustDecision` canonical result belongs to Module Registry / Distribution Owner.

Conceptually:

```text
PackageTrustDecision
- trust_decision_ref
- subject_package_digest / exact package identity
- policy_context_ref / policy_revision_refs
- decision
- evidence_refs[]
- scope
- decided_at / owner_order
```

The decision may be scoped by Project, Workspace, system, package, publisher, Registry, isolation profile or another explicitly bounded context.

Distribution Owner is responsible for:
- validating the exact package identity/digest being judged;
- applying the referenced trust-policy contract/evidence;
- committing the canonical trust decision;
- preserving decision history and evidence references;
- fail-closed handling when required trust evidence/policy is unresolved.

`TRUSTED` does not mean enabled, executable, capable, safe under every host profile or authorized for an external effect.

---

## 3. PWP Owns Trust Policy Context, Not Trust Result

Project / Workspace Context Owner may own/reference the immutable policy context determining which trust-policy inputs apply in a given Project/Workspace.

PWP may supply:
- `project_ref` / `workspace_ref`;
- exact `policy_context_revision_ref`;
- exact trust/security policy source refs;
- environment/isolation requirements;
- scope context needed to evaluate trust.

PWP MUST NOT directly commit `PackageTrustDecision` merely because the trust decision is Project/Workspace-scoped.

Therefore:

```text
PWP policy context
-> input to Distribution trust evaluation
-> Distribution Owner commits PackageTrustDecision
```

This follows the same system pattern as:

```text
PWP capability policy context
-> Capability Authority evaluation
-> Capability Authority commits CapabilityGrant / deny
```

Policy context/reference ownership and decision-result ownership are distinct.

### Added invariant

**PWP-INV-24 — Policy Context Does Not Own Package Trust Result**

PWP may pin and supply the trust-policy inputs applicable to a Project/Workspace, but canonical package trust decision/result remains owned by Module Registry / Distribution Owner.

---

## 4. Trust / Enable / Capability / Runtime Remain Orthogonal

The following remain distinct:

```text
PackageTrustDecision
!= InstalledPackage
!= PackageEnablement
!= CapabilityGrant
!= Runtime execution admission
!= Host isolation proof
```

Examples:
- validly installed package may be UNTRUSTED;
- TRUSTED package may be disabled;
- trusted+enabled package may still fail Host isolation requirements;
- trusted+enabled package does not receive CapabilityGrant;
- GraphRevision exact reference is not modified by trust state;
- withdrawal/security revocation may block future admission without rewriting historical GraphRevision or ModuleDefinition truth.

Any emergency action against already-running executions must use the appropriate Runtime/Capability/Effect/Host contract; changing PackageTrustDecision alone does not fabricate that foreign transition.

---

## 5. Exact-Version Resolution Remains Immutable

Trust policy or registry priority cannot select a different semantic payload for an already exact `module_ref@version`.

If two sources claim different payloads for the same exact identity, resolution fails closed.

A package becoming untrusted/withdrawn may deny new loading/admission, but cannot silently rebind the exact ModuleDefinition identity to another version or payload.

---

## 6. Lead Disposition

`OQ-DIST-03` — **RESOLVED**.

NYRON-D-007 Lead integration result: **PASS WITH CLARIFICATION 001**.

NYRON-D-010 remains **PASS WITH AF-PWP-001 RESOLVED**.

No Frozen Module or Frozen Graph/Composite amendment is required.
