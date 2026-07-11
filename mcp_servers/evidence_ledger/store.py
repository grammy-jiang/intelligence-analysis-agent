"""SQLite append-only + hash-chained store for evidence-ledger (design v3, Server 2)."""

from __future__ import annotations

import fcntl
import io
import json
import os
import sqlite3
import sys
import threading
import uuid
from typing import Literal

from ..common import GENESIS, ChainMismatch, ChainStatus, now_iso, row_hash
from ..staleness import StalenessStore
from .models import (
    RELIABILITY_ORDER,
    EvidenceList,
    EvidenceRecord,
    EvidenceRef,
    Grade,
    SourceHistory,
)

_TABLES = ("evidence", "grades")
# MF-1: the judgment-input boundary. `judgment_source` is ASSERTED by the calling skill and is NOT
# server-verifiable (design v3 "Judgment provenance" — over stdio the server cannot confirm a human read-back
# happened). We do NOT pretend to verify it. We DO enforce the two grounded, non-faking guarantees the server
# can make: (a) the tag can only take an intended value — validated here at the store layer so even a direct
# store caller (test/script/other transport) cannot smuggle a third value into the hash-chained payload,
# mirroring ach-engine's SF7; (b) provenance is recorded tamper-evidently — every grade row hashes the trusted
# local `analyst_id` (who) alongside `judgment_source` (what), and `get_evidence` surfaces both the grade's
# judgment_source AND the evidence's source_channel, so a `source_channel='ingested'` item self-stamped
# `analyst_confirmed` is auditable rather than hidden. Real enforcement (binding analyst_confirmed to a verified
# human action) remains the calling skill's responsibility + the deferred token-gated confirm step.
_JUDGMENT_SOURCE = ("analyst_confirmed", "model_draft")


class EvidenceError(Exception):
    """Business-rule violation; the server wraps this as a FastMCP ToolError."""


class EvidenceStore:
    def __init__(self, db_path: str, staleness: StalenessStore, analyst_id: str | None = None):
        self.db_path = db_path
        self.staleness = staleness
        # analyst_id: trusted local binding, never a tool arg (design v3 "Identity"). Recorded on every
        # grade row and folded into its hash so provenance ("who judged") is tamper-evident.
        self.analyst_id = analyst_id or os.environ.get("EVIDENCE_ANALYST_ID", "local-analyst")
        self.manifest_path = db_path + ".manifest.jsonl" if db_path != ":memory:" else None
        # SF2/SF3: serialize every head-read -> INSERT -> commit -> manifest sequence in-process so two
        # threads cannot read the same head and fork the append-only chain.
        self._write_lock = threading.RLock()
        # SF3: an OS-level exclusive advisory lock on a sidecar so a SECOND process opening the same file
        # DB fails closed instead of forking the chain (single-writer-local design). :memory: DBs cannot
        # be shared cross-process, so they need no lock.
        self._lock_fh: io.TextIOWrapper | None = None
        if db_path != ":memory:":
            self._acquire_process_lock(db_path)
        # check_same_thread=False: defensive — a future FastMCP dispatch model may run tool bodies on a
        # worker thread. All writes are already serialized by self._write_lock, so this cannot race.
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        mode = self._conn.execute("PRAGMA journal_mode=WAL").fetchone()[0]
        # WAL silently falls back to the prior mode on some filesystems; fail loud rather than run under
        # concurrency assumptions the journal mode does not actually provide.
        if db_path != ":memory:" and str(mode).lower() != "wal":
            raise EvidenceError(f"could not enable WAL journal mode (got {mode!r}); refusing to run.")
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS evidence(
                seq INTEGER PRIMARY KEY AUTOINCREMENT,
                evidence_id TEXT UNIQUE NOT NULL, case_id TEXT NOT NULL, item TEXT NOT NULL,
                source_id TEXT NOT NULL, evidence_type TEXT NOT NULL, source_channel TEXT NOT NULL,
                expected_observables TEXT NOT NULL DEFAULT '{}', pii INTEGER NOT NULL,
                prev_hash TEXT NOT NULL, row_hash TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS grades(
                seq INTEGER PRIMARY KEY AUTOINCREMENT,
                evidence_id TEXT NOT NULL, reliability TEXT NOT NULL, credibility TEXT NOT NULL,
                diagnosticity TEXT NOT NULL, analyst_id TEXT NOT NULL, judgment_source TEXT NOT NULL,
                rationale TEXT NOT NULL DEFAULT '', reason TEXT NOT NULL DEFAULT '', graded_at TEXT NOT NULL,
                prev_hash TEXT NOT NULL, row_hash TEXT NOT NULL);
            """
        )
        self._conn.commit()
        # MF3: tail of the self-chained external manifest, read once at open.
        self._manifest_head = self._read_manifest_head()

    def _acquire_process_lock(self, db_path: str) -> None:
        lock_path = db_path + ".lock"
        fh = open(lock_path, "w", encoding="utf-8")  # noqa: SIM115 - held for the store's lifetime
        try:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as e:
            fh.close()
            raise EvidenceError(
                f"evidence DB {db_path} is already open by another process (single-writer local design); "
                "refusing to open a second writer."
            ) from e
        self._lock_fh = fh

    def close(self) -> None:
        self._conn.close()
        if self._lock_fh is not None:
            fcntl.flock(self._lock_fh.fileno(), fcntl.LOCK_UN)
            self._lock_fh.close()
            self._lock_fh = None

    def _head(self, table: str) -> str:
        if table not in _TABLES:  # N4: survives `python -O` (assert is stripped); not attacker-controlled
            raise ValueError(f"unknown table: {table!r}")
        r = self._conn.execute(
            f"SELECT row_hash FROM {table} ORDER BY seq DESC LIMIT 1"  # noqa: S608 - internal literal
        ).fetchone()
        return r["row_hash"] if r else GENESIS

    # ---- external manifest (MF3: anchor against tail-truncation / whole-chain reset) ----------------
    def _read_manifest_head(self) -> str:
        """Last manifest_hash on disk (GENESIS if no manifest yet) — the tail of the self-chain."""
        if not self.manifest_path or not os.path.exists(self.manifest_path):
            return GENESIS
        last = GENESIS
        with open(self.manifest_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    last = json.loads(line).get("manifest_hash", GENESIS)
        return last

    def _append_manifest(self, table: str, head: str) -> None:
        # Self-chained + fsync'd external attestation of each per-table head. Each line binds to the
        # previous manifest line's hash, so a mid-file line cannot be edited or dropped undetected;
        # whole-file / whole-table deletion is caught fail-closed by _check_manifest's presence check.
        # Residual risk (documented, SF4): the manifest shares the DB's trust domain, so an attacker with
        # filesystem write can recompute the self-chain in lockstep — durable tamper-evidence needs these
        # heads shipped to a separate append-only/WORM log.
        if not self.manifest_path:
            return
        payload = {"table": table, "head": head, "at": now_iso()}
        mh = row_hash(self._manifest_head, payload)
        entry = {**payload, "prev_manifest_hash": self._manifest_head, "manifest_hash": mh}
        with open(self.manifest_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        self._manifest_head = mh

    def seed_manifest_baseline(self) -> int:
        """One-time migration: attest the current per-table heads for a DB that predates the manifest.
        Trust-on-first-use — only meaningful when no manifest exists yet. Returns entries written."""
        if not self.manifest_path or os.path.exists(self.manifest_path):
            return 0
        written = 0
        with self._write_lock:
            for table in _TABLES:
                head = self._head(table)
                if head != GENESIS:
                    self._append_manifest(table, head)
                    written += 1
        return written

    # ---- evidence ----------------------------------------------------------
    def add_evidence(
        self,
        case_id: str,
        item: str,
        source_id: str,
        evidence_type: str,
        pii: bool,
        source_channel: str,
        expected_observables: dict[str, str] | None = None,
    ) -> EvidenceRef:
        expected_observables = expected_observables if expected_observables is not None else {}
        evidence_id = uuid.uuid4().hex
        payload = {
            "evidence_id": evidence_id, "case_id": case_id, "item": item, "source_id": source_id,
            "evidence_type": evidence_type, "source_channel": source_channel,
            "expected_observables": expected_observables, "pii": bool(pii),
        }
        with self._write_lock:
            prev = self._head("evidence")
            rh = row_hash(prev, payload)
            self._conn.execute(
                "INSERT INTO evidence(evidence_id, case_id, item, source_id, evidence_type, source_channel, "
                "expected_observables, pii, prev_hash, row_hash) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (
                    evidence_id, case_id, item, source_id, evidence_type, source_channel,
                    json.dumps(expected_observables, sort_keys=True), int(bool(pii)), prev, rh,
                ),
            )
            self._conn.commit()
            self._append_manifest("evidence", rh)
        return EvidenceRef(evidence_id=evidence_id, case_id=case_id, pii=bool(pii))

    def _evidence_row(self, evidence_id: str) -> sqlite3.Row:
        r = self._conn.execute("SELECT * FROM evidence WHERE evidence_id=?", (evidence_id,)).fetchone()
        if not r:
            raise EvidenceError(f"unknown evidence_id: {evidence_id}")
        return r

    def _effective_grade(self, evidence_id: str) -> sqlite3.Row | None:
        return self._conn.execute(
            "SELECT * FROM grades WHERE evidence_id=? ORDER BY seq DESC LIMIT 1", (evidence_id,)
        ).fetchone()

    def _mark_staleness_signals(self, evidence_id: str, judgment_source: str) -> None:
        # MF4: the grade row lives in evidence.db; the two signals below live in the SEPARATE staleness.db.
        # There is no cross-DB transaction, so if these writes fail after the grade has committed, the two
        # stores diverge (ach-engine would read a graded item as "never graded", or miss a stale cell).
        # A silent return here is the real defect — so we retry once and, on persistent failure, FAIL LOUD
        # (log + raise) telling the caller exactly how to reconcile, rather than returning normally.
        for attempt in (1, 2):
            try:
                self.staleness.mark_stale(evidence_id, "grade")
                self.staleness.mark_graded(evidence_id, judgment_source)
                return
            except Exception as e:  # noqa: BLE001 - surfaced, never swallowed
                if attempt == 2:
                    print(
                        f"[evidence-ledger] STALENESS SIGNAL WRITE FAILED for {evidence_id} "
                        f"(judgment_source={judgment_source}): {e}",
                        file=sys.stderr,
                    )
                    raise EvidenceError(
                        f"grade for {evidence_id} committed but cross-store staleness signals failed "
                        f"({e}); the ledger and signal store are now inconsistent — re-run update_grade "
                        "to reconcile before this evidence is scored."
                    ) from e

    def _insert_grade(
        self, evidence_id, reliability, credibility, diagnosticity, judgment_source, rationale, reason,
        *, require_first: bool,
    ) -> None:
        # MF-1(a): enforce the judgment_source domain at the store layer, independent of the tool-boundary
        # pydantic Literal — the tag can only ever be one of the two intended values, via any code path.
        if judgment_source not in _JUDGMENT_SOURCE:
            raise EvidenceError(
                f"judgment_source must be one of {_JUDGMENT_SOURCE}, got {judgment_source!r}."
            )
        graded_at = now_iso()
        payload = {
            "evidence_id": evidence_id, "reliability": reliability, "credibility": credibility,
            "diagnosticity": diagnosticity, "analyst_id": self.analyst_id, "judgment_source": judgment_source,
            "rationale": rationale, "reason": reason, "graded_at": graded_at,
        }
        with self._write_lock:
            # M1: the first-grade / has-prior-grade check MUST be inside the same lock as the insert.
            # Checking it in grade_evidence/update_grade (before the lock) is a TOCTOU: two concurrent
            # grade_evidence calls for one evidence_id could both observe "no grade" and both insert as
            # first grades, breaking the single-first-grade / supersede-via-update_grade invariant.
            existing = self._effective_grade(evidence_id)
            if require_first and existing is not None:
                raise EvidenceError("a grade already exists for this evidence — use update_grade to supersede.")
            if not require_first and existing is None:
                raise EvidenceError("no prior grade exists for this evidence — use grade_evidence first.")
            prev = self._head("grades")
            rh = row_hash(prev, payload)
            self._conn.execute(
                "INSERT INTO grades(evidence_id, reliability, credibility, diagnosticity, analyst_id, "
                "judgment_source, rationale, reason, graded_at, prev_hash, row_hash) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (
                    evidence_id, reliability, credibility, diagnosticity, self.analyst_id, judgment_source,
                    rationale, reason, graded_at, prev, rh,
                ),
            )
            self._conn.commit()
            self._append_manifest("grades", rh)
            # cross-server signals: a (re)grade marks dependent ACH cells stale, and records the grade's
            # judgment_source so ach-engine can refuse to score evidence that was never analyst_confirmed.
            self._mark_staleness_signals(evidence_id, judgment_source)

    def grade_evidence(
        self, evidence_id, reliability, credibility, diagnosticity, judgment_source, rationale=""
    ) -> EvidenceRecord:
        self._evidence_row(evidence_id)
        self._insert_grade(
            evidence_id, reliability, credibility, diagnosticity, judgment_source, rationale, "",
            require_first=True,
        )
        return self.get_evidence(evidence_id, redact_pii=True)

    def update_grade(
        self, evidence_id, reliability, credibility, diagnosticity, reason, judgment_source, rationale=""
    ) -> EvidenceRecord:
        self._evidence_row(evidence_id)
        if not reason.strip():
            raise EvidenceError("update_grade requires a non-empty reason (a superseding correction).")
        self._insert_grade(
            evidence_id, reliability, credibility, diagnosticity, judgment_source, rationale, reason,
            require_first=False,
        )
        return self.get_evidence(evidence_id, redact_pii=True)

    def get_evidence(self, evidence_id: str, redact_pii: bool = True) -> EvidenceRecord:
        r = self._evidence_row(evidence_id)
        grade_rows = self._conn.execute(
            "SELECT * FROM grades WHERE evidence_id=? ORDER BY seq ASC", (evidence_id,)
        ).fetchall()
        grades: list[Grade] = []
        n = len(grade_rows)
        for i, g in enumerate(grade_rows):
            grades.append(
                Grade(
                    reliability=g["reliability"], credibility=g["credibility"], diagnosticity=g["diagnosticity"],
                    analyst_id=g["analyst_id"], judgment_source=g["judgment_source"], rationale=g["rationale"],
                    reason=g["reason"], graded_at=g["graded_at"], superseded=(i < n - 1),
                )
            )
        item = "REDACTED" if (r["pii"] and redact_pii) else r["item"]
        return EvidenceRecord(
            evidence_id=r["evidence_id"], case_id=r["case_id"], item=item, source_id=r["source_id"],
            evidence_type=r["evidence_type"], source_channel=r["source_channel"],
            expected_observables=json.loads(r["expected_observables"]), grades=grades,
            pii=bool(r["pii"]), row_hash=r["row_hash"],
        )

    def list_evidence(
        self, case_id: str, redact_pii: bool = True, limit: int = 100, cursor: str | None = None
    ) -> EvidenceList:
        # S4: fail loud (like the cursor check below) rather than silently clamp — limit=0 silently
        # returning 1 item, or a >1000 limit silently capped, hides a caller bug.
        if limit < 1 or limit > 1000:
            raise EvidenceError(f"limit must be in [1,1000], got {limit}")
        if cursor is None:
            after = 0
        else:
            try:  # SF1: a malformed cursor must be a business-rule error, not a raw ValueError at the boundary
                after = int(cursor)
            except (TypeError, ValueError) as e:
                raise EvidenceError(f"invalid cursor: {cursor!r}") from e
        rows = self._conn.execute(
            "SELECT evidence_id, seq FROM evidence WHERE case_id=? AND seq>? ORDER BY seq ASC LIMIT ?",
            (case_id, after, limit + 1),
        ).fetchall()
        items = [self.get_evidence(r["evidence_id"], redact_pii) for r in rows[:limit]]
        next_cursor = str(rows[limit - 1]["seq"]) if len(rows) > limit else None
        return EvidenceList(items=items, next_cursor=next_cursor)

    def get_source_history(self, source_id: str, redact_pii: bool = True) -> SourceHistory:
        ev_rows = self._conn.execute(
            "SELECT evidence_id, case_id, seq FROM evidence WHERE source_id=? ORDER BY seq ASC", (source_id,)
        ).fetchall()
        seq_items: list[tuple[int, str, str]] = []  # (grade_seq, reliability, case_id)
        n_draft = 0
        cases: list[str] = []
        for ev in ev_rows:
            eff = self._effective_grade(ev["evidence_id"])
            if eff is None:
                continue
            if ev["case_id"] not in cases:
                cases.append(ev["case_id"])
            if eff["judgment_source"] == "analyst_confirmed":
                seq_items.append((eff["seq"], eff["reliability"], ev["case_id"]))
            else:
                n_draft += 1
        seq_items.sort(key=lambda t: t[0])
        grade_sequence = [r for _, r, _ in seq_items]
        direction: Literal["improved", "worsened", "same", "n/a"] = "n/a"
        if len(grade_sequence) >= 2:
            a, b = RELIABILITY_ORDER[grade_sequence[-2]], RELIABILITY_ORDER[grade_sequence[-1]]
            direction = "improved" if b < a else ("worsened" if b > a else "same")
        return SourceHistory(
            source_id=source_id, cases=cases, grade_sequence=grade_sequence, last_change_direction=direction,
            n=len(grade_sequence), n_model_draft_excluded=n_draft,
        )

    # ---- integrity ---------------------------------------------------------
    def verify_chain(self) -> ChainStatus:
        """Verify BOTH append-only hash chains (evidence + grades) AND anchor each table's DB head to the
        external manifest. Verification is ALWAYS GLOBAL (there is no per-case scope: grades carry no
        case_id, and tamper-evidence is a whole-ledger property)."""
        # M2: hold the write lock for the whole read+manifest walk. Every writer holds _write_lock across
        # its commit -> manifest-append sequence; without the lock here, a verify interleaved with an
        # in-flight write can read a row already committed but not yet manifest-attested and report a
        # spurious tamper (ok=False) on a healthy ledger. RLock is reentrant, so callers already holding
        # the lock (none today) would not deadlock. seed_manifest_baseline already locks the same way.
        with self._write_lock:
            heads: dict[str, str] = {}
            verified = 0
            for table in _TABLES:
                prev = GENESIS
                rows = self._conn.execute(
                    f"SELECT * FROM {table} ORDER BY seq ASC"  # noqa: S608 - internal literal
                ).fetchall()
                for r in rows:
                    payload = self._payload_for(table, r)
                    expected = row_hash(prev, payload)
                    if expected != r["row_hash"] or r["prev_hash"] != prev:
                        return ChainStatus(
                            server="evidence-ledger", scope="all", ok=False, head_hash=heads,
                            rows_verified=verified,
                            mismatch=ChainMismatch(
                                table=table, row_id=str(r["seq"]), expected_hash=expected,
                                got_hash=r["row_hash"],
                            ),
                        )
                    prev = r["row_hash"]
                    verified += 1
                heads[table] = prev
            # MF3: DB head must match the last manifest entry per table (catches tail-truncation /
            # whole-chain reset that leaves the surviving rows internally self-consistent).
            manifest_ok, mismatch = self._check_manifest(heads)
            return ChainStatus(
                server="evidence-ledger", scope="all", ok=manifest_ok, head_hash=heads,
                rows_verified=verified, mismatch=mismatch,
            )

    def _check_manifest(self, heads: dict[str, str]) -> tuple[bool, ChainMismatch | None]:
        # In-memory stores have no manifest by design (nothing to attest).
        if not self.manifest_path:
            return True, None
        # Any table whose DB chain is non-empty MUST be attested by the manifest; a missing manifest file
        # — or a missing per-table entry — is treated fail-closed as tampering, NOT a vacuous pass. This is
        # what catches whole-chain / whole-table deletion of both the rows and the file.
        non_genesis = {t for t in _TABLES if heads.get(t, GENESIS) != GENESIS}
        if not os.path.exists(self.manifest_path):
            if non_genesis:
                table = sorted(non_genesis)[0]
                return False, ChainMismatch(
                    table=table, row_id="<manifest-missing>",
                    expected_hash=heads.get(table, GENESIS), got_hash=GENESIS,
                )
            return True, None
        # Walk the manifest, verifying its own hash-chain so a mid-file line cannot be edited/dropped
        # undetected, and collect the last attested head per table.
        last: dict[str, str] = {}
        prev = GENESIS
        with open(self.manifest_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                e = json.loads(line)
                expected = row_hash(prev, {"table": e["table"], "head": e["head"], "at": e["at"]})
                if e.get("prev_manifest_hash") != prev or e.get("manifest_hash") != expected:
                    return False, ChainMismatch(
                        table=e.get("table", "?"), row_id="<manifest-chain>",
                        expected_hash=expected, got_hash=str(e.get("manifest_hash", "")),
                    )
                prev = expected
                last[e["table"]] = e["head"]
        for table in non_genesis:
            if table not in last:
                return False, ChainMismatch(
                    table=table, row_id="<manifest-missing-table>",
                    expected_hash=heads.get(table, GENESIS), got_hash=GENESIS,
                )
        for table, mhead in last.items():
            dbhead = heads.get(table, GENESIS)
            if dbhead != mhead:
                return False, ChainMismatch(
                    table=table, row_id="<manifest>", expected_hash=mhead, got_hash=dbhead
                )
        return True, None

    def _payload_for(self, table: str, r: sqlite3.Row) -> dict:
        if table == "evidence":
            return {
                "evidence_id": r["evidence_id"], "case_id": r["case_id"], "item": r["item"],
                "source_id": r["source_id"], "evidence_type": r["evidence_type"],
                "source_channel": r["source_channel"],
                "expected_observables": json.loads(r["expected_observables"]), "pii": bool(r["pii"]),
            }
        return {
            "evidence_id": r["evidence_id"], "reliability": r["reliability"], "credibility": r["credibility"],
            "diagnosticity": r["diagnosticity"], "analyst_id": r["analyst_id"],
            "judgment_source": r["judgment_source"], "rationale": r["rationale"], "reason": r["reason"],
            "graded_at": r["graded_at"],
        }
