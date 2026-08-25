# Resource Provenance TOCTOU and Trust-Boundary Timing

Date: 2026-08-25  
Related Task / Design: `NYRON-T-20260825-037`, `NYRON-T-20260825-038`, D-004 Resource / Host trust boundary  
Status: **WORKING / VALIDATED BY INDEPENDENT REVIEW — NON-NORMATIVE**

## Problem / Context

ARE-GATE-2 introduces a real managed-directory Resource with crash recovery and provenance markers, but intentionally does not yet expose Module filesystem read/write APIs or hostile-plugin / multi-tenant isolation.

Independent Review Task 038 identified a narrow provisioning TOCTOU window:

```text
mkdir(exact managed path)
-> another co-resident actor removes/replaces the new directory with a symlink
-> provenance marker open/write follows the substituted path
```

The destructive `shutil.rmtree` path was independently checked and does not have the same top-level symlink behavior under the reviewed CPython implementation, but the provisioning marker-write sequence still leaves a real race under a stronger local-adversary threat model.

## Decision / Current Direction

Do not block the minimal ARE-GATE-2 Kernel Resource foundation solely on this race while all of the following remain true:

- the managed root is assumed Resource-Manager-owned;
- less-trusted code is not granted concurrent write access to that root;
- no Module-facing file I/O is routed through `resource.external_ref`;
- hostile-plugin / multi-tenant filesystem isolation remains deferred to the later Host trust-boundary gate.

However, the finding must remain explicit technical debt and become a prerequisite before the threat model changes.

## Why

Security severity and release blocking are related but not identical.

A real flaw can be non-blocking in an earlier bounded Gate when the capability needed to exploit it is not yet exposed. Treating every future-threat-model weakness as an immediate blocker encourages premature platform hardening and can blur gate boundaries.

The opposite mistake is more dangerous: calling a weakness "out of scope" and then forgetting it when the next Gate activates the missing attacker capability.

Therefore the safe pattern is:

```text
real weakness found
-> classify against current reachable attack surface
-> preserve as explicit Finding / design debt
-> name the future activation condition
-> promote to blocking prerequisite before that condition becomes true
```

## Alternatives Considered

### Harden immediately in ARE-GATE-2

Possible direction includes descriptor-relative / no-follow filesystem operations (for example dir-fd / `openat`-style handling or equivalent platform-safe primitives).

Deferred because Task 037's explicit goal is the smallest real Resource foundation and the current gate does not expose the hostile concurrent-root writer threat model.

This deferral does **not** decide the eventual hardening mechanism.

### Ignore because the current tests pass

Rejected.

Tests proving path hashing, root confinement and provenance matching do not eliminate a race between two filesystem syscalls. A code-reading concurrency/security finding can be valid even when the available Windows sandbox cannot reproduce POSIX symlink behavior.

### Treat `path.is_symlink()` pre-checks as sufficient

Rejected as a general rule.

A path check followed by a separate filesystem use can itself race. Security-sensitive filesystem ownership should eventually prefer operations whose lookup/use semantics are bound strongly enough to the intended directory identity rather than relying only on pre-use pathname checks.

## Risks / Open Questions

- Exact cross-platform primitive for safe provisioning is not frozen.
- Windows and POSIX filesystem semantics differ; eventual implementation must define supported guarantees per platform.
- Before Module file I/O or hostile co-resident execution is enabled, the entire Resource-handle filesystem mediation path should be reviewed as one trust boundary, not just the marker write.

## Reusable Insight

**Gate-aligned security debt:** a security weakness may be non-blocking when its prerequisite attacker capability is intentionally absent from the current slice, but the project must record the precise future capability that activates the risk and convert the debt into a blocking prerequisite before that capability ships.

**Filesystem provenance insight:** deterministic paths and marker files establish identity evidence, but pathname-based multi-step sequences do not automatically establish race-safe ownership. Provenance correctness and TOCTOU resistance are separate properties.

## Promote To

- future Resource / Host trust-boundary implementation checklist;
- future generic Security Review guide;
- future generic AI-assisted development documentation on gate-scoped security debt and deferred hardening.
