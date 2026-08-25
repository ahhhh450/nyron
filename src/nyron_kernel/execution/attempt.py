"""Canonical identity for one Runtime RunAttempt."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RunAttempt:
    run_ref: str
    attempt_seq: int
    fencing_token: str
    state: str
