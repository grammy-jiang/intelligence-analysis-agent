---
name: calibrated-forecasting
description: "Produce a calibrated numeric forecast for a question under uncertainty — take the outside view / base rate first, Fermi-decompose, adjust with case specifics, express the probability as an explicit number, and plan to update it. Invoke when you need a defensible probability (not a hedge word like 'likely') and want to avoid over- or under-confidence. Pairs with the calibration-forecasting-reviewer, which independently checks the result."
---

# Calibrated Forecasting

## Purpose

Produce a probability you would actually bet on — **calibrated** (stated probabilities match observed
frequencies) and **discriminating** (decisive where the evidence allows) — by starting from the outside view
and moving off it only as far as diagnostic evidence justifies. This is the *doing* skill; the
`calibration-forecasting-reviewer` subagent is the independent *check* on what it produces.

## When to use

- A question needs a probability or forecast under real uncertainty, and being over- or under-confident is costly.
- You are at Step 9 of the `structured-analysis` workflow: an ACH ranking exists and must become a number.
- A broad "how does this end?" question needs decomposing into scorable pieces before it can be judged.

## When not to use

- A question with a known or near-certain answer — do not manufacture false uncertainty.
- Critiquing an *existing* forecast for calibration — that is the `calibration-forecasting-reviewer`'s job.

## Procedure

1. **Make the question scorable.** Restate it as a precise, resolvable claim with a horizon and a
   clairvoyance-passing outcome definition (what exactly counts as it happening). Decompose a broad question
   into sub-questions whose answers converge on the whole *(Tetlock — decompose the intractable)*.
2. **Take the outside view first.** Find the reference class and its base rate, and anchor there **before**
   case specifics — intuitive predictions are nonregressive and run as extreme as the evidence, so start from
   the reference-class rate and adjust toward it, not away from it *(P006, P007; causal vs merely statistical
   base rates, P023)*.
3. **Fermi-decompose the hard part.** Break the intractable question into knowable and unknowable sub-parts,
   expose and examine each assumption, and set a rough interval per part *(P036)*. For a **conjunctive**
   scenario (this AND this AND this), **multiply** the sub-event probabilities — do not average, which
   inflates the total *(P018)*.
4. **Adjust with the inside view — moderately.** Move off the base rate only as far as genuinely diagnostic
   evidence warrants; regress an extreme read toward the mean *(P005, P007)*. Prefer a moderate,
   base-rate-respecting "muddle-through" forecast over a doomsday or rosy extreme *(P043)*.
5. **Handle uncertain evidence probabilistically.** Do not collapse a 70–80%-likely item into a yes/no before
   combining it — carry it at its weight *(P014)*.
6. **State the probability as an explicit number** (or a bounded range), and state **confidence separately**
   — how much evidence, how diagnostic — because calibration and resolution are different axes *(P015)*.
   Convey the *degree and sources* of the remaining uncertainty rather than a bare point *(P010)*. Behind long
   odds, still name the residual (three-to-one leaves one-in-four).
7. **Plan to update.** Name the lead indicators that would move the number, and update in **small
   increments** — hunt subtle diagnostic signals early, but resist both over- and under-reaction *(P012)*.
   Log the forecast verbatim now so it can be scored later.

## Inputs

- The question and its horizon; the evidence or ACH ranking to turn into a number; any reference-class /
  base-rate data available.

## Output

A calibrated forecast: the **probability as a number** (+ range), the **reference-class base rate** it started
from, the **Fermi decomposition**, **confidence stated separately** from the probability, and the
**indicators + review date** for updating. Never a bare hedge word ("likely", "probable") in place of a number.

## Persistence — the `calibration-tracker` MCP (Phase 3, available)

The `calibration-tracker` MCP server now persists forecasts and computes your Brier track record. After the
human gate, **commit** the number with `log_forecast(case_id, question, probability, resolution_criteria,
horizon, judgment_source="analyst_confirmed")` — it **locks** the question + probability (only the outcome is
appended later). When the outcome is known, `resolve_forecast(forecast_id, outcome, resolved_at)`;
`get_calibration_report()` returns your Brier + a calibration table over resolved forecasts *(Tetlock C086)*.
The probability is still **your** judgment — the tool validates, persists, and scores; it never invents the
number, and `analyst_confirmed` is asserted by this skill after a human read-back, not verified by the tool.

## Grounding

Method traces to the distilled calibration/forecasting corpus (Tetlock's *Superforecasting* and *Expert
Political Judgment*, via the `calibration-forecasting-reviewer` principles): outside view P006/P007/P023;
Fermi + conjunction P036/P018; regression + moderation P005/P043; probabilistic handling P014;
calibration-vs-resolution P015; convey uncertainty P010; incremental updating P012. Pipeline of record:
`docs/intelligence-analysis/PIPELINE-grounded.md` Step 9 (Tetlock C076/C077; EPJ C041) + outside-view C155.
Scoring (Brier C086) is deferred plumbing at MVP.
