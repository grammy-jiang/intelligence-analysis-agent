---
name: bayesian-belief-updating
description: "Audit whether a probability's move from prior to posterior was sized to the evidence's true diagnosticity; use when a belief was, or should have been, revised after new evidence."
kind: skill
status: ready
provenance:
  principles:
  - P012
  - P022
  - P024
  - P046
  - P053
  - P054
  - P069
  - P074
  - P080
  claims:
  - C00984
  - C01034
  - C01145
  - C01146
  - C01580
  - C01581
  - C01710
  - C01711
  - C01567
  - C01568
  - C01575
  - C01576
  evidence:
  - E00163
  - E00188
  - E00245
  - E00246
  - E00524
  - E00525
  - E00604
  - E00605
  - E00512
  - E00513
  - E00520
  - E00521
  source_anchors:
  - e3c7c0b4e46f-c0003
  - e3c7c0b4e46f-c0006
  - e3c7c0b4e46f-c0012
  - 5da0a790f5ae-c0013
  - 5da0a790f5ae-c0021
  - 5da0a790f5ae-c0007
  - 5da0a790f5ae-c0028
  - e3c7c0b4e46f-c0019
  - 3a2b4f822beb-c0015
  authored_from_digest: 43e7b7e03988930271278244f1dfc128f6a6741f274b06c8729b24a7567ae939
---

# Bayesian Belief Updating

## Purpose

Review how a probability moved from a prior to a claimed posterior after new evidence arrived,
and judge whether that move behaves the way a calibrated Bayesian's would: sized to the
evidence's true diagnosticity, not mistaken for irrationality just because it was slow or
divergent, resistant to self-serving distortion, structured so it can actually be scored, and
reported with its residual uncertainty left visible. This skill audits the update itself — the
mechanics and the honesty of the move — not the domain content of the forecast.

## When to use

- A forecast, probability, or belief was revised — or the caller expects it should have been —
  after a specific piece of new evidence, and the size or direction of that move needs checking.
- Two analysts, or the same one at two points in time, reacted differently to the same evidence,
  and it is unclear whether that reflects legitimate disagreement or a symptom of bias.
- An estimate reads as close to certain around a single storyline, with no visible weight given
  to a serious rival account.
- A forecaster's history shows lopsided reactions to outcomes — quick to reaffirm after a win,
  slow, defensive, or hardening after a loss.
- The question under review is too broad or vague to score directly (for example, "how does this
  play out?") and needs to be broken into checkable pieces.
- A reported probability sits well short of certainty, and the write-up needs to state plainly
  what is left over for the decision-maker.

## Procedure

1. Establish the object under review: the prior probability, the specific new evidence, and the
   claimed posterior. Fix this before judging whether the move is too big, too small, or in the
   wrong direction.
2. Recompute the licensed move in two factors, then multiply: the likelihood ratio (how much more
   likely this evidence is under the hypothesis than under the rival) and the prior odds. Confirm
   the actual shift tracked that product rather than a round number, moved in small steps
   proportional to the evidence's diagnosticity, credited subtle lead indicators over louder but
   less diagnostic ones, discounted wishful thinking and irrelevant noise (the dilution effect),
   and — where the forecast rested on a single supporting fact — was dropped once that fact
   collapsed rather than kept alive on the prior alone (P022, P012).
3. Before flagging a slow, resistant, or diverging update as irrational, check for a rational
   explanation: a different starting prior, a different diagnosticity read of the same evidence,
   or a legitimate discount of the evidence because its source is untrustworthy given a
   well-established prior position. Two Bayesians can see identical evidence and reasonably
   respond differently (P024).
4. Check the estimate is not anchored on the reviewed party's own account alone. It should read
   as a confidence-weighted average of the outcome's likelihood under that account and under the
   strongest rival, not a near-certainty resting on one preferred story (P053).
5. Watch for two systematic tilts layered on top of the arithmetic: the egocentricity gap, which
   hands the favored outcome more probability than a fair weighing of rivals would support and is
   worst when an extreme likelihood judgment sits on a cautious prior or comes from an aggressive
   forecaster (P069); and asymmetric updating, which reaffirms a prior quickly after a win but
   resists — sometimes hardens — after a loss, with foxes moving closer to the prescribed amount
   than hedgehogs (P054).
6. If the question under review is itself too big or vague to score ("how does this end?"),
   check that it was decomposed into a cluster of smaller, scorable sub-questions whose answers
   were meant to converge on the bigger picture, rather than answered as one ungraded judgment
   call (P074).
7. Check the update is structured as a scoreable, falsifiable commitment: confidence in the
   reviewed party's own account and in the strongest rival should sum to one, each carrying its
   own probability for the outcome — or, depersonalized, the hypothesis is rated with
   conditional-likelihood judgments made assuming it true and assuming it false (P046).
8. Confirm the write-up states the residual probability in plain terms even behind long odds — a
   chance of roughly one in four still sits behind three-to-one odds — so the decision-maker can
   see what is left over for contingency planning or heightened attention (P080).
9. Emit findings highest-impact first, each in the name-the-flaw / correction / residual-
   uncertainty / next-step format.

## Inputs

- The prior probability (or belief) and the claimed posterior after the update.
- The specific new evidence that triggered, or should trigger, the revision, and any stated
  reason it is diagnostic.
- The strongest rival hypothesis or scenario, named or reconstructable from context.
- Any track record showing how this forecaster or team has updated after past wins and losses.
- The question as posed, so it can be checked for direct scorability or the need to decompose
  it.
- The horizon and the precise outcome being predicted, so the residual probability can be
  reported meaningfully.

## Output

Per finding: name the updating flaw (an ungrounded jump size, the egocentricity gap, asymmetric
updating, an unscored mega-question, a missing residual), apply the correction (recompute via
likelihood ratio times prior odds, reweight against the strongest rival, decompose into
sub-questions, restate as a reputational bet), state the residual uncertainty the correction
leaves, and end with a concrete next step. Order findings highest-impact first. Never close a
review with a bare number in place of this structure.

## Anti-patterns to flag

- A stance frozen despite firm disconfirming evidence, or a large jump with no reasoning shown,
  both waved through as "clearly irrational" without checking for a different prior, a different
  diagnosticity read, or legitimate source-distrust (P024).
- A "gut jump" — the probability changes by a large, round amount with no likelihood-ratio-times-
  prior-odds arithmetic and no proportionality to the evidence's strength (P022, P012).
- A forecast kept alive after its one supporting fact was discredited, instead of dropped (P012).
- An estimate built entirely from the reviewed party's own hypothesis, with the strongest rival's
  likelihood never entered into the average (P053), especially paired with an extreme likelihood
  ratio sitting on a cautious prior (P069).
- A track record that reaffirms every win instantly but stalls, litigates, or hardens on every
  loss (P054).
- A vague master question ("how does this end?") scored directly instead of broken into scorable
  sub-questions (P074).
- An update presented as a bare personal impression — no reputational-bet split against the
  rival, no conditional-outcome probabilities, no true/false hypothesis rating (P046).
- A write-up that rounds long odds down to "essentially never" or "certain" and never states the
  residual chance the decision-maker needs for contingency planning (P080).

## References

See `../../references/calibration-forecasting-principles-index.md` for the full principle catalogue.
For adjacent concerns, see the sibling skills: `base-rates-outside-view-and-regression` sets the
prior this update starts from; `forecast-scoring-and-evaluation` scores the resulting posterior
once the outcome resolves; `cognitive-bias-and-mindset-control` covers the wider bias catalogue
behind the egocentricity gap and asymmetric updating.

## Provenance

Derived solely from P012, P022, P024, P046, P053, P054, P069, P074, and P080 (Superforecasting;
Expert Political Judgment: How Good Is It? How Can We Know?; Psychology of Intelligence Analysis —
all distillation-only; see the frontmatter above for the full claim, evidence, and source-anchor
list).
