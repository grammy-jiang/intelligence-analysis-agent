---
name: calibration-and-probabilistic-estimation
description: Audits whether a probability judgment is numeric, granular, effort-triaged, self-checked, and coherent; invoke when reviewing an analytic estimate, probability, or forecast.
kind: skill
status: ready
provenance:
  principles:
  - P049
  - P067
  - P120
  - P151
  - P190
  - P191
  - P198
  - P200
  claims:
  - C00154
  - C00175
  - C00176
  - C00208
  - C00209
  - C00313
  - C00455
  - C00456
  - C00457
  - C00458
  - C00459
  - C01036
  evidence: []
  source_anchors: []
  authored_from_digest: 29d6b2d59f3a312c62af24d65fcd6f74a533f5b7e0c03273766711fe3b208064
---

# Calibration And Probabilistic Estimation

## Purpose

Review whether a probability judgment is expressed and tested the way a calibrated
estimate should be: a granular number rather than a vague hedge-word, effort spent only
where it can move accuracy, checked against an independently generated second estimate
and a parameter thought experiment, decomposed into scorable sub-questions when the
master question cannot be graded directly, and coherent across how it is framed. This
skill audits the form, testing, and stability of the estimate itself — not the
arithmetic of a specific update after a named piece of new evidence arrived — and it
distinguishes a judgment that is rationally resistant to a single new data point from one
that is failing to update out of motivated reasoning.

## When to use

- A probability, forecast, or belief is expressed in hedge-words ("likely," "a real
  chance," "maybe") or on a coarse two- or three-setting dial, and needs to be checked
  for whether it is actually gradable.
- Analytical effort is about to be spent on a question that is already near-certain,
  near-impossible, or an effectively unforecastable turning point years out, and the
  allocation of that effort itself needs auditing.
- An analyst has produced only one estimate, with no independently generated second
  self-estimate (the crowd within) and no thought-experiment stress-test of what should
  happen if the question's own time frame or threshold changed.
- The substantive question under review is too vague or broad to score directly ("how
  does this turn out?") and needs to be checked for decomposition into scorable
  sub-questions.
- A judgment about a past or future outcome is framed two ways — as inevitability and as
  impossibility, or considered in a fixed order against its alternatives — and needs a
  coherence check.
- A forecast or belief did not change after a specific new data point, and it is unclear
  whether that reflects a rationally strong prior or motivated resistance to updating.

## Procedure

1. Establish what is under review: the exact wording of the probability judgment or
   forecast, the question it purports to answer, and how much analytical effort has
   already gone into it.
2. Check that the judgment is stated as a number, not a word. A two- or three-setting
   mental dial ("likely," "some chance," "maybe") should be rejected in favor of a
   granular numeric scale fine enough to capture real distinctions; frequent, reflexive
   use of exactly 50% is a signal of "I don't know" dressed up as an estimate, not a
   considered judgment (P049, P067).
3. Check the effort spent against the Goldilocks zone: flag time invested refining a
   question that is already trivially easy (near-certain or near-impossible), and flag a
   question that is effectively unforecastable (for example, a turning point years out)
   being scored with false precision instead of triaged away (P120).
4. Check whether the estimate was tested against a second, independently generated view
   of itself — the crowd within (assume the first answer is wrong, generate a second,
   average the two, or let time pass before re-estimating), written down so it can be
   critiqued as an outsider would, with the question's own wording flipped to counter
   confirmation bias. Flag a single, unchecked first answer presented as final (P151).
5. Check whether the underlying mental model was stress-tested with a thought
   experiment: does the estimate move appropriately, and stay scope-sensitive, when the
   question's own parameters (time frame, threshold) are varied? Remember that cognitive
   illusions cannot be switched off, only monitored and checked with a "ruler"; flag an
   estimate that does not move, or moves incoherently, when its own terms change (P190).
6. If the substantive question is itself too vague or broad to score directly ("how does
   this turn out?"), check that it was decomposed via Bayesian question clustering into
   many small, pertinent, scorable sub-questions meant to converge on the bigger picture,
   rather than answered as one ungraded impression (P191).
7. Check coherence: do paired inevitability and impossibility judgments about the same
   past or future outcome complement to one, and was the order in which the outcome
   versus its alternatives were considered counterbalanced to rule out an order effect?
   Flag a pair that does not complement, or a framing that always considers the favored
   outcome first (P198).
8. Before flagging a stable or slow-moving estimate as motivated bias, check for a
   rational explanation: strong prior grounds can justify distrusting a single contrary
   study, and because motivated and unmotivated non-updating are hard to tell apart from
   the outside, the most diagnostic case is one where the analyst's expectations and
   interests pull in opposite directions — use that as the test (P200).
9. Emit findings highest-impact first, each in the name-the-flaw / correction /
   residual-uncertainty / next-step format.

## Inputs

- The probability judgment or forecast as stated (in words or as a number) and the
  question it purports to answer.
- Any indication of how much analytical time or effort was allocated to reaching it.
- Whether a second, independently generated self-estimate or an outsider critique of the
  written judgment was attempted.
- The question's tunable parameters (time frame, threshold), if a stress-test thought
  experiment is to be checked.
- Whether the master question was decomposed into sub-questions, and what those
  sub-questions were if so.
- Any paired framing of the same judgment (for example, inevitability versus
  impossibility) and the order in which the outcome and its alternatives were considered.
- The judgment's history of stability or change over time, and what the analyst's
  expectations and interests are relative to the conclusion (needed for the
  motivated-bias test).

## Output

Per finding: name the calibration flaw (a vague verbal probability, a coarse mental dial,
effort misallocated away from the Goldilocks zone, an unchecked single estimate, an
untested mental model, an unscored mega-question, an incoherent paired judgment, or a
slow update mislabeled as bias), apply the correction (convert to a granular number,
retriage the effort, generate and average a second self-estimate, run a parameter thought
experiment, decompose into scorable sub-questions, recheck the paired curves and
counterbalance the elicitation order, or test for a rational strong-prior explanation),
state the residual uncertainty the correction leaves, and end with a concrete next step.
Order findings highest-impact first. Never close a review with a bare probability number
in place of this structure.

## Anti-patterns to flag

- A probability reported in hedge-words ("likely," "a real chance," "some chance") or on
  a coarse two- or three-setting dial, with no numeric equivalent fine enough to capture
  what the analyst actually believes (P049, P067).
- Frequent, reflexive use of exactly 50% offered as a considered estimate rather than an
  admission that the analyst does not know (P067).
- Analytical effort spent refining a question that is already essentially certain or
  impossible, or spent forcing false precision onto a genuinely unforecastable turning
  point, instead of triaging effort to where it can move accuracy (P120).
- A single first-pass estimate delivered as final, with no independently generated second
  estimate, no written self-critique, and no attempt to flip the question's wording to
  check for confirmation bias (P151).
- A mental model whose answer does not move, or moves incoherently, when the question's
  own time frame or threshold is varied in a thought experiment — treated as robust when
  it has simply never been tested (P190).
- A vague master question ("how does this end?") scored directly as one impression
  instead of decomposed into a cluster of smaller, scorable sub-questions (P191).
- Paired judgments about the same event's inevitability and impossibility that do not
  complement to one, or a framing that always considers the favored outcome before its
  alternatives with no counterbalancing of elicitation order (P198).
- A stable or slowly moving estimate labelled "motivated bias" with no check for a
  rational strong-prior explanation — or, the mirror error, genuine non-updating excused
  as principled with no test of whether expectations and interests actually pulled in
  different directions (P200).

## References

See `../../references/bias-perception-principles-index.md` for the full principle catalogue.
For adjacent concerns, see the sibling skills: `judgment-anchoring-and-base-rates` owns
base-rate anchoring and diagnosing calibration failure (over- or under-prediction, over-
or under-extremity) by task difficulty; `forecasting-judgment-foxes-and-track-record`
owns aggregating across many independent people and sources (the dragonfly eye) and
scoring a track record over time, distinct from this skill's single-analyst self-check;
`motivated-reasoning-and-belief-perseverance` owns the wider catalogue of
motivated-reasoning tells that this skill's rational-prior-versus-bias test draws on
narrowly.

## Provenance

Derived solely from P049, P067, P120, P151, P190, P191, P198, and P200
(Superforecasting; Expert Political Judgment; Psychology of Intelligence Analysis;
Perception and Misperception in International Politics — all distillation-only; see the
frontmatter above for the full claim, evidence, and source-anchor list).
