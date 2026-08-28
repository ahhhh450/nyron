"""Adversarial unary Provider identity and Accounting reconciliation foundation tests."""
from __future__ import annotations
import sqlite3
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from nyron_kernel.accounting import (
    AccountingReconciliationAuthority, ProviderReconciliationRequest,
    SettlementAuthority, SettlementAuthorityError, SettlementRequest,
    UsageFactRequest, UsageLedger, UsageLedgerError,
)
from nyron_kernel.host import (
    ProviderFoundationError, ProviderOperationRequest, ProviderProfileRevision,
    ProviderRepository, TrustedUnaryProviderBroker,
)
from nyron_kernel.store import SQLiteStore

OP="effect:provider/1"; RUN="run:provider/1"; RES="reservation:provider/1"
PROFILE="provider-profile:test@1"; GRANT="grant:provider/1"; LEASE="lease:provider/1"


class ProviderFoundationTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.db=Path(self.temp.name)/"provider.db"; self.now=100
        self.store=SQLiteStore(self.db); self.repo=ProviderRepository(self.store, lambda:self.now)
        self._seed(self.store); self.profile=self.repo.register_profile(self._profile()); self.request=self._request()
    def tearDown(self): self.store.close(); self.temp.cleanup()

    @staticmethod
    def _profile(**changes):
        values=dict(profile_ref="provider-profile:test", profile_revision_ref=PROFILE,
            adapter_ref="adapter:test-unary", provider_scope_ref="provider:test",
            account_scope_ref="provider-account:test", endpoint_scope_ref="endpoint:invoke",
            model_scope_ref="model:test", usage_source_namespace="provider-usage:test@1",
            operation_class="MODEL_INVOKE",
            idempotent_same_key=True, authoritative_lookup=False,
            lookup_not_found_proves_absence=False, cancellation_request=True,
            terminal_cancel_confirmation=False, external_identity_recovery=False,
            continuation_resume=False, streaming=False)
        values.update(changes); return ProviderProfileRevision(**values)
    @staticmethod
    def _request(**changes):
        values=dict(operation_ref=OP, semantic_request_hash="sha256:semantic-a",
            profile_revision_ref=PROFILE, idempotency_key="idem:1",
            dispatch_admission_ref="dispatch:provider/1", run_ref=RUN, attempt_seq=1,
            capability_grant_ref=GRANT, resource_lease_ref=LEASE, reservation_ref=RES)
        values.update(changes); return ProviderOperationRequest(**values)

    def test_identity_committed_before_simulated_boundary_and_exact_replay(self):
        first=self.repo.prepare(self.request); second=self.repo.prepare(self.request)
        self.assertEqual(first,second); admitted=TrustedUnaryProviderBroker(self.store,self.repo).admit_simulated_dispatch(OP)
        self.assertTrue(admitted.simulated); self.assertEqual("sha256:semantic-a",self.repo.resolve(OP).semantic_request_hash)
    def test_identity_replay_after_restart(self):
        expected=self.repo.prepare(self.request); self.store.close(); self.store=SQLiteStore(self.db); self.repo=ProviderRepository(self.store,lambda:self.now)
        self.assertEqual(expected,self.repo.prepare(self.request))
    def test_operation_conflicts_fail_closed(self):
        self.repo.prepare(self.request)
        for changed in (replace(self.request,semantic_request_hash="sha256:other"), replace(self.request,profile_revision_ref="missing@2"), replace(self.request,idempotency_key="idem:other")):
            with self.assertRaises(ProviderFoundationError): self.repo.prepare(changed)
    def test_protected_key_reuse_fails_closed(self):
        self.repo.prepare(self.request); self._clone_effect_and_reservation("effect:provider/2","reservation:provider/2")
        with self.assertRaises(ProviderFoundationError) as raised:
            self.repo.prepare(replace(self.request,operation_ref="effect:provider/2",reservation_ref="reservation:provider/2"))
        self.assertEqual("PROVIDER_OPERATION_IDENTITY_CONFLICT",raised.exception.code)
    def test_external_request_id_is_set_once(self):
        self.repo.prepare(self.request); first=self.repo.bind_external_request_id(OP,"external:req-1")
        self.assertEqual(first,self.repo.bind_external_request_id(OP,"external:req-1"))
        with self.assertRaises(ProviderFoundationError): self.repo.bind_external_request_id(OP,"external:req-2")
    def test_profile_claims_are_truthful_and_unsupported_features_fail(self):
        for change in ({"streaming":True},{"continuation_resume":True},{"lookup_not_found_proves_absence":True},{"terminal_cancel_confirmation":True,"cancellation_request":False}):
            with self.assertRaises(ProviderFoundationError): self.repo.register_profile(self._profile(profile_revision_ref=f"bad:{change}",**change))
        self.repo.prepare(self.request)
        evidence=self.repo.record_evidence(evidence_ref="e:not-found",operation_ref=OP,evidence_kind="LOOKUP",evidence_semantics="NOT_FOUND",authoritative=False,historical_outcome="KNOWN")
        self.assertEqual("UNKNOWN",evidence.historical_outcome)
        cancel=self.repo.record_evidence(evidence_ref="e:cancel",operation_ref=OP,evidence_kind="CANCEL_REQUEST",evidence_semantics="accepted",authoritative=False,historical_outcome="KNOWN")
        self.assertEqual("UNKNOWN",cancel.historical_outcome)
        with self.assertRaises(ProviderFoundationError): self.repo.record_evidence(evidence_ref="e:terminal",operation_ref=OP,evidence_kind="CANCEL_CONFIRMATION",evidence_semantics="terminal",authoritative=True,historical_outcome="KNOWN")
    def test_boundary_revalidates_reservation_grant_lease_and_attempt(self):
        self.repo.prepare(self.request); broker=TrustedUnaryProviderBroker(self.store,self.repo); broker.admit_simulated_dispatch(OP)
        for table,key in (("capability_grants","grant_ref"),("resource_leases","lease_ref")):
            with self.store.transaction() as c: c.execute(f"UPDATE {table} SET state=? WHERE {key}=?",(("REVOKED" if table=="capability_grants" else "REVOKE_REQUESTED"),(GRANT if table=="capability_grants" else LEASE)))
            with self.assertRaises(ProviderFoundationError): broker.admit_simulated_dispatch(OP)
            break
    def test_no_reservation_or_nonprepared_effect_fails_before_boundary(self):
        self.repo.prepare(self.request); self.store.connection.execute("UPDATE budget_reservations SET state='RECONCILING' WHERE reservation_ref=?",(RES,))
        with self.assertRaises(ProviderFoundationError): TrustedUnaryProviderBroker(self.store,self.repo).admit_simulated_dispatch(OP)
    def test_fenced_unknown_and_partial_never_enable_dispatch(self):
        self.repo.prepare(self.request); broker=TrustedUnaryProviderBroker(self.store,self.repo)
        self.store.connection.execute("UPDATE effect_operations SET state='FENCED', fence_evidence_json='{}' WHERE operation_ref=?",(OP,))
        row=self.store.connection.execute("SELECT state,historical_outcome FROM effect_operations WHERE operation_ref=?",(OP,)).fetchone(); self.assertEqual(("FENCED","UNKNOWN"),tuple(row))
        with self.assertRaises(ProviderFoundationError): broker.admit_simulated_dispatch(OP)
        self.store.connection.execute("UPDATE effect_operations SET historical_outcome='PARTIAL', historical_outcome_evidence_json='{}' WHERE operation_ref=?",(OP,))
        row=self.store.connection.execute("SELECT state,historical_outcome FROM effect_operations WHERE operation_ref=?",(OP,)).fetchone(); self.assertEqual(("FENCED","PARTIAL"),tuple(row))
        with self.assertRaises(ProviderFoundationError): broker.admit_simulated_dispatch(OP)
    def test_stable_usage_source_identity(self):
        self.repo.prepare(self.request); self.assertEqual(self.repo.usage_source_identity(OP,"line:1"),self.repo.usage_source_identity(OP,"line:1"))

    def test_unknown_partial_enter_reconciling_without_zero_or_release(self):
        self.repo.prepare(self.request); accounting=AccountingReconciliationAuthority(self.store,lambda:self.now); req=self._reconciliation("UNKNOWN")
        self._record_ambiguity("UNKNOWN")
        first=accounting.enter_provider_ambiguity(req); self.assertEqual(first,accounting.enter_provider_ambiguity(req))
        row=self.store.connection.execute("SELECT state,reserved_dimensions_json,committed_dimensions_json,released_dimensions_json FROM budget_reservations WHERE reservation_ref=?",(RES,)).fetchone()
        self.assertEqual(("RECONCILING",'[["tokens",100]]','[]','[]'),tuple(row))
    def test_reconciliation_restart_conflict_and_raw_immutability(self):
        self.repo.prepare(self.request); self._record_ambiguity("PARTIAL"); accounting=AccountingReconciliationAuthority(self.store,lambda:self.now); req=self._reconciliation("PARTIAL"); expected=accounting.enter_provider_ambiguity(req)
        self.store.close(); self.store=SQLiteStore(self.db); accounting=AccountingReconciliationAuthority(self.store,lambda:self.now)
        self.assertEqual(expected,accounting.enter_provider_ambiguity(req))
        with self.assertRaises(SettlementAuthorityError): accounting.enter_provider_ambiguity(replace(req,evidence_ref="evidence:other"))
        for sql in ("UPDATE provider_accounting_reconciliations SET evidence_ref='x'","DELETE FROM provider_accounting_reconciliations"):
            with self.assertRaises(sqlite3.IntegrityError): self.store.connection.execute(sql)
    def test_usage_identity_dedupes_and_conflict_fails(self):
        self.repo.prepare(self.request); authority,source=self.repo.usage_source_identity(OP,"line:tokens"); ledger=UsageLedger(self.store,lambda:self.now)
        req=UsageFactRequest(authority,source,"METERED_USAGE","tokens","accounting:provider",40,"TOKEN","evidence:usage","event:usage",reservation_ref=RES,operation_ref=OP)
        self.assertEqual(ledger.record_usage(req),ledger.record_usage(req))
        with self.assertRaises(UsageLedgerError): ledger.record_usage(replace(req,quantity=41))
    def test_authoritative_usage_resolves_reconciliation_without_rewriting_ambiguity(self):
        self.repo.prepare(self.request); self._record_ambiguity("UNKNOWN"); AccountingReconciliationAuthority(self.store,lambda:self.now).enter_provider_ambiguity(self._reconciliation("UNKNOWN"))
        authority,source=self.repo.usage_source_identity(OP,"line:known"); UsageLedger(self.store,lambda:self.now).record_usage(UsageFactRequest(authority,source,"METERED_USAGE","tokens","accounting:provider",40,"TOKEN","evidence:known","event:known",reservation_ref=RES,operation_ref=OP))
        settlement=SettlementAuthority(self.store,lambda:self.now).settle(SettlementRequest("settle:provider",RES,"evidence:known"))
        self.assertEqual("COMMITTED",settlement.resulting_state)
        ambiguity=self.store.connection.execute("SELECT ambiguity_outcome FROM provider_accounting_reconciliations").fetchone()[0]
        self.assertEqual("UNKNOWN",ambiguity); self.assertEqual(1,self.store.connection.execute("SELECT COUNT(*) FROM provider_accounting_reconciliation_resolutions").fetchone()[0])
    def test_zero_requires_explicit_usage_fact_and_can_release(self):
        self.repo.prepare(self.request); self._record_ambiguity("UNKNOWN"); AccountingReconciliationAuthority(self.store,lambda:self.now).enter_provider_ambiguity(self._reconciliation("UNKNOWN"))
        with self.assertRaises(SettlementAuthorityError): SettlementAuthority(self.store,lambda:self.now).settle(SettlementRequest("settle:none",RES,"e:none"))
        authority,source="provider-usage:test@1","provider-usage:explicit-zero"; UsageLedger(self.store,lambda:self.now).record_usage(UsageFactRequest(authority,source,"METERED_USAGE","tokens","accounting:provider",0,"TOKEN","evidence:zero","event:zero",reservation_ref=RES,operation_ref=OP))
        self.assertEqual("RELEASED",SettlementAuthority(self.store,lambda:self.now).settle(SettlementRequest("settle:zero",RES,"e:zero")).resulting_state)
    def test_raw_provider_identity_and_evidence_are_immutable(self):
        self.repo.prepare(self.request); self.repo.record_evidence(evidence_ref="e:ack",operation_ref=OP,evidence_kind="ACKNOWLEDGEMENT",evidence_semantics="accepted",authoritative=True,historical_outcome="PARTIAL")
        for sql in ("UPDATE provider_operations SET semantic_request_hash='x'","DELETE FROM provider_operations","UPDATE provider_evidence SET evidence_semantics='x'","DELETE FROM provider_evidence"):
            with self.assertRaises(sqlite3.IntegrityError): self.store.connection.execute(sql)

    @staticmethod
    def _reconciliation(outcome): return ProviderReconciliationRequest("reconcile:provider/1",RES,OP,"provider-usage:test@1",outcome,"evidence:ambiguous","effect-history:ambiguous")
    def _record_ambiguity(self, outcome):
        return self.repo.record_evidence(evidence_ref="evidence:ambiguous",operation_ref=OP,evidence_kind="ACKNOWLEDGEMENT",evidence_semantics="billable-ambiguity",authoritative=True,historical_outcome=outcome)
    def _clone_effect_and_reservation(self,op,res):
        self.store.connection.execute("INSERT INTO effect_operations SELECT ?,effect_class,execution_ref,activation_ref,run_ref,attempt_seq,fencing_token||'-2',fencing_generation,capability_grant_ref,resource_ref,resource_lease_ref,target_ref||'-2',payload_json,payload_hash,caused_by_ref,state,prepared_at,dispatch_admission_ref||'-2',dispatch_admitted_at,completion_evidence_json,fence_evidence_json,historical_outcome,historical_outcome_evidence_json FROM effect_operations WHERE operation_ref=?",(op,OP))
        self.store.connection.execute("INSERT INTO budget_reservations SELECT ?,request_ref||'-2',activation_ref,run_ref,attempt_seq,accounting_scope_ref,graph_revision_ref,definition_anchor_ref,ancestry_snapshot_json,policy_revision_refs_json,estimate_ref,requested_dimensions_json,reserved_dimensions_json,committed_dimensions_json,released_dimensions_json,state,deny_reason_code,subject_refs_json,created_at,updated_at,caused_by_ref FROM budget_reservations WHERE reservation_ref=?",(res,RES))
    @staticmethod
    def _seed(store):
        c=store.connection
        c.execute("INSERT INTO graph_revisions VALUES ('graph:provider@1','{}',1,NULL)")
        c.execute("INSERT INTO module_instance_revisions VALUES ('module:provider@1','graph:provider@1','module:provider','test.provider','1','config@1','hash','{}','{}','[\"root\"]','accounting:provider')")
        c.execute("INSERT INTO accounting_scopes VALUES ('accounting:provider','graph:provider@1','module:provider@1',NULL,'MODULE','ancestry:provider','module:provider@1','ACTIVE')")
        c.execute("INSERT INTO execution_admissions VALUES ('admission:provider','execution:provider','graph:provider@1','policy@1',1,'ADMITTED')")
        c.execute("INSERT INTO workflow_executions VALUES ('execution:provider','graph:provider@1','admission:provider','policy@1','ADMITTED')")
        c.execute("INSERT INTO activations VALUES ('activation:provider','execution:provider','graph:provider@1','module:provider@1','delivery:provider','[]','accounting:provider','event:activation:provider')")
        c.execute("INSERT INTO activation_created_events VALUES ('event:activation:provider','activation:provider','ActivationCreated')")
        c.execute("INSERT INTO runs VALUES (?, 'activation:provider','execution:provider',1,1,'RUNNING',NULL,NULL)",(RUN,)); c.execute("INSERT INTO run_attempts VALUES (?,1,'fence:provider','ACTIVE')",(RUN,))
        c.execute("INSERT INTO capability_types VALUES ('capability.model-invoke','1','{}')")
        c.execute("INSERT INTO capability_grants VALUES (?, 'capability.model-invoke','1','execution:provider','activation:provider',?,1,'fence:provider',1,'{}','test',NULL,1,NULL,NULL,'ACTIVE')",(GRANT,RUN))
        c.execute("INSERT INTO resources VALUES ('resource:provider','PROVIDER_ENDPOINT','resource-owner','{}','AVAILABLE','provider-endpoint:test','{}')")
        c.execute("INSERT INTO resource_leases VALUES (?, 'resource:provider','provider-broker','execution:provider','activation:provider',?,1,'fence:provider',1,1,NULL,'ACTIVE')",(LEASE,RUN))
        c.execute("INSERT INTO effect_operations(operation_ref,effect_class,execution_ref,activation_ref,run_ref,attempt_seq,fencing_token,fencing_generation,capability_grant_ref,resource_ref,resource_lease_ref,target_ref,payload_json,payload_hash,caused_by_ref,state,prepared_at,dispatch_admission_ref,dispatch_admitted_at,completion_evidence_json,fence_evidence_json,historical_outcome,historical_outcome_evidence_json) VALUES (?, 'MODEL_INVOKE','execution:provider','activation:provider',?,1,'fence:provider',1,?,'resource:provider',?,'provider:model:test','{}','sha256:semantic-a','event:provider','PREPARED',1,'dispatch:provider/1',1,NULL,NULL,'UNKNOWN',NULL)",(OP,RUN,GRANT,LEASE))
        c.execute("INSERT INTO budget_reservations VALUES (?, 'reserve-request:provider','activation:provider',?,1,'accounting:provider','graph:provider@1','module:provider@1','[\"accounting:provider\"]','[\"policy:provider@1\"]','estimate:provider','[[\"tokens\",100]]','[[\"tokens\",100]]','[]','[]','RESERVED',NULL,'[]',1,1,'event:reserve')",(RES,RUN))
        c.execute("INSERT INTO budget_scope_exposure VALUES ('accounting:provider','tokens',100,0)")
        c.execute("INSERT INTO budget_policy_revisions VALUES ('policy:provider@1','accounting:provider',0,NULL,'[{\"dimension_ref\":\"tokens\",\"unit\":\"TOKEN\",\"measurement_semantics_ref\":\"sem:tokens\"}]','[]','test',NULL)")

if __name__=='__main__': unittest.main()
