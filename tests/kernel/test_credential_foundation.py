"""Adversarial credential reference/resolution boundary tests."""
from __future__ import annotations

import json
import pickle
import sqlite3
import tempfile
import unittest
from dataclasses import asdict, replace
from pathlib import Path

from nyron_kernel.host import (
    CredentialBoundaryError, CredentialRepository, CredentialResolutionAuthority,
    CredentialResolutionRequest, ProviderOperationRequest, ProviderProfileRevision,
    ProviderRepository, TrustedUnaryProviderBroker,
)
from nyron_kernel.host.credential.foundation import _issue_resolved_credential
from nyron_kernel.store import SQLiteStore

OP="effect:credential/1"; RUN="run:credential/1"; RES="reservation:credential/1"
PROFILE="provider-profile:credential@1"; GRANT="grant:credential/1"; LEASE="lease:credential/1"
BINDING="credential-binding:test@1"; SYNTHETIC="synthetic-super-secret-value"


class _SyntheticResolver:
    def resolve(self, binding, request):
        return _issue_resolved_credential(SYNTHETIC)


class _LeakingResolver:
    def resolve(self, binding, request):
        raise RuntimeError(SYNTHETIC)


class CredentialFoundationTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.db=Path(self.temp.name)/"credential.db"
        self.store=SQLiteStore(self.db); self.now=100
        self.provider=ProviderRepository(self.store,lambda:self.now); self._seed(self.store)
        self.provider.register_profile(self._profile())
        self.provider.prepare(self._operation())
        self.repo=CredentialRepository(self.store,lambda:self.now)
        self.binding=self._register()
        self.request=self._request()
    def tearDown(self): self.store.close(); self.temp.cleanup()

    def test_persistence_is_reference_only_and_exact_replay_is_idempotent(self):
        self.assertEqual(self.binding,self._register())
        dump="\n".join(self.store.connection.iterdump())
        self.assertNotIn(SYNTHETIC,dump)
        self.assertIn("workspace-secret:opaque@1",dump)
        with self.assertRaises(CredentialBoundaryError):
            self._register(workspace_secret_ref="workspace-secret:other@1")

    def test_rotation_is_new_monotonic_identity_and_preserves_old(self):
        rotated=self._register(credential_binding_ref="credential-binding:test@2",
            workspace_secret_ref="workspace-secret:opaque@2",revision_seq=2,
            predecessor_binding_ref=BINDING,creation_evidence_ref="evidence:create-2")
        self.assertEqual(2,rotated.revision_seq)
        self.assertEqual("workspace-secret:opaque@1",self.repo.resolve_binding(BINDING).workspace_secret_ref)
        with self.assertRaises(CredentialBoundaryError):
            self._register(credential_binding_ref="credential-binding:test@3",revision_seq=3,
                predecessor_binding_ref=BINDING)

    def test_revocation_and_restart_fail_future_resolution(self):
        self.repo.revoke(BINDING,"evidence:revoke")
        self.store.close(); self.store=SQLiteStore(self.db)
        self.repo=CredentialRepository(self.store,lambda:self.now)
        self.assertTrue(self.repo.is_revoked(BINDING))
        with self.assertRaises(CredentialBoundaryError) as raised:
            CredentialResolutionAuthority(self.repo).use_resolved(
                self.request,lambda value: value == SYNTHETIC,_SyntheticResolver())
        self.assertEqual("CREDENTIAL_BINDING_REVOKED",raised.exception.code)

    def test_default_resolver_has_no_fallback_and_fails_closed_after_restart(self):
        with self.assertRaises(CredentialBoundaryError) as raised:
            CredentialResolutionAuthority(self.repo).use_resolved(self.request,lambda value: True)
        self.assertEqual("CREDENTIAL_RESOLVER_NOT_CONFIGURED",raised.exception.code)
        self.store.close(); self.store=SQLiteStore(self.db); self.repo=CredentialRepository(self.store,lambda:self.now)
        with self.assertRaises(CredentialBoundaryError) as restarted:
            CredentialResolutionAuthority(self.repo).use_resolved(self.request,lambda value: True)
        self.assertEqual("CREDENTIAL_RESOLVER_NOT_CONFIGURED",restarted.exception.code)

    def test_handle_repr_str_and_serialization_are_redacted_or_rejected(self):
        handle=_issue_resolved_credential(SYNTHETIC)
        self.assertEqual("<resolved-credential:redacted>",repr(handle)); self.assertEqual(repr(handle),str(handle))
        self.assertNotIn(SYNTHETIC,repr(handle)); self.assertNotIn(SYNTHETIC,str(handle))
        with self.assertRaises(CredentialBoundaryError): pickle.dumps(handle)
        with self.assertRaises(TypeError): json.dumps(handle)
        with self.assertRaises(TypeError): asdict(handle)
        self.assertFalse(hasattr(handle,"value")); self.assertFalse(hasattr(handle,"__dict__"))

    def test_resolver_and_consumer_failures_are_redacted_without_exception_context(self):
        for resolver,consumer,code in (
            (_LeakingResolver(),lambda value: True,"CREDENTIAL_RESOLUTION_FAILED"),
            (_SyntheticResolver(),lambda value: (_ for _ in ()).throw(RuntimeError(value)),"CREDENTIAL_CONSUMER_FAILED"),
        ):
            with self.assertRaises(CredentialBoundaryError) as raised:
                CredentialResolutionAuthority(self.repo).use_resolved(self.request,consumer,resolver)
            self.assertEqual(code,raised.exception.code)
            self.assertNotIn(SYNTHETIC,str(raised.exception)); self.assertNotIn(SYNTHETIC,repr(raised.exception))
            self.assertIsNone(raised.exception.__context__)

    def test_consumer_cannot_return_secret_material(self):
        with self.assertRaises(CredentialBoundaryError) as raised:
            CredentialResolutionAuthority(self.repo).use_resolved(
                self.request,lambda value: value,_SyntheticResolver())
        self.assertEqual("CREDENTIAL_CONSUMER_RESULT_UNSAFE",raised.exception.code)

    def test_resolution_request_is_exact_immutable_and_context_bound(self):
        expected=self.repo.prepare_resolution(self.request)
        self.assertEqual(expected,self.repo.prepare_resolution(self.request))
        for change in (
            {"operation_ref":"effect:other"},{"run_ref":"run:other"},{"attempt_seq":2},
            {"capability_grant_ref":"grant:other"},{"resource_lease_ref":"lease:other"},
            {"profile_revision_ref":"profile:other"},
        ):
            candidate=replace(self.request,resolution_request_ref="resolution:"+next(iter(change)),**change)
            with self.assertRaises(CredentialBoundaryError): self.repo.prepare_resolution(candidate)
        with self.assertRaises(CredentialBoundaryError):
            self.repo.prepare_resolution(replace(self.request,operation_ref="effect:other"))

    def test_success_does_not_mutate_or_substitute_authority(self):
        tables=("run_attempts","capability_grants","resource_leases","effect_operations","budget_reservations")
        before={table:tuple(tuple(row) for row in self.store.connection.execute(f"SELECT * FROM {table}")) for table in tables}
        result=CredentialResolutionAuthority(self.repo).use_resolved(
            self.request,lambda value: value == SYNTHETIC,_SyntheticResolver())
        self.assertTrue(result)
        after={table:tuple(tuple(row) for row in self.store.connection.execute(f"SELECT * FROM {table}")) for table in tables}
        self.assertEqual(before,after)
        self.store.connection.execute("UPDATE capability_grants SET state='REVOKED' WHERE grant_ref=?",(GRANT,))
        self.assertTrue(CredentialResolutionAuthority(self.repo).use_resolved(
            self.request,lambda value: value == SYNTHETIC,_SyntheticResolver()))
        with self.assertRaises(Exception): TrustedUnaryProviderBroker(self.store,self.provider).admit_simulated_dispatch(OP)

    def test_raw_sql_binding_revocation_and_resolution_history_are_immutable(self):
        self.repo.prepare_resolution(self.request); self.repo.revoke(BINDING,"evidence:revoke")
        for sql in (
            "UPDATE credential_binding_revisions SET workspace_secret_ref='x'",
            "DELETE FROM credential_binding_revisions",
            "UPDATE credential_binding_revocations SET evidence_ref='x'",
            "DELETE FROM credential_binding_revocations",
            "UPDATE credential_resolution_requests SET run_ref='x'",
            "DELETE FROM credential_resolution_requests",
        ):
            with self.assertRaises(sqlite3.IntegrityError): self.store.connection.execute(sql)

    def test_success_and_failure_never_persist_synthetic_material(self):
        CredentialResolutionAuthority(self.repo).use_resolved(
            self.request,lambda value: value == SYNTHETIC,_SyntheticResolver())
        with self.assertRaises(CredentialBoundaryError):
            CredentialResolutionAuthority(self.repo).use_resolved(
                self.request,lambda value: True,_LeakingResolver())
        self.assertNotIn(SYNTHETIC,"\n".join(self.store.connection.iterdump()))

    @staticmethod
    def _profile():
        return ProviderProfileRevision("provider-profile:credential",PROFILE,"adapter:test",
            "provider:test","account:test","endpoint:test","model:test","usage:test",
            "MODEL_INVOKE",True,False,False,True,False,False,True,True,False,False)
    @staticmethod
    def _operation():
        return ProviderOperationRequest(OP,"sha256:credential",PROFILE,"idem:credential",
            "dispatch:credential",RUN,1,GRANT,LEASE,RES)
    def _register(self,**changes):
        values=dict(credential_binding_ref=BINDING,workspace_secret_ref="workspace-secret:opaque@1",
            profile_ref="provider-profile:credential",profile_revision_ref=PROFILE,
            binding_class="PROVIDER_API_KEY",revision_seq=1,predecessor_binding_ref=None,
            creation_evidence_ref="evidence:create")
        values.update(changes); return self.repo.register_binding(**values)
    @staticmethod
    def _request():
        return CredentialResolutionRequest("resolution:credential/1",BINDING,OP,RUN,1,GRANT,LEASE,PROFILE)
    @staticmethod
    def _seed(store):
        c=store.connection
        c.execute("INSERT INTO graph_revisions VALUES ('graph:credential@1','{}',1,NULL)")
        c.execute("INSERT INTO module_instance_revisions VALUES ('module:credential@1','graph:credential@1','module:credential','test.credential','1','config@1','hash','{}','{}','[\"root\"]','accounting:credential')")
        c.execute("INSERT INTO accounting_scopes VALUES ('accounting:credential','graph:credential@1','module:credential@1',NULL,'MODULE','ancestry:credential','module:credential@1','ACTIVE')")
        c.execute("INSERT INTO execution_admissions VALUES ('admission:credential','execution:credential','graph:credential@1','policy@1',1,'ADMITTED')")
        c.execute("INSERT INTO workflow_executions VALUES ('execution:credential','graph:credential@1','admission:credential','policy@1','ADMITTED')")
        c.execute("INSERT INTO activations VALUES ('activation:credential','execution:credential','graph:credential@1','module:credential@1','delivery:credential','[]','accounting:credential','event:activation:credential')")
        c.execute("INSERT INTO activation_created_events VALUES ('event:activation:credential','activation:credential','ActivationCreated')")
        c.execute("INSERT INTO runs VALUES (?, 'activation:credential','execution:credential',1,1,'RUNNING',NULL,NULL)",(RUN,)); c.execute("INSERT INTO run_attempts VALUES (?,1,'fence:credential','ACTIVE')",(RUN,))
        c.execute("INSERT INTO capability_types VALUES ('capability.model-invoke','1','{}')")
        c.execute("INSERT INTO capability_grants VALUES (?, 'capability.model-invoke','1','execution:credential','activation:credential',?,1,'fence:credential',1,'{}','test',NULL,1,NULL,NULL,'ACTIVE')",(GRANT,RUN))
        c.execute("INSERT INTO resources VALUES ('resource:credential','PROVIDER_ENDPOINT','owner','{}','AVAILABLE','provider:test','{}')")
        c.execute("INSERT INTO resource_leases VALUES (?, 'resource:credential','broker','execution:credential','activation:credential',?,1,'fence:credential',1,1,NULL,'ACTIVE')",(LEASE,RUN))
        c.execute("INSERT INTO effect_operations(operation_ref,effect_class,execution_ref,activation_ref,run_ref,attempt_seq,fencing_token,fencing_generation,capability_grant_ref,resource_ref,resource_lease_ref,target_ref,payload_json,payload_hash,caused_by_ref,state,prepared_at,dispatch_admission_ref,dispatch_admitted_at,completion_evidence_json,fence_evidence_json,historical_outcome,historical_outcome_evidence_json) VALUES (?, 'MODEL_INVOKE','execution:credential','activation:credential',?,1,'fence:credential',1,?,'resource:credential',?,'provider:model','{}','sha256:credential','event:credential','PREPARED',1,'dispatch:credential',1,NULL,NULL,'UNKNOWN',NULL)",(OP,RUN,GRANT,LEASE))
        c.execute("INSERT INTO budget_reservations VALUES (?, 'reserve:credential','activation:credential',?,1,'accounting:credential','graph:credential@1','module:credential@1','[\"accounting:credential\"]','[\"policy:credential@1\"]','estimate:credential','[[\"tokens\",1]]','[[\"tokens\",1]]','[]','[]','RESERVED',NULL,'[]',1,1,'event:reserve')",(RES,RUN))
        c.execute("INSERT INTO budget_scope_exposure VALUES ('accounting:credential','tokens',1,0)")
        c.execute("INSERT INTO budget_policy_revisions VALUES ('policy:credential@1','accounting:credential',0,NULL,'[{\"dimension_ref\":\"tokens\",\"unit\":\"TOKEN\",\"measurement_semantics_ref\":\"sem:tokens\"}]','[]','test',NULL)")


if __name__=='__main__': unittest.main()
