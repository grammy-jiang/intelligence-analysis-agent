---
name: probabilistic-judgment-and-calibration
description: Audits a stated probability or forecast for coherence, aggregation, and calibration; invoke also to advise on or compare aggregation approaches before one is finalized.
kind: skill
status: ready
provenance:
  principles:
    - P005
    - P012
    - P034
    - P035
    - P044
    - P050
    - P068
  claims:
    - C00023
    - C00024
    - C00025
    - C00026
    - C00027
    - C00028
    - C00029
    - C00030
    - C00031
    - C00032
    - C00582
    - C00583
  evidence: []
  source_anchors: []
---

# Probabilistic Judgment And Calibration

## Purpose

Audit whether a probabilistic judgment or forecast is internally coherent and properly
aggregated: whether its probabilities obey the formal rules for combining exclusive and
independent events, whether an outside view (a base rate) and an inside view (case-specific
investigation) were genuinely synthesized rather than one silently overriding the other, whether
disagreement among independent estimates was treated as signal rather than smoothed away, and
whether confidence rose only as independent evidence actually converged. When no number yet
exists, the same principles drive a short advise-or-compare recommendation on which aggregation
or coherence approach fits the caller's problem. This skill audits the coherence and aggregation
mechanics behind a probabilistic claim — not the domain content of the forecast, and not the
scoring of its track record once the outcome resolves.

## When to use

- A probability or forecast is stated as a single number, or a set of them, and needs a formal
  coherence check — do the additive, multiplicative, total-probability, and updating rules hold,
  or is there hidden sub-additivity (P068).
- An estimate was assembled from several independent judges' or advisors' inputs, and it is
  unclear whether their spread was synthesized as signal or smoothed away as noise (P035).
- An estimate blends a base rate with case-specific digging, and it is unclear whether the inside
  view was investigated as a real hypothesis or merely asserted alongside the outside view (P034).
- A judgment or forecast reads as deliberately cautious, and it needs checking whether that
  caution reflects a genuinely asymmetric cost between the two error types or an unrevisited
  "right mistake" defense, and whether an outside-view input needs adjusting for a known source
  bias (P012).
- The process that produced the judgment needs checking for organized quality control — distinct
  framing, evidence-collection, and reflection stages, with a shared vocabulary of biases
  available for constructive criticism (P005).
- A polarized dispute over a probabilistic judgment could be settled by a concrete, testable
  forecast, and it is unclear whether adversarial collaboration is the right way to resolve it
  (P044).
- The caller is choosing how to aggregate several inputs, or which coherence approach to run, and
  has not yet produced a number to review — a recommendation or comparison among candidate
  approaches is wanted instead (P034, P035, P044, P050).

## Procedure

1. Fix what is under review: a stated probability, forecast, or judgment together with its
   supporting reasoning (review branch, steps 2-8), or a decision about which aggregation or
   coherence approach to use before a number exists (advise/compare branch, step 9).
2. Check that the judgment passed through organized quality control rather than a single unaided
   pass: framing the problem, collecting the evidence, and a distinct reflection-and-review
   stage, with a shared vocabulary of biases available to invite constructive criticism rather
   than left as vague unease (P005).
3. If the judgment leans deliberately cautious, confirm the caution is licensed by a genuinely
   asymmetric cost between the two error types, not a "right mistake" defense that is never
   revisited once evidence accumulates; confirm any outside-view input has been adjusted for a
   known systematic bias in its source, such as social-desirability effects in polling data
   (P012).
4. Where the estimate blends an outside view (base rate) with case-specific detail, confirm the
   inside view was investigated as a hypothesis argued for and against — an investigation, not an
   amble — and that the two were merged into one estimate rather than the inside view silently
   overriding the base rate (P034).
5. Where multiple independent estimates feed the judgment, confirm their disagreement was treated
   as a signal to weigh, not noise to explain away: flag a suspiciously unanimous read as a
   possible groupthink symptom, and confirm the synthesis is a respect-weighted average of the
   spread rather than a retreat to a 50% ignorance prior or a demand for false consensus (P035).
6. If a polarized dispute over the judgment could be tested by a concrete forecast, check whether
   it was — or should be — resolved through adversarial collaboration: opposing sides and a
   trusted moderator jointly designing a precise, benchmarked, time-bound question, with a split
   decision accepted as a legitimate outcome rather than papered over (P044).
7. Confirm any stated rise in confidence tracks independent evidence, methods, or experts actually
   converging (multimethod triangulation), rather than the same view being repeated or restated
   by more voices (P050).
8. Run the four formal coherence checks against the stated probabilities: the additive rule for
   mutually exclusive events, the multiplicative rule for independent events, the
   total-probability form of Bayes's rule, and Bayesian updating on the stated evidence; flag any
   sub-additivity — exhaustive alternatives whose probabilities sum to less than one — as a
   coherence violation (P068).
9. Advise/compare branch: when the caller is choosing an aggregation or coherence approach rather
   than presenting a finished number, recommend or compare among synthesizing outside and inside
   views (P034), a respect-weighted average of independent estimates (P035), and adversarial
   collaboration for a polarized, testable dispute (P044); name which fits the stakes, the degree
   of disagreement, and how independent the inputs are, and note that confidence should rise only
   as the chosen approach's inputs actually converge (P050).
10. Emit findings, or the recommendation/comparison, highest-impact first, in the output contract
    format below.

## Inputs

- The stated probability, probabilities, or forecast under review, or — for the advise/compare
  branch — the decision the caller is facing and the candidate approaches.
- Whether the estimate rests on a single judge or synthesizes multiple independent inputs, and
  what those inputs are.
- The base-rate or outside-view reference class used, if any, and the case-specific (inside-view)
  reasoning offered alongside it.
- Any cost asymmetry cited to justify a cautious call, and whether an input carries a known
  systematic bias (for example, social-desirability effects).
- Whether the judgment, or the process that produced it, passed through distinct framing,
  evidence-collection, and review stages.
- For a polarized dispute, both sides' positions and whether a concrete, time-bound forecast could
  adjudicate between them.

## Output

Review mode — per finding: name the coherence, aggregation, or process flaw (sub-additive
probabilities, an unweighed or artificially unanimous aggregation of independent estimates, an
unexamined "right mistake" defense, a missing quality-control stage, an untested polarized
dispute), apply the principle(s) by ID, name the correction, state the residual uncertainty the
correction leaves, and end with a concrete next step. Order findings highest-impact first. Never
state what the probability itself should be — substitute only a coherence, aggregation, or process
finding for the analyst's own estimate.

Advise/compare mode — when the caller is choosing an approach rather than presenting a finished
number: a recommendation, or a comparison across candidate approaches, naming the principle(s) it
rests on, why it fits the caller's stakes and degree of disagreement, and the residual uncertainty
it still leaves. Never let this substitute for the review once a number exists.

## Anti-patterns to flag

- A judgment delivered as a single unstructured pass, with no separate framing,
  evidence-collection, and reflection stage, and no shared vocabulary of bias terms offered for
  others to push back with (P005).
- A cautious or hedged call defended as "the right mistake to make" with no stated asymmetry
  between the two error types, or a caution never revisited as evidence accumulates; an
  outside-view input taken at face value despite a known systematic bias in its source (P012).
- An inside-view case asserted once and merged with the outside view without ever being tested
  against the reasons it might be wrong — a hypothesis stated, not investigated (P034).
- Independent estimates folded into one number by seeking consensus or discarding outliers,
  instead of a respect-weighted average that treats their spread as signal; or unanimous agreement
  accepted at face value with no check for groupthink (P035).
- A polarized, testable dispute left unresolved or settled by authority instead of a precise,
  benchmarked, time-bound forecast run through adversarial collaboration; a split outcome from
  that process treated as a failure rather than an accepted result (P044).
- Confidence in a judgment rising because the same view was repeated by more voices, rather than
  because independent methods, evidence, or experts actually converged on it (P050).
- A probability set presented as coherent when it is sub-additive — exhaustive, exclusive outcomes
  whose probabilities sum to less than one — with no additive-rule, multiplicative-rule, or
  updating check ever run (P068).

## References

See `../../references/analytic-method-principles-index.md` for the full principle catalogue. For
adjacent concerns, see the sibling skills: `competing-hypotheses-and-diagnostic-evidence` for
hypothesis-set completeness and evidence diagnosticity, `structured-analytic-techniques` for which
technique to run and how to sequence it, and `analytic-collaboration-training-and-process` for the
wider training and institutional-process context adversarial collaboration sits within. Scoring a
forecast's track record once it resolves, and auditing the full mechanics and honesty of a
specific Bayesian update once new evidence has arrived (P068's fourth coherence rule), are the
full remit of the sibling subagent `calibration-forecasting-reviewer` (see its
`forecast-scoring-and-evaluation` and `bayesian-belief-updating` skills); this skill covers only
the method-side coherence and aggregation hygiene an analytic review or advisory here requires.

## Provenance

Derived solely from P005, P012, P034, P035, P044, P050, and P068 (A Tradecraft Primer —
Structured Analytic Techniques; Thinking, Fast and Slow; Superforecasting; Expert Political
Judgment — all distillation-only; see the frontmatter above for the full claim, evidence, and
source-anchor list).
