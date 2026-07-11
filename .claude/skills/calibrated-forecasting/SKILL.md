---
name: calibrated-forecasting
description: "Produce the calibrated numeric probability — a draft Judgment — for a question under uncertainty: outside view / base rate first, Fermi-decompose, fold in the bias/deception review findings, adjust with case specifics, then state an explicit number with confidence and dissent. Invoke when a defensible probability is needed (not a hedge word like 'likely') and being over- or under-confident is costly. This is the sole entry point for producing the draft probability — the pipeline commits it only after the orchestrator's Step 9a audit, Step 10 human gate, and Step 10a lock. Runs as Step 9 of the structured-analysis workflow, which owns the independent reviewer audit (Step 9a), the human gate (Step 10), and the commit (Step 10a): this skill produces the number, it does not audit, approve, or lock it."
allowed-tools: calibration-tracker:get_calibration_report
---

# Calibrated Forecasting

## Purpose

Produce a probability you would actually bet on — **calibrated** (stated probabilities match observed
frequencies) and **discriminating** (decisive where the evidence allows) — by starting from the outside view
and moving off it only as far as diagnostic evidence justifies. This is the *doing* skill: it produces the
**draft Judgment** (the number). The independent audit, the human gate, and the commit are **not this skill's**
— they belong to the `structured-analysis` orchestrator (Steps 9a / 10 / 10a). The
`calibration-forecasting-reviewer` subagent is the independent *check* the orchestrator runs on what this skill
produces.

## When to use

- You are at Step 9 of the `structured-analysis` workflow: an ACH ranking and its `ReviewFinding[]` exist and
  must become a number. **This is the primary path** — the orchestrator owns the audit, the human gate, and the
  commit this skill's output flows into.
- A broad "how does this end?" question needs decomposing into scorable pieces before it can be judged.
- A well-scoped, low-stakes probability is needed where a full hypothesis workflow is not warranted. **Even
  here this skill only produces the draft number** — the human still owns it, and no number is audited,
  approved, or locked from inside this skill.

## When not to use

- A question with a known or near-certain answer — do not manufacture false uncertainty.
- Critiquing an *existing* forecast for calibration — that is the `calibration-forecasting-reviewer`'s job.
- **A contested, multi-hypothesis, or high-stakes question with no prior hypothesis set, evidence grading, or
  bias/deception critique** — route it to `structured-analysis` FIRST and reach this skill only at its Step 9.
  A bare base-rate number on such a question bypasses the pipeline's safeguards and is confidently wrong, not
  merely imprecise.

## Procedure

This procedure produces the **draft Judgment** and stops. It does **not** invoke the reviewer, run the human
gate, or call `log_forecast` — those are the orchestrator's Steps 9a / 10 / 10a. Hand the draft back for them.

1. **Make the question scorable.** Restate it as a precise, resolvable claim with a horizon and a
   clairvoyance-passing outcome definition (what exactly counts as it happening). Decompose a broad question
   into sub-questions whose answers converge on the whole.
2. **Take the outside view first, and check your own track record.** Find the reference class and its base
   rate, and anchor there **before** case specifics — intuitive predictions are nonregressive and run as
   extreme as the evidence, so start from the reference-class rate and adjust toward it, not away from it
   (distinguish causal from merely statistical base rates). Before finalizing, read your own calibration
   history with `get_calibration_report()` (MCP — see Persistence) — if your resolved forecasts show a standing
   over- or under-confidence bias, shade this estimate to correct it.
3. **Fermi-decompose the hard part.** Break the intractable question into knowable and unknowable sub-parts,
   expose and examine each assumption, and set a rough interval per part. For a **conjunctive** scenario (this
   AND this AND this), **multiply** the sub-event probabilities — do not average, which inflates the total.
   Compute the product explicitly as arithmetic; do not eyeball a conjunction by token generation.
4. **Fold in the review findings.** Read the `ReviewFinding[]` handed in from the bias/misperception check and
   the contrarian + deception check. For each flagged bias or D&D risk, discount or re-anchor the estimate so
   the number is not calibrated around an unflagged-bias anchor — e.g. a mirror-imaging flag on the lead
   hypothesis must move the number, not be ignored.
5. **Adjust with the inside view — moderately.** Move off the base rate only as far as genuinely diagnostic
   evidence warrants; regress an extreme read toward the mean. Prefer a moderate, base-rate-respecting
   "muddle-through" forecast over a doomsday or rosy extreme.
6. **Handle uncertain evidence probabilistically.** Do not collapse a 70–80%-likely item into a yes/no before
   combining it — carry it at its weight.
7. **Run your own pre-commit self-check.** Before you fix the number, catch your *own* biases (distinct from
   the externally supplied `ReviewFinding[]` of step 4): Are you anchored on your first estimate? Is a vivid or
   recent case being over-weighted? Does your track record justify this much confidence? Correct for any you
   find.
8. **State the probability as an explicit number** (or a bounded range), state **confidence separately** — how
   much evidence, how diagnostic — because calibration and resolution are different axes, and record any
   **dissent** (a defensible minority read the decisionmaker should see). Convey the *degree and sources* of
   the remaining uncertainty rather than a bare point. Behind long odds, still name the residual
   (three-to-one leaves one-in-four).
9. **Plan to update, then hand off the draft.** Name the lead indicators *you* would watch to revise the
   number, and note that updates should move in **small increments** — hunt subtle diagnostic signals early,
   but resist both over- and under-reaction. Write the **draft** forecast into the case artifact (this is *not*
   the `log_forecast` MCP call — see Persistence) and return control to the orchestrator. The reviewer audit
   (Step 9a), the human gate (Step 10), and the `log_forecast` lock (Step 10a) happen there, on the raw case
   state — not inside this skill.

## Inputs

- The question and its horizon.
- The **ACH ranking** to turn into a number, plus any reference-class / base-rate data available.
- The **`ReviewFinding[]`** from the bias/misperception and contrarian + deception checks — **required** on the
  Step-9 path; they must be folded in (Procedure 4) before the number is set.

## Output

A **draft** calibrated forecast: the **probability as a number** (+ range), the **reference-class base rate**
it started from, the **Fermi decomposition**, **confidence stated separately** from the probability, any
**dissent** (a minority read the decisionmaker should see), and the **indicators + review date** the forecaster
would use to revise. These indicators are the forecaster's own revision triggers — distinct from the formal
Step-11 `Indicator[]` watch-list the SAT skill produces. Never a bare hedge word ("likely", "probable") in
place of a number. The number is a draft until the orchestrator's audit, human gate, and commit run — this
skill does not lock it.

## Persistence — the `calibration-tracker` MCP (Phase 3, available)

This skill reads **one** tool, read-only: `get_calibration_report()` (Procedure 2), which returns your Brier
score + a calibration table over resolved forecasts. That is its only `calibration-tracker` access.

Everything that **writes or locks** is the orchestrator's, not this skill's:

- **Required order: draft → reviewer audit → human gate → `log_forecast` lock.**
- "Log the draft" in the Procedure means **write it into the case artifact** — it is not the `log_forecast`
  tool call. The case artifact is the `structured-analysis` orchestrator's in-context **case workspace**
  (`PIPELINE-grounded.md` per-case `case-workspace`; drafted in-context this phase, no MCP server), so recording
  the draft there — or returning it to the orchestrator — needs **no write tool**. `get_calibration_report`
  (read-only) is correctly this skill's sole MCP grant, and the read-only restriction does not block step 9.
- The reviewer audit (`calibration-forecasting-reviewer` via Task) is the orchestrator's **Step 9a**, run on
  the raw case state.
- The human decisionmaker who owns the finished Assessment approves at the orchestrator's **Step 10** —
  intelligence serves the decisionmaker; the analyst produces, the human owns.
- `log_forecast(case_id, question, probability, resolution_criteria, horizon,
  judgment_source="analyst_confirmed")` is the orchestrator's **Step 10a**, fired **only after** that approval.
  It **locks** the question + probability (only the outcome is appended later, so there is no correction path
  afterward). `resolve_forecast(...)` and Brier scoring are Step 12.

The probability is always **your** judgment — the tracker validates, persists, and scores; it never invents the
number.

## Grounding

Method traces to the distilled calibration/forecasting corpus (Tetlock's *Superforecasting* and *Expert
Political Judgment*, via the `calibration-forecasting-reviewer` principles): outside view P006/P007/P023;
Fermi + conjunction P036/P018; regression + moderation P005/P043; probabilistic handling P014;
calibration-vs-resolution P015; convey uncertainty P010; incremental updating P012; own-bias pre-commit
self-check (anchoring/availability/overconfidence, Kahneman C009). Pipeline of record:
`docs/intelligence-analysis/PIPELINE-grounded.md` Step 9 (in the factory repo) — Tetlock C076/C077; EPJ C041;
Ranking + ReviewFinding[] input; Judgment artifact = probability + confidence + dissent; own track record as
input (Tetlock C239 / EPJ C005); outside-view C155; iterate (Heuer C249). The audit (Step 9a), the human-owned
gate (Step 10; Kent C020, Heuer C167), and the `log_forecast` commit (Step 10a) are owned by the
`structured-analysis` orchestrator, per its invariants 1–2. Bias/deception review inputs to Procedure 4:
Kahneman C009, Jervis C006, Primer C051, Masterman C002. Scoring (Brier C086) is deferred plumbing at MVP.
