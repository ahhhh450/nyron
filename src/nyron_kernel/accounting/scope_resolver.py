"""Accounting Owner persistence and static ancestry resolution.

The SHA-256 encoding used here is an implementation-local choice for this
SQLite slice.  It hashes canonical JSON containing the root-to-leaf sequence
of ``accounting_scope_ref`` values; it is not a frozen architecture fact.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass

from nyron_kernel.store import SQLiteStore


class AccountingScopeError(RuntimeError):
    """Fail-closed Accounting-local error with a stable reason code."""

    def __init__(self, code: str, **context: object) -> None:
        super().__init__(code)
        self.code = code
        self.context = context


@dataclass(frozen=True)
class AccountingScope:
    """Canonical Accounting-owned scope identity and static ancestry facts."""

    accounting_scope_ref: str
    graph_revision_ref: str
    definition_anchor_ref: str
    parent_accounting_scope_ref: str | None
    scope_kind: str
    ancestry_hash: str
    created_from_definition_ref: str
    state: str


@dataclass(frozen=True)
class AccountingScopeResolution:
    """Authoritative immutable evidence for a later Runtime admission gate."""

    accounting_scope_ref: str
    graph_revision_ref: str
    definition_anchor_ref: str
    ancestry: tuple[AccountingScope, ...]
    ancestry_hash: str


def compute_ancestry_hash(accounting_scope_refs: tuple[str, ...]) -> str:
    """Hash one complete root-to-leaf canonical scope-reference chain."""

    if not accounting_scope_refs or any(
        not isinstance(reference, str) or not reference.strip()
        for reference in accounting_scope_refs
    ):
        raise AccountingScopeError("ACCOUNTING_SCOPE_ANCESTRY_INVALID")
    encoded = json.dumps(
        list(accounting_scope_refs),
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


class AccountingScopeResolver:
    """The concrete Accounting Owner boundary for this SQLite-backed slice."""

    def __init__(self, store: SQLiteStore) -> None:
        self._store = store

    def publish(self, scope: AccountingScope) -> AccountingScope:
        """Persist one immutable scope, idempotently for identical facts."""

        self._validate_scope(scope)
        existing = self._load(scope.accounting_scope_ref)
        if existing is not None:
            if existing == scope:
                return existing
            raise AccountingScopeError(
                "ACCOUNTING_SCOPE_IDENTITY_CONFLICT",
                accounting_scope_ref=scope.accounting_scope_ref,
            )

        try:
            with self._store.transaction() as connection:
                connection.execute(
                    """
                    INSERT INTO accounting_scopes(
                        accounting_scope_ref,
                        graph_revision_ref,
                        definition_anchor_ref,
                        parent_accounting_scope_ref,
                        scope_kind,
                        ancestry_hash,
                        created_from_definition_ref,
                        state
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        scope.accounting_scope_ref,
                        scope.graph_revision_ref,
                        scope.definition_anchor_ref,
                        scope.parent_accounting_scope_ref,
                        scope.scope_kind,
                        scope.ancestry_hash,
                        scope.created_from_definition_ref,
                        scope.state,
                    ),
                )
        except sqlite3.IntegrityError as error:
            raise AccountingScopeError(
                "ACCOUNTING_SCOPE_IDENTITY_CONFLICT",
                accounting_scope_ref=scope.accounting_scope_ref,
                graph_revision_ref=scope.graph_revision_ref,
                definition_anchor_ref=scope.definition_anchor_ref,
            ) from error
        return scope

    def resolve(
        self,
        accounting_scope_ref: str,
        graph_revision_ref: str,
        definition_anchor_ref: str,
    ) -> AccountingScopeResolution:
        """Resolve and validate one complete Accounting-owned static ancestry."""

        if not self._is_nonempty(accounting_scope_ref):
            raise AccountingScopeError(
                "UNRESOLVED_ACCOUNTING_SCOPE_REFERENCE",
                accounting_scope_ref=accounting_scope_ref,
            )
        if not self._is_nonempty(graph_revision_ref) or not self._is_nonempty(
            definition_anchor_ref
        ):
            raise AccountingScopeError("ACCOUNTING_SCOPE_BINDING_INVALID")

        leaf_to_root: list[AccountingScope] = []
        visited: set[str] = set()
        current_ref: str | None = accounting_scope_ref
        while current_ref is not None:
            if not self._is_nonempty(current_ref) or current_ref in visited:
                raise AccountingScopeError(
                    "ACCOUNTING_SCOPE_ANCESTRY_INVALID",
                    accounting_scope_ref=accounting_scope_ref,
                )
            visited.add(current_ref)
            scope = self._load(current_ref)
            if scope is None:
                code = (
                    "UNRESOLVED_ACCOUNTING_SCOPE_REFERENCE"
                    if not leaf_to_root
                    else "ACCOUNTING_SCOPE_ANCESTRY_INVALID"
                )
                raise AccountingScopeError(
                    code,
                    accounting_scope_ref=accounting_scope_ref,
                    missing_scope_ref=current_ref,
                )
            self._validate_loaded_scope(scope)
            leaf_to_root.append(scope)
            current_ref = scope.parent_accounting_scope_ref

        leaf = leaf_to_root[0]
        if (
            leaf.graph_revision_ref != graph_revision_ref
            or leaf.definition_anchor_ref != definition_anchor_ref
        ):
            raise AccountingScopeError(
                "ACCOUNTING_SCOPE_BINDING_INVALID",
                accounting_scope_ref=accounting_scope_ref,
            )

        ancestry = tuple(reversed(leaf_to_root))
        if any(scope.graph_revision_ref != graph_revision_ref for scope in ancestry):
            raise AccountingScopeError(
                "ACCOUNTING_SCOPE_ANCESTRY_INVALID",
                accounting_scope_ref=accounting_scope_ref,
            )

        ancestry_refs: list[str] = []
        for scope in ancestry:
            ancestry_refs.append(scope.accounting_scope_ref)
            if scope.ancestry_hash != compute_ancestry_hash(tuple(ancestry_refs)):
                raise AccountingScopeError(
                    "ACCOUNTING_SCOPE_ANCESTRY_INVALID",
                    accounting_scope_ref=accounting_scope_ref,
                    inconsistent_scope_ref=scope.accounting_scope_ref,
                )

        return AccountingScopeResolution(
            accounting_scope_ref=leaf.accounting_scope_ref,
            graph_revision_ref=leaf.graph_revision_ref,
            definition_anchor_ref=leaf.definition_anchor_ref,
            ancestry=ancestry,
            ancestry_hash=leaf.ancestry_hash,
        )

    def _load(self, accounting_scope_ref: str) -> AccountingScope | None:
        row = self._store.connection.execute(
            """
            SELECT
                accounting_scope_ref,
                graph_revision_ref,
                definition_anchor_ref,
                parent_accounting_scope_ref,
                scope_kind,
                ancestry_hash,
                created_from_definition_ref,
                state
            FROM accounting_scopes
            WHERE accounting_scope_ref = ?
            """,
            (accounting_scope_ref,),
        ).fetchone()
        if row is None:
            return None
        return AccountingScope(
            accounting_scope_ref=row["accounting_scope_ref"],
            graph_revision_ref=row["graph_revision_ref"],
            definition_anchor_ref=row["definition_anchor_ref"],
            parent_accounting_scope_ref=row["parent_accounting_scope_ref"],
            scope_kind=row["scope_kind"],
            ancestry_hash=row["ancestry_hash"],
            created_from_definition_ref=row["created_from_definition_ref"],
            state=row["state"],
        )

    @classmethod
    def _validate_scope(cls, scope: AccountingScope) -> None:
        if not isinstance(scope, AccountingScope):
            raise AccountingScopeError("ACCOUNTING_SCOPE_BINDING_INVALID")
        identity_values = (
            scope.accounting_scope_ref,
            scope.graph_revision_ref,
            scope.definition_anchor_ref,
            scope.scope_kind,
            scope.ancestry_hash,
            scope.created_from_definition_ref,
            scope.state,
        )
        if any(not cls._is_nonempty(value) for value in identity_values):
            raise AccountingScopeError("ACCOUNTING_SCOPE_BINDING_INVALID")
        if scope.parent_accounting_scope_ref is not None and not cls._is_nonempty(
            scope.parent_accounting_scope_ref
        ):
            raise AccountingScopeError("ACCOUNTING_SCOPE_ANCESTRY_INVALID")
        if scope.parent_accounting_scope_ref == scope.accounting_scope_ref:
            raise AccountingScopeError("ACCOUNTING_SCOPE_ANCESTRY_INVALID")

    @classmethod
    def _validate_loaded_scope(cls, scope: AccountingScope) -> None:
        cls._validate_scope(scope)

    @staticmethod
    def _is_nonempty(value: object) -> bool:
        return isinstance(value, str) and bool(value.strip())
