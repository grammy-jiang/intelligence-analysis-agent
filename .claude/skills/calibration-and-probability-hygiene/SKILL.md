---
name: calibration-and-probability-hygiene
description: "Review a single stated probability or confidence judgment, and its reasoning, for the failure modes that make numbers miscalibrated; use when checking one forecast's number."
kind: skill
status: ready
provenance:
  principles:
  - P002
  - P003
  - P010
  - P014
  - P018
  - P028
  - P031
  - P032
  - P038
  - P052
  - P058
  - P073
  - P076
  - P078
  claims:
  - C00700
  - C00701
  - C00111
  - C00112
  - C00514
  - C01108
  - C00393
  - C00394
  - C00463
  - C00464
  - C00470
  - C00736
  evidence:
  - E00094
  - E00095
  - E00009
  - E00010
  - E00050
  - E00225
  - E00025
  - E00026
  - E00035
  - E00036
  - E00042
  - E00109
  source_anchors:
  - d88ef7714f29-c0008
  - 3a2b4f822beb-c0000
  - 3a2b4f822beb-c0015
  - e3c7c0b4e46f-c0010
  - 3a2b4f822beb-c0010
  - 3a2b4f822beb-c0013
  - d88ef7714f29-c0010
  - e3c7c0b4e46f-c0009
  - e3c7c0b4e46f-c0022
  - d88ef7714f29-c0004
  - 5da0a790f5ae-c0011
  - d88ef7714f29-c0019
  authored_from_digest: 24028903e9c7b37d57cf5630e73fc3333a43c16b5e8def0f7d82e597f7d87d92
---

# Calibration and Probability Hygiene

## Purpose

A single stated probability, forecast, or confidence judgment is easy to state and hard to get
right. This skill reviews that one number — and the reasoning behind it — for the specific failure
modes that make probability judgments miscalibrated, overconfident, or simply incoherent:

- Confidence set by how good the supporting story looks rather than by the domain's real
  predictability, with redundant, correlated inputs mistaken for independent support (P002); a large
  body of information mistaken for a reason to be more confident, when past a fairly small point
  more information usually just inflates confidence rather than accuracy (P003).
- A flat 0.5 offered as a shrug at an "unknowable" case, wasting whatever partial information is
  actually available (P032), and a number left anchored, unexamined, on whatever figure happened to
  already be in view (P038).
- A stated certainty pinned at exactly 1.0 or 0.0, leaving no room for any future evidence to move it
  again (P078).
- An interval built too tight around its point estimate, and a suspiciously precise or
  confidently-delivered number mistaken for genuine calibration (P073, P031).
- A fact of doubtful reliability folded in as settled truth instead of weighted by its own assessed
  validity, with the residual uncertainty left unstated instead of given as an actual number (P014,
  P010).
- A multi-step scenario's odds built by averaging its parts instead of multiplying them, and a
  chain-structure bias that misjudges multi-step plans and multi-part systems in opposite directions
  (P018, P028).
- A whole outcome set judged less likely than the sum of its own mutually exclusive parts, and a
  probability scale that collapses toward its ends so extreme calls are rewarded out of proportion
  and low-probability events are systematically mis-weighted once a decision is actually made on them
  (P076, P052, P058).

This skill reviews and corrects the probability statement itself. It does not produce the
underlying forecast, decide the substantive question the number answers, or make the call the
number feeds into — that stays with the forecaster and the decision-maker.

## When to use

- A forecast, estimate, or judgment states a bare probability, odds, or confidence interval, and it
  needs a calibration sanity-check before anyone relies on it, scores it, or repeats it.
- A confident number ("90% sure," "extremely likely," "no way this fails") rests on a vivid
  narrative, a fluent expert, or a large pile of consistent-looking information rather than on
  demonstrated predictability.
- Someone is tempted to answer "50-50," or "I really don't know," because the question feels
  unanswerable.
- A multi-step plan's probability of finishing on time, or a complex system's probability of
  failure, was estimated from case-specific detail rather than computed from its component parts.
- A stated interval, credible range, or confidence level looks suspiciously narrow, or suspiciously
  precise, for the kind of question being asked.
- A judgment folds in a piece of evidence of uncertain reliability as if it were simply established
  fact.
- Someone has stated, or is implicitly relying on, a probability of exactly 1.0 in their own view, or
  exactly 0.0 in a rival's.
- A set of mutually exclusive, exhaustive outcomes needs a coherence check, or a low-probability
  event is being weighed as part of a decision.
- The caller wants advice on which of these hygiene rules bears on an upcoming judgment, or wants two
  ways of stating or handling the same probability compared side by side.

## Procedure

Work through these checks, in order, against the single probability judgment under review. Each
check that turns up a problem becomes one finding in Output below; a check that is already
satisfied is noted rather than silently skipped.

1. **Set the ceiling on extremeness by predictability, and question where the confidence came from
   (P002, P003).** In a domain with essentially no genuine predictability, the right call is one
   steady central estimate for every similar case, not a case-by-case extreme guess; only sanction a
   wider spread of predictions once real predictability is demonstrably higher. A tidy, story-like
   match between the inputs and the claimed outcome is not proof of predictability, and that illusion
   holds even once the inputs behind it are already known to be weak (P002). Also check input
   independence: when two or more inputs are correlated and effectively say the same thing, treat any
   added confidence from the second one as illusory — accuracy will not rise to match it — and prefer
   inputs that are independent of one another and roughly comparable in their own validity (P002).
   Separately, interrogate any claim that a large volume of information itself justifies the stated
   confidence: beyond a fairly small threshold, more information keeps pushing confidence upward
   without a matching rise in accuracy, a pattern seen across multiple expert fields, including cases
   where practitioners were properly calibrated only when working from the barest minimum of
   information. Treat this as a strong default to test for, while allowing that specific
   circumstances can genuinely break it (P003).

2. **Kill the default 0.5 (P032).** A flat 0.5, or "toss-up," offered purely because the case feels
   unreadable is a hygiene failure, not honest humility: spread across an unpacked set of sub-cases,
   a reflexive 0.5 can push the total probability mass above 100%, and it wastes whatever sliver of
   real information the assessor does hold. When the one fact actually known is simply how long the
   thing being judged has already persisted, prefer a duration-based estimate (reasoning from how
   long something has already lasted to how much longer it likely has) over a reflexive half-and-half
   guess.

3. **Check for anchoring (P038).** Treat any number that was already sitting in view before the
   estimate was formed — a target figure, a prior number, a round figure embedded in how the question
   was asked — as a live anchor on the final answer by default: people under-adjust away from an
   anchor reliably, experts are barely more resistant to the effect than novices, and it is not a bias
   a person can simply will away by trying harder. Where the stakes justify the effort, confirm
   someone deliberately searched for reasons the anchor itself might be wrong before the final number
   was accepted.

4. **Cap certainty short of the endpoints (P078).** Flag any probability stated or implied at exactly
   1.0 in the assessor's own view, or exactly 0.0 in a rival's — at that point the odds ratio involved
   is undefined, and no future evidence can shift the number again. Ask that the ceiling be drawn back
   to something short of the extreme (figures like .95 and .05 are a reasonable working limit) so the
   belief stays open to revision, noting that beliefs genuinely converge toward the truth through the
   accumulation of evidence — fastest when a strong prior meets evidence that is highly diagnostic —
   not by declaring the matter closed in advance.

5. **Widen intervals anchored too tight, and discount precision theatre (P073, P031).** Assume any
   stated interval is narrower than it should be until shown otherwise: subjective ranges are
   characteristically overconfident, with the true value landing outside a stated 98%-style interval
   something like three times in ten, because the range gets built by anchoring on one best guess and
   then under-adjusting the width around it — and rewarding accuracy alone does not cure this. Examine
   too exactly how the interval was elicited, since the wording or procedure used to draw a range out
   of someone can itself change the answer given (P073). Separately, do not let apparent precision
   substitute for evidence of calibration: a number carried to several decimal places, or delivered by
   a source who sounds sure of themselves, is not by itself proof that the finer distinctions being
   drawn correspond to any real difference in frequency, and a source's confidence should never be
   read as a proxy for that source's actual competence (P031).

6. **Handle uncertain evidence probabilistically, and say the uncertainty out loud (P014, P010).**
   Where the judgment leans on a fact whose own reliability is not settled, flag any place that fact
   gets silently rounded to a plain yes or no: treating something assessed at roughly seventy-to-
   eighty-percent likely as though it were simply true manufactures overconfidence on its own, and
   even applying a discount proportional to the fact's assessed reliability tends to leave the result
   still overconfident (P014). Require that whatever uncertainty remains be written down as an actual
   number — a probability range or a set of odds — together with where that uncertainty comes from
   and the specific milestones that would narrow it, rather than left as an unquantified qualifier
   like "fairly confident" (P010).

7. **Multiply, don't average, a scenario's components, and check the direction of the bias (P018,
   P028).** For a scenario built from several sequential events, recompute its overall probability as
   the product of the individual event probabilities rather than an average of them: averaging
   systematically overstates the true figure, since the whole chain can be no more reliable than its
   weakest link, and note that piling a vivid, plausible-sounding extra detail onto the scenario tends
   to make it feel more probable to a reader even while it mathematically drives the true joint
   probability down (P018). Then check which way a chain-structure bias is likely running: when every
   one of several steps must succeed for the outcome to occur, people tend to rate that outcome as
   more likely than it is; when any single one of several components failing is enough to cause the
   outcome, people tend to rate it as less likely than it is. Both errors come from anchoring on the
   probability of one representative step and under-adjusting for the rest of the chain, so the
   direction of the likely error can be read straight off whether the structure in front of you is a
   "must all succeed" or a "just one has to fail" shape (P028).

8. **Run the coherence and scale checks (P076, P052, P058).** Wherever the judgment can be broken
   into a set of outcomes that are mutually exclusive and jointly cover every possibility, add up the
   probabilities assigned to the individual pieces and compare that sum to whatever probability was
   assigned to the whole: if the whole was rated less likely than its own parts sum to, that
   incoherence is a genuine probability-axiom violation, serious enough to expose the assessor to
   being exploited across a sequence of bets constructed against them (P076). Then consider how the
   number will actually be read once it leaves this review: a scoring approach that collapses the
   whole probability scale down to its two ends treats every middling value as interchangeable,
   rewards a confident call at either extreme when it turns out right, punishes it when it turns out
   wrong, and treats a confident call that turns out wrong in the wrong direction as the single worst
   outcome of all (P052). And consider how a decision-maker downstream will actually weight this
   number rather than how it is written: people systematically give a low probability more weight
   than it deserves and a moderate-to-high probability less weight than it deserves relative to
   outright certainty, so a shift from "impossible" to merely "possible," or from "possible" to
   "certain," moves a decision more than an equal-sized shift in the middle of the scale would — watch
   in particular for a genuinely uncertain outcome framed in sequential stages ending up treated as
   though it were already certain (P058).

## Inputs

- The probability judgment, forecast, or confidence statement under review, in whatever form it was
  given (a percentage, an odds ratio, a verbal phrase such as "very likely," or a stated interval).
- The reasoning or evidence behind it: whether the case is genuinely repeatable or formula-like, or
  built from case-specific detail, and whether any piece of that evidence is itself of uncertain
  reliability.
- Any interval, confidence level, or multi-step scenario decomposition stated alongside the number.
- Any number already "in the air" before the estimate was made — a target, a prior figure, a round
  number embedded in the question itself — that could be anchoring it.
- How the number was elicited, if known (the exact question or procedure used to draw it out), since
  the elicitation method itself can shift the answer.
- For an advise or compare request with no single judgment yet on the table: the question being
  faced and its horizon, so the right hygiene rule (or the right side-by-side) can be matched to it.

## Output

One finding per problem surfaced in the Procedure, ordered highest-impact first, each in this
four-part form:

1. **Flaw** — name the specific defect and the principle it violates (for example: "default 0.5
   offered as a shrug, P032"; "a 90%-style interval with no sign it was ever widened, P073").
2. **Correction** — apply the fix directly: rescale extremeness to the real predictability, replace
   the flat 0.5 with a duration-based or partial-information estimate, pull certainty back short of
   1.0/0.0, widen the interval, recompute a scenario as a product rather than an average, or re-run
   the coherence check on the decomposed set.
3. **Residual uncertainty** — state, as a number (a range or an odds ratio) rather than a hedge word,
   how much uncertainty remains even after the correction, and what evidence would move it further.
4. **Next step** — a concrete action: gather one named piece of diagnostic evidence, re-elicit the
   interval with a different procedure, recompute the scenario probability, or hand the corrected
   number back to whoever owns the decision.

Even where every check is passed, produce at least one finding-shaped note naming which specific
checks the judgment already satisfies — never a bare "looks fine" with nothing named.

In **advise** mode (a single upcoming hygiene question rather than a full review), collapse this to
one recommendation in the same four-part shape. In **compare** mode (weighing two ways of stating or
handling the same probability — for example a tight interval against a widened one, or a flat 0.5
against a duration-based bound), lay out what each choice costs against these same checks and close
with a calibration-weighted recommendation.

This skill never substitutes its own probability for the one under review, and it never makes the
decision the number feeds into — the corrected judgment and the residual odds are handed back to the
forecaster and the decision-maker.

## Anti-patterns to flag

- A confident forecast whose basis is a coherent, vivid story rather than demonstrated
  predictability (P002).
- A large, consistent-looking body of information cited as grounds for high confidence, with no
  check on whether it actually improved accuracy (P003).
- A bare probability or verbal confidence phrase with no stated sources of uncertainty or milestones
  to watch (P010).
- Evidence of doubtful reliability treated as a flat yes/no fact instead of weighted by its own
  assessed validity (P014).
- A scenario probability produced by averaging its steps rather than multiplying them — especially
  right after a vivid supporting detail was added (P018).
- A multi-step plan judged too likely to finish on time, or a many-component system judged too
  unlikely to fail (P028).
- A suspiciously precise number, or a confident-sounding adviser, treated as if it were evidence of
  real calibration (P031).
- "50-50" or "I really don't know" given as the number itself, with no use made of whatever partial
  information — even just elapsed duration — is actually available (P032).
- An estimate that visibly tracks a number already on the table, with no recorded attempt to argue
  against that anchor (P038).
- A probability scale collapsed to its two ends, or a low-probability event weighted, once it
  reaches a decision, as if it were far more or far less likely than the number stated (P052, P058).
- A stated confidence interval narrow enough that it would be a surprise if it were ever actually
  checked against outcomes (P073).
- A whole set of outcomes rated less likely than the sum of its own exhaustive, mutually exclusive
  parts (P076).
- A stated probability of exactly 1.0 (or exactly 0.0 for an opposing view), leaving no room for any
  future evidence to change it (P078).

## References

- [`../../references/calibration-forecasting-principles-index.md`](../../references/calibration-forecasting-principles-index.md)
  — the package-wide index of every promoted principle cited above, with its full statement,
  confidence level, and source anchor.

## Provenance

This skill's every check derives from P002, P003, P010, P014, P018, P028, P031, P032, P038, P052,
P058, P073, P076, and P078 (P031 at medium confidence, the rest at high), grounded in Kahneman's
*Thinking, Fast and Slow*, Tetlock & Gardner's *Superforecasting*, Tetlock's *Expert Political
Judgment*, and Heuer's *Psychology of Intelligence Analysis*; see the frontmatter `provenance` block
above for the exact claim, evidence, and source-anchor ids.
