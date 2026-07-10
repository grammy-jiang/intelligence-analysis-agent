---
name: structured-analysis
description: "Run the structured analytic-tradecraft workflow on an intelligence or analytic question — frame it, enumerate ALL competing hypotheses, weigh evidence in an ACH matrix ranked by disconfirmation, get independent bias / method / calibration critique from reviewer subagents, then a human-approved calibrated judgment. Invoke when analyzing a question under uncertainty where being wrong is costly and hidden assumptions, bias, or overconfidence are real risks — not for quick factual lookups."
---

# Structured Analysis

## Purpose

Drive an analytic question through the full structured-analytic-techniques method: frame → enumerate
competing hypotheses → weigh evidence in an Analysis of Competing Hypotheses (ACH) matrix that ranks by
*disconfirmation* → subject the reasoning to independent bias / method / calibration critique → commit a
calibrated judgment **only after a human approves it**. The thesis is **augment, not replace**: this skill
structures and challenges the reasoning; the human analyst owns the judgment (Kent C020; Heuer C167).

This is an **MVP (Phase 1)**: the whole case runs **in-context as prose** — no persistent store, no MCP.
The cross-case learning layer (a calibration track-record, a source-trust registry) and outcome scoring
are deferred to a later phase; where a step would read or write them, it says so and proceeds without.

## When to use

- A question under real uncertainty where a wrong answer is costly, and a single confident storyline is
  the failure risk (premature closure, one favoured hypothesis).
- You suspect a hidden assumption, a cognitive bias, or overconfidence is shaping an estimate.
- You need a defensible assessment that shows *which alternatives were considered and why rejected*, not
  just a conclusion.

## When not to use

- A quick factual lookup, or a question with one uncontested answer.
- Producing the substantive intelligence/policy content itself on someone's behalf without their judgment
  in the loop — this skill runs the *method* and gates on a human; it does not self-commit an assessment.

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
   precise. State them as judgments and show the reasoning.
5. **Keep `unproven` separate from `disproved`.** A hypothesis with no supporting evidence is not thereby
   refuted; keep it alive until evidence is *inconsistent* with it. *(Heuer C241.)*

## The method — maintain a CASE WORKSPACE in context

Keep a single running markdown artifact (the **case workspace**) and update it at each step. Show it to the
analyst as it grows. Its sections: `Question`, `Hypotheses`, `Evidence`, `ACH matrix`, `Key assumptions`,
`Ranking`, `Findings`, `Judgment`, `Assessment`, `Indicators`, `Audit trail`.

### Step 1 — Frame the question *(Kent C012, C020; Tetlock C150)*
Turn the raw input into a **precise question + sub-questions + the decision it serves**. Break a broad
question ("how does this end?") into scorable sub-questions. Note the outside view early — the base rate of
the question's reference class — so later judgment starts from it, not from the vivid specifics *(Tetlock
C155; MVP: state the base rate from reasoning, no tracker to read)*.
→ writes `Question`.

### Step 2 — Enumerate ALL competing hypotheses *(Heuer C102, C241)*
Generate a **full, mutually exclusive set** of hypotheses, including ones that seem unlikely — a hypothesis
never listed can never win. Mark each `candidate / unproven / disproved`; start none as disproved.
→ writes `Hypotheses`.

### Step 3 — Collect and grade evidence *(FM 2-22.3 C023/C027/C428; Heuer ACH Step 2)*
Gather relevant evidence and, per item, record it as an **EvidenceItem** that goes beyond concrete reporting
to include: (1) your own assumptions and deductions; (2) for each hypothesis, "if it were true, what should
I see — or NOT see?"; and (3) the **absence of expected evidence** — the dog that did not bark. Grade each
item for source **reliability A–F** and information **credibility 1–6**, as a stated judgment. *(MVP: no
source-trust registry to read a source's history — grade from what is known now and say so.)*
→ writes `Evidence`.

### Step 4 — Build the ACH matrix *(Heuer C234; ACH Step 3)*
Lay hypotheses across the top, evidence down the side, as a markdown table. Work **across each row**: for
each evidence item, rate its consistency with *each* hypothesis (e.g. `C` consistent / `I` inconsistent /
`N/A` not applicable, plus a strength). Rate row-by-row (is this item consistent with each hypothesis?), not
column-by-column.
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
→ writes `Ranking`.

### Step 7 — Independent critique — delegate to the reviewer subagents *(Kahneman C009; Jervis C006; Primer C051)*
Invoke the reviewer **subagents** (via the Task tool), each handed the **raw case workspace** (invariant 2),
each producing findings in its name-the-flaw / correction / residual-uncertainty / next-step format. Run:
- **`bias-perception-reviewer`** — cognitive bias, perception/misperception, framing, anchoring, motivated
  reasoning in the hypotheses, grades, and ranking.
- **`analytic-method-reviewer`** — method fidelity + the contrarian pass: the best case for a
  non-leading hypothesis, key-assumption soundness, ACH done by disconfirmation, any deception/D&D risk
  where a source could be manipulated *(Primer C051; Masterman C002; ACH Step 6)*.
- **`calibration-forecasting-reviewer`** — run once a probability exists (Step 9), or now if the ranking
  already implies confidence: over/under-confidence, base-rate neglect, an untested single-outcome read.
Collect all findings into `Findings`.

### Step 8 — Loop back and revise *(Heuer C249; ACH Step 4)*
Treat the findings as work, not decoration. Revise: re-open hypotheses, re-rate cells, add missing
evidence, fix an assumption. Re-run the affected earlier steps. Keep `unproven` hypotheses alive. Iterate
until the reviewers raise nothing new material; if a reviewer raises the **same** finding twice, surface it
to the analyst to decide rather than looping again. *(Bounded-retry / escalation counter = deferred
plumbing; at MVP the analyst is the escalation target.)*

### Step 9 — Calibrated judgment *(Tetlock C076/C077; EPJ C041)*
State the judgment as an explicit **probability number** (or a numeric range), not "likely/probable" alone.
Give the leading hypothesis and the residual probability on the alternatives — three-to-one odds still
leave a one-in-four. Note confidence (how much evidence, how diagnostic) separately from the probability,
and record any dissent. *(MVP: no calibration tracker to read your own past accuracy — reason the number
and mark it as an un-scored forecast.)*
→ writes `Judgment`.

### Step 10 — Report, then the HUMAN APPROVAL gate *(Heuer ACH Step 7; Kent C012, C020, C167)*
Assemble the **Assessment**: the relative likelihood of **all** hypotheses, the specific confidence, and
**which alternatives were considered and why rejected** — plus the audit trail (what changed after review).
Then **stop and present it to the human analyst for approval.** Do not treat it as final, publish it, or
act on it until the analyst approves. If they reject or amend, loop back (Step 8).
→ writes `Assessment` (status: `draft — awaiting approval` until the human approves).

### Step 11 — Indicators to monitor *(CIA Primer Indicators method; C032)*
After approval, list the **observables that would confirm or break** the leading hypothesis going forward —
a short Topics × Indicators list with the trigger that would change the assessment. *(MVP: produce the
watch-list; there is no persistent store to maintain it over time yet.)*
→ writes `Indicators`.

## Output

The **Assessment** (Step 10), gated on human approval: relative likelihood of all hypotheses, explicit
probability + confidence, alternatives-considered-and-why-rejected, the reviewer findings and how they were
resolved, and the indicators to watch. Never a bare conclusion without the alternatives and the audit trail.

## Deferred (not in this MVP — say so if a case needs them)

- **Persistent stores**: `calibration-tracker` (your Brier track record over time, Tetlock C086) and
  `source-trust-registry` (a source's credibility built over time, Masterman C044). At MVP, grade and judge
  from present reasoning and mark forecasts un-scored.
- **Step 12 — score + feedback**: Brier-scoring a resolved forecast and updating the track records — needs
  the stores + the outcome, deferred to Phase 3.
- **OSINT collection** and the **deception-detection reviewer** — Phase 4, gated on a security review.

## Grounding

Every step and artifact above traces to a source claim in the pipeline of record
(`docs/intelligence-analysis/PIPELINE-grounded.md` in the factory repo): Frame Kent C012 / Tetlock C150;
Hypotheses Heuer C102/C241; grade FM 2-22.3 C023/C027/C428; ACH Heuer C234 / ACH Steps 2–5; key assumptions
Primer C009; disprove Heuer ACH Step 5; bias Kahneman C009 / Jervis C006; contrarian+deception Primer C051 /
Masterman C002; calibrated judgment Tetlock C076/C077 / EPJ C041; report+gate Heuer ACH Step 7 / Kent
C020/C167; indicators Primer C032; loop-back Heuer C249. Pure build-plumbing (retry caps, the approval-gate
surface, persistence mechanics) is deferred, not grounded.
