# Effect Linearization Concurrency Interlock

Status: NON-NORMATIVE / WORKING REFERENCE
Date: 2026-08-26
Source: NYRON-T-20260826-043 independent review

## Why this note exists

ARE-GATE-3A established a sound bounded authority-consumption linearization for the current SQLite-backed Kernel, but the proof depends on specific transaction and connection-model assumptions that are easy for a later implementation to accidentally invalidate.

This note records those assumptions and the exact trigger for mandatory revalidation. It does not modify Frozen Design.

## Current load-bearing invariant

The current proof relies on all authority-mutating writes participating in the same logical SQLite writer discipline and using `SQLiteStore.transaction()` with `BEGIN IMMEDIATE`.

At the Effect dispatch boundary, fresh Runtime Attempt/fencing, CapabilityGrant and Resource/ResourceLease facts are read and the durable exact-operation admission evidence is written inside one `BEGIN IMMEDIATE` transaction.

Independent Task 043 review additionally probed two real OS threads with two independent file-backed SQLite connections and observed that the second writer could not enter its own `BEGIN IMMEDIATE` transaction until the first committed. This confirms the serialization is real SQLite engine behavior rather than a single-Python-connection artifact.

## What must not silently change

The current proof must not be assumed valid if any of the following changes:

- raw `sqlite3.connect()` write paths are introduced outside the canonical store discipline;
- connection pooling or multiple writer abstractions are introduced;
- transaction mode changes away from the current `BEGIN IMMEDIATE` discipline;
- WAL/synchronous/locking assumptions are materially changed;
- a worker-pool or genuinely multi-threaded Runtime starts mutating authority state concurrently;
- long/async Effect execution changes when and where authority admission is linearized;
- authority ownership is distributed across databases/processes without a replacement ordering proof.

## Mandatory revalidation trigger

Before a Gate introduces any of the above, the Task must explicitly include a concurrency/linearization revalidation requirement.

The proof should include at least:

1. real independent connections or processes, not only deterministic hooks;
2. a race in which revoke/release/stale Attempt competes with dispatch admission;
3. evidence that exactly one ordering wins and no plain check-then-use window appears;
4. failure-mode behavior under lock timeout / transaction failure;
5. confirmation that admission evidence remains exact-operation-owned and non-transferable.

## Relationship to ARE-GATE-3B and later gates

If ARE-GATE-3B introduces genuine long-running concurrency, it must first satisfy this interlock. If 3B stays logically single-writer, the interlock remains open but does not automatically block unrelated semantics.

In all cases the interlock becomes blocking before a real multi-threaded/worker-pool Runtime, connection-pool migration, or equivalent change to the writer model.

## General lesson

A concurrency guarantee is only as durable as the transaction model it depends on. When a correctness proof rests on a storage/locking convention, record the convention as a first-class revalidation trigger rather than assuming later contributors will infer it from implementation details.
