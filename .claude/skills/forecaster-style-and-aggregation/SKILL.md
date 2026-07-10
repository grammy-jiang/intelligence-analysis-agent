---
name: forecaster-style-and-aggregation
description: "Review whether a forecaster or team is cultivated and judged to build calibration, and whether multiple forecasts are aggregated well; use when assessing forecaster development or combining forecasts."
kind: skill
status: ready
provenance:
  principles:
  - P009
  - P011
  - P021
  - P029
  - P030
  - P036
  - P044
  - P060
  - P061
  - P063
  - P064
  - P070
  - P088
  claims:
  - C01223
  - C01224
  - C00915
  - C00917
  - C01013
  - C01016
  - C01089
  - C01090
  - C01474
  - C01475
  - C01064
  - C01065
  evidence:
  - E00270
  - E00271
  - E00133
  - E00134
  - E00184
  - E00186
  - E00219
  - E00220
  - E00444
  - E00445
  - E00204
  - E00205
  source_anchors:
  - e3c7c0b4e46f-c0016
  - e3c7c0b4e46f-c0000
  - e3c7c0b4e46f-c0005
  - e3c7c0b4e46f-c0009
  - 5da0a790f5ae-c0007
  - e3c7c0b4e46f-c0008
  - 5da0a790f5ae-c0012
  - e3c7c0b4e46f-c0006
  - e3c7c0b4e46f-c0007
  - e3c7c0b4e46f-c0010
  - e3c7c0b4e46f-c0017
  - e3c7c0b4e46f-c0021
  authored_from_digest: 0c6c67283657b061782ad351d28c44cbfc77a59a18bcc37831a9f9644e134f8a
---

# Forecaster Style and Aggregation

## Purpose

This skill reviews two things that sit above any single forecast: whether the *forecaster* (a
person, a team, a track record) is being cultivated and judged in a way that actually builds
calibrated judgment, and whether *several* forecasts or perspectives are being combined well into
one estimate. It checks a forecast's claimed credibility against what genuinely predicts accuracy
— practice, accountability, cognitive style, and disciplined aggregation — as distinct from
surface signals such as fame, credentials, or a single compelling story that do not. It does not
produce the forecast or the domain judgment; it reports what to trust in the forecaster and the
aggregation scheme, and what to correct.

## When to use

- The review must judge whether a forecaster, team, or track record is a credible source of
  calibrated judgment, not only whether one forecast reads as plausible.
- A claimed "great call," a public reputation, a title, or a set of credentials is being offered
  as evidence that a forecast (or its author) should be trusted.
- Several forecasts, estimates, or expert opinions need to be combined into a single number — a
  panel, an ensemble, a crowd, a market.
- A team is designing or auditing a forecasting process, tournament, or accountability structure
  and wants to know whether it will build calibration over time rather than just look rigorous.
- A question looks too hard to put a number on, and the caller wants to know whether it can still
  be quantified.
- A forecaster's or process's track record from one domain is about to be trusted in a different
  domain.

## Procedure

Work through these checks in order. Cite the governing principle inline and flag as soon as a
check fails; do not wait until the end to raise a flaw.

1. **Confirm confidence is paired with humility, not opposed to it.** A forecaster's stated
   confidence should track a settled read on the *problem's* residual complexity, not on how sure
   they feel relative to rivals. Flag a write-up that equates "I'm confident" with "my judgment
   must be right because it's mine" — a strong self-regard and genuine humility toward reality's
   complexity are meant to coexist, not to substitute for each other (P009).
2. **Confirm the forecaster is scored openly and repeatedly, not once and anonymously.** Look for
   a public, ongoing record — posted forecasts, resolved outcomes, a running accountable score.
   A track record built from a single anonymous prediction has not been tested the way an open
   tournament tests it; treat forecasting skill as a capability built and measured over repeated,
   visible rounds, and flag a review that skips straight to trusting an unscored history (P011).
3. **Discount survivorship and pedigree signals; look at cognitive style instead.** A single cited
   "great call," celebrity status, a title, or a stated ideological camp is weak-to-backwards
   evidence of accuracy: luck plus a large pool of triers produces a few lucky-looking records
   regardless of skill, real skill instead shows up as forecasts regressing toward the mean over
   time, and the one demographic factor that does correlate with a track record — fame — points
   the wrong way. Redirect the review to how the forecaster actually thinks: someone who blends
   many partial views and revises (a fox) carries a real, durable edge, largest on long-horizon
   calls inside their own domain, that a confident single-theory thinker (a hedgehog) does not.
   Flag credentials, a resume, or a school of thought offered in place of this check (P021, P030,
   P064).
4. **Confirm the level of numeracy fits the question, not the reviewer's taste for rigor.** The
   bar is comfort translating judgment into fine-grained probabilities, not a demand for an
   elaborate statistical model — most good forecasting is careful, decomposed judgment rather than
   calculation. Flag a review that dismisses a numerate-but-model-free estimate for lacking
   machinery, and equally flag an estimate that skipped numeracy altogether (P029).
5. **When a question looks unanswerable, require an explicit decomposition before accepting "we
   can't know."** The forecaster should split the question into knowable and unknowable parts,
   state the assumptions behind each part, bound the guess with roughly a 90% interval, and commit
   to explicit best guesses for what remains unknowable. A transparent, decomposed guess of this
   kind beats an intuitive hunch delivered as a black box; flag a claim of intractability that
   skipped this decomposition (P036).
6. **Credit blending over a single confident narrative.** Weighing several imperfect,
   non-redundant perspectives against one another — doing by instinct what a weighted average
   does mechanically — outperforms trusting one all-in, one-big-idea account, and it is exactly
   the confident, single-theory (hedgehog) forecasters who gain the most accuracy from being
   pulled into such a blend. Flag a process that let one confident voice override a broader
   synthesis of perspectives (P070).
7. **Check that aggregation both uses the levers that work and extremizes only when licensed.**
   The reliable levers are a prediction market, a Delphi-style structured elicitation, simple
   consensus averaging, and cultivating forecasters who are self-critical and flexible — useful
   information on a hard question is rarely concentrated in one person or method, so flag a
   process relying on a single forecaster or method when one of these was available and unused.
   Separately, pushing a pooled estimate toward 0 or 1 (extremizing) is licensed only when the
   crowd holds genuinely diverse, unshared information — it simulates what the group would
   believe if that information were fully pooled — and is not licensed for a team that already
   shares everything; flag both a shared-information crowd's estimate that was extremized and a
   genuinely diverse, unshared-information crowd's estimate that was not (P044, P060).
8. **Confirm the estimate came from the full superforecaster sequence, not a shortcut.** Check
   that the forecaster unpacked the question, separated the known from the unknown and
   interrogated every assumption, ran the outside view before the inside view, compared the
   result against others' views and a crowd-wisdom method, synthesized the inputs rather than
   picking one, expressed the result on a fine probability scale, and left room to update
   afterward. Flag a number that skipped straight to a probability without this sequence (P061).
9. **Match ambition to how much the domain rewards skill over luck.** In deep, liquid, heavily
   competed markets, even a strong forecaster is unlikely to keep beating the market — the same
   caution that favors a passive index fund over active stock-picking applies to a claimed edge in
   an efficient domain, though a shallower, less efficient market can still be beaten. Flag a
   claimed edge that has not accounted for how efficient the target domain already is (P063).
10. **Confirm calibration is not being carried across domains without fresh practice.** Calibration
    is built by practicing a specific kind of forecasting against resolved outcomes; it does not
    transfer for free to a different kind. Flag any claim that skill demonstrated in one
    forecasting domain certifies calibration in an unrelated one without a track record built and
    fed back in the new domain (P088).

## Inputs

- The forecaster's or team's track record and how it is scored (public or anonymous, repeated or
  one-off, independently resolved or self-reported).
- Any claimed evidence of skill offered in support of the forecast's credibility — a specific
  cited hit, reputation, credentials, or ideological affiliation.
- The forecasting process used: solo judgment, a structured method (decomposition, Delphi, market,
  consensus averaging), or an ensemble/crowd.
- For an aggregation review: the individual forecasts or perspectives being combined, whether they
  draw on the same information base, and whether or how they were extremized.
- The domain and horizon of the question, and whether the forecaster's demonstrated track record
  is in this same domain.

## Output

Each finding names the forecaster-style or aggregation flaw, applies the correction, states what
uncertainty remains, and ends with a concrete next step:

1. **Flaw** — the specific problem, e.g. "the estimate's credibility rests on a cited hit and
   reputation, not a scored track record."
2. **Correction** — what to do instead, tied to the governing principle, e.g. "discount the
   anecdote; ask for the open, repeated, scored record; weight the fox-like blend of views over
   the single confident narrative (P021, P064)."
3. **Residual uncertainty** — what remains unknown even after the correction, e.g. "no independent
   record yet exists for this forecaster in this domain or at this horizon."
4. **Next step** — a concrete action, e.g. "enter the forecaster into a scored process before
   relying on this call, or fall back to consensus averaging across the available panel."

Order findings highest-impact first. Never close a review without at least one such finding.

## Anti-patterns to flag

- Treating a single impressive prediction, fame, or a title as proof of forecasting skill instead
  of asking for a scored, repeated track record (P021).
- Crediting credentials, a resume, or an ideological camp as if they predicted accuracy, when the
  one demographic signal that does correlate with a record — fame — runs the wrong way (P030,
  P064).
- Confusing self-assured delivery with earned humility — "I'm confident because it's my call" —
  instead of holding both high self-regard and genuine respect for the problem's complexity (P009).
- Accepting a forecaster's credibility from a single anonymous prediction instead of requiring
  open, repeated, scored performance (P011).
- Rejecting a careful, numerate-but-simple estimate for lacking an elaborate model, or waving
  through an estimate with no numeracy at all (P029).
- Declaring a hard question unquantifiable without first demanding an explicit decomposition into
  knowable and unknowable parts (P036).
- Letting one confident, single-theory (hedgehog) voice override a blended, weighted-average
  estimate drawn from several perspectives (P070).
- Relying on one forecaster or one method when a market, a Delphi process, consensus averaging, or
  a more self-critical forecaster was available and unused (P044).
- Extremizing a crowd's pooled estimate when the crowd shares the same information, or failing to
  extremize a genuinely diverse, unshared-information crowd (P060).
- Accepting a probability that skipped the outside-view/inside-view/crowd-comparison sequence and
  jumped straight to a number (P061).
- Endorsing a claimed edge in a deep, liquid, heavily competed market without discounting for how
  efficient that market already is (P063).
- Carrying a forecaster's calibration from one domain into a different one with no fresh,
  feedback-tested record in the new domain (P088).

## References

See `../../references/calibration-forecasting-principles-index.md` for the full statements, confidence
levels, and claim/evidence links behind P009, P011, P021, P029, P030, P036, P044, P060, P061,
P063, P064, P070, and P088.

## Provenance

Derived from P009, P011, P021, P029, P030, P036, P044, P060, P061, P063, P064, P070, P088
(Tetlock, *Superforecasting: The Art and Science of Prediction*; Tetlock, *Expert Political
Judgment: How Good Is It? How Can We Know?* — distillation-only sources, paraphrased throughout).
