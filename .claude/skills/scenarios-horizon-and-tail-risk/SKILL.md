---
name: scenarios-horizon-and-tail-risk
description: "Check whether a forecast's precision, form, and confidence match what is knowable at its horizon and its subject's tail behaviour; use when reviewing scenario, range, or tail-risk framing."
kind: skill
status: ready
provenance:
  principles:
  - P004
  - P026
  - P040
  - P047
  - P055
  - P056
  - P079
  - P081
  - P084
  - P085
  - P087
  - P089
  claims:
  - C00098
  - C00099
  - C01252
  - C01253
  - C00920
  - C00924
  - C01242
  - C01243
  - C02793
  - C02794
  - C01367
  - C01368
  evidence:
  - E00001
  - E00002
  - E00285
  - E00286
  - E00136
  - E00138
  - E00275
  - E00276
  - E00694
  - E00695
  - E00360
  - E00361
  source_anchors:
  - 6ec9d9fb28d6-c0002
  - e3c7c0b4e46f-c0018
  - e3c7c0b4e46f-c0000
  - e3c7c0b4e46f-c0001
  - e3c7c0b4e46f-c0017
  - a445f2941de4-c0057
  - 5da0a790f5ae-c0002
  - 5da0a790f5ae-c0010
  - 5da0a790f5ae-c0009
  - 5da0a790f5ae-c0011
  - 5da0a790f5ae-c0012
  - d88ef7714f29-c0012
  authored_from_digest: a423039cd785971870e6f2d812633644ccd8a5e260edd1f965f85fe66a2e8109
---

# Scenarios, Horizon, and Tail Risk

## Purpose

This skill reviews whether a forecast's claimed precision, form, and confidence actually match
what is knowable about its subject, at its stated horizon, given how the world it describes
really behaves. It checks whether a single-outcome estimate should instead have been built as a
branching set of scenarios, whether the forecast's confidence has been discounted for how far out
it reaches, whether the domain being forecast is quietly treated as bell-curved when it is really
fat-tailed and capable of throwing up outcomes far outside intuition, and whether the forecast's
theory of the case is one deduced storyline or a macro-theory properly gated by checkable
micro-variables and an explicit hedge. Good calibration is not only "is the number right" — it is
"is the number right for what is actually forecastable at this range, in this kind of world."

## When to use

Use this skill once the estimate has passed the sibling calibration, scoring, base-rate, and
bias checks, to test its fit to horizon and its exposure to tail risk. Concretely:

- The estimate is a single confident point or narrative about a complex, high-consequence
  situation, and no one has asked whether a branching set of futures would serve the
  decision-maker better (P004).
- The forecast states or implies a horizon (next quarter, next year, next decade), and the
  reviewer needs to judge whether the stated confidence is realistic for that distance (P040).
- The quantity being forecast is the kind that can produce extreme values far outside a
  normal-curve intuition (P026).
- Someone in the discussion argues forecasting is either a solved, formulaic problem or a
  worthless enterprise, and the review needs to locate the real claim between those poles (P047).
- The decision under review is a low-probability, high-payoff bet, and the reviewer must check
  how much weight a small change in the probability estimate is being asked to carry (P055).
- The forecast's justification reads like an explanation of mechanism, and the reviewer must
  check whether that explanatory soundness has been mistaken for predictive power (P056).
- The forecast chains two or more predicted outcomes together (a shock causing a downstream
  event), and each link needs its own scrutiny (P079).
- The forecast leans toward an extreme trajectory, or toward a sharp regime break, and the
  reviewer must check whether that lean is disciplined (P081, P084).
- The forecast rests on one macro-theory deducing a single outcome, or on a theoretical concept
  whose predictive value has never been tested, or on a simplicity that discards real structure
  (P085, P087, P089).

## Procedure

Work the following checks in order; skip a check only when the input plainly does not raise it,
and say so in the finding.

1. **Decide whether a single outcome is trustworthy, or whether scenarios are owed (P004).** If
   the situation is complex and uncertain enough that no single story should be trusted, check
   whether the estimate should instead have been built as an Alternative Futures analysis: the
   two most critical and uncertain drivers chosen as axes, crossed into four future worlds each
   with a plausible narrative and early signposts, built so decision-makers can pressure-test
   their strategies against every world. Because the technique is costly, flag its absence only
   for genuinely high-consequence problems — do not demand it for a routine, low-stakes estimate.

2. **Calibrate confidence to the stated horizon (P040).** Predictability is not a fixed property
   of a topic; it depends on what is being forecast, how far out, and under what conditions.
   Check that stated or implied confidence declines as the horizon lengthens, and treat a
   forecast that holds the same confidence from one year out to five-plus years out as
   miscalibrated by construction — in most open systems accuracy decays toward chance by three to
   five years out, and nothing much past a decade should be presented as reliable. Ask the
   forecaster to scope the claim to the window it can actually support.

3. **Check the shape of the distribution being forecast (P026).** Before accepting a confidence
   interval or a "this is too unlikely to matter" dismissal, ask whether the underlying quantity
   is fat-tailed rather than bell-curved — many consequential quantities are (wealth is the
   familiar case: a normal-curve intuition badly undersells how far some outcomes sit out on the
   tail). If so, extreme outcomes are far likelier than that intuition suggests, and a wide
   interval or a scenario branch for the tail is not overcaution. Also weigh that the present
   outcome is only one draw among many once-possible worlds: a near-miss catastrophe is evidence
   for taking prevention more seriously, not evidence the risk was overstated.

4. **Place the claim correctly between "forecasting is a formula" and "forecasting is bunk"
   (P047).** If the forecast's credibility rests on a short-horizon accuracy record, flag that
   this says nothing about its ability to catch rare, high-impact events — that is a different
   claim needing different evidence. If the forecast is being dismissed because of one missed
   rare event, check whether that event was genuinely inconceivable beforehand or merely "grey" —
   imaginable, and reachable through a chain of smaller, forecastable steps that were themselves
   visible. Neither extreme position should stand unexamined.

5. **Weigh how much a small probability shift is being asked to carry (P055).** When the decision
   on the table is a low-probability, high-payoff option, choosing to proceed despite long odds
   can be entirely reasonable — a large enough payoff can make even a slight chance of success
   worth pursuing. Check two things: whether the estimate's precision is actually good enough to
   support the fine distinction the decision turns on (it often is not), and whether the size of
   the stakes is itself inflating the probability estimate — that distortion is sharpest exactly
   when the decision-maker cannot yet test the estimate by acting on it.

6. **Keep prediction and explanation apart (P056).** Confirm that an account explaining why
   something happened, or why a mechanism should produce an outcome, is not being credited as if
   it were itself a validated predictive claim. A theory can be sound and still fail to predict
   correctly when its antecedent conditions are unknown at forecast time, or when the system it
   describes is chaotic. Ask specifically: has this forecast been tested against the future, or
   does its confidence come entirely from how well it explains the past?

7. **Evaluate each causal linkage in the chain separately (P079).** Where the forecast couples
   two predictions — a shock leading to a downstream event, a policy leading to an outcome — do
   not let confidence in one link transfer to the other. Question the tightness of the assumed
   coupling on its own terms; a forecaster well-calibrated on the first link can still go badly
   overboard on the second.

8. **Check for reluctance at the extremes (P081).** Because positive feedback loops in real
   systems are usually checked by dampening mechanisms before they run away, a forecast that
   leans toward an extreme trajectory needs a specific reason the usual checks will fail this
   time. Absent that reason, treat the extreme lean as a flag, not a feature.

9. **Check that sharp regime change is still treated as rare (P084).** Even where the forecaster
   genuinely expects a transformative break, the disciplined move is to nudge the assigned
   probability up from the low base rate for such events — a higher probability than others would
   give it — not to assign it a high probability outright. Flag forecasts that jump straight to
   "likely" for a regime change.

10. **Require a macro-theory to be gated, not deduced from directly (P085).** If the forecast's
    real engine is one macro-theory producing a single deduced outcome, flag that the theory
    should instead be paired with specific, checkable micro-variables that gate which of several
    plausible futures actually occurs, plus an explicit hedge naming what would revise the call.

11. **Test any load-bearing theoretical concept for real predictive value (P087).** Where a
    concept or framework is doing the work behind the forecast (a bias, a structural theory, a
    historical analogy), check whether it earns that role the way a strong concept should: by
    having generated a precise, nonintuitive, testable prediction elsewhere — the way loss
    aversion correctly predicted golfers would putt better to avoid a bogey than to sink a
    birdie — not merely by sounding plausible or fitting the story after the fact.

12. **Do not let a demand for parsimony strip out needed structure (P089).** A simple, elegant
    theory is a scientific virtue, but check whether the forecast has been pared down to one
    clean driver for tidiness in a domain — geopolitics, markets, conflict — where the gated
    micro-variables from step 10 are doing real work. Treat an unexplained loss of that structure
    as a liability, not a strength.

## Inputs

- The forecast or estimate itself, including its stated or implied horizon and exactly what
  outcome it commits to.
- The reasoning behind it: the mechanism, theory, or causal chain it rests on, and whether that
  chain links more than one prediction together.
- Whether the situation is high-complexity / high-consequence enough that a scenario-based
  approach would plausibly be worth its cost, and whether one was considered.
- The stakes and payoff structure of the decision the forecast feeds, especially if it is a
  low-probability, high-payoff bet.
- What is known about the historical base rate of extreme values or regime breaks in this
  domain, so the fat-tail and rare-regime-change checks have something to compare against.

## Output

Each finding follows the same four-part shape used across this reviewer's findings:

1. **Name the flaw** — which of the twelve checks above it fails, and the specific way (for
   example: confidence held flat across a lengthening horizon; a macro-theory deducing a single
   outcome with no gating variables).
2. **Apply the correction** — the concrete fix: switch to an Alternative Futures scenario set,
   discount confidence for the horizon, widen the interval for a fat-tailed quantity, add gating
   micro-variables and a hedge, or separate the explanatory claim from the predictive one.
3. **State the residual uncertainty** — what remains unresolved even after the correction, and
   the horizon or scope it is bounded to.
4. **Give a next step** — the concrete action the forecaster or decision-maker should take next
   (build the four-world matrix; re-scope the claim to the tractable window; name the
   micro-variables to watch).

Order findings highest-impact first. Never end on a bare "the forecast is right/wrong" —
always close on the next step.

## Anti-patterns to flag

- A single confident point forecast offered for a high-complexity, high-consequence question
  with no scenario alternative considered (P004).
- Stated confidence that does not decay as the horizon lengthens, or a claim projected years past
  the window the method can actually support (P040).
- A fat-tailed quantity treated as if it were bell-curved, or an extreme outcome dismissed as
  impossible because it lies outside a normal-curve interval (P026).
- Either "this forecasting method is a solved formula" argued from a short-horizon track record,
  or "forecasting is bunk" argued from one missed event that was actually foreseeable through
  smaller forecastable steps (P047).
- A low-probability, high-payoff estimate whose precision is treated as adequate to the decision,
  or whose probability looks inflated by the size of the stakes rather than by evidence (P055).
- An explanatory account of mechanism presented as if it were a tested predictive claim (P056).
- Confidence in one predicted linkage bleeding into confidence in a second, separately-uncertain
  linkage (P079).
- An extreme or runaway trajectory asserted with no argument for why the usual dampening
  mechanisms would fail this time (P081).
- A sharp regime change assigned a high absolute probability rather than a probability nudged up
  from a low base rate (P084).
- A single outcome deduced straight from one macro-theory, with no gating micro-variables and no
  hedge (P085).
- A theory or framework credited with predictive power it has never demonstrated through a
  precise, nonintuitive, testable prediction (P087).
- A forecast simplified to one clean driver for elegance, in a domain where the gated
  micro-variables it discarded were doing real work (P089).

## References

- `../../references/calibration-forecasting-principles-index.md` — the full principle index for this
  reviewer, including the principles this skill applies (P004, P026, P040, P047, P055, P056,
  P079, P081, P084, P085, P087, P089) alongside the sibling-skill principles it does not
  duplicate.

## Provenance

This skill body derives from P004, P026, P040, P047, P055, P056, P079, P081, P084, P085, P087,
and P089, distilled from *A Tradecraft Primer*, *Superforecasting*, *Expert Political Judgment*,
*Perception and Misperception in International Politics*, and *Thinking, Fast and Slow* (all
distillation-only sources; paraphrased throughout, no verbatim quotation).
