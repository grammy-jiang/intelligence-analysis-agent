---
name: base-rates-outside-view-and-regression
description: "Audit whether an estimate anchored to its reference-class base rate (the outside view) before case detail moved it; use when a forecast leans on inside-view specifics or ignores regression to the mean."
kind: skill
status: ready
provenance:
  principles:
  - P005
  - P006
  - P007
  - P023
  - P049
  - P051
  - P066
  - P067
  - P082
  - P091
  claims:
  - C00653
  - C00654
  - C00732
  - C00733
  - C00661
  - C00662
  - C00467
  - C00468
  - C01345
  - C01346
  - C01421
  - C01422
  evidence:
  - E00071
  - E00072
  - E00105
  - E00106
  - E00079
  - E00080
  - E00039
  - E00040
  - E00346
  - E00347
  - E00399
  - E00400
  source_anchors:
  - d88ef7714f29-c0006
  - d88ef7714f29-c0010
  - d88ef7714f29-c0007
  - 3a2b4f822beb-c0013
  - 5da0a790f5ae-c0001
  - 5da0a790f5ae-c0005
  - 5da0a790f5ae-c0006
  - 5da0a790f5ae-c0010
  - 5da0a790f5ae-c0027
  authored_from_digest: 79621240000661dfdb95368b47b96de8fb6ff5b92ee36214a2892998b32b138a
---

# Base rates, the outside view, and regression

## Purpose

Anchor every estimate to the outside view — the base rate of its reference class — before
letting case-specific detail move it. A forecast built from the inside view alone (the
specifics of the case at hand) routinely misses an available base rate, because a vivid,
case-specific story crowds out a pallid statistic even when the forecaster already holds it
(P006). Left uncorrected, a case-based prediction is also nonregressive: it runs as extreme as
the evidence feels, instead of being pulled back toward the baseline by how predictive that
evidence actually is (P007) — and an extreme result taken in isolation is often nothing more
than regression to the mean, not a caused effect (P005). This skill reviews whether a forecast
did that anchoring work: whether it named and led with the right reference class, regressed its
extremes by the right fraction, kept a causal base rate that a moral or rhetorical impulse
might otherwise discard (P023), matched its performance baseline to the regime it was made in
(P066), and defaulted to the status quo — including the survival of an existing regime — as
the most probable outcome absent a specific case for change (P067, P082). It also keeps the
review's own expectations calibrated: most human forecasters sit closer to simple
extrapolation than to a real statistical model, and even formal models beat people only
modestly, because a disciplined persistence-plus-regression rule already captures most of what
is predictable (P049, P091).

## When to use

- A forecast, probability judgment, or estimate is presented and it is unclear whether a
  reference class or base rate was ever consulted (P006).
- The estimate was built from a compelling case-specific narrative, analogy, or track record,
  with no base rate named alongside it (P006).
- A prediction reads as extreme as the underlying evidence itself — a near-certain call from
  one strong indicator, or a projection that simply repeats an intuitive impression (P007).
- The review turns up an unusually good or bad result, a "before vs. after" comparison, or a
  claim that an intervention (coaching, discipline, a new program) caused a change (P005).
- A base rate for the case's category exists but reads as "merely statistical" rather than
  causal, and there is a temptation to set it aside (P023).
- A forecasting approach, or a specific forecaster's track record, needs a performance
  baseline, and the environment must first be classified as turbulent or stable (P066).
- The question concerns whether an existing state of affairs, policy, or government will
  continue or change (P067, P082).
- The caller wants to know how much weight to put on gut extrapolation versus a base-rate- or
  persistence-based rule (P049, P051, P091).

Do **not** use this skill to invent the missing reference class or base rate: if none is
knowable from the material supplied, name the gap and hand the request for reference-class
data back to the forecaster or domain owner rather than substituting a guess.

## Procedure

1. **Name the reference class and lead with its base rate.** Before weighing any
   case-specific detail, identify the class of comparable cases this forecast belongs to and
   state its base rate — that number is the anchor the rest of the review works from,
   adjusted toward the case's own specifics only in proportion to how valid those specifics
   really are. Flag any estimate that jumps straight to case reasoning without ever naming a
   reference class: holders of vivid case detail routinely feel no need for the base rate
   even when they already have it, and a pallid statistic loses to a vivid story unless the
   review actively resists that pull (P006).
2. **Regress a nonregressive extreme back toward the baseline.** An intuitive prediction
   that simply matches the felt strength of the evidence is nonregressive — as extreme as
   the evidence itself — so it runs over-optimistic for the best-looking cases and
   over-pessimistic for the worst. Correct it explicitly: start from the reference-class
   baseline, form the case-based estimate, then move from the baseline toward that estimate
   only by the fraction equal to the evidence's actual correlation with the outcome; the
   weaker that correlation, the closer the corrected number should stay to the baseline.
   Treat this as deliberate, effortful work worth doing when the stakes are high and accuracy
   matters, not a formality to skip (P007).
3. **Check whether an extreme result is just regression to the mean.** When a finding turns
   on an unusually good or bad outcome — a rebound after criticism, a slump after praise, an
   improvement credited to a new program — ask first whether it is simply the ordinary result
   of an imperfect correlation between two measurements: an extreme score is partly luck and
   tends to be followed by something less extreme, with no cause required. The pattern runs
   symmetrically whether you look forward or backward in time, which is exactly why it cannot
   be a causal effect — yet people, including domain experts, routinely invent a causal story
   for it anyway. Do not accept a causal claim built only on a before/after comparison;
   require a control or comparison group before crediting an intervention (P005).
4. **Reinstate a causal base rate even when it reads as merely statistical.** Forecasters
   (and reviewers) tend to use a base rate when it seems to say something about the mechanism
   of the individual case, and to quietly drop an equally valid base rate that is "merely" a
   statistic about the category. A statistically valid base rate still carries real
   predictive information regardless of whether it feels causal, and dropping it costs
   accuracy — even when there is a legitimate reason, moral or otherwise, to set it aside.
   The review's job is to make that trade-off explicit — name the accuracy cost of
   discarding the base rate — and leave the decision on whether to act on it to the
   forecaster or domain owner (P023).
5. **Match the performance baseline to the regime.** Before crediting or faulting a
   forecast's accuracy, classify the environment: during genuine turbulence, random guessing
   is the right comparison; during a stable regime, a simple extrapolation algorithm is. Do
   not read skill into a forecast that merely beat an easy baseline, and do not demand it
   beat an unreachable one. A regime break is far easier to identify after the fact than
   while it is happening, and confident guidance is least reliable in exactly the crises when
   demand for it peaks — treat a forecaster's composure under those conditions as no
   substitute for the right baseline comparison (P066).
6. **Default to status-quo and regime-survival continuation.** Across both short- and
   long-term horizons, treat "nothing material changes" as the single most likely outcome,
   and require any forecast of change to carry a specific, weighted case for why the status
   quo will not hold. Extend this default to an existing government or regime specifically:
   treat a bet against its survival as usually a bad bet, and require extra weight of
   evidence before accepting that its collapse or replacement is imminent (P067, P082).
7. **Calibrate expectations of forecaster performance to simple rules, not virtuosity.**
   Expect most unaided human forecasters to sit closer to random guessing or simple
   extrapolation than to a real statistical model, and to fall below even a plain
   extrapolation rule once a compelling case-based story crowds the base rate out — treat
   that as the default expectation for a forecast under review, not a surprising failure
   (P049). Where the outcome is random or near-random with a stable base rate, reward a
   deviation from that base rate only when it is diagnostically justified, not when it is
   pattern-hunting in noise dressed up as insight — and check whether the "right" reference
   population for the base rate is itself disputed (P051). Finally, remember that even
   formal statistical models beat human forecasters only modestly, because many of the
   variables in play are close to a first-order autoregressive process that a disciplined
   "mostly persistence, some reversion toward the mean" rule already captures well — judge
   the forecast against that modest, achievable ceiling, not against an assumption that skill
   can routinely do far better (P091).

## Inputs

- The forecast, probability judgment, or estimate under review, plus as much of its stated
  reasoning as is available.
- Whatever reference class or base rate is already stated, or discoverable, for the case's
  category, and whether it was actually used.
- The specific evidence behind any case-based estimate and, if known, how strongly that kind
  of evidence has historically correlated with the outcome.
- Whether the situation is closer to a stable regime or a turbulent one.
- Whether the question concerns continuation versus change of an existing state of affairs,
  policy, or government.
- Any track record or comparison baseline already used to judge the forecaster or the
  forecasting method.

## Output

Each finding follows the same four-part chain, ordered highest-impact first:

1. **Flaw** — name the specific outside-view lapse and the principle it violates (for
   example: no reference class named, a nonregressive extreme, a causal base rate discarded,
   the status-quo default ignored).
2. **Correction** — the concrete fix: state the reference-class base rate, regress the
   estimate toward it by the evidence's correlation with the outcome, reinstate a discarded
   causal base rate, or restate the estimate as "status quo, unless a specific case is made."
3. **Residual uncertainty** — what remains unknown after the correction (how strong the
   evidence-outcome correlation really is, how contested the reference class is, whether this
   is a genuine regime break) and the horizon the corrected estimate holds over.
4. **Next step** — a concrete action for the forecaster or domain owner: supply the missing
   base rate, restate the estimate as baseline-plus-regressed-adjustment, or justify the
   specific departure from the status-quo default.

At minimum, produce one finding that names a flaw, applies a correction, and states the
residual uncertainty it leaves.

## Anti-patterns to flag

- **Inside-view neglect of the base rate** — an estimate built entirely from case specifics,
  with a relevant reference-class base rate available and unused, or a valid statistical base
  rate dropped because it does not feel causal (P006, P023).
- **Nonregressive extremes** — a prediction as extreme as the evidence itself, never walked
  back toward the baseline by the evidence's real predictability; includes reading an extreme
  result's natural rebound as proof that an intervention worked (P007, P005).
- **Mismatched performance baseline** — judging a forecast against an extrapolation baseline
  during genuine turbulence, or against a random-guessing baseline during a stable regime, and
  crediting or blaming skill accordingly (P066).
- **Betting against the status quo without a specific case** — forecasting material change,
  or the fall of an existing government or regime, without the weight of evidence needed to
  overcome the default expectation of continuation (P067, P082).
- **Mechanical base-rate purism or blind deviation-chasing** — either punishing every
  departure from the base rate as an error, or crediting a colorful, pattern-based deviation
  as skill, without checking whether it was diagnostically justified or the reference
  population is itself disputed (P051).
- **Assuming forecaster virtuosity by default** — treating a fluent, case-based prediction as
  more accurate than a plain persistence-plus-regression rule with no evidence that this
  forecaster, or forecasters generally, actually beat that simple baseline (P049, P091).

## References

- `../../references/calibration-forecasting-principles-index.md` — the package's full principle
  index; cross-check every Pxxx id cited in a finding (P005, P006, P007, P023, P049, P051,
  P066, P067, P082, P091) against it.

## Provenance

Derived from P005, P006, P007, P023, P049, P051, P066, P067, P082, P091 of this package
(claims C00653, C00654, C00732, C00733, C00661, C00662, C00467, C00468, C01345, C01346,
C01421, C01422; evidence E00071, E00072, E00105, E00106, E00079, E00080, E00039, E00040,
E00346, E00347, E00399, E00400). Sources: Kahneman, *Thinking, Fast and Slow* (2011); Heuer,
*Psychology of Intelligence Analysis* (1999); Tetlock, *Expert Political Judgment* (2005) —
all `distillation-only`, paraphrased, no verbatim quotation.
