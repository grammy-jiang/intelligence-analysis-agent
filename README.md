# intelligence-analysis-agent

A composed AI agent that runs the **intelligence-analysis / analytic-tradecraft workflow** — frame a
question, enumerate competing hypotheses, weigh evidence in an ACH matrix ranked by *disconfirmation*, get
independent bias / method / calibration critique, and commit a calibrated judgment **only after a human
approves it**. Thesis: *augment, not replace* — the agent structures and challenges the reasoning; the
human owns the judgment.

Grounded in a distilled corpus of canonical works (Heuer, Kahneman, Tetlock ×2, Jervis, Kent, CIA SAT
Primer, FM 2-22.3, Masterman). Built by, and consuming reviewers from, the
[subagent-factory](../subagent-factory).

## Status — Phase 3 complete (MCP state layer); Phase 4 built, live collection gated

The prose core proved out first (MVP-0 → Phase 2 gates passed), then the persistent state/compute layer
was built on top. The whole thing still runs a case as prose in-context; the MCP layer adds a durable,
tamper-evident store and compute for cross-case learning.

| Layer | What | State |
|---|---|---|
| **Skill** (the method) | `structured-analysis` — the 11-step workflow the main agent runs in-flight | ✅ built |
| **"Doing" skills** | `source-evaluation` (Step 3) + `calibrated-forecasting` (Step 9) — the *doing* counterparts to the reviewer critics | ✅ built (Phase 2) |
| **Subagents** (the critics) | `bias-perception-reviewer`, `analytic-method-reviewer`, `calibration-forecasting-reviewer`, `deception-detection-reviewer` — read-only, delegated critique | ✅ deployed |
| **Human gate + loop-back** | no judgment is final until a human approves; failed review loops back | ✅ in the skill |
| **MCP** (state + compute) | `ach-engine`, `calibration-tracker`, `evidence-ledger` — durable, hash-chained, tamper-evident | ✅ built (Phase 3), 149 tests |
| **OSINT + deception** | `osint-toolkit` (sole egress, SSRF-guarded) + `osint-investigation` skill + `deception-detection-reviewer` | 🟡 built (Phase 4); **live collection gated off** (`OSINT_LIVE=0`) |

A case still runs **in-context as prose**; the MCP state layer is opt-in durability, not a rewrite of the
method. External collection is **off by default** and confined to a single audited egress surface.

## Validation

- **MVP-0 / Phase 1 gate — PASS** (`docs/validation/results-2026-07-10.md`, Heuer Iraqi-retaliation ACH):
  agent-assisted surfaced **5** hypotheses vs the baseline's **2**; the ACH matrix demoted the lead
  hypothesis on a "dog that didn't bark" disconfirming item; and **3/3 deliberately injected flaws** were
  each caught by the correct reviewer (vividness → bias, unstated assumption → method, overconfidence →
  calibration). The reviewers also caught a real, *unplanted* bookkeeping error in the hand-built matrix.
- **Phase 2 Brier gate — PASS** (`docs/validation/brier-forecasting-demo.md`): assisted **0.091** vs a
  naive/overconfident baseline **0.247** (63% lower) on 8 resolved questions. Honest caveat recorded — this
  validates the mechanics + direction, not a blind benchmark (that needs a held-out feed, now possible via
  `calibration-tracker`).
- **Phase 3/4 tests — 149 passing** (`python3 -m pytest`): server logic + cross-server wiring + OSINT egress
  and EXIF hardening.

Each design was gated through a factory advisor panel to **must-fix = 0** before any code: Phase 3 over
three rounds (mcp-protocol / mcp-security / mcp-quality / ai-agent-engineering); Phase 4 through a mandatory,
blocking security review (mcp-security + application-security).

## MCP servers (state + compute)

Four **FastMCP** servers, wired in `.mcp.json`. Every server keeps an append-only, hash-chained manifest and
exposes a read-only **`verify_chain`** integrity tool (run at startup + anchored to an external head hash),
so the store is tamper-evident.

| Server | Tools | Grounding |
|---|---|---|
| **calibration-tracker** | `log_forecast`, `resolve_forecast`, `void_forecast`, `get_forecast`, `list_forecasts`, `get_calibration_report`, `verify_chain` | Tetlock — question + probability **locked at commit**, only the outcome is appended; Brier/calibration computed by the tool |
| **evidence-ledger** | `add_evidence`, `grade_evidence`, `update_grade`, `get_evidence`, `list_evidence`, `get_source_history`, `verify_chain`, `verify_signals_chain` | FM 2-22.3 — reliability/credibility on two independent axes; PII a required field; unredaction gated |
| **ach-engine** | `create_matrix`, `add_hypothesis`, `rate_cell`, `score_matrix`, `get_matrix`, `list_matrices`, `verify_chain` | Heuer ACH — ranks by least-inconsistency; `score_matrix` **refuses** any cell whose evidence lacks an `analyst_confirmed` grade (collect-then-grade hole closed) |
| **osint-toolkit** | `search`, `fetch`, `compute_hash`, `extract_exif`, `reverse_image_search`, `get_map_tile`, `propose_to_ledger`, `verify_chain` | The **sole** external-egress surface; per-hop SSRF guard (IANA blocklist + canonicalization + connection pinning), egress audit log, opaque `artifact_ref`, `extract_exif` RCE-hardened |

**Security posture (Phase 4 gate = unclassified / OSINT-only):** public open-source data only; egress limited
to allowlisted OSINT sources; no classified data at rest. `judgment_source` / `analyst_id` come from a
trusted local binding, **not** an LLM argument — and are honestly bounded (skill-asserted, not server-verified).
`OSINT_LIVE=0` keeps all live connectors off until explicitly enabled.

## Use it

Open Claude Code in this repo (the `.claude/` here provides the skill + the reviewer subagents; `.mcp.json`
provides the state servers), then:

```
/structured-analysis
```

or just describe an analytic question under uncertainty. The skill maintains a **case workspace** (question
· hypotheses · evidence+grades · ACH matrix · assumptions · ranking · findings · judgment · assessment ·
indicators), delegates critique to the reviewer subagents on the raw case state, and **stops for your
approval** before finalizing. Persisting a case to the MCP servers is optional.

The product is **repo-local**: the skill and the critic subagents are co-located in this repo's `.claude/`,
so they must run together here (the orchestrator delegates to the reviewer subagents, which are not global).
Work a case per session in this repo.

## Layout

```
.claude/
  agents/     the 4 reviewer subagents (deployed from the factory — do not edit; re-export to update)
  skills/     structured-analysis (orchestrator) + source-evaluation + calibrated-forecasting
              + osint-investigation + the reviewers' own skill modules
mcp_servers/  ach_engine · calibration_tracker · evidence_ledger · osint_toolkit + common/staleness
docs/
  design/     phase3-mcp-design.md · phase4-osint-design.md (each gated to must-fix=0)
  validation/ the MVP-0/Phase-2 gates + run results + Brier tooling
tests/        149 tests — server logic + cross-server wiring + OSINT egress/EXIF
```

## Design of record

The what/why/decisions live in the factory repo under `docs/intelligence-analysis/`:
`BLUEPRINT-*` (decisions + open questions), `PIPELINE-grounded.md` (the workflow, every step cites a
source claim), `DESIGN-SPEC-*` (the how). The reviewer subagents are regenerated there and deployed here via
`cli export-deployable`.
