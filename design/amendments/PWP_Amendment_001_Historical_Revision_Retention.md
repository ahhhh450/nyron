# PWP Amendment 001 — Historical Revision Retention and Resolvability

**Status:** **FROZEN PROJECT / WORKSPACE / POLICY CONTEXT ARCHITECTURE AMENDMENT**  
**Authority:** Nyron Lead Design Authority  
**Applies to:** `design/Nyron_Project_Workspace_Policy_Context_Frozen_Baseline_v0.1.md`  
**Reason:** Resolve the ambiguity identified by `NYRON-D-001-CLAUDE-F02` during integrated adversarial review.

## 1. Existing frozen intent

The frozen D-010 bundle already requires:
- historical resolution after Project archival;
- exact pinned revisions for admitted executions;
- historical consumers to retain exact revision refs;
- superseded revisions to remain resolvable while referenced by canonical history.

This Amendment does not reverse that design. It makes the retention obligation explicit across **all** PWP-owned revision classes so implementation cannot interpret the earlier wording as applying only to ProjectConfig / WorkspaceConfig.

## 2. Revision classes covered

The retention/resolvability rule applies to every PWP-owned immutable revision that may be referenced by retained canonical history, including at minimum:

- `ProjectConfigRevision`;
- `WorkspaceConfigRevision`;
- `PolicyContextRevision`;
- `EnvironmentBindingRevision`;
- `IngressRouteRevision`;
- any future PWP-owned immutable revision explicitly permitted to enter a pinned execution/admission context.

Stable `Project` / `Workspace` / `IngressRoute` logical identities required to resolve those revisions are covered as well.

## 3. Mandatory retention rule

If a PWP identity/revision is referenced by retained durable canonical history, it MUST remain semantically resolvable for as long as that history remains within Nyron's retention contract.

Examples of retained history include:
- admitted WorkflowExecution context refs;
- canonical ingress/admission facts;
- durable audit/history records whose interpretation depends on exact PWP context;
- recovery/reconciliation evidence that references the exact admission context.

No mutable `current/latest` pointer may substitute for the historical revision.

## 4. Archive / supersede is not deletion

For PWP-owned context:

```text
DEPRECATED / ARCHIVED / SUPERSEDED
!= hard deleted
!= semantically unresolvable
```

Archival or supersession may:
- prohibit new ordinary admission;
- remove a revision from current/default selection;
- hide it from normal authoring UX;
- move it to archival storage.

It MUST NOT make a still-referenced historical revision impossible to resolve.

## 5. Garbage collection condition

A PWP-owned immutable revision may be physically deleted only when the system can establish that no retained canonical history still requires it for semantic interpretation, audit, replay, recovery or late evidence processing.

The exact retention index/reference-count/storage mechanism is implementation detail.

The semantic requirement is:

```text
retained canonical reference exists
-> referenced revision remains resolvable
```

## 6. Import/export and rebinding

Import, export, rebinding, Project archival or Workspace archival MUST NOT rewrite an old execution's pinned revision refs to newer local/current revisions.

A new environment may create a new `EnvironmentBindingRevision` for future work, but historical execution remains bound to the exact old context that was admitted.

If an external environment realization no longer exists, the old immutable binding configuration remains resolvable as historical configuration even though it does not prove live Resource availability.

## 7. Added invariant

**PWP-INV-RET-01 — Every Historically Referenced PWP Revision Remains Resolvable**  
Every PWP-owned immutable revision referenced by retained canonical history MUST remain resolvable until no retained history requires it. Archive, deprecation, supersession, rebinding or current-pointer advancement cannot destroy that historical semantic context.

## 8. Baseline effect

This Amendment is authoritative if earlier D-010 wording could be read as limiting retention protection to only some PWP revision classes.

It does not change:
- PWP ownership boundaries;
- Runtime execution ownership;
- Resource/Lease ownership;
- Capability authority;
- Graph topology ownership;
- the distinction between EnvironmentBinding configuration and live environment state.
