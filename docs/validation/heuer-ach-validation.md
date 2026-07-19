# MVP-0 validation — Heuer ACH worked example

> The gate the blueprint requires **before** Phase 2 (blueprint MVP-0 success criteria). Defines the
> question set + the concrete pass bar. Run it against the `structured-analysis` skill + the three reviewer
> subagents.

## What we are proving

That the *agent-assisted* pass beats an *unaided baseline* on the two things the method exists to buy:

- **(a) a broader, better-disconfirmed hypothesis set** — not a single favoured storyline.
- **(b) independent critique that catches injected bias / assumption / overconfidence flaws** the baseline misses.

## Test items

1. **Primary — a Heuer ACH worked example.** Use the canonical Analysis-of-Competing-Hypotheses case from
   *Psychology of Intelligence Analysis* Ch. 8 (the Iraqi-retaliation question following the 1993 strike on
   the Iraqi intelligence HQ): **"Will Iraq retaliate (and how) for the US action?"** Heuer walks the same
   question through ACH, so it is a like-for-like reference for hypothesis breadth and disconfirmation.
2. **Secondary (optional) — a classic intelligence-failure case** with known hindsight (e.g. a surprise-
   attack warning question). Used only to confirm the method generalizes beyond the reference example.

## Procedure

For the primary item, produce three runs:

- **Control / baseline (unaided):** ask the question once, in a single pass, with no ACH matrix and no
  reviewers — "give your best analysis." Record its hypotheses, its conclusion, and its stated confidence.
- **Agent-assisted:** run `/structured-analysis` end-to-end (Steps 1–11): frame → all hypotheses →
  evidence+grades → ACH matrix → key assumptions → disprove-rank → the three reviewer subagents → loop-back
  → calibrated judgment → (human-approve) → indicators.
- **Injected-flaw run (for criterion b):** take a *plausible-looking* agent draft and inject three specific
  defects, one each, then run the reviewers on the raw case state:
  - a **cognitive bias** — e.g. an availability/vividness-driven over-weight of one dramatic report, or
    anchoring the probability on the first number mentioned → expect **bias-perception-reviewer** to name it.
  - an **unstated load-bearing assumption** — e.g. "the adversary is a unitary rational actor" left implicit
    → expect **analytic-method-reviewer** (key-assumptions) to surface it.
  - an **overconfident probability** — e.g. "95% certain" on thin, non-diagnostic evidence → expect
    **calibration-forecasting-reviewer** to flag the miscalibration / base-rate neglect.

## Pass bar (both must hold on the primary item)

**(a) Hypothesis set + disconfirmation.** PASS if ALL of:

- the agent-assisted hypothesis set is a **superset** of the baseline's, and includes **≥ 1 substantive
  hypothesis the baseline omitted** (not a trivial reword);
- every hypothesis is mutually exclusive and marked `candidate/unproven/disproved` (none pre-marked
  disproved);
- the ACH ranking is **by least-inconsistency** — the write-up shows the leading hypothesis is the one with
  the *fewest strong inconsistencies*, and at least one initially-appealing hypothesis is demoted by a
  disconfirming item (not promoted by confirming ones).

**(b) Flaw catch.** PASS if for **all three** injected flaws:

- the correct reviewer **names the specific flaw** (not a generic caution) and gives a correction, AND
- the unaided baseline run did **not** surface that flaw.

**Overall:** MVP-0 passes the gate when (a) AND (b) hold on the primary item. Record the three runs + the
verdict in `docs/validation/results-<date>.md`. A miss on (a) points at the SAT skill; a miss on (b) points
at a reviewer.

## Out of scope for this gate

Brier scoring against the real outcome (needs the resolved outcome + a calibration tracker — Phase 3); live
OSINT collection and deception review (Phase 4). This gate tests the **prose analysis core only**.
