from __future__ import annotations

import sqlite3
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from nyron_kernel.recovery import (
    RecoveryError,
    RecoveryEvidence,
    RecoveryRepository,
    RecoveryResolution,
)
from nyron_kernel.store import SQLiteStore


class MutableClock:
    def __init__(self, value: int = 100) -> None:
        self.value = value

    def __call__(self) -> int:
        return self.value


class RecoveryReconciliationFoundationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.clock = MutableClock()
        self.store = SQLiteStore()
        self.repository = RecoveryRepository(self.store, self.clock)

    def tearDown(self) -> None:
        self.store.close()

    def open_case(self, **overrides: object):
        values = dict(
            reconciliation_case_ref="case:1",
            open_request_ref="open:1",
            subject_owner_ref="effect-authority",
            subject_ref="effect:unknown",
            reason_code="EFFECT_DISPATCH_HISTORY_UNKNOWN",
            opened_by_ref="accounting:request",
            max_attempts=3,
            retry_policy_ref="retry:fixed",
            backoff_seconds=10,
            deadline=1000,
            escalation_policy_ref="escalate:human",
            caused_by_ref="event:1",
        )
        values.update(overrides)
        return self.repository.open_case(**values)

    def evidence(self, evidence_ref: str, payload_hash: str) -> RecoveryEvidence:
        return RecoveryEvidence(
            evidence_ref=evidence_ref,
            evidence_kind="provider-idempotency-lookup",
            source_authority_ref="provider:authority",
            source_identity=f"lookup:{evidence_ref}",
            subject_ref="effect:unknown",
            payload_ref=f"payload:{evidence_ref}",
            payload_hash=payload_hash,
            observed_at=90,
            ingested_at=self.clock(),
            authenticity_status="AUTHENTICATED",
            semantics_ref="semantics:lookup-result",
            caused_by_ref="event:evidence",
        )

    def test_stable_open_identity_and_conflicting_binding_fail_closed(self) -> None:
        opened = self.open_case()
        self.assertEqual(opened, self.open_case())
        same_condition = self.open_case(
            reconciliation_case_ref="case:ignored",
            open_request_ref="open:2",
        )
        self.assertEqual(opened.reconciliation_case_ref, same_condition.reconciliation_case_ref)
        with self.assertRaisesRegex(RecoveryError, "RECONCILIATION_CASE_IDENTITY_CONFLICT"):
            self.open_case(subject_ref="effect:different")
        self.assertEqual(
            1,
            self.store.connection.execute("SELECT count(*) FROM reconciliation_cases").fetchone()[0],
        )

    def test_evidence_is_append_only_idempotent_and_conflicts_are_preserved(self) -> None:
        self.open_case()
        first = self.evidence("evidence:1", "hash:success")
        conflicting = self.evidence("evidence:2", "hash:failure")
        self.assertEqual(first, self.repository.append_evidence("case:1", first))
        self.assertEqual(first, self.repository.append_evidence("case:1", first))
        self.repository.append_evidence("case:1", conflicting)
        self.assertEqual((first, conflicting), self.repository.list_evidence("case:1"))
        with self.assertRaisesRegex(RecoveryError, "RECOVERY_EVIDENCE_IDENTITY_CONFLICT"):
            self.repository.append_evidence(
                "case:1", self.evidence("evidence:1", "hash:changed")
            )
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.connection.execute(
                "UPDATE recovery_evidence SET payload_hash = 'latest-wins' WHERE evidence_ref = 'evidence:1'"
            )

    def test_retry_identity_backoff_and_resolution_survive_restart(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "recovery.db"
            clock = MutableClock()
            with SQLiteStore(path) as initial:
                repository = RecoveryRepository(initial, clock)
                self.repository = repository
                self.store = initial
                self.open_case()
                attempt = repository.record_retry(
                    case_ref="case:1", attempt_ref="attempt:1", observation_kind="READ_ONLY_PROVIDER_QUERY"
                )
                self.assertEqual(1, attempt.attempt_number)
                self.assertEqual(110, attempt.next_retry_at)
                self.assertEqual(attempt, repository.record_retry(
                    case_ref="case:1", attempt_ref="attempt:1", observation_kind="READ_ONLY_PROVIDER_QUERY"
                ))
            with SQLiteStore(path) as reopened:
                repository = RecoveryRepository(reopened, clock)
                case = repository.resolve_case_by_ref("case:1")
                self.assertEqual("RETRYING", case.state)
                self.assertEqual(110, case.next_retry_at)
                evidence = self.evidence("evidence:resolved", "hash:known")
                repository.append_evidence("case:1", evidence)
                resolution = RecoveryResolution(
                    resolution_ref="resolution:1",
                    reconciliation_case_ref="case:1",
                    resolution_kind="EVIDENCE_SUPPORTED",
                    evidence_refs=(evidence.evidence_ref,),
                    disposition="CASE_DISPOSED_SUBJECT_REMAINS_OWNER_AUTHORITY",
                    disposition_scope="RECOVERY_CASE_ONLY",
                    permits_runtime_closure=False,
                    policy_ref="policy:resolution",
                    caused_by_ref="evidence:resolved",
                    authorized_by_ref=None,
                    resolved_at=clock(),
                )
                resolved = repository.resolve_case(resolution)
                self.assertEqual("RESOLVED", resolved.state)
                self.assertEqual(resolved, repository.resolve_case(resolution))

    def test_max_attempts_escalates_and_ends_retry_authority(self) -> None:
        self.open_case(max_attempts=2)
        self.repository.record_retry(
            case_ref="case:1", attempt_ref="attempt:1", observation_kind="READ_ONLY_QUERY"
        )
        self.clock.value = 110
        last = self.repository.record_retry(
            case_ref="case:1", attempt_ref="attempt:2", observation_kind="READ_ONLY_QUERY"
        )
        self.assertIsNone(last.next_retry_at)
        self.assertEqual("ESCALATED", self.repository.resolve_case_by_ref("case:1").state)
        with self.assertRaisesRegex(RecoveryError, "AUTOMATIC_RETRY_AUTHORITY_ENDED"):
            self.repository.record_retry(
                case_ref="case:1", attempt_ref="attempt:3", observation_kind="READ_ONLY_QUERY"
            )

    def test_fresh_retry_must_reach_committed_eligibility_time(self) -> None:
        self.open_case()
        first = self.repository.record_retry(
            case_ref="case:1",
            attempt_ref="attempt:1",
            observation_kind="READ_ONLY_QUERY",
        )
        before = self.repository.resolve_case_by_ref("case:1")
        with self.assertRaisesRegex(
            RecoveryError, "RECOVERY_RETRY_NOT_YET_ELIGIBLE"
        ):
            self.repository.record_retry(
                case_ref="case:1",
                attempt_ref="attempt:early",
                observation_kind="READ_ONLY_QUERY",
            )
        self.assertEqual(before, self.repository.resolve_case_by_ref("case:1"))
        self.assertIsNone(self.repository.resolve_attempt("attempt:early"))
        self.assertEqual(
            first,
            self.repository.record_retry(
                case_ref="case:1",
                attempt_ref="attempt:1",
                observation_kind="READ_ONLY_QUERY",
            ),
        )
        self.clock.value = first.next_retry_at
        second = self.repository.record_retry(
            case_ref="case:1",
            attempt_ref="attempt:2",
            observation_kind="READ_ONLY_QUERY",
        )
        self.assertEqual(2, second.attempt_number)

    def test_early_retry_remains_blocked_after_restart(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "early-retry.db"
            clock = MutableClock()
            with SQLiteStore(path) as initial:
                repository = RecoveryRepository(initial, clock)
                self.repository = repository
                self.store = initial
                self.open_case()
                repository.record_retry(
                    case_ref="case:1",
                    attempt_ref="attempt:1",
                    observation_kind="READ_ONLY_QUERY",
                )
            with SQLiteStore(path) as reopened:
                repository = RecoveryRepository(reopened, clock)
                before = repository.resolve_case_by_ref("case:1")
                with self.assertRaisesRegex(
                    RecoveryError, "RECOVERY_RETRY_NOT_YET_ELIGIBLE"
                ):
                    repository.record_retry(
                        case_ref="case:1",
                        attempt_ref="attempt:early",
                        observation_kind="READ_ONLY_QUERY",
                    )
                self.assertEqual(before, repository.resolve_case_by_ref("case:1"))

    def test_active_condition_reuse_rejects_divergent_bounded_binding(self) -> None:
        opened = self.open_case()
        legitimate = self.open_case(
            reconciliation_case_ref="case:duplicate",
            open_request_ref="open:duplicate",
        )
        self.assertEqual(opened, legitimate)
        with self.assertRaisesRegex(
            RecoveryError, "RECONCILIATION_CASE_IDENTITY_CONFLICT"
        ):
            self.open_case(
                reconciliation_case_ref="case:conflict",
                open_request_ref="open:conflict",
                max_attempts=99,
                retry_policy_ref="retry:conflict",
            )

    def test_racing_identical_opens_converge_and_conflicts_fail_closed(self) -> None:
        def race(database: Path, conflicting: bool) -> list[object]:
            barrier = threading.Barrier(2)

            def open_from_connection(index: int) -> object:
                with SQLiteStore(database) as store:
                    repository = RecoveryRepository(store, MutableClock())
                    barrier.wait()
                    try:
                        return repository.open_case(
                            reconciliation_case_ref="case:race",
                            open_request_ref="open:race",
                            subject_owner_ref="effect-authority",
                            subject_ref="effect:race",
                            reason_code="EFFECT_DISPATCH_HISTORY_UNKNOWN",
                            opened_by_ref="accounting:request",
                            max_attempts=3 + (index if conflicting else 0),
                            retry_policy_ref="retry:fixed",
                            backoff_seconds=10,
                            deadline=1000,
                            escalation_policy_ref="escalate:human",
                            caused_by_ref="event:race",
                        )
                    except RecoveryError as error:
                        return error

            with ThreadPoolExecutor(max_workers=2) as executor:
                return list(executor.map(open_from_connection, (0, 1)))

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            identical = race(root / "identical.db", conflicting=False)
            self.assertTrue(all(not isinstance(item, RecoveryError) for item in identical))
            self.assertEqual(
                {item.reconciliation_case_ref for item in identical}, {"case:race"}
            )

            conflicting = race(root / "conflicting.db", conflicting=True)
            self.assertEqual(
                1, sum(isinstance(item, RecoveryError) for item in conflicting)
            )
            error = next(item for item in conflicting if isinstance(item, RecoveryError))
            self.assertEqual("RECONCILIATION_CASE_IDENTITY_CONFLICT", error.code)

    def test_canonical_recovery_rows_and_links_reject_raw_delete(self) -> None:
        self.open_case()
        self.repository.record_retry(
            case_ref="case:1",
            attempt_ref="attempt:1",
            observation_kind="READ_ONLY_QUERY",
        )
        evidence = self.evidence("evidence:durable", "hash:durable")
        self.repository.append_evidence("case:1", evidence)
        self.repository.resolve_case(
            RecoveryResolution(
                resolution_ref="resolution:durable",
                reconciliation_case_ref="case:1",
                resolution_kind="EVIDENCE_SUPPORTED",
                evidence_refs=(evidence.evidence_ref,),
                disposition="RECOVERY_CASE_ONLY",
                disposition_scope="RECOVERY_CASE_ONLY",
                permits_runtime_closure=False,
                policy_ref="policy:resolution",
                caused_by_ref="evidence:durable",
                authorized_by_ref=None,
                resolved_at=100,
            )
        )
        deletes = (
            ("reconciliation_cases", "reconciliation_case_ref = 'case:1'"),
            ("recovery_evidence", "evidence_ref = 'evidence:durable'"),
            (
                "reconciliation_case_evidence",
                "reconciliation_case_ref = 'case:1' AND evidence_ref = 'evidence:durable'",
            ),
            ("recovery_attempts", "attempt_ref = 'attempt:1'"),
            ("recovery_resolutions", "resolution_ref = 'resolution:durable'"),
        )
        for table, predicate in deletes:
            with self.subTest(table=table):
                with self.assertRaises(sqlite3.IntegrityError):
                    self.store.connection.execute(
                        f"DELETE FROM {table} WHERE {predicate}"
                    )
                self.assertEqual(
                    1,
                    self.store.connection.execute(
                        f"SELECT count(*) FROM {table} WHERE {predicate}"
                    ).fetchone()[0],
                )

    def test_deadline_escalates_without_recording_attempt(self) -> None:
        self.open_case(deadline=101)
        self.clock.value = 101
        with self.assertRaisesRegex(RecoveryError, "RECOVERY_DEADLINE_EXHAUSTED"):
            self.repository.record_retry(
                case_ref="case:1", attempt_ref="attempt:late", observation_kind="READ_ONLY_QUERY"
            )
        self.assertEqual("ESCALATED", self.repository.resolve_case_by_ref("case:1").state)
        self.assertIsNone(self.repository.resolve_attempt("attempt:late"))

    def test_manual_disposition_is_recovery_truth_only(self) -> None:
        self.store.connection.execute(
            "CREATE TABLE subject_truth(subject_ref TEXT PRIMARY KEY, state TEXT NOT NULL)"
        )
        self.store.connection.execute(
            "INSERT INTO subject_truth VALUES ('effect:unknown', 'UNKNOWN')"
        )
        self.open_case()
        manual = self.evidence("evidence:manual", "hash:attestation")
        self.repository.append_evidence("case:1", manual)
        resolution = RecoveryResolution(
            resolution_ref="resolution:manual",
            reconciliation_case_ref="case:1",
            resolution_kind="MANUAL_POLICY_DISPOSITION",
            evidence_refs=(manual.evidence_ref,),
            disposition="PERMIT_ADMINISTRATIVE_CLOSURE_ONLY",
            disposition_scope="RUNTIME_ADMINISTRATIVE_CLOSURE",
            permits_runtime_closure=True,
            policy_ref="policy:manual",
            caused_by_ref="human-response:1",
            authorized_by_ref="identity:operator",
            resolved_at=100,
        )
        case = self.repository.resolve_case(resolution)
        self.assertEqual("RESOLVED", case.state)
        self.assertEqual(
            "UNKNOWN",
            self.store.connection.execute(
                "SELECT state FROM subject_truth WHERE subject_ref = 'effect:unknown'"
            ).fetchone()[0],
        )
        stored = self.repository.resolve_resolution("resolution:manual")
        self.assertTrue(stored.permits_runtime_closure)
        self.assertEqual("RUNTIME_ADMINISTRATIVE_CLOSURE", stored.disposition_scope)

    def test_api_exposes_no_business_effect_execution_helper(self) -> None:
        forbidden = {"execute", "dispatch", "replay_effect", "apply_accounting_disposition"}
        self.assertTrue(forbidden.isdisjoint(set(dir(self.repository))))


if __name__ == "__main__":
    unittest.main()
