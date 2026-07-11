---
name: structured-analysis
description: "Run the structured analytic-tradecraft workflow on an intelligence or analytic question — frame it, enumerate ALL competing hypotheses, weigh evidence in an ACH matrix ranked by disconfirmation, get independent bias / method / calibration critique from reviewer subagents, then a human-approved calibrated judgment. Delegates grading to source-evaluation, forecasting to calibrated-forecasting, and critique to the reviewer subagents. Invoke when analyzing a question under uncertainty where being wrong is costly and hidden assumptions, bias, or overconfidence are real risks — not for quick factual lookups."
allowed-tools: Task, Skill, evidence-ledger:add_evidence, evidence-ledger:grade_evidence, ach-engine:create_matrix, ach-engine:rate_cell, ach-engine:score_matrix, calibration-tracker:log_forecast
---

# Structured Analysis

## Purpose

Drive an analytic question through the full structured-analytic-techniques method: frame → enumerate
competing hypotheses → weigh evidence in an Analysis of Competing Hypotheses (ACH) matrix that ranks by
*disconfirmation* → subject the reasoning to independent bias / method / calibration critique → commit a
calibrated judgment **only after a human approves it**. The thesis is **augment, not replace**: this skill
structures and challenges the reasoning; the human analyst owns the judgment (Kent C020; Heuer C167).

**Current phase.** The case is drafted in-context as a running prose **case workspace**, and three MCP
servers persist the load-bearing state: **`evidence-ledger`** (per-case evidence + grades, Step 3),
**`ach-engine`** (the matrix + least-inconsistency scoring, Steps 4/6), and **`calibration-tracker`** (the
committed forecast, Steps 9/10a). Still deferred — where a step would use one it says so and proceeds
without: the **`source-trust-registry`** cross-case source-credibility store (Step 3 grades from present
evidence alone), **Brier scoring** a resolved forecast (Step 12), and **live OSINT collection**
(`osint-toolkit` runs read-only, `OSINT_LIVE=0`).

## When to use

- A question under real uncertainty where a wrong answer is costly, and a single confident storyline is
  the failure risk (premature closure, one favoured hypothesis).
- You suspect a hidden assumption, a cognitive bias, or overconfidence is shaping an estimate.
- You need a defensible assessment that shows *which alternatives were considered and why rejected*, not
  just a conclusion.

## When not to use

- A quick factual lookup, or a question with one uncontested answer.

*Scope note (not an anti-trigger):* this skill will not ghostwrite a final assessment — it runs the
*method* and gates on a human, and does not self-commit a judgment (see invariant 1).

## Load-bearing invariants (must hold — they take precedence over convenience)

1. **Human approves before any commit.** No probability, grade, ranking, or assessment is treated as final
   until the human analyst approves it. A failed review loops back to revise; it does not ship. *(Kent
   C020; Heuer C167.)*
2. **Independent critique reads the RAW case state, not your narrative.** When you invoke a reviewer
   subagent, hand it the actual hypotheses, evidence, grades, matrix, and assumptions — never a summary of
   your conclusion. A critic fed only the story critiques only the story. *(Heuer — self-review from inside
   one's own reasoning fails.)*
3. **ACH ranks by least-inconsistency (disconfirmation), not most-confirmation.** The leading hypothesis is
   the one with the *fewest* strong inconsistencies, not the most supporting evidence. Reversing this
   inverts the method. *(Heuer ACH Step 5.)*
4. **You/the analyst supply judgment; never fabricate a grade or probability.** Evidence grades, cell
   ratings, and the final probability are analyst/model judgments made explicit — never invented to look
   precise. State them as judgments and show the reasoning. *(Anti-hallucination guardrail — engineering
   inference, not a corpus claim; grades/probabilities themselves are graded per FM C428 / Tetlock
   C076/C077.)*
5. **Keep `unproven` separate from `disproved`.** A hypothesis with no supporting evidence is not thereby
   refuted; keep it alive until evidence is *inconsistent* with it. *(Heuer C241.)*

## The method — maintain a CASE WORKSPACE in context

Keep a single running markdown artifact (the **case workspace**) and update it at each step. Show it to the
analyst as it grows. Its sections: `Question`, `Hypotheses`, `Evidence`, `ACH matrix`, `Key assumptions`,
`Ranking`, `Findings`, `Judgment`, `Assessment`, `Indicators`, `Audit trail`. The workspace is the
source of truth: if any MCP write (`evidence-ledger`, `ach-engine`, `calibration-tracker`) fails, keep the
state in the workspace and flag that store as out-of-sync — never drop the state silently.

### Step 1 — Frame the question *(Kent C012, C020; Tetlock C150)*
Turn the raw input into a **precise question + sub-questions + the decision it serves**. Break a broad
question ("how does this end?") into scorable sub-questions. Note the outside view early — the base rate of
the question's reference class — so later judgment starts from it, not from the vivid specifics *(Tetlock
C155; state the base rate from reasoning — the live `calibration-tracker` holds committed forecasts, not a
reference-class base-rate store)*.
→ writes `Question`.

### Step 2 — Enumerate ALL competing hypotheses *(Heuer C102, C241)*
Generate a **full, mutually exclusive set** of hypotheses, including ones that seem unlikely — a hypothesis
never listed can never win. Mark each `candidate / unproven / disproved`; start none as disproved.
→ writes `Hypotheses`.

### Step 3 — Collect and grade evidence *(FM 2-22.3 C023/C027/C428; Heuer ACH Step 2)*
Gather relevant evidence and, per item, record it as an **EvidenceItem** that goes beyond concrete reporting
to include: (1) your own assumptions and deductions; (2) for each hypothesis, "if it were true, what should
I see — or NOT see?"; and (3) the **absence of expected evidence** — the dog that did not bark. Grade each
item for source **reliability A–F** and information **credibility 1–6**, as a stated judgment.
Where open-source **collection** is needed, invoke the `osint-investigation` skill (read-only while
`OSINT_LIVE=0`); everything it returns is still graded via `source-evaluation` before it enters the ledger.
**Use the `source-evaluation` skill** to grade each item — it supplies the two-axis grade, the diagnosticity
read (which hypotheses the item does and does not discriminate), corroboration status, and a deception check.
**Persist via the `evidence-ledger` MCP** (per-case): `evidence-ledger:add_evidence` (raw item, `pii` flag,
expected observables keyed by hypothesis_id) then `evidence-ledger:grade_evidence` (A–F / 1–6,
`judgment_source`). *(A grade change later marks dependent ACH cells stale — see Step 6.)* The cross-case
`source-trust-registry` (a source's credibility history, Masterman C044) is **deferred** — grade from the
present evidence alone, not from a stored per-source track record.
→ writes `Evidence`.

### Step 4 — Build the ACH matrix *(Heuer C234; ACH Step 3)*
Lay hypotheses across the top, evidence down the side, as a markdown table. Work **across each row**: for
each evidence item, rate its consistency with *each* hypothesis (e.g. `C` consistent / `I` inconsistent /
`N/A` not applicable, plus a strength). Rate row-by-row (is this item consistent with each hypothesis?), not
column-by-column. **Back it with the `ach-engine` MCP**: `ach-engine:create_matrix` (from the Step-2
hypotheses) mints stable `hypothesis_id`s; `ach-engine:rate_cell` records each consistency judgment
(`judgment_source`), superseding with a `reason` to change one.
→ writes `ACH matrix`.

### Step 5 — Surface and test key assumptions *(CIA Primer Key-Assumptions-Check; C009)*
List the premises the analytic line rests on — **stated and unstated**. Challenge each: why must it be true?
what would make it false? Keep the refined list of must-be-true assumptions with, per assumption, a
confidence and what would undermine it.
→ writes `Key assumptions`.

### Step 6 — Conclude by disproving — rank by least-inconsistency *(Heuer ACH Step 4–5)*
Now work **down each column**: the diagnostic power is in *inconsistency*. Refine or delete evidence that is
consistent with everything (non-diagnostic — it does not help). Rank hypotheses by **fewest strong
inconsistencies**; the leading one is the hardest to disprove, not the best supported. (Invariant 3.)
**Use `ach-engine:score_matrix`** — it computes the least-inconsistency ranking and **refuses (listing the
blocking cells) if any rests on a since-changed grade or an unconfirmed `model_draft` rating**; re-rate those,
then re-score.
→ writes `Ranking`.

### Step 7 — Independent critique — delegate to the reviewer subagents *(Kahneman C009; Jervis C006; Primer C051)*
Invoke the reviewer **subagents** (via the Task tool), each handed the **raw case workspace** (invariant 2),
each producing findings in its name-the-flaw / correction / residual-uncertainty / next-step format. Run:
- **`bias-perception-reviewer`** — cognitive bias, perception/misperception, framing, anchoring, motivated
  reasoning in the hypotheses, grades, and ranking.
- **`analytic-method-reviewer`** — method fidelity + the contrarian pass: the best case for a
  non-leading hypothesis, key-assumption soundness, ACH done by disconfirmation, any deception/D&D risk
  where a source could be manipulated *(Primer C051; Masterman C002; ACH Step 6)*.
- **`calibration-forecasting-reviewer`** — over/under-confidence, base-rate neglect, an untested
  single-outcome read. Its **guaranteed** run is **Step 9a** (once the probability exists); invoke it here
  early only if the ranking already implies confidence.
- **`deception-detection-reviewer`** *(gated on a security review — skip unless that gate is cleared; see
  Deferred)* — when live, and the evidence chain includes ingested/OSINT material or a source who could
  control the footprint: interrogate for denial & deception — a channel being fed to mislead, too-neat
  corroboration, the absence that fits a cover story *(Masterman, Double-Cross D&D)*.
Collect all findings into `Findings`. If a reviewer Task fails or times out, **halt and surface it to the
analyst** — do not proceed without the independent critique (invariant 2 is load-bearing).

### Step 8 — Loop back and revise *(Heuer C249; ACH Step 4)*
Treat the findings as work, not decoration. Revise: re-open hypotheses, re-rate cells, add missing
evidence, fix an assumption. Re-run the affected earlier steps. Keep `unproven` hypotheses alive. Iterate
until the reviewers raise nothing new material; if a reviewer raises the **same** finding twice, surface it
to the analyst to decide rather than looping again. Where two reviewers **conflict** (e.g. one flags
overconfidence, another underconfidence), surface the conflict explicitly to the analyst — do not average or
silently drop either. As a hard stop, if Steps 7–8 iterate **more than three times**, escalate to the
analyst regardless of whether the findings are textually identical. *(Bounded-retry / escalation counter =
deferred plumbing; here the analyst is the escalation target.)*

### Step 9 — Calibrated judgment *(Tetlock C076/C077; EPJ C041)*
State the judgment as an explicit **probability number**, not "likely/probable" alone. Give the leading
hypothesis and the residual probability on the alternatives — three-to-one odds still leave a one-in-four.
Note confidence (how much evidence, how diagnostic) separately from the probability, and record any dissent.
**First read the learning leg** *(pipeline row 9)*: query the `calibration-tracker` MCP for the
analyst/model's own resolved track record on similar questions *(Tetlock C239; EPJ C005)* and adjust the
stated confidence for any known bias — e.g. temper it if the track record shows overconfidence. If the store
holds no relevant history, say so and proceed from the base rate alone.
**Use the `calibrated-forecasting` skill** to produce the number — outside view / base rate first,
Fermi-decompose, adjust moderately, probability as a number with confidence stated separately, and an update
plan. The number is a **draft** until the human gate approves it; it is committed to `calibration-tracker`
only afterwards — see Step 10a.
→ writes `Judgment`.

### Step 9a — Audit the number *(Tetlock C076/C077; EPJ C041; pipeline row 9)*
Invoke **`calibration-forecasting-reviewer`** (via the Task tool) on the completed `Judgment`, handed the
**raw case state** (invariant 2): over/under-confidence, base-rate neglect, an untested single-outcome read.
On any material finding, loop back to **Step 8** and revise, then re-run — the same loop-back discipline as
the Step 10 gate. **This audit always runs** — it is the pipeline's required calibration check, not optional.
→ appends to `Findings` / `Audit trail`.

### Step 10 — Report, then the HUMAN APPROVAL gate *(Heuer ACH Step 7; Kent C012, C020, C167)*
Assemble the **Assessment**: the relative likelihood of **all** hypotheses, the specific confidence, and
**which alternatives were considered and why rejected** — plus the audit trail (what changed after review).
Then **stop and present it to the human analyst for approval.** Do not treat it as final, publish it, or
act on it until the analyst approves. If they reject or amend, loop back (Step 8).
→ writes `Assessment` (status: `draft — awaiting approval` until the human approves).

### Step 10a — Commit the forecast *(Tetlock C076/C077; store-write pipeline row 9)*
Once — and only once — the human approves the Assessment, persist the number:
**`calibration-tracker:log_forecast`** with `judgment_source="analyst_confirmed"`, which locks the question +
probability so it can be Brier-scored when the outcome resolves. Do not call it on a `draft — awaiting
approval` assessment. *(The Brier scoring itself is Step 12 — deferred.)*
→ writes to `calibration-tracker`.

### Step 11 — Indicators to monitor *(CIA Primer Indicators method; C032)*
After approval, list the **observables that would confirm or break** the leading hypothesis going forward —
a short Topics × Indicators list with the trigger that would change the assessment. *(produce the
watch-list; there is no persistent store to maintain it over time yet.)*
→ writes `Indicators`.

## Output

The **Assessment** (Step 10), gated on human approval: relative likelihood of all hypotheses, explicit
probability + confidence, alternatives-considered-and-why-rejected, the reviewer findings and how they were
resolved, and the indicators to watch. Never a bare conclusion without the alternatives and the audit trail.

## Deferred (not in this phase — say so if a case needs them)

- **`source-trust-registry`** — the cross-case source-credibility store (Masterman C044). Not built: Step 3
  grades from present evidence alone, with no stored per-source track record to read.
- **Step 12 — score + feedback**: Brier-scoring a resolved forecast and updating the track records (Tetlock
  C086) — needs the outcome plus the registry. The forecast itself **is** committed now (Step 10a →
  `calibration-tracker`); only the later scoring is deferred.
- **Live OSINT collection** — `osint-toolkit` runs read-only (`OSINT_LIVE=0`); no external fetch yet.
- **`deception-detection-reviewer`** — gated on a security review; skip it in Step 7 unless that gate is
  cleared.

## Grounding

Every step and artifact above traces to a source claim in the pipeline of record
(`docs/intelligence-analysis/PIPELINE-grounded.md` in the factory repo): Frame Kent C012 / Tetlock C150;
Hypotheses Heuer C102/C241; grade FM 2-22.3 C023/C027/C428; ACH Heuer C234 / ACH Steps 2–5; key assumptions
Primer C009; disprove Heuer ACH Step 5; bias Kahneman C009 / Jervis C006; contrarian+deception Primer C051 /
Masterman C002; calibrated judgment Tetlock C076/C077 / EPJ C041; report+gate Heuer ACH Step 7 / Kent
C020/C167; indicators Primer C032; loop-back Heuer C249. Pure build-plumbing (retry caps, the approval-gate
surface, persistence mechanics) is deferred, not grounded.
