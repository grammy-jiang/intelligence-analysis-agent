---
name: forecasting-accountability-and-communication
description: "Guard a forecast review against failures in how forecasts are judged, rewarded, and defended (not the math); use when accountability, incentives, or communication of a forecast is in scope."
kind: skill
status: ready
provenance:
  principles:
  - P037
  - P043
  - P062
  - P072
  - P083
  - P086
  claims:
  - C01397
  - C01398
  - C01515
  - C01516
  - C01262
  - C01263
  - C01723
  - C01726
  - C01522
  - C01813
  evidence:
  - E00386
  - E00387
  - E00476
  - E00477
  - E00293
  - E00294
  - E00610
  - E00613
  - E00480
  - E00672
  source_anchors:
  - 5da0a790f5ae-c0003
  - 5da0a790f5ae-c0009
  - e3c7c0b4e46f-c0018
  - 5da0a790f5ae-c0022
  - 5da0a790f5ae-c0010
  - 5da0a790f5ae-c0029
  authored_from_digest: aeb97fd160ae41fed78c73f6c34b8e7012f22a61b4c6e7042151507dc089af6e
---

# Forecasting Accountability and Communication

## Purpose

Guard a forecast review against failure modes that live in how a forecast is judged, rewarded, and defended — not in the probability math itself, which the sibling calibration skills cover. A forecast can be numerically defensible and still be reviewed badly if the reviewer trusts an unaccountable audience to sort good calls from bad, treats extremity as if it were insight, conflates accuracy with tribal loyalty, lets a fluent story stand in for a probability estimate, or accepts a forecaster's after-the-fact excuses at face value. This skill checks that layer: the venue a forecast is judged in, the incentives that shape it, and the rhetorical moves forecasters use to survive being wrong (P037, P043, P062, P072, P083, P086).

## When to use

- The forecast or commentary under review sits in a public, political, or partisan setting where "everyone will eventually see who was right" is assumed rather than demonstrated.
- Several forecasters or schools of thought are being compared and one or more leans toward a doomsday or a rosy extreme.
- A forecast's quality is being judged in a setting where accuracy and whose side the forecast serves can be confused with each other.
- The forecast is presented mainly as a narrative or case account rather than as an explicit, scoreable probability.
- A forecaster is defending a miss, especially with "I was just off on timing" or "it almost happened."

## Procedure

1. Check whether the review is implicitly trusting an unaccountable venue to self-correct: if the forecast lives inside a political "marketplace of ideas," do not assume the audience, the pundits, or the passage of time will sort accurate from inaccurate calls on their own — that self-correcting story only works when consumers are motivated by truth rather than solidarity and the task is easy enough to judge, and political prediction's mix of unmotivated, solidarity-seeking consumers plus genuine cognitive and task-difficulty limits can leave even engaged experts unable to tell who was actually right. Flag any argument that leans on "the marketplace will decide" as a substitute for an actual accuracy check (P037).
2. Weigh moderate, muddle-through, and zigzag forecasts above doomsday or rosy extremes, all else equal: a forecast that blends opposing arguments and respects the base rate should outrank one built on an extreme narrative, even a vivid one. When a school of thought points to one member who was later "vindicated," treat that as expected background noise — inside any school someone always ends up looking right by chance — not as evidence the school, or its method, has skill (P043).
3. Before judging a forecast as good or bad, ask which goal it actually serves: in a political or tribal setting, forecasts are frequently rewarded or punished for whose side they favor, not for whether they came true — the same forecaster can be praised or attacked for the same call depending only on who is doing the judging, and a forecast that turns out wrong can still "succeed" for its author. Separate the accuracy question from the whom-does-it-serve question explicitly, and say which one the review is answering (P062).
4. When a forecast is delivered as a story, use the narrative to understand the mechanism and the scenario — stories are genuinely useful for grasping contingency and how events could unfold — but do not let the story's coherence or vividness substitute for the probability calculus when judging how likely the outcome actually is. Do not apply one evidentiary standard to a compelling storyteller and a stricter one to a forecaster who states an explicit number; pick the probability-based standard, because that is the one the eventual decision has to be made on (P072).
5. Treat "I was just off on timing" as a warning sign, not a mitigating explanation: ask what the original horizon was and whether it is now being silently extended, because a horizon stretched far enough makes almost any prediction eventually come true, which means the claim was never falsifiable in the first place — the original call should be scored as wrong or unresolved, not as "right, just early" (P083).
6. When a forecaster explains away a miss with "it almost happened," do not accept it at face value: compare how often they reach for that near-miss counterfactual after a failure versus after a success. The more lopsided that ratio, the more the excuse functions as a rhetorical bailout rather than a genuine account of a close call, and the credit given should shrink in step with the asymmetry, down to a token amount when the pattern is stark (P086).
7. Write up every finding from steps 1–6 in the format given under `## Output`: name the accountability or communication flaw, apply the correction the principle implies, state what uncertainty remains even after the correction, and give one concrete next step — highest-impact finding first.

## Inputs

- The forecast or commentary under review, including how it was originally delivered — an explicit probability, a narrative account, or both — and its stated reasoning.
- The venue: is this public, political, or partisan commentary where an unaccountable "marketplace of ideas" might be implicitly trusted to sort it out?
- What is known about whose side the forecast favors and how it has already been praised, attacked, or scored, if available — versus what is merely assumed.
- The forecaster's track record of defenses, if any: prior "off on timing" or "it almost happened" claims, and whether those cluster after failures rather than successes.
- The original horizon and the exact outcome predicted, so a "still could happen" defense can be checked against the boundary actually stated, not one quietly moved.

## Output

One finding per flaw, in this order:

1. **Flaw** — name the specific accountability/communication pathology (trusting an unaccountable venue, extremity reward, kto-kogo tribal scoring, narrative-for-calculus substitution, unfalsifiable timing defense, asymmetric near-miss excuse) and the principle it violates.
2. **Correction** — the concrete fix: demand an actual accuracy check instead of "the marketplace will decide"; discount the extreme forecast relative to the moderate one; state explicitly whether the review is scoring accuracy or tribal service; re-derive the likelihood with the probability calculus instead of the story; score the original horizon as missed rather than accept a moved one; discount the near-miss excuse by its failure-only asymmetry.
3. **Residual uncertainty** — what the correction does not resolve, for example: the forecast may still be directionally right even though the defense offered for it is illegitimate, or whose side it serves may remain genuinely unknown.
4. **Next step** — one concrete action: request the missing accuracy check, ask for the reference class, ask the forecaster to restate the claim as a scoreable probability with a fixed horizon, or hand the domain judgment back to the forecaster or decision-maker.

Order findings highest-impact first. A finding always closes on a next step, never on a bare domain forecast — this skill critiques the calibration and reasoning, it does not supply the estimate.

## Anti-patterns to flag

- Assuming a political "marketplace of ideas" will self-correct a bad forecast without ever running an actual accuracy check (P037).
- Treating a doomsday or utopian extreme as more insightful than a moderate, base-rate-respecting forecast, or citing one later-vindicated pundit as proof a school of thought has skill (P043).
- Judging a forecast as good or bad without first asking, and stating, whether accuracy or tribal service is the standard being applied (P062).
- Letting a fluent, coherent narrative stand in for a probability judgment, or holding storytellers and number-stating forecasters to different evidentiary standards (P072).
- Accepting "I was just off on timing" as if it rescues a miss, especially over a horizon that has quietly been extended (P083).
- Accepting "it almost happened" as evidence of forecasting quality without checking whether the forecaster only reaches for it after losses (P086).

## References

- `../../references/calibration-forecasting-principles-index.md` — full statements, confidence levels, and source anchors for P037, P043, P062, P072, P083, P086, alongside every other principle in this package.
- For flaw classes outside this skill's scope — miscalibration, base-rate neglect, improper scoring, faulty Bayesian updating, cognitive-bias traps, horizon/tail-risk error — hand off to the sibling skill that owns it: `calibration-and-probability-hygiene`, `forecast-scoring-and-evaluation`, `base-rates-outside-view-and-regression`, `bayesian-belief-updating`, `cognitive-bias-and-mindset-control`, `forecaster-style-and-aggregation`, or `scenarios-horizon-and-tail-risk`.

## Provenance

This skill body derives solely from principles P037, P043, P062, P072, P083, and P086 (Expert Political Judgment and Superforecasting); see the frontmatter `provenance` block for the corresponding claim, evidence, and source-anchor ids.
