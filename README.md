# intelligence-analysis-agent

A composed AI agent that runs the **intelligence-analysis / analytic-tradecraft workflow** — frame a
question, enumerate competing hypotheses, weigh evidence in an ACH matrix ranked by *disconfirmation*, get
independent bias / method / calibration critique, and commit a calibrated judgment **only after a human
approves it**. Thesis: *augment, not replace* — the agent structures and challenges the reasoning; the
human owns the judgment.

Grounded in a distilled corpus of canonical works (Heuer, Kahneman, Tetlock ×2, Jervis, Kent, CIA SAT
Primer, FM 2-22.3). Built by, and consuming reviewers from, the [subagent-factory](../subagent-factory).

## Status — MVP-0 (Phase 1): prose analysis core, zero MCP

| Layer | What | State |
|---|---|---|
| **Skill** (the method) | `structured-analysis` — the 11-step workflow the main agent runs in-flight | ✅ built |
| **Subagents** (the critics) | `bias-perception-reviewer`, `analytic-method-reviewer`, `calibration-forecasting-reviewer` — read-only, delegated critique | ✅ deployed |
| **Human gate + loop-back** | no judgment is final until a human approves; failed review loops back | ✅ in the skill |
| **MCP** (state + compute) | ACH engine, calibration tracker, source-trust registry | ⏳ Phase 3 (deferred) |
| **OSINT + deception** | live collection, deception-detection reviewer | ⏳ Phase 4 (gated on a security review) |

The whole case runs **in-context as prose** at MVP: no persistent store, no external collection. The
cross-case learning layer (a calibration track-record, a source-trust registry) and outcome scoring come in
a later phase.

## Use it

Open Claude Code in this repo (the `.claude/` here provides the skill + the three reviewer subagents), then:

```
/structured-analysis
```

or just describe an analytic question under uncertainty. The skill maintains a **case workspace** (question
· hypotheses · evidence+grades · ACH matrix · assumptions · ranking · findings · judgment · assessment ·
indicators), delegates critique to the reviewer subagents on the raw case state, and **stops for your
approval** before finalizing.

The product is **repo-local**: the skill and the three critic subagents are co-located in this repo's
`.claude/`, so they must run together here (the orchestrator delegates to the reviewer subagents, which are
not global). Work a case per session in this repo.

## Validate

`docs/validation/heuer-ach-validation.md` defines the MVP-0 gate — a Heuer ACH worked example, a baseline vs
agent-assisted comparison, and the concrete pass bar (broader/better-disconfirmed hypotheses + reviewers
catching injected flaws). Passing it is what lets Phase 2 start.

## Layout

```
.claude/
  agents/     the 3 reviewer subagents (deployed from the factory — do not edit; re-export to update)
  skills/     structured-analysis (the orchestrator) + the reviewers' own skill modules
docs/
  validation/ the MVP-0 gate + run results
```

## Design of record

The what/why/decisions live in the factory repo under `docs/intelligence-analysis/`:
`BLUEPRINT-*` (decisions + open questions), `PIPELINE-grounded.md` (the 12-step workflow, every step cites a
source claim), `DESIGN-SPEC-*` (the how). The reviewer subagents are regenerated there and deployed here via
`cli export-deployable`.
