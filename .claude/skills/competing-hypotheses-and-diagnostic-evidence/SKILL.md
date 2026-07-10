---
name: competing-hypotheses-and-diagnostic-evidence
description: Audits whether an analytic judgment weighed a full hypothesis set by diagnostic evidence rather than fit; invoke before finalizing a hypothesis-driven judgment or forecast.
kind: skill
status: ready
provenance:
  principles:
    - P003
    - P013
    - P014
    - P020
    - P027
    - P028
    - P032
    - P054
    - P060
    - P061
    - P062
    - P070
  claims:
    - C00038
    - C00039
    - C00040
    - C00041
    - C00042
    - C00043
    - C00044
    - C00045
    - C00046
    - C00047
    - C00048
    - C00049
  evidence: []
  source_anchors: []
---

# Competing Hypotheses And Diagnostic Evidence

## Purpose

Audit whether an analytic judgment or forecast was built from a full set of competing
hypotheses, with each piece of evidence weighed by how far it discriminates among them
rather than by how well it merely fits the favored account. This skill checks the
hypothesis-generation, evidence-weighing, and refutation steps behind a conclusion — never
the conclusion's substance — and flags where a single uncontested hypothesis,
confirmation-seeking, or an ACH matrix treated as decisive let a weaker case pass as sound.

## When to use

- A judgment or forecast rests on a single hypothesis that was never made to contend
  against a real rival.
- Cited evidence is described as supporting or consistent with a hypothesis, but whether
  it also fits — and so fails to discriminate from — a rival hypothesis has not been
  checked.
- The write-up states or implies "there is no evidence of X," and it is unclear whether
  that was checked against what evidence would even be expected to appear if X were true.
- A working image or interpretation of an actor reads as though no observed event,
  whichever way it went, could have counted against it.
- A formal ACH matrix, or an informal pros-and-cons tally, was filled in and a conclusion
  drawn from it, and the analyst's agreement or disagreement with the tally needs
  checking.
- The conclusion looks reached by accumulating consistent evidence, or by satisficing,
  consensus, analogy, or a maxim, rather than by an active attempt to disprove the weaker
  hypotheses.
- A claim that clashes with an established, well-confirmed theory is being credited or
  dismissed, and whether that rested on the claim's fit to the theory — not the raw
  evidence alone — is unclear.
- A judgment on a still-developing situation is about to be finalized with no stated
  milestones for a different course, or is being presented as settled rather than
  tentative.

## Procedure

1. Establish the object under review: the hypothesis or hypotheses the judgment rests on,
   the evidence cited for and against each, and how firmly the conclusion is held. Fix
   this before judging whether the reasoning behind it holds up.
2. Check whether a full set of alternative hypotheses was built and carried through the
   analysis rather than one favored hypothesis tested alone. A single operative hypothesis
   with no competitor is too readily confirmed; where the stakes are high, check for a
   structured devil's-advocate or multiple-image process that made a genuine rival
   contend against it (P013, P032, P020).
3. For the evidence cited, check whether it was tested for diagnosticity — whether it
   discriminates among the hypotheses — rather than credited because it is merely
   consistent with the favored one. Evidence consistent with several or all hypotheses
   carries no diagnostic weight, and diagnosticity cannot be judged at all without the
   full hypothesis set in view (P054, P060, P014).
4. Check whether the analysis sought to refute rather than confirm: a hypothesis should be
   screened out by a single well-founded inconsistent item, not kept alive by an
   accumulation of merely consistent ones. Flag confirmation-seeking, and flag
   satisficing, incrementalism, consensus, reasoning by analogy, or reliance on a maxim
   standing in for systematic evaluation (P027, P032).
5. If the reviewed judgment reads as though it were immune to any contrary event — where
   the opposite of an observed fact would have been read as just as supportive of the
   same conclusion — flag this as an unfalsifiable, bad-faith-model framing rather than a
   tested hypothesis (P003).
6. Check the specific move from "no supporting evidence was found" to "there is no
   indication of the event": confirm the analysis asked whether that evidence would even
   be expected to surface if the event were actually occurring, rather than treating its
   absence as evidence of absence (P013).
7. Where a matrix (formal ACH or an informal tally) was used, check that it served as an
   aid to structure the evidence rather than as the source of the conclusion. Where the
   analyst's judgment departs from what the matrix shows, confirm the departure is traced
   to a specific factor the matrix omitted, not left unexplained (P061).
8. Check that the reasoning was externalized — written down and decomposed — rather than
   held as an unstructured mental tally, especially where more factors are in play than
   one analyst can hold in mind at once (P028).
9. Where a claim clashes with an established, well-confirmed theory, check that crediting
   or rejecting it accounted for its fit to that theory as well as the raw evidence, and
   that any discrepant information set aside was a visible, reasoned choice rather than a
   silent omission (P070).
10. For a judgment on a still-developing situation, check that milestones were specified
    for observations that would signal a different course, and that the conclusion is
    presented as tentative rather than final (P062).
11. Emit findings highest-impact-to-the-judgment first, each naming the flaw, the failure
    it enables, the principle(s) it violates, the corrective structured technique, and the
    residual uncertainty — never asserting the substantive judgment yourself.

## Inputs

- The analytic judgment or forecast under review and the hypothesis or hypotheses it
  rests on.
- Any alternative hypotheses considered — or explicitly not considered — so the
  completeness of the hypothesis set can be checked.
- The evidence cited for the conclusion and, where available, how each item bears on the
  rival hypotheses and not only the favored one.
- Any ACH matrix, tally, or informal pros-and-cons list produced during the analysis, plus
  where the final judgment agreed or disagreed with it.
- Whether the situation is still evolving, so milestones and the conclusion's
  tentativeness can be checked.
- Any established theory or well-confirmed prior finding a claim in the judgment clashes
  with, where relevant.

## Output

Per finding: name the reasoning flaw and what it lets stand unchallenged — a missing
hypothesis set, evidence credited for fit rather than diagnosticity, confirmation-seeking
that spares a hypothesis one fatal inconsistency, an unfalsifiable image immune to any
event, a matrix treated as the verdict instead of an aid, an unexternalized tally, or a
conclusion published with no milestone or hedge — apply the principle(s) violated by ID,
name the corrective technique (build out the full hypothesis set, run the diagnosticity
test, take a refutation pass, specify disconfirming milestones), state the residual
uncertainty the correction leaves, and end with a concrete next step. Order findings
highest-impact-to-the-judgment first. Never substitute a corrected hypothesis or estimate
for the analyst's own conclusion.

## Anti-patterns to flag

- A judgment built and defended around one hypothesis, with no rival ever built out or
  made to contend against it (P013, P020, P032).
- Evidence treated as confirming because it is merely consistent with the favored
  hypothesis, when it is equally consistent with a rival and so carries no diagnostic
  weight (P054, P060, P014).
- A conclusion reached by accumulating consistent-but-non-diagnostic evidence, or by
  satisficing, incrementalism, consensus, analogy, or a maxim, rather than by an active
  attempt to disprove the weaker hypotheses (P027, P032).
- An image or interpretation read as though no observed event, whichever way it went,
  could have counted against it (P003).
- "There is no evidence of X" written or implied with no check on whether that evidence
  would even be expected to surface if X were true — unproven treated as disproved
  (P013).
- A matrix's tally substituted for the analyst's own judgment, or a disagreement with the
  matrix left unexplained instead of traced to an omitted factor (P061).
- Several contending factors held as an unstructured mental impression rather than
  written down and decomposed (P028).
- A claim clashing with an established theory accepted or dismissed on the raw evidence
  alone, with no visible reasoning about its fit to that theory (P070).
- A judgment on a still-evolving situation published as settled, with no milestone set
  for a different course (P062).

## References

See `../../references/analytic-method-principles-index.md` for the full principle catalogue.
For adjacent concerns, see the sibling skills: `structured-analytic-techniques` owns
choosing and sequencing the wider technique set — a Key Assumptions Check, Outside-In
Thinking, Red Team, Alternative Futures, Indicators — that ACH sits alongside, including
how many hypotheses a project should carry; `probabilistic-judgment-and-calibration`
checks the coherence of the probability estimate once the hypotheses have been weighed;
`cognitive-biases-and-dual-process-reasoning` covers the broader fast-intuitive bias
catalogue behind a premature lock onto one hypothesis.

## Provenance

Derived solely from P003, P013, P014, P020, P027, P028, P032, P054, P060, P061, P062, and
P070 (Psychology of Intelligence Analysis; A Tradecraft Primer — Structured Analytic
Techniques for Improving Intelligence Analysis; Superforecasting: The Art and Science of
Prediction; Perception and Misperception in International Politics — all
distillation-only; see the frontmatter above for the full claim, evidence, and
source-anchor list).
