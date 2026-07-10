---
name: source-evaluation
description: "Grade an evidence item or source before it drives a judgment — classify what kind of evidence it is, rate source reliability (A–F) and information credibility (1–6) independently, weight it by diagnosticity rather than vividness, seek corroboration, check for deception, and record the absence of expected evidence. Invoke when weighing raw reporting into an analysis. Pairs with the bias-perception and analytic-method reviewers, which check the grading."
---

# Source Evaluation

## Purpose

Turn raw reporting into a **graded EvidenceItem** an analysis can rely on: what kind of evidence it is, how
reliable the source and how credible the information (rated on two independent axes), how *diagnostic* it is
between hypotheses, whether it is corroborated, whether it might be planted, and what expected evidence is
**absent**. This is the *doing* skill for Step 3 of the `structured-analysis` workflow; the bias-perception
and analytic-method reviewers independently check the result.

## When to use

- You are gathering evidence for an analysis and must weigh each item before it feeds the ACH matrix.
- A single dramatic report is dominating discussion and you need its actual evidentiary weight.
- The cost of error is high and a source could be manipulated.

## When not to use

- Producing the substantive judgment itself (that is the analysis, not the grading).
- Critiquing an existing grade for bias or method — that is the reviewer subagents' job.

## Procedure

1. **Classify the evidence type** *(Heuer, ACH Step 2)*. Go beyond concrete reporting to record: (a) your own
   assumptions and deductions feeding the read; (b) for each hypothesis, "if it were true, what should I see —
   or NOT see?"; and (c) the **absence of expected evidence** — the dog that did not bark.
2. **Grade on two independent axes** *(FM 2-22.3, C428)*. Rate the **source's reliability A–F** (A reliable →
   E unreliable → F cannot be judged) and the **information's credibility 1–6** (1 confirmed → 5 improbable →
   6 cannot be judged) **separately** — a reliable source can carry doubtful information and vice versa. State
   each as a judgment with its reason.
3. **Grade consistently, regardless of fit.** Do not rate evidence that cuts against your favoured hypothesis
   more harshly than evidence that supports it — that is motivated skepticism, holding quality constant and
   scrutinising only the dissonant *(method P009)*.
4. **Weight by diagnosticity, not vividness.** Evidence consistent with *several* hypotheses is
   non-diagnostic — it feels informative but does not discriminate *(method P014, P013)*. Discount vivid,
   firsthand, anecdotal items that would otherwise outweigh duller but more valuable statistical evidence
   *(bias P001)*; treat worthless or unverified information the same as an **absence** of information, do not
   process it as true *(bias P022)*.
5. **Seek corroboration.** Aggregate diverse, **independent** sources rather than leaning on one — combine
   many views so idiosyncratic error cancels; a single uncorroborated account is weak however vivid *(bias
   P073)*.
6. **Check for deception.** Where the subject controls the very footprint being collected and the cost of
   error is high, a single uncorroborated, conveniently-timed, alarming item may be **planted** — grade it for
   plantability, not only reliability, and reject single-outcome reliance when deception is a serious
   possibility *(method P010; Masterman C044/C002)*. Source vetting itself belongs to the owning HUMINT
   authority, not this skill.
7. **Record the absence.** Note, per hypothesis, the expected observable that is *missing*, and carry it as
   evidence in its own right into the matrix *(Heuer, ACH Step 2)*.

## Inputs

- The raw item/report; the source and what is known of it; the hypothesis set it will be weighed against.

## Output

A graded **EvidenceItem**: the item, its evidence type, **reliability A–F / credibility 1–6** (each with a
reason), a diagnosticity note (which hypotheses it does and does not discriminate), corroboration status, a
deception flag if warranted, and the per-hypothesis expected / absent observables. Never a bare "reliable
source says X" without the two grades and the diagnosticity read.

## MVP note (Phase 1)

No persistent **source-trust registry** yet (Phase 3): you cannot read a source's credibility history to
inform the grade. Grade from what is known now, say so, and note that repeated use of the same source should
later be tracked *(Masterman C044)*.

## Grounding

Method traces to the distilled corpus via the pipeline of record
(`docs/intelligence-analysis/PIPELINE-grounded.md` Step 3): the A–F / 1–6 grading scale is FM 2-22.3 (C428);
evidence types + absence-of-evidence + expected observables are Heuer's ACH Step 2; diagnosticity is Heuer /
`analytic-method-reviewer` P013/P014; consistent grading (motivated skepticism) P009; deception-awareness
P010 + Masterman C002/C044; evidence-quality insensitivity + vividness + corroboration are Kahneman / Jervis
via `bias-perception-reviewer` P001/P022/P073.
