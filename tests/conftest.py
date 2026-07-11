"""Shared pytest fixtures/helpers for the MCP state-layer tests."""

from __future__ import annotations

import pytest


class TrackedLock:
    """Wraps a real lock (Lock/RLock), counting acquire/release depth so a test can prove a critical section
    ran while the lock was held (depth > 0 at that moment).

    DRY: extracted from the per-store TOCTOU / verify_chain lock-holding tests (previously duplicated inline in
    test_evidence_ledger.py, test_calibration_tracker.py, and test_ach_engine.py). Only the context-manager +
    acquire/release surface the stores use is wrapped; anything else on the wrapped lock is intentionally not
    forwarded (the tests only ever use `with self._write_lock:`).
    """

    def __init__(self, inner):
        self._inner = inner
        self.depth = 0

    def acquire(self, *a, **k):
        r = self._inner.acquire(*a, **k)
        self.depth += 1
        return r

    def release(self):
        self.depth -= 1
        self._inner.release()

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, *a):
        self.release()


@pytest.fixture()
def tracked_lock():
    """Return the TrackedLock class (a factory) so a test can wrap a store's write lock and assert lock depth
    at the moment a probed method runs — e.g. `store._write_lock = tracked_lock(store._write_lock)`."""
    return TrackedLock
