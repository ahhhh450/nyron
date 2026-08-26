# Resource Provenance Residual Namespace Race after Task 045

Status: `NON-NORMATIVE / WORKING REFERENCE`
Related: `NYRON-T-20260825-038-F-001`, `NYRON-T-20260826-045`, `NYRON-T-20260826-046`

Task 045 materially narrows the Resource provenance/path-substitution attack surface, but does not close it.

## What is now hardened

- final-component symlink following/adoption is rejected;
- Windows junction/reparse-point adoption is rejected;
- descriptor-relative/no-follow marker creation and object-identity rechecks prevent pathname substitution after the first trusted identity/descriptor has been acquired;
- post-identity substitution before destructive removal is detected/fail-closed where implemented.

## Exact residual

A less-trusted/co-resident actor that can concurrently mutate the managed-root namespace can still win a race **before the first object identity/descriptor read**:

1. provisioning: after directory creation returns but before the first identity/descriptor capture, the same path can be replaced with another real directory; later marker creation can then bind valid provenance to the substituted object;
2. destruction: between the first provenance/evidence read and the first stable object-identity capture, the proven directory can be moved aside and replaced by a decoy carrying cloned provenance, allowing deletion of the decoy while the original survives outside Nyron's tracked namespace.

This residual exists conceptually on descriptor-capable and fallback platforms because ordinary directory creation does not atomically return a durable identity/handle equivalent to an `O_EXCL` create-and-open primitive.

## Current disposition

`NYRON-T-20260825-038-F-001` remains `SECURITY / NARROWED / OPEN`.

It remains NON_BLOCKING only while the managed-root namespace is trusted against concurrent mutation by less-trusted/co-resident actors. Any Module filesystem API, Host trust-boundary exposure, shared/network-root assumption, or other change that activates this attacker capability makes the finding a blocking prerequisite.

Full closure would require a separately scoped design/implementation such as private staging followed by verified rename-into-place or another primitive with a newly proven namespace-binding argument. Do not infer closure from descriptor-relative APIs alone.

## Reusable design lesson

Hardening a race window can be materially valuable without eliminating the entire attack class. Security findings should track the earliest still-unprotected linearization/identity boundary, not the most visible syscall in the original bug report.
