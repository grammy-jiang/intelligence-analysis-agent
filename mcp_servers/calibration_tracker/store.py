"""SQLite (WAL) append-only + hash-chained store for calibration-tracker (design v3, Server 1).

Invariants enforced here (not in the tool layer):
- forecast question+probability lock at commit; only outcomes/voids are appended (never edited) — decision #5/#4.
- `analyst_id` comes from a trusted local binding (env), NOT a tool argument.
- per-table hash chain (prev_hash + canonical_json) + an external append-only manifest for whole-chain-
  deletion detection.
All VALUES use bound parameters; only internal table-name literals are ever interpolated into SQL.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import time
import uuid
from datetime import datetime, timezone

from .models import (
    Bucket,
    CalibrationReport,
    ChainMismatch,
    ChainStatus,
    ForecastList,
    ForecastRecord,
    ForecastRef,
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


class CalibrationStore:
    def __init__(self, db_path: str, analyst_id: str | None = None):
        self.db_path = db_path
        # analyst_id: trusted local binding, never a tool arg (design v3 "Identity").
        self.analyst_id = analyst_id or os.environ.get("CALIBRATION_ANALYST_ID", "local-analyst")
        self.manifest_path = db_path + ".manifest.jsonl" if db_path != ":memory:" else None
        self._conn = sqlite3.connect(db_path)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def close(self) -> None:
        self._conn.close()

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
        assert table in _TABLES
        row = self._conn.execute(
            f"SELECT row_hash FROM {table} ORDER BY seq DESC LIMIT 1"  # noqa: S608 - table is an internal literal
        ).fetchone()
        return row["row_hash"] if row else GENESIS

    def _append_manifest(self, table: str, head: str) -> None:
        if not self.manifest_path:
            return
        with open(self.manifest_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"table": table, "head": head, "at": _now_iso()}) + "\n")

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
    ) -> ForecastRef:
        if judgment_source != "analyst_confirmed":
            raise ForecastError(
                "log_forecast requires judgment_source='analyst_confirmed' — a locked forecast must be "
                "human-confirmed (model_draft is rejected here)."
            )
        if not (0.0 <= probability <= 1.0):
            raise ForecastError("probability must be in [0, 1].")
        if not resolution_criteria.strip():
            raise ForecastError("resolution_criteria must be non-empty (a clairvoyance-style definition).")

        # Idempotency: an identical logical forecast within a short window returns the existing row.
        now = time.time()
        existing = self._conn.execute(
            "SELECT forecast_id, case_id, locked_at, created_ts FROM forecasts "
            "WHERE case_id=? AND question=? AND analyst_id=? AND ROUND(probability,4)=ROUND(?,4) "
            "ORDER BY seq DESC LIMIT 1",
            (case_id, question, self.analyst_id, probability),
        ).fetchone()
        if existing and (now - existing["created_ts"]) <= IDEMPOTENCY_WINDOW_S:
            return ForecastRef(
                forecast_id=existing["forecast_id"], case_id=existing["case_id"], locked_at=existing["locked_at"]
            )

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
        }
        prev = self._head("forecasts")
        rh = _row_hash(prev, payload)
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
        self._append_manifest("forecasts", rh)
        return ForecastRef(forecast_id=forecast_id, case_id=case_id, locked_at=locked_at)

    def _forecast_row(self, forecast_id: str) -> sqlite3.Row:
        row = self._conn.execute(
            "SELECT * FROM forecasts WHERE forecast_id=?", (forecast_id,)
        ).fetchone()
        if not row:
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
        self._forecast_row(forecast_id)
        if self._is_voided(forecast_id):
            raise ForecastError("cannot resolve a voided forecast.")
        existing = self._latest_resolution(forecast_id)
        if existing is not None and not is_correction:
            raise ForecastError(
                "forecast already resolved — pass is_correction=True with a reason to supersede (never edited)."
            )
        if is_correction and not reason.strip():
            raise ForecastError("a correction requires a non-empty reason.")
        if is_correction and existing is None:
            raise ForecastError("is_correction=True but there is no prior resolution to correct.")

        payload = {
            "forecast_id": forecast_id,
            "outcome": int(bool(outcome)),
            "resolved_at": resolved_at,
            "is_correction": int(is_correction),
            "reason": reason,
        }
        prev = self._head("resolutions")
        rh = _row_hash(prev, payload)
        self._conn.execute(
            "INSERT INTO resolutions(forecast_id, outcome, resolved_at, is_correction, reason, prev_hash, "
            "row_hash) VALUES(?,?,?,?,?,?,?)",
            (forecast_id, int(bool(outcome)), resolved_at, int(is_correction), reason, prev, rh),
        )
        self._conn.commit()
        self._append_manifest("resolutions", rh)
        return self.get_forecast(forecast_id)

    def void_forecast(self, forecast_id: str, reason: str) -> ForecastRecord:
        self._forecast_row(forecast_id)
        if self._latest_resolution(forecast_id) is not None:
            raise ForecastError(
                "cannot void an already-resolved forecast (that would let a bad outcome be purged "
                "retroactively). void is pre-resolution only."
            )
        if self._is_voided(forecast_id):
            raise ForecastError("forecast already voided.")
        if not reason.strip():
            raise ForecastError("void requires a non-empty reason.")
        payload = {"forecast_id": forecast_id, "reason": reason, "at": _now_iso()}
        prev = self._head("voids")
        rh = _row_hash(prev, payload)
        self._conn.execute(
            "INSERT INTO voids(forecast_id, reason, at, prev_hash, row_hash) VALUES(?,?,?,?,?)",
            (forecast_id, reason, payload["at"], prev, rh),
        )
        self._conn.commit()
        self._append_manifest("voids", rh)
        return self.get_forecast(forecast_id)

    def get_forecast(self, forecast_id: str) -> ForecastRecord:
        row = self._forecast_row(forecast_id)
        res = self._latest_resolution(forecast_id)
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
            row_hash=row["row_hash"],
        )

    def list_forecasts(
        self, case_id: str | None = None, resolved: bool | None = None, limit: int = 100, cursor: str | None = None
    ) -> ForecastList:
        limit = max(1, min(limit, 1000))
        after = int(cursor) if cursor else 0
        rows = self._conn.execute(
            "SELECT forecast_id, seq FROM forecasts WHERE seq > ? "
            + ("AND case_id = ? " if case_id else "")
            + "ORDER BY seq ASC LIMIT ?",
            ((after, case_id, limit + 1) if case_id else (after, limit + 1)),
        ).fetchall()
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
        q = (
            "SELECT f.forecast_id, f.probability FROM forecasts f "
            "WHERE f.judgment_source='analyst_confirmed' "
            "AND f.forecast_id NOT IN (SELECT forecast_id FROM voids) "
            + ("AND f.case_id = ? " if case_id else "")
        )
        rows = self._conn.execute(q, ((case_id,) if case_id else ())).fetchall()
        pairs: list[tuple[float, int]] = []
        for r in rows:
            res = self._latest_resolution(r["forecast_id"])
            if res is not None:
                pairs.append((r["probability"], int(res["outcome"])))
        n_voided = self._conn.execute(
            "SELECT COUNT(*) c FROM voids v JOIN forecasts f ON f.forecast_id=v.forecast_id "
            "WHERE f.judgment_source='analyst_confirmed' " + ("AND f.case_id=?" if case_id else ""),
            ((case_id,) if case_id else ()),
        ).fetchone()["c"]

        n = len(pairs)
        if n == 0:
            return CalibrationReport(
                n=0, n_voided=n_voided, brier=None, buckets=[], resolution_component=None,
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
            brier=round(brier, 6),
            buckets=buckets,
            resolution_component=round(resolution, 6),
            reliability_component=round(reliability, 6),
            note=("n<10" if n < 10 else ""),
        )

    # ---- integrity ---------------------------------------------------------
    def verify_chain(self, case_id: str | None = None) -> ChainStatus:
        heads: dict[str, str] = {}
        verified = 0
        for table in _TABLES:
            prev = GENESIS
            rows = self._conn.execute(
                f"SELECT * FROM {table} ORDER BY seq ASC"  # noqa: S608 - internal literal
            ).fetchall()
            for r in rows:
                payload = self._payload_for(table, r)
                expected = _row_hash(prev, payload)
                if expected != r["row_hash"] or r["prev_hash"] != prev:
                    return ChainStatus(
                        server="calibration-tracker", scope=case_id or "all", ok=False,
                        head_hash=heads, rows_verified=verified,
                        mismatch=ChainMismatch(
                            table=table, row_id=str(r["seq"]), expected_hash=expected, got_hash=r["row_hash"]
                        ),
                    )
                prev = r["row_hash"]
                verified += 1
            heads[table] = prev
        # External manifest check: DB head must match the last manifest entry per table (whole-chain deletion).
        manifest_ok, mismatch = self._check_manifest(heads)
        return ChainStatus(
            server="calibration-tracker", scope=case_id or "all", ok=manifest_ok,
            head_hash=heads, rows_verified=verified, mismatch=mismatch,
        )

    def _payload_for(self, table: str, r: sqlite3.Row) -> dict:
        if table == "forecasts":
            return {
                "forecast_id": r["forecast_id"], "case_id": r["case_id"], "question": r["question"],
                "probability": r["probability"], "resolution_criteria": r["resolution_criteria"],
                "horizon": r["horizon"], "analyst_id": r["analyst_id"],
                "judgment_source": r["judgment_source"], "rationale": r["rationale"], "locked_at": r["locked_at"],
            }
        if table == "resolutions":
            return {
                "forecast_id": r["forecast_id"], "outcome": r["outcome"], "resolved_at": r["resolved_at"],
                "is_correction": r["is_correction"], "reason": r["reason"],
            }
        return {"forecast_id": r["forecast_id"], "reason": r["reason"], "at": r["at"]}

    def _check_manifest(self, heads: dict[str, str]) -> tuple[bool, ChainMismatch | None]:
        if not self.manifest_path or not os.path.exists(self.manifest_path):
            return True, None
        last: dict[str, str] = {}
        with open(self.manifest_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    e = json.loads(line)
                    last[e["table"]] = e["head"]
        for table, mhead in last.items():
            dbhead = heads.get(table, GENESIS)
            if dbhead != mhead:
                return False, ChainMismatch(
                    table=table, row_id="<manifest>", expected_hash=mhead, got_hash=dbhead
                )
        return True, None
