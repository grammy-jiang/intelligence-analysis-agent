"""Hash-chained egress audit log (design v3 control #10). Per-tool ALLOWLIST of loggable fields (fail-closed:
a field not listed is never logged, so a future secret-bearing field can't leak by omission — not a denylist)."""

from __future__ import annotations

import json
import os
import sqlite3
import threading

from ..common import GENESIS, ChainMismatch, ChainStatus, now_iso, row_hash

# Loggable arg fields per tool. Note: `query` (search) and the full `url` (fetch) are DELIBERATELY absent —
# they may carry case/source identifiers; only the validated host + connector are recorded.
LOGGABLE_FIELDS = {
    "search": ("connector", "max_results"),
    "fetch": ("host",),
    "reverse_image_search": ("connector",),
    "get_map_tile": ("connector", "zoom"),
}


class EgressAudit:
    def __init__(self, db_path: str):
        # S14: check_same_thread=False to match every sibling store — FastMCP may dispatch a tool body on a
        # worker thread. All writes are serialized by self._lock (S15), so this cannot race.
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        # S15: serialize the head-read -> hash -> INSERT -> commit sequence so two concurrent egress calls
        # cannot read the same prev_hash and fork the append-only chain (mirrors EvidenceStore._write_lock).
        self._lock = threading.Lock()
        # MF3: an external append-only manifest anchoring the chain head + row count, so trailing-row
        # truncation (deleting an attempt->ok egress pair to erase an event) is detectable — a forward-only
        # re-derivation cannot catch it. Mirrors ach-engine's manifest reconciliation.
        self._manifest_path = db_path + ".manifest.jsonl" if db_path != ":memory:" else None
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.row_factory = sqlite3.Row
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS egress_log("
            "seq INTEGER PRIMARY KEY AUTOINCREMENT, tool TEXT NOT NULL, fields TEXT NOT NULL, "
            "resolved_ip TEXT NOT NULL, outcome TEXT NOT NULL, at TEXT NOT NULL, "
            "prev_hash TEXT NOT NULL, row_hash TEXT NOT NULL)"
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def _head(self) -> str:
        r = self._conn.execute("SELECT row_hash FROM egress_log ORDER BY seq DESC LIMIT 1").fetchone()
        return r["row_hash"] if r else GENESIS

    def _append_manifest(self, head: str) -> None:
        # MF3: one manifest line per audit row (the chain head after that append), created 0600 — the
        # unkeyed chain's tamper-evidence rests on OS file isolation of both the DB and this anchor.
        if not self._manifest_path:
            return
        fd = os.open(self._manifest_path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        with os.fdopen(fd, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"head": head, "at": now_iso()}) + "\n")

    def _manifest_state(self) -> tuple[str, int] | None:
        """Last attested head + append-count from the manifest (None if this store has no manifest)."""
        if not self._manifest_path:
            return None
        head, count = GENESIS, 0
        try:
            with open(self._manifest_path, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    head = json.loads(line)["head"]
                    count += 1
        except FileNotFoundError:
            return (GENESIS, 0)
        return (head, count)

    def record(self, tool: str, fields: dict, resolved_ip: str, outcome: str) -> None:
        allow = LOGGABLE_FIELDS.get(tool, ())
        logged = {k: fields[k] for k in allow if k in fields}  # fail-closed allowlist
        with self._lock:  # S15: whole head-read -> INSERT -> commit is atomic vs other writers
            payload = {"tool": tool, "fields": logged, "resolved_ip": resolved_ip, "outcome": outcome,
                       "at": now_iso()}
            prev = self._head()
            rh = row_hash(prev, payload)
            self._conn.execute(
                "INSERT INTO egress_log(tool, fields, resolved_ip, outcome, at, prev_hash, row_hash) "
                "VALUES(?,?,?,?,?,?,?)",
                (tool, json.dumps(logged, sort_keys=True), resolved_ip, outcome, payload["at"], prev, rh),
            )
            self._conn.commit()
            self._append_manifest(rh)  # MF3: attest the new head AFTER the row durably commits

    def verify_chain(self) -> ChainStatus:
        prev = GENESIS
        verified = 0
        for r in self._conn.execute("SELECT * FROM egress_log ORDER BY seq ASC").fetchall():
            payload = {"tool": r["tool"], "fields": json.loads(r["fields"]), "resolved_ip": r["resolved_ip"],
                       "outcome": r["outcome"], "at": r["at"]}
            expected = row_hash(prev, payload)
            if expected != r["row_hash"] or r["prev_hash"] != prev:
                return ChainStatus(
                    server="osint-egress-audit", scope="all", ok=False, head_hash={"egress_log": prev},
                    rows_verified=verified,
                    mismatch=ChainMismatch(table="egress_log", row_id=str(r["seq"]), expected_hash=expected,
                                           got_hash=r["row_hash"]),
                )
            prev = r["row_hash"]
            verified += 1
        # MF3: reconcile the live table against the manifest. Truncating trailing rows leaves a self-consistent
        # shorter chain; the head + count anchor catches it (the residual both-truncated attack — dropping the
        # matching manifest tail too — needs an off-host WORM anchor).
        manifest = self._manifest_state()
        if manifest is not None:
            m_head, m_count = manifest
            if m_head != prev or m_count != verified:
                return ChainStatus(
                    server="osint-egress-audit", scope="all", ok=False, head_hash={"egress_log": prev},
                    rows_verified=verified,
                    mismatch=ChainMismatch(
                        table="egress_log", row_id="manifest",
                        expected_hash=f"{m_head} ({m_count} rows)", got_hash=f"{prev} ({verified} rows)",
                    ),
                )
        return ChainStatus(server="osint-egress-audit", scope="all", ok=True, head_hash={"egress_log": prev},
                           rows_verified=verified)

    def count(self) -> int:
        return self._conn.execute("SELECT COUNT(*) c FROM egress_log").fetchone()["c"]
