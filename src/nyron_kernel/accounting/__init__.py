"""Accounting-owned canonical scope identity and ancestry resolution."""

from .scope_resolver import (
    AccountingScope,
    AccountingScopeError,
    AccountingScopeResolution,
    AccountingScopeResolver,
    compute_ancestry_hash,
)

__all__ = [
    "AccountingScope",
    "AccountingScopeError",
    "AccountingScopeResolution",
    "AccountingScopeResolver",
    "compute_ancestry_hash",
]
