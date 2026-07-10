---
name: forecast-scoring-and-evaluation
description: "Make a forecast or track record scoreable and score it without a story or excuse standing in for the arithmetic; use when evaluating forecast accuracy or a proper score."
kind: skill
status: ready
provenance:
  principles:
  - P013
  - P015
  - P025
  - P035
  - P039
  - P048
  - P050
  - P059
  - P065
  - P068
  - P071
  - P075
  - P077
  - P090
  claims:
  - C01326
  - C01361
  - C00996
  - C00998
  - C00992
  - C00993
  - C01488
  - C01495
  - C01331
  - C01343
  - C01269
  - C01270
  evidence:
  - E00327
  - E00354
  - E00171
  - E00172
  - E00167
  - E00168
  - E00457
  - E00464
  - E00332
  - E00344
  - E00297
  - E00298
  source_anchors:
  - 5da0a790f5ae-c0000
  - 5da0a790f5ae-c0001
  - e3c7c0b4e46f-c0004
  - 5da0a790f5ae-c0008
  - e3c7c0b4e46f-c0019
  - 5da0a790f5ae-c0002
  - 5da0a790f5ae-c0006
  - 5da0a790f5ae-c0027
  - 5da0a790f5ae-c0017
  - e3c7c0b4e46f-c0020
  - e3c7c0b4e46f-c0021
  - 5da0a790f5ae-c0028
  authored_from_digest: 0a18c9098e68b74a854bc9dcd71b47be6d5a9f1b429f334a58b5fa9678b35f97
---

# Forecast Scoring and Evaluation

## Purpose

Turn a forecast, or a forecaster's track record, into something that can actually be scored — and then score it without letting a good story, a single number, or a self-serving excuse stand in for the arithmetic. This skill covers scoreability and honest scoring end to end: defining the outcome precisely, decomposing accuracy into calibration and resolution/discrimination under a proper scoring rule, reading the result only against a named baseline, and refusing any adjustment generous enough to erase a real skill gap. It is the reviewer's scoring layer — use it to critique how a forecast is defined, measured, or compared, not to hand the caller a probability of your own.

## When to use

- A forecast or estimate is about to be judged after the fact, and the outcome needs to be pinned down precisely enough to score at all (P050).
- A forecaster's, pundit's, or model's track record is being scored or compared against a rival, and the team needs the right decomposition, scoring rule, and baseline (P015, P059, P065, P068).
- Someone proposes adjusting a raw score — for difficulty, stakes, a disputed outcome, fuzzy boundaries, or reweighted probabilities — and the adjustment itself needs a legitimacy check (P071, P035, P077).
- A continuous quantity (a rate, an index, a level) has been forecast and nobody has said how it will be judged right or wrong (P090).
- A single metric is being used to settle who is more skilled, and it needs to be read in context rather than taken as the whole verdict (P048).

## Procedure

1. **Pin the outcome to a scoreable claim.** Apply the clairvoyance test first: could someone who already knew the future score this outcome without asking a clarifying question? Send back anything oracular, hedged past falsifiability, or dressed in rhetoric, and restate it on the plain facts being predicted before scoring proceeds (P050).
2. **Bracket a disputed outcome instead of refereeing it.** When there is genuine disagreement about whether the outcome occurred, do not let your own reading decide the score. Compute it once under the reading most favorable to the forecaster and once under the least favorable, and trust a conclusion only if it holds under both. Weigh any "I was almost right" defense against how rarely that same forecaster credits luck rather than skill when a call happens to land — an asymmetric excuse is itself worth flagging (P025).
3. **Decompose accuracy into calibration and resolution/discrimination, and score with a proper rule.** Separate two questions: calibration (do events assigned probability p happen about p percent of the time?) and resolution/discrimination (are high probabilities reserved for things that go on to happen, beating a strategy of always naming the base rate?). Score with a proper rule such as the Brier score, where lower is better and a confident miss costs more than a hedged one (P015, P065). Never certify from resolution/discrimination alone — it is carried by a squared term and can look strong even for someone decisively and consistently wrong — read it paired with calibration always, and lean toward calibration when missing a real event costs more than a false alarm (P068).
4. **Read any score only against a named baseline, same questions, same period.** A score in isolation says nothing. State the naive comparator being beaten — persistence, the base rate, or an equivalent simple rule — and compare only forecasters scored on the same questions over the same stretch of time. A low score can just mean an easy run of questions rather than skill (P059).
5. **Cross-check with the betting test.** Ask whether the forecaster would actually stake money at the odds their stated probability implies. A proper scoring rule already punishes overconfidence the way a bad bet does; if they would not take the bet, the number is not their real belief and needs revising before it is scored at all (P075).
6. **Separate skill from how hard the questions were.** Adjust for the fact that some forecasters faced harder questions, but do not expect that to explain away a real gap — a difficulty-adjusted score that stays below zero still means the forecaster did worse than simply naming the base rate, and the failure is sharpest for someone reasoning confidently inside one specialty but forecasting on a long horizon outside it (P013).
7. **Screen any proposed adjustment against the five legitimate categories, then reject the ones that erase the comparison.** A score adjustment is only legitimate if it answers one of five objections: the question's difficulty, the stakes riding on being right, a genuine dispute over the outcome, fuzzy boundaries on what counts as the predicted set, or a needed reweighting of the stated probabilities. After applying the matching adjustment, judge skill by whether it still beats a base-rate strategy — a skill score of zero means the forecaster added nothing beyond guessing (P071). Reject any adjustment so generous it could never show a real gap between two forecasters or approaches: a stakes/value adjustment cannot manufacture parity when one side is making more errors of both kinds, and a genuine gap of this sort holds up across different variables, horizons, and domains (P035). Never score over-prediction and under-prediction errors on separate, independently chosen scales either — that can flatter a forecaster stuck on one answer into looking calibrated and silently assumes they knew in advance which error they would make; instead test any claimed group difference across many plausible ways of weighting the two error types and trust it only if it survives all of them (P077).
8. **Treat the resulting metric as a tool, not a totem.** No metric is uniformly good, and elevating one to the sole measure invites people to game it. Do not respond by discarding scoring altogether — scrutinize the metric, tune it to what the decision actually needs (weigh a missed real event against a false alarm the way the stakes demand), and resist reading more precision into it than it has. Even an imperfect score still beats a verdict based on job title, fame, or confidence (P048).
9. **Make a continuous forecast scoreable before scoring it.** A forecast about a continuous quantity is not automatically a yes/no claim. Wrap a confidence band around the recent value — for example, plus or minus half a standard deviation of the last five to ten years of readings — and score whether the outcome later lands below, inside, or above that band (P090).
10. **Close by judging progress, not perfection.** Expect disagreement about what "good judgment" even means to persist, and treat that as something worth studying rather than a defect to resolve before any score counts. Judge the review by whether the team now knows more than before it started, not against an unreachable standard of perfection, and revisit how heavily misses are weighed against false alarms as the stakes and priorities shift (P039).

## Inputs

- The forecast or track record under review: exactly what was predicted, the horizon, and — if scoring after the fact — what happened, including whether that outcome is disputed.
- Paired data when scoring a body of forecasts: each stated probability alongside its observed outcome, and whether the variable is binary/categorical or continuous.
- A stated naive baseline or comparator, and confirmation the comparison set is same-question, same-period.
- Any proposed scoring adjustment and its stated justification (difficulty, stakes/value, disputed outcome, fuzzy-set boundary, or probability reweighting).
- Whether the forecaster's confidence has ever been tested against a real bet, if that can be asked.

## Output

Per finding, highest-impact first:

1. **Flaw** — the scoring or definitional defect and the principle it violates (for example: outcome fails the clairvoyance test, score reported with no baseline, adjustment collapses the parity test).
2. **Correction** — the concrete fix, citing the Pxxx it comes from: restate the outcome on plain facts, add the naive baseline, decompose into calibration and resolution/discrimination, recompute under both bounds of a disputed outcome, reject or bound the adjustment, wrap a continuous forecast in a confidence band.
3. **Residual uncertainty** — what the correction leaves open: too few paired observations to trust the resolution term, a still-unsettled dispute over the outcome, a single score that is not yet a track record, an adjustment that is legitimate in kind but unverified in size.
4. **Next step** — one concrete action: gather more paired observations, get the baseline stated explicitly, rerun the score under both outcome bounds and report only if they agree, or rerun the group comparison across a range of penalty weightings.

Hand the forecast, the decision, and any adjustment call back to the forecaster and the decision-maker in every finding — this skill critiques scoreability and scoring, it does not supply the estimate.

## Anti-patterns to flag

- An outcome so vague or oracular it cannot be scored without asking the forecaster what they meant (P050).
- A score quoted with no stated baseline, or compared across different questions or time periods (P059).
- Crediting "almost right," "off only on timing," or a lucky call as evidence of skill — especially from a forecaster who never credits luck when wrong (P025).
- Judging accuracy from resolution/discrimination alone, when a decisively wrong-but-consistent forecaster can still score well on that term (P015, P065, P068).
- Separate value scales for over-prediction and under-prediction errors, which can flatter a broken-clock forecaster (P077).
- A difficulty, stakes, or value adjustment so generous it makes a real skill gap unfalsifiable (P035).
- Ignoring task difficulty entirely when comparing forecasters, or assuming a difficulty adjustment must erase the underlying gap (P013).
- Treating one anointed metric as the whole verdict, or abandoning scoring altogether once a metric proves gameable (P048).
- An adjustment that matches none of the five legitimate categories, or one applied without checking the adjusted score still beats the base rate (P071).
- Leaving a continuous-quantity forecast unscored because "it isn't really a probability" (P090).
- Insisting on a final, perfect definition of good judgment before crediting any measurement progress (P039).

## References

- `../../references/calibration-forecasting-principles-index.md` — the package's full principle index (statement, confidence, and applies-when conditions for every principle, including the fourteen this skill applies); consult it for the exact wording behind any Pxxx cited above and for the sibling scoring-adjacent principles this skill does not cover.

## Provenance

This skill body is derived entirely from P013, P015, P025, P035, P039, P048, P050, P059, P065, P068, P071, P075, P077, and P090; see the frontmatter `provenance` block above for the backing claim, evidence, and source-anchor ids.
