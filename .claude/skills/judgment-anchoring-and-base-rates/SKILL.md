---
name: judgment-anchoring-and-base-rates
description: Audits an analytic judgment's anchors, base-rate use, and adjoining reasoning slips before the estimate drives a decision.
kind: skill
status: ready
provenance:
  principles:
  - P008
  - P020
  - P025
  - P047
  - P082
  - P101
  - P102
  - P123
  - P143
  - P180
  - P199
  claims:
  - C00003
  - C00004
  - C00005
  - C00006
  - C00007
  - C00009
  - C00132
  - C00147
  - C00148
  - C00149
  - C00157
  - C00160
  evidence: []
  source_anchors: []
  authored_from_digest: 37e77a12e8611a915c32f1e20a42f8d043b9adb84259af1d88536f9174eaa729
---

# Judgment Anchoring And Base Rates

## Purpose

Review whether a judgment's numbers behave the way a well-calibrated analyst's would: that an
estimate is not simply dragged toward whatever reference figure appeared first, that a stated
probability or a track record is read against the outcome's true base rate rather than its
surface vividness, and that a claimed correlation, an oddly specific scenario, or a big-cause
explanation survives a check for illusory correlation, the conjunction trap, and cause-effect
magnitude matching. It also probes the softer conditions that let a bad anchor or a neglected
base rate slip through unnoticed — a self-report of thoroughness standing in for genuine
hypothesis testing, an unacknowledged emotional pull, an analogy drawn from a narrow, biased
sample of past cases, and an omitted variable nobody named. This skill audits the reference
points and baseline reasoning behind a judgment or forecast, not the substantive conclusion
itself.

## When to use

- A numeric estimate, probability, or confidence range appears right after any reference
  figure — a predecessor's number, a quoted target, an opening negotiating offer, or a stated
  cap — and the adjustment away from it needs checking (P082, P102, P180).
- A judgment's difficulty, or a track record's miscalibration, is being assessed, and the
  outcome's base rate has not been used to separate an easy call from a genuinely hard one
  (P199).
- An indicator or feature is claimed to correlate with, or predict, an outcome, and it is
  unclear whether the indicator-absent cases were ever checked (P025).
- A richly detailed scenario, or a long chain of individually plausible causal steps, is being
  judged more probable than the simpler class or single step it depends on (P123).
- A large or dramatic effect is being explained by a correspondingly large, centralized, or
  deliberately coordinated cause — including two sides each reading the other's move as
  calculated escalation (P101).
- A judgment or track-record review is defended as purely objective, or it explains or
  predicts how an actor will react to a provocation, and an unacknowledged emotional pull on
  that read has not been considered (P020).
- Confidence in a judgment — or a request for more collection before deciding — rests on an
  analyst's own account of having been thorough, long having followed the issue, or being open
  to revise, rather than on an explicit hypothesis or a track record of actual past calls
  (P008).
- A lesson, analogy, or a choice between a psychological and a structural explanation is being
  drawn from a narrow, personally learned set of past cases whose representativeness has not
  been checked (P047).
- An important variable bearing on the judgment is unobserved or missing, and the write-up has
  not said whether that absence is normal or itself a signal (P143).

## Procedure

1. Establish the object under review: the number, probability, range, or comparative judgment
   being made; any reference figure — a predecessor's number, a quoted target, a negotiating
   offer, a stated cap — that preceded it; and the base rate, if known, for the outcome class.
2. Find the anchor and test any confidence range for a second, hidden anchoring pass: assume
   any number on the table — including a predecessor's earlier judgment — has anchored the
   estimate through insufficient adjustment regardless of the analyst's expertise, confirm
   that a deliberate search for reasons the anchor is wrong took place when the stakes are
   high, and reject a range built by nudging a single point estimate up and down in favor of
   one built from hard information about the plausible limits (P082, P102).
3. If a single-issue negotiated quantity or a stated cap is at issue, check whether moving
   first set an advantageous anchor, whether an outrageous opening figure was refused rather
   than matched — matching still sets the anchor — and whether the cap itself is quietly
   pulling an otherwise-modest outcome upward (P180).
4. Weigh the base rate directly: treat a base rate near zero or one as the easy case and one
   near one-half as the hardest, and use that difficulty read to diagnose which calibration
   failure — systematic over- or under-prediction, or over- or under-extremity — the judgment
   or track record actually shows (P199).
5. Test any claimed correlation between an indicator and an outcome for illusory correlation
   by requiring evidence on all four cells of the table — indicator present or absent, crossed
   with outcome present or absent — not just the co-occurrence cases; a claim such as "this
   indicator is likeliest under high-stakes conditions" is unsupported unless the low-stakes
   and negative cases were checked too (P025).
6. Flag the conjunction trap: a richly specified scenario, or a long chain of individually
   plausible causal links, is necessarily less probable than the simpler class or single link
   it is built from, however plausible each piece sounds (P123).
7. Where a big or dramatic effect is explained by a correspondingly large, centralized, or
   deliberate cause — including two sides each reading the other's move as calculated
   escalation — check for the fallacy of identity: matching cause magnitude to effect
   magnitude is valid for physical properties only, not economic or political ones, and paired
   with a tendency to see the other side as more centrally directed than it is, this is what
   feeds conspiracy-style over-reads (P101).
8. Where a judgment is defended as objective, or it explains or predicts how an actor will
   respond to a provocation, or it scores an estimative track record, check that emotion —
   which saturates cognition rather than opposing it — has not quietly shaped the read of
   attention, risk, or moral judgment; a claim of objectivity is not proof emotion was absent
   (P020).
9. Where confidence — or a request for more collection before deciding — rests on an
   analyst's self-described thoroughness or long familiarity with the issue, check whether an
   explicit hypothesis actually directed the search, since more data collection alone does not
   improve accuracy, and distrust the self-report of method: self-insight into one's own
   reasoning is unreliable, mental models are simpler than believed, and a model built from the
   analyst's actual past decisions describes them better than their own verbal account (P008).
10. Where a lesson or analogy is drawn from a small set of cases the analyst personally
    learned from — including a choice between a psychological and a structural explanation
    made on that basis — check the sample for the bias toward firsthand, career-affecting, and
    nationally consequential cases; note that a few such high-impact events get overworked as
    analogies while whatever was constant across them goes unexamined, and that verification
    is rare, so a preferred reading can stabilize before it is actually earned (P047).
11. Confirm that any variable relevant to the judgment but unobserved or missing is named
    explicitly, that alternative hypotheses about its unknown status were considered, that
    confidence was adjusted down accordingly, and that the write-up asks whether the absence
    is normal or itself a signal — people are systematically insensitive to what has been left
    out (P143).
12. Emit findings highest-impact first, each in the name-the-mechanism / correction /
    residual-uncertainty / next-step format.

## Inputs

- The estimate, probability, range, or comparative judgment under review, plus any reference
  number, prior figure, negotiating offer, or cap that preceded it.
- The outcome's base rate or reference class, if known, and any track record the judgment's
  calibration can be checked against.
- The evidence behind a claimed correlation or indicator, including the cases where the
  indicator was absent, not only where it co-occurred with the outcome.
- The scenario or causal chain as stated in full, so its specificity can be weighed against
  the simpler class or link it is built from.
- The analyst's own account of their method — how thorough, how long they have followed the
  issue — and any record of their actual past calls.
- The sample of past cases a lesson or analogy is drawn from, and how it was learned:
  firsthand or secondhand, verified or unverified.
- Any variable known to be relevant to the judgment but unobserved or missing from the
  analysis.

## Output

Per finding: name the anchoring, base-rate, or adjoining reasoning flaw (an unadjusted anchor,
an overconfident range, an unrefused negotiating anchor, a base rate ignored or misdiagnosed,
illusory correlation, the conjunction trap, cause-effect magnitude matching, an unacknowledged
emotional pull, unverifiable self-reported thoroughness, a narrow biased-sample analogy, or an
unflagged omitted variable), apply the correction the matching principle gives, state the
residual uncertainty the correction leaves, and end with a concrete next step. Order findings
highest-impact first. Never close a review with a bare corrected number in place of this
structure.

## Anti-patterns to flag

- An estimate or confidence range dragged toward a predecessor's figure, an arbitrary quoted
  number, or a single point estimate nudged up and down — with no reasoning shown for the
  adjustment and no hard information used to set the range's true limits (P082, P102).
- A negotiating position that matched an outrageous opening offer instead of refusing it, or a
  stated cap that was allowed to quietly pull an otherwise-modest outcome upward (P180).
- A probability, difficulty rating, or track-record critique that never states the outcome's
  base rate, or that calls a near-fifty-fifty call "easy" while treating a near-certain one as
  requiring special skill (P199).
- A correlation between an indicator and an outcome argued only from the co-occurrence cases,
  with the indicator-absent cases never checked (P025).
- A specific, richly detailed scenario, or a long causal chain, judged more probable than the
  simpler class or single link it depends on (P123).
- A big or dramatic effect explained by a correspondingly large, centralized, or deliberate
  cause — especially paired with reading a rival as more centrally coordinated than it is —
  with no acknowledgment that magnitude-matching holds for physical causes only (P101).
- A judgment defended as "objective" or dispassionate — especially a prediction of an actor's
  reaction to provocation, or a self-review of an estimative track record — with no check for
  the emotion that saturates cognition and is easy to miss in oneself (P020).
- Confidence justified by the analyst's own account of having been thorough or having followed
  the issue a long time — or a request for more collection before deciding — with no explicit
  hypothesis stated and no track record of actual past calls consulted (P008).
- A lesson or forecast built on a narrow set of firsthand, career-affecting, or nationally
  consequential cases, presented as generalizable without flagging that the sample is small
  and largely unverifiable (P047).
- An analysis that never names which relevant variables are unobserved, never asks whether
  their absence is itself informative, and leaves confidence unadjusted for the gap (P143).

## References

See `../../references/bias-perception-principles-index.md` for the full principle catalogue. For
adjacent concerns, see the sibling skills: `dual-process-heuristics-and-cognitive-ease` covers
the broader System-1/System-2 catalogue — availability, attribute substitution, cognitive
ease — that anchoring and base-rate neglect ride on; `calibration-and-probabilistic-estimation`
scores the granular probability once a base rate has been correctly applied here;
`historical-analogy-learning-and-hindsight` tests a flagged analogy itself for spuriousness
once its narrow, biased sample of cases has been surfaced in this skill.

## Provenance

Derived solely from P008, P020, P025, P047, P082, P101, P102, P123, P143, P180, and P199
(Heuer's Psychology of Intelligence Analysis and the CIA Tradecraft Primer; Kahneman's
Thinking, Fast and Slow; Tetlock's Superforecasting and Expert Political Judgment; Jervis's
Perception and Misperception in International Politics — all distillation-only; see the
frontmatter above for the full claim list).
