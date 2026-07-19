"""SQLite (WAL) append-only + hash-chained store for calibration-tracker (design v3, Server 1).

Invariants enforced here (not in the tool layer):
- forecast question+probability lock at commit; only outcomes/voids are appended (never edited) — decision #5/#4.
- `analyst_id` comes from a trusted local binding (env), NOT a tool argument.
- per-table hash chain (prev_hash + canonical_json) + an external append-only manifest for whole-chain-
  deletion detection.
All VALUES use bound parameters; only internal table-name literals are ever interpolated into SQL.
"""

from __future__ import annotations

import fcntl
import hashlib
import io
import json
import os
import sqlite3
import threading
import time
import uuid
from datetime import date, datetime, timezone

from .models import (
    Bucket,
    CalibrationReport,
    ChainMismatch,
    ChainStatus,
    ForecastList,
    ForecastRecord,
)

GENESIS = "0" * 64
IDEMPOTENCY_WINDOW_S = 5.0
_TABLES = ("forecasts", "resolutions", "voids")


class ForecastError(Exception):
    """Business-rule violation; the server layer wraps this as a FastMCP ToolError."""


def _canon(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _row_hash(prev_hash: str, payload: dict) -> str:
    return hashlib.sha256((prev_hash + _canon(payload)).encode("utf-8")).hexdigest()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# Free-text field caps (S5): bound every string that lands in the hash-chained ledger so a single
# tool call cannot inflate the append-only store without limit. MAX_ID = 512 aligns case_id — the SHARED
# cross-server correlation key — with ach-engine and evidence-ledger (both 512), so a case_id valid in one
# server is valid in all three (it was 200 here, a silent inconsistency on the shared key).
MAX_ID = 512
MAX_SHORT = 500
MAX_TEXT = 4000

# Advisory hindsight heuristic (M3, the ungameable half): a resolution logged less than this long after the
# SERVER-AUTHORED locked_at is flagged (resolved_within_min_latency) as a possible log-then-immediately-
# self-grade with hindsight. Unlike the horizon-keyed signal, the anchor (locked_at) is NOT analyst-
# controllable, so it catches the honest same-day / ISO-duration-horizon case the horizon comparison misses.
# Advisory only — early resolution is legitimate and nothing is excluded from scoring.
_MIN_RESOLUTION_LATENCY_S = 86400  # 24h


def _parse_iso(value: str) -> datetime:
    """Parse an ISO-8601 date or datetime; naive values are treated as UTC. Raises ValueError on junk."""
    dt = datetime.fromisoformat(value) if "T" in value or ":" in value else datetime.combine(
        date.fromisoformat(value), datetime.min.time()
    )
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


class CalibrationStore:
    def __init__(self, db_path: str, analyst_id: str | None = None):
        self.db_path = db_path
        # analyst_id: trusted local binding, never a tool arg (design v3 "Identity").
        self.analyst_id = analyst_id or os.environ.get("CALIBRATION_ANALYST_ID", "local-analyst")
        self.manifest_path = db_path + ".manifest.jsonl" if db_path != ":memory:" else None
        # Serialize all head-read -> INSERT -> commit -> manifest sequences in-process so two threads
        # cannot read the same head and fork the chain (S1). Cross-process writers remain out of scope
        # (single-writer local design); a fork is still caught fail-closed by verify_chain at startup.
        self._write_lock = threading.RLock()
        # S3: the RLock only serializes threads inside ONE process. Take an OS-level exclusive advisory
        # lock on a sidecar so a SECOND process opening the same file DB fails closed instead of forking
        # the append-only chain (single-writer-local design). :memory: DBs have no cross-process sharing.
        self._lock_fh: io.TextIOWrapper | None = None
        if db_path != ":memory:":
            self._acquire_process_lock(db_path)
        # check_same_thread=False (N3): defensive — a future FastMCP dispatch model may run tool bodies on
        # a worker thread; all writes are already serialized by self._write_lock, so this cannot race.
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        mode = self._conn.execute("PRAGMA journal_mode=WAL").fetchone()[0]
        # N8: WAL silently falls back to the prior mode on some filesystems; fail loud rather than run
        # under concurrency assumptions the journal mode does not actually provide.
        if db_path != ":memory:" and str(mode).lower() != "wal":
            raise ForecastError(f"could not enable WAL journal mode (got {mode!r}); refusing to run.")
        self._conn.row_factory = sqlite3.Row
        self._init_schema()
        # M2: the manifest tail hash + the last attested per-table row count (the truncation anchor).
        self._manifest_head, self._manifest_counts = self._read_manifest_state()

    def _acquire_process_lock(self, db_path: str) -> None:
        lock_path = db_path + ".lock"
        fh = open(lock_path, "w", encoding="utf-8")  # noqa: SIM115 - held for the store's lifetime
        try:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            fh.close()
            raise ForecastError(
                f"calibration DB {db_path} is already open by another process (single-writer local design); "
                "refusing to open a second writer."
            )
        self._lock_fh = fh

    def close(self) -> None:
        self._conn.close()
        if self._lock_fh is not None:
            fcntl.flock(self._lock_fh.fileno(), fcntl.LOCK_UN)
            self._lock_fh.close()
            self._lock_fh = None

    def _init_schema(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS forecasts(
                seq INTEGER PRIMARY KEY AUTOINCREMENT,
                forecast_id TEXT UNIQUE NOT NULL, case_id TEXT NOT NULL, question TEXT NOT NULL,
                probability REAL NOT NULL, resolution_criteria TEXT NOT NULL, horizon TEXT NOT NULL,
                analyst_id TEXT NOT NULL, judgment_source TEXT NOT NULL, rationale TEXT NOT NULL DEFAULT '',
                locked_at TEXT NOT NULL, created_ts REAL NOT NULL,
                prev_hash TEXT NOT NULL, row_hash TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS resolutions(
                seq INTEGER PRIMARY KEY AUTOINCREMENT,
                forecast_id TEXT NOT NULL, outcome INTEGER NOT NULL, resolved_at TEXT NOT NULL,
                is_correction INTEGER NOT NULL DEFAULT 0, reason TEXT NOT NULL DEFAULT '',
                prev_hash TEXT NOT NULL, row_hash TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS voids(
                seq INTEGER PRIMARY KEY AUTOINCREMENT,
                forecast_id TEXT NOT NULL, reason TEXT NOT NULL, at TEXT NOT NULL,
                prev_hash TEXT NOT NULL, row_hash TEXT NOT NULL);
            """
        )
        self._conn.commit()

    # ---- hash chain helpers ------------------------------------------------
    def _head(self, table: str) -> str:
        if table not in _TABLES:  # N4: guard survives `python -O` (assert is stripped), not attacker-controlled
            raise ValueError(f"unknown table: {table!r}")
        row = self._conn.execute(
            f"SELECT row_hash FROM {table} ORDER BY seq DESC LIMIT 1"  # noqa: S608 - table is an internal literal
        ).fetchone()
        return row["row_hash"] if row else GENESIS

    def _read_manifest_state(self) -> tuple[str, dict[str, int]]:
        """Last manifest_hash (tail of the self-chain) + the last attested per-table row count on disk.
        GENESIS + {} if no manifest yet. M2: the counts feed verify_chain's tail-truncation anchor."""
        counts: dict[str, int] = {}
        if not self.manifest_path or not os.path.exists(self.manifest_path):
            return GENESIS, counts
        last = GENESIS
        seen: set[str] = set()  # tables with ANY manifest entry
        has_count: set[str] = set()  # tables with at least one "count"-bearing entry
        with open(self.manifest_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                e = json.loads(line)
                last = e.get("manifest_hash", GENESIS)
                seen.add(e["table"])
                if "count" in e:
                    counts[e["table"]] = e["count"]
                    has_count.add(e["table"])
        # M2 count-migration: a PRE-count manifest (entries lacking "count") would otherwise seed the next
        # append's running count from 0 — so the following write attests count=1 while the live table already
        # holds N rows, a FALSE verify_chain tamper on upgrade. Seed the running count from the live table's
        # actual row count for any table that has manifest entries but never carried a "count".
        for table in seen - has_count:
            if table in _TABLES:  # ignore an unknown/forged table name (the self-chain check catches that)
                counts[table] = self._conn.execute(
                    f"SELECT COUNT(*) c FROM {table}"  # noqa: S608 - table is an internal literal from _TABLES
                ).fetchone()["c"]
        return last, counts

    def _append_manifest(self, table: str, head: str, count: int | None = None) -> None:
        # Self-chained + fsync'd external attestation of each per-table head. Each line binds to the
        # previous manifest line's hash, so a mid-file line cannot be edited or dropped undetected;
        # a whole-file/whole-table deletion is caught by _check_manifest's fail-closed presence check.
        # Residual risk (documented): the manifest shares the DB's trust domain, so an attacker with
        # filesystem write can recompute the entire self-chain in lockstep — durable tamper-evidence
        # requires shipping these heads to a separate append-only/WORM log.
        if not self.manifest_path:
            return
        at = _now_iso()
        # M2: attest a monotonic per-table row count alongside the head. Normal per-row appends increment it;
        # seed_manifest_baseline passes the true current count. `count` is inside the hashed payload, so it is
        # covered by the manifest self-chain and cannot be edited without breaking it.
        if count is None:
            count = self._manifest_counts.get(table, 0) + 1
        payload = {"table": table, "head": head, "at": at, "count": count}
        mh = _row_hash(self._manifest_head, payload)
        entry = {**payload, "prev_manifest_hash": self._manifest_head, "manifest_hash": mh}
        with open(self.manifest_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        self._manifest_head = mh
        self._manifest_counts[table] = count

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
                    n = self._conn.execute(
                        f"SELECT COUNT(*) c FROM {table}"  # noqa: S608 - table is an internal literal
                    ).fetchone()["c"]
                    self._append_manifest(table, head, count=n)  # M2: seed the true row count
                    written += 1
        return written

    # ---- forecast lifecycle ------------------------------------------------
    def log_forecast(
        self,
        case_id: str,
        question: str,
        probability: float,
        resolution_criteria: str,
        horizon: str,
        judgment_source: str,
        rationale: str = "",
    ) -> ForecastRecord:
        if judgment_source != "analyst_confirmed":
            raise ForecastError(
                "log_forecast requires judgment_source='analyst_confirmed' — a locked forecast must be "
                "human-confirmed (model_draft is rejected here)."
            )
        if not (0.0 <= probability <= 1.0):
            raise ForecastError("probability must be in [0, 1].")
        # Every required string that enters the immutable ledger must be non-empty and bounded (S5/S6).
        for name, value, cap in (
            ("case_id", case_id, MAX_ID),
            ("question", question, MAX_TEXT),
            ("resolution_criteria", resolution_criteria, MAX_TEXT),
            ("horizon", horizon, MAX_SHORT),
        ):
            if not value.strip():
                raise ForecastError(f"{name} must be non-empty.")
            if len(value) > cap:
                raise ForecastError(f"{name} exceeds max length {cap}.")
        if len(rationale) > MAX_TEXT:
            raise ForecastError(f"rationale exceeds max length {MAX_TEXT}.")

        with self._write_lock:
            # Idempotency: an identical logical forecast within a short window returns the existing row.
            # The dedup key is the full logical content (S11) so a retry that differs in any field is a
            # NEW forecast, never silently dropped as a duplicate.
            now = time.time()
            existing = self._conn.execute(
                "SELECT forecast_id, case_id, locked_at, created_ts FROM forecasts "
                "WHERE case_id=? AND question=? AND analyst_id=? AND ROUND(probability,4)=ROUND(?,4) "
                "AND resolution_criteria=? AND horizon=? AND rationale=? "
                "ORDER BY seq DESC LIMIT 1",
                (case_id, question, self.analyst_id, probability, resolution_criteria, horizon, rationale),
            ).fetchone()
            if existing and (now - existing["created_ts"]) <= IDEMPOTENCY_WINDOW_S:
                # S5: echo the full locked record even on the idempotent short-circuit.
                return self.get_forecast(existing["forecast_id"])

            forecast_id = uuid.uuid4().hex
            locked_at = _now_iso()
            payload = {
                "forecast_id": forecast_id,
                "case_id": case_id,
                "question": question,
                "probability": probability,
                "resolution_criteria": resolution_criteria,
                "horizon": horizon,
                "analyst_id": self.analyst_id,
                "judgment_source": judgment_source,
                "rationale": rationale,
                "locked_at": locked_at,
                # S2: created_ts is a real column (gates the idempotency window). Cover it in the row hash
                # so it cannot be altered in the DB file without verify_chain detecting it.
                "created_ts": now,
            }
            prev = self._head("forecasts")
            rh = _row_hash(prev, payload)
            # S1: on a failed execute, roll back so a dangling open transaction cannot be smuggled into
            # the append-only ledger by the next successful commit.
            try:
                self._conn.execute(
                    "INSERT INTO forecasts(forecast_id, case_id, question, probability, resolution_criteria, "
                    "horizon, analyst_id, judgment_source, rationale, locked_at, created_ts, prev_hash, row_hash) "
                    "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        forecast_id, case_id, question, probability, resolution_criteria, horizon,
                        self.analyst_id, judgment_source, rationale, locked_at, now, prev, rh,
                    ),
                )
                self._conn.commit()
            except Exception:
                self._conn.rollback()
                raise
            self._append_manifest("forecasts", rh)
            return self.get_forecast(forecast_id)

    def _forecast_row(self, forecast_id: str) -> sqlite3.Row:
        row = self._conn.execute(
            "SELECT * FROM forecasts WHERE forecast_id=?", (forecast_id,)
        ).fetchone()
        # S3: a shared DB file may hold other analysts' rows. Reject cross-analyst access, and report it
        # as "unknown" so this store is not an oracle for another analyst's forecast_ids.
        if not row or row["analyst_id"] != self.analyst_id:
            raise ForecastError(f"unknown forecast_id: {forecast_id}")
        return row

    def _latest_resolution(self, forecast_id: str) -> sqlite3.Row | None:
        return self._conn.execute(
            "SELECT * FROM resolutions WHERE forecast_id=? ORDER BY seq DESC LIMIT 1", (forecast_id,)
        ).fetchone()

    def _is_voided(self, forecast_id: str) -> bool:
        return (
            self._conn.execute(
                "SELECT 1 FROM voids WHERE forecast_id=? LIMIT 1", (forecast_id,)
            ).fetchone()
            is not None
        )

    def resolve_forecast(
        self, forecast_id: str, outcome: bool, resolved_at: str, is_correction: bool = False, reason: str = ""
    ) -> ForecastRecord:
        if len(reason) > MAX_TEXT:
            raise ForecastError(f"reason exceeds max length {MAX_TEXT}.")
        # resolved_at must be a real ISO-8601 timestamp (pure input validation — no chain state yet).
        try:
            resolved_dt = _parse_iso(resolved_at)
        except ValueError as e:
            raise ForecastError(f"resolved_at must be ISO-8601 (e.g. 2026-01-31 or 2026-01-31T12:00:00Z): {e}")

        # M1 (TOCTOU): the single-resolution decision (does a prior resolution already exist?) and the
        # head-read + INSERT MUST be one atomic critical section. Reading `_latest_resolution` OUTSIDE the lock
        # lets two concurrent resolve_forecast(is_correction=False) calls both observe "unresolved" and both
        # append a first resolution — silently defeating the no-double-resolve invariant. Mirror the correct
        # _insert_hypothesis / evidence-ledger _insert_grade pattern: check-then-act under the lock.
        with self._write_lock:
            row = self._forecast_row(forecast_id)
            if self._is_voided(forecast_id):
                raise ForecastError("cannot resolve a voided forecast.")
            existing = self._latest_resolution(forecast_id)
            if existing is not None and not is_correction:
                raise ForecastError(
                    "forecast already resolved — pass is_correction=True with a reason to supersede "
                    "(never edited)."
                )
            if is_correction and not reason.strip():
                raise ForecastError("a correction requires a non-empty reason.")
            if is_correction and existing is None:
                raise ForecastError("is_correction=True but there is no prior resolution to correct.")
            # N5: locked_at is written by the store itself, so a parse failure means the row is corrupt —
            # fail loud rather than silently disabling the anti-backdating check.
            try:
                locked_dt = _parse_iso(row["locked_at"])
            except ValueError as e:
                raise ForecastError(
                    f"stored locked_at ({row['locked_at']!r}) is not valid ISO-8601 — refusing to resolve "
                    f"against a corrupt lock timestamp: {e}"
                )
            # resolved_at cannot predate the forecast lock — else an outcome could be backdated (S4).
            if resolved_dt < locked_dt:
                raise ForecastError(
                    f"resolved_at ({resolved_at}) is earlier than the forecast's locked_at ({row['locked_at']})."
                )
            payload = {
                "forecast_id": forecast_id,
                "outcome": int(bool(outcome)),
                "resolved_at": resolved_at,
                "is_correction": int(is_correction),
                "reason": reason,
            }
            prev = self._head("resolutions")
            rh = _row_hash(prev, payload)
            try:  # S1: roll back a failed execute so no partial transaction survives to the next commit.
                self._conn.execute(
                    "INSERT INTO resolutions(forecast_id, outcome, resolved_at, is_correction, reason, prev_hash, "
                    "row_hash) VALUES(?,?,?,?,?,?,?)",
                    (forecast_id, int(bool(outcome)), resolved_at, int(is_correction), reason, prev, rh),
                )
                self._conn.commit()
            except Exception:
                self._conn.rollback()
                raise
            self._append_manifest("resolutions", rh)
        return self.get_forecast(forecast_id)

    def void_forecast(self, forecast_id: str, reason: str) -> ForecastRecord:
        if not reason.strip():
            raise ForecastError("void requires a non-empty reason.")
        if len(reason) > MAX_TEXT:
            raise ForecastError(f"reason exceeds max length {MAX_TEXT}.")
        # M1 (TOCTOU): existence + not-resolved + not-already-voided decisions and the INSERT are one atomic
        # critical section (mirrors resolve_forecast). Reading these outside the lock lets a concurrent
        # resolve/void interleave defeat the pre-resolution-only + single-void invariants.
        with self._write_lock:
            self._forecast_row(forecast_id)
            if self._latest_resolution(forecast_id) is not None:
                raise ForecastError(
                    "cannot void an already-resolved forecast (that would let a bad outcome be purged "
                    "retroactively). void is pre-resolution only."
                )
            if self._is_voided(forecast_id):
                raise ForecastError("forecast already voided.")
            payload = {"forecast_id": forecast_id, "reason": reason, "at": _now_iso()}
            prev = self._head("voids")
            rh = _row_hash(prev, payload)
            try:  # S1: roll back a failed execute so no partial transaction survives to the next commit.
                self._conn.execute(
                    "INSERT INTO voids(forecast_id, reason, at, prev_hash, row_hash) VALUES(?,?,?,?,?)",
                    (forecast_id, reason, payload["at"], prev, rh),
                )
                self._conn.commit()
            except Exception:
                self._conn.rollback()
                raise
            self._append_manifest("voids", rh)
        return self.get_forecast(forecast_id)

    def _correction_count(self, forecast_id: str) -> int:
        return self._conn.execute(
            "SELECT COUNT(*) c FROM resolutions WHERE forecast_id=? AND is_correction=1", (forecast_id,)
        ).fetchone()["c"]

    def get_forecast(self, forecast_id: str) -> ForecastRecord:
        row = self._forecast_row(forecast_id)
        res = self._latest_resolution(forecast_id)
        corrections = self._correction_count(forecast_id)
        return ForecastRecord(
            forecast_id=row["forecast_id"],
            case_id=row["case_id"],
            question=row["question"],
            probability=row["probability"],
            resolution_criteria=row["resolution_criteria"],
            horizon=row["horizon"],
            analyst_id=row["analyst_id"],
            judgment_source=row["judgment_source"],
            rationale=row["rationale"],
            locked_at=row["locked_at"],
            outcome=(bool(res["outcome"]) if res else None),
            resolved_at=(res["resolved_at"] if res else None),
            voided=self._is_voided(forecast_id),
            was_corrected=corrections > 0,
            correction_count=corrections,
            row_hash=row["row_hash"],
        )

    def list_forecasts(
        self, case_id: str | None = None, resolved: bool | None = None, limit: int = 100, cursor: str | None = None
    ) -> ForecastList:
        limit = max(1, min(limit, 1000))
        try:
            after = int(cursor) if cursor else 0
        except (ValueError, TypeError):
            raise ForecastError("invalid cursor.")
        if after < 0:
            raise ForecastError("invalid cursor.")
        # S3: only ever list this analyst's own rows, even on a shared DB file.
        sql = "SELECT forecast_id, seq FROM forecasts WHERE seq > ? AND analyst_id = ? "
        params: list = [after, self.analyst_id]
        if case_id:
            sql += "AND case_id = ? "
            params.append(case_id)
        sql += "ORDER BY seq ASC LIMIT ?"
        params.append(limit + 1)
        rows = self._conn.execute(sql, params).fetchall()
        items: list[ForecastRecord] = []
        last_seq = after
        for r in rows[:limit]:
            rec = self.get_forecast(r["forecast_id"])
            if resolved is not None and (rec.outcome is not None) != resolved:
                last_seq = r["seq"]
                continue
            items.append(rec)
            last_seq = r["seq"]
        next_cursor = str(last_seq) if len(rows) > limit else None
        return ForecastList(items=items, next_cursor=next_cursor)

    # ---- calibration report -----------------------------------------------
    def get_calibration_report(self, case_id: str | None = None) -> CalibrationReport:
        """Compute Brier + Murphy decomposition over resolved, non-voided analyst_confirmed forecasts.

        Also emits `resolved_before_horizon`: an ADVISORY count of resolutions that landed strictly before
        a stated, ISO-8601-parseable `horizon` — a signal for human review of possible premature/hindsight
        resolution, NOT a correctness failure. Early resolution is legitimate (an outcome can be known
        before the stated deadline) and a free-form (non-date) horizon is skipped. The HARD anti-hindsight
        controls live in resolve_forecast (the immutable lock + the resolved_at >= locked_at anti-backdate);
        this is a review signal only and excludes nothing from scoring.
        """
        # S3: scope the report to this analyst's own forecasts on a shared DB file.
        q = (
            "SELECT f.forecast_id, f.probability, f.horizon, f.locked_at FROM forecasts f "
            "WHERE f.judgment_source='analyst_confirmed' AND f.analyst_id = ? "
            "AND f.forecast_id NOT IN (SELECT forecast_id FROM voids) "
            + ("AND f.case_id = ? " if case_id else "")
        )
        rows = self._conn.execute(
            q, ((self.analyst_id, case_id) if case_id else (self.analyst_id,))
        ).fetchall()
        pairs: list[tuple[float, int]] = []
        n_corrected = 0
        resolved_before_horizon = 0
        n_horizon_checked = 0
        n_horizon_skipped = 0
        resolved_within_min_latency = 0
        for r in rows:
            res = self._latest_resolution(r["forecast_id"])
            if res is not None:
                pairs.append((r["probability"], int(res["outcome"])))
                if self._correction_count(r["forecast_id"]) > 0:
                    n_corrected += 1
                # ADVISORY (hindsight-auditability), NOT a gate. TWO independent signals — nothing here is
                # blocked or excluded from Brier; the HARD controls are the immutable lock + resolved_at>=locked_at:
                # (1) HORIZON-keyed: resolved strictly before a stated, PARSEABLE horizon. `horizon` is free-form
                #     (S5) and ANALYST-authored, so a non-date ("end of Q2"), an ISO-8601 DURATION ("P30D"), or a
                #     same-day date does not flag — n_horizon_checked/skipped disclose that coverage so
                #     resolved_before_horizon=0 cannot be misread as "no risk" when it means "no parseable horizon".
                # (2) LATENCY-keyed: resolved within _MIN_RESOLUTION_LATENCY_S of the SERVER-authored locked_at.
                #     The anchor is not analyst-controllable, so this catches the honest log-then-immediately-
                #     self-grade case signal (1) misses. Still advisory (an actor can assert a late resolved_at,
                #     but that then lives on the hash-chained record).
                try:
                    if _parse_iso(res["resolved_at"]) < _parse_iso(r["horizon"]):
                        resolved_before_horizon += 1
                    n_horizon_checked += 1
                except ValueError:
                    n_horizon_skipped += 1  # non-date horizon (free-form OR ISO-8601 duration) — no signal
                try:
                    gap = (_parse_iso(res["resolved_at"]) - _parse_iso(r["locked_at"])).total_seconds()
                    if gap < _MIN_RESOLUTION_LATENCY_S:
                        resolved_within_min_latency += 1
                except ValueError:
                    pass  # locked_at is server-authored ISO; guard defensively, never fatal
        n_voided = self._conn.execute(
            "SELECT COUNT(*) c FROM voids v JOIN forecasts f ON f.forecast_id=v.forecast_id "
            "WHERE f.judgment_source='analyst_confirmed' AND f.analyst_id=? "
            + ("AND f.case_id=?" if case_id else ""),
            ((self.analyst_id, case_id) if case_id else (self.analyst_id,)),
        ).fetchone()["c"]

        n = len(pairs)
        if n == 0:
            return CalibrationReport(
                n=0, n_voided=n_voided, n_corrected=0, resolved_before_horizon=resolved_before_horizon,
                n_horizon_checked=n_horizon_checked, n_horizon_skipped=n_horizon_skipped,
                resolved_within_min_latency=resolved_within_min_latency,
                brier=None, buckets=[], resolution_component=None,
                reliability_component=None, note="no resolved analyst_confirmed forecasts yet",
            )
        brier = sum((p - o) ** 2 for p, o in pairs) / n
        obar = sum(o for _, o in pairs) / n
        buckets: list[Bucket] = []
        reliability = 0.0
        resolution = 0.0
        for i in range(10):
            lo, hi = i / 10, (i + 1) / 10
            grp = [(p, o) for p, o in pairs if (lo <= p < hi or (i == 9 and p == 1.0))]
            if grp:
                nk = len(grp)
                pk = sum(p for p, _ in grp) / nk
                ok = sum(o for _, o in grp) / nk
                reliability += nk * (pk - ok) ** 2
                resolution += nk * (ok - obar) ** 2
                buckets.append(Bucket(p_range=f"{lo:.1f}-{hi:.1f}", n=nk, observed_freq=round(ok, 4)))
            else:
                buckets.append(Bucket(p_range=f"{lo:.1f}-{hi:.1f}", n=0, observed_freq=None))
        reliability /= n
        resolution /= n
        return CalibrationReport(
            n=n,
            n_voided=n_voided,
            n_corrected=n_corrected,
            resolved_before_horizon=resolved_before_horizon,
            n_horizon_checked=n_horizon_checked,
            n_horizon_skipped=n_horizon_skipped,
            resolved_within_min_latency=resolved_within_min_latency,
            brier=round(brier, 6),
            buckets=buckets,
            resolution_component=round(resolution, 6),
            reliability_component=round(reliability, 6),
            note=("n<10" if n < 10 else ""),
        )

    # ---- integrity ---------------------------------------------------------
    def verify_chain(self) -> ChainStatus:
        # Integrity is table-wide by construction and CANNOT be scoped to a case_id, so no scope param
        # is accepted and scope is always reported as "all" (S8) — the response never claims a narrower
        # check than the one that actually ran.
        # M1/lock: hold the write lock for the whole read+manifest walk (mirrors evidence-ledger). Every
        # writer holds _write_lock across its commit -> manifest-append; without the lock here a verify
        # interleaved with an in-flight write could read a row committed-but-not-yet-manifest-attested and
        # report a spurious tamper. RLock is reentrant, so a caller already holding it won't deadlock.
        with self._write_lock:
            heads: dict[str, str] = {}
            counts: dict[str, int] = {}
            verified = 0
            for table in _TABLES:
                prev = GENESIS
                count = 0
                rows = self._conn.execute(
                    f"SELECT * FROM {table} ORDER BY seq ASC"  # noqa: S608 - internal literal
                ).fetchall()
                for r in rows:
                    payload = self._payload_for(table, r)
                    expected = _row_hash(prev, payload)
                    if expected != r["row_hash"] or r["prev_hash"] != prev:
                        return ChainStatus(
                            server="calibration-tracker", scope="all", ok=False,
                            head_hash=heads, rows_verified=verified,
                            mismatch=ChainMismatch(
                                table=table, row_id=str(r["seq"]), expected_hash=expected, got_hash=r["row_hash"]
                            ),
                        )
                    prev = r["row_hash"]
                    count += 1
                    verified += 1
                heads[table] = prev
                counts[table] = count
            # External manifest check: DB head AND row count must match the last manifest entry per table
            # (catches whole-chain deletion and trailing-row truncation of a self-consistent shorter chain).
            manifest_ok, mismatch = self._check_manifest(heads, counts)
            return ChainStatus(
                server="calibration-tracker", scope="all", ok=manifest_ok,
                head_hash=heads, rows_verified=verified, mismatch=mismatch,
            )

    def _payload_for(self, table: str, r: sqlite3.Row) -> dict:
        if table == "forecasts":
            return {
                "forecast_id": r["forecast_id"], "case_id": r["case_id"], "question": r["question"],
                "probability": r["probability"], "resolution_criteria": r["resolution_criteria"],
                "horizon": r["horizon"], "analyst_id": r["analyst_id"],
                "judgment_source": r["judgment_source"], "rationale": r["rationale"], "locked_at": r["locked_at"],
                "created_ts": r["created_ts"],  # S2: hash covers created_ts (see log_forecast payload).
            }
        if table == "resolutions":
            return {
                "forecast_id": r["forecast_id"], "outcome": r["outcome"], "resolved_at": r["resolved_at"],
                "is_correction": r["is_correction"], "reason": r["reason"],
            }
        return {"forecast_id": r["forecast_id"], "reason": r["reason"], "at": r["at"]}

    def _check_manifest(
        self, heads: dict[str, str], counts: dict[str, int]
    ) -> tuple[bool, ChainMismatch | None]:
        # In-memory stores have no manifest by design (nothing to attest).
        if not self.manifest_path:
            return True, None
        # Any table whose DB chain is non-empty MUST be attested by the manifest; a missing manifest
        # file — or a missing per-table entry — is treated fail-closed as tampering, NOT a vacuous pass
        # (M1a). This is what catches whole-chain / whole-table deletion of both the rows and the file.
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
        last_count: dict[str, int] = {}
        prev = GENESIS
        with open(self.manifest_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                e = json.loads(line)
                mpayload = {"table": e["table"], "head": e["head"], "at": e["at"]}
                if "count" in e:  # M2: count is part of the attested (hashed) payload when present
                    mpayload["count"] = e["count"]
                expected = _row_hash(prev, mpayload)
                if e.get("prev_manifest_hash") != prev or e.get("manifest_hash") != expected:
                    return False, ChainMismatch(
                        table=e.get("table", "?"), row_id="<manifest-chain>",
                        expected_hash=expected, got_hash=str(e.get("manifest_hash", "")),
                    )
                prev = expected
                last[e["table"]] = e["head"]
                if "count" in e:
                    last_count[e["table"]] = e["count"]
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
        # M2: the last attested per-table row count must match the live table — catches trailing-row
        # truncation that leaves a self-consistent but shorter chain (defense-in-depth alongside the head
        # check; the residual both-truncated attack needs an off-host WORM anchor — see _append_manifest).
        for table, mcount in last_count.items():
            if mcount != counts.get(table, 0):
                return False, ChainMismatch(
                    table=table, row_id="<manifest-count>",
                    expected_hash=f"{mcount} rows (manifest)", got_hash=f"{counts.get(table, 0)} rows (table)",
                )
        return True, None
