---
name: governance-approval-and-organization
description: Review the organisation, policy, and approval machinery around a deception
  system; use when reviewing this facet of a deception or counter-deception case.
kind: skill
status: ready
provenance:
  principles:
  - P006
  - P016
  - P017
  - P025
  - P027
  - P028
  - P033
  - P042
  - P049
  - P056
  - P076
  - P079
  - P092
  claims:
  - C00017
  - C00022
  - C00045
  - C00046
  - C00053
  - C00055
  - C00056
  - C00058
  - C00065
  - C00066
  - C00067
  - C00071
  evidence: []
  source_anchors: []
  authored_from_digest: 7e4ae026532be698cb68ba4055bfa26a9f9553fd5ecd96297f56c34d404d0edc
---

# Governance Approval And Organization

## Purpose

Review the organisational and approval signatures behind a suspected deception, and — in the
same pass — the governance hygiene of the analyst's own counter-deception assessment. A
deception large enough to matter over time needs coordinated top-level direction, differentiated
staffing, and a single approval gate that keeps every signal it sends consistent; the presence,
absence, or visible seams in that coordination are themselves evidence about who is running the
operation and how centrally it is controlled. This skill audits an evidence chain for those
adversary coordination signatures, and separately audits the reviewing team's own case policy,
approval routing, and integrity for the same discipline it is judging the adversary against —
never for how to build a deception organisation.

## When to use

- An assessment claims a run of adversary activity is a single coordinated deception, and the
  case for "coordinated" rests on top-level direction the scattered pieces could not plausibly
  have originated on their own.
- Evidence from several channels or incidents needs reading for whether one central approval
  authority sits behind all of it — a consistent, disciplined signal — or whether it instead
  looks like several uncoordinated sources acting on their own.
- A suspect or controlled channel's pattern of use needs judging: is it being husbanded for a
  long-game strategic effect, or is some other unit spending it for a quick tactical win at the
  cost of its future credibility?
- A team is about to release a specific piece of intelligence, a corrective finding, or a
  judgment about a channel to stakeholders, and wants that release weighed case by case rather
  than left to whoever happens to hold the case.
- A D&D case review, or the policy behind it, was set by one officer or analyst alone, and needs
  checking against the right level of authority, the right board, and genuine cross-team
  cooperation.
- A reviewer is sitting on a significant, unwelcome deduction and hesitating to raise it, or an
  approval step has hardened into a body that only ever blocks and never enables, and the review
  process itself needs auditing before its output is trusted.
- A D&D capability, review board, or approval model is being stood up for a new theatre, team, or
  case load, and wants checking against replicating a model that already works rather than
  routing everything back through one far-off decision point.

## Procedure

1. Test whether a claimed "coordinated adversary deception" really shows the top-level direction
   that large-scale deception depends on, rather than assuming coordination just because several
   signals point the same way. Ask what single directing authority the scattered local activity
   would have to be answering to, and — if none is evidenced — flag the finding as unconfirmed:
   it may be coincidence, or several uncoordinated actors, rather than one strategic hand (P017).
2. Look for the signature of a single approval gate in the traffic or record under review: a
   centrally-run deception disciplines every outgoing signal through one documented sign-off, so
   a consistent pattern across channels supports central control while a documented
   split-authority pattern — or none at all — argues against it. Apply the identical check to the
   reviewing team's own outgoing findings: they should reach the customer through one documented
   approval, not piecemeal (P033).
3. Where governance is visible — the adversary's apparatus or the reviewing team's own — check
   for a two-layer structure: a senior board with final sign-off authority, and a standing
   working committee, spanning more than one department and including a non-military approving
   voice, that actually handles day-to-day clearance and liaison. Its presence signals a
   resourced, sanctioned effort; its absence on the reviewing side is a gap to close before
   trusting the review's own output (P028).
4. Check whether the record shows the kind of functional differentiation a working apparatus
   needs: policy and accept-or-reject decisions kept apart from day-to-day case handling, from
   technical channel management, from records, and from exploiting what comes back. A
   disciplined, resourced effort and an opportunistic one leave different fingerprints — and the
   reviewing team should keep the same separation itself, so no single function's blind spot goes
   unchecked (P006).
5. Test whether a genuine-seeming, sometimes costly disclosure reaching the reviewed side through
   a suspect channel was examined as a possible calculated release, weighed case by case by
   whoever knows the asset's standing together with whoever holds the technical or subject
   expertise, rather than accepted at face value as proof of good faith. Apply the same joint,
   case-by-case weighing before the reviewing team releases its own finding or judgment outward
   (P016).
6. Confirm case policy for the matter under review was set at the section or board level rather
   than by the single officer or analyst running the case: unchecked ownership breeds an
   outsized personal stake in one case's cleanliness, which is not the same thing as what serves
   the wider system it sits inside (P025).
7. Where the channel or asset under review serves a deception purpose rather than plain
   intelligence collection, check whether it is being kept multi-purpose and husbanded for a
   long-game strategic payoff by whoever owns it, walled off from any unit that would burn it for
   a quick tactical win. Run this way, a channel protects its own long-term credibility on either
   side of the deception; run the other way, it is a candidate for premature exposure (P027).
8. Check for the inter-departmental or inter-service cooperation a genuinely coordinated effort
   requires: its visible presence in the record supports a claim of centralised adversary
   direction, and its absence argues against one. Separately, check the reviewing team is not
   siloed in a way that would blind it to the very coordination it is trying to detect (P049).
9. Where a governance body is visible, weigh whether its members actually put the shared
   objective ahead of their own department's turf and thrash out decisions by discussion rather
   than a headcount vote — that habit of mind, not a tidy charter, is what makes an imperfect
   structure work, and it is what the body should be judged by (P056).
10. Check every officer or analyst on the reviewing side for freedom from profit motive,
    prestige-seeking, or any personal stake that could bend a finding — treat this as the
    review's own first hygiene test. By the same logic, self-interest is also the likeliest crack
    to work loose in the adversary's own personnel (P042).
11. Confirm a reviewer who reached a significant, uncomfortable deduction actually raised it to
    whoever needed to hear it, instead of staying quiet from self-doubt or fear of pushback
    (P076); and confirm the approval step has not calcified into a body that only ever says no,
    with nothing it actively helps move forward (P079).
12. Where a D&D governance or approval model is being extended to a new theatre, team, or growing
    case load, check whether it mirrors an approach already shown to work rather than routing
    every new case back through one overloaded, far-off decision point (P092).
13. Emit findings highest-impact first, each in the flaw / correction / residual-uncertainty /
    next-step format set out below.

## Inputs

- The case file, assessment, or evidence chain under review, including who is credited with
  directing it and at what level of authority its key decisions were made.
- The record of approvals on outgoing traffic, or on the finding being released: who signed off,
  at what tier, and whether that sign-off is documented in writing.
- Any staffing or organisation description of the apparatus under review, and of the reviewing
  team itself — who covers policy, case handling, technical/channel management, records, and
  exploitation of what comes back.
- The history of disclosures or releases through the channel or in the assessment, so
  case-by-case profit-and-loss reasoning can be checked rather than assumed.
- Evidence of cross-department or cross-service involvement — or its conspicuous absence —
  bearing on the coordination claim under review.
- A record of whether a reviewer's dissenting or unwelcome deduction was raised, and how the
  approval step responded to the risk it flagged.

## Output

Per finding: name the governance or approval flaw and the principle it violates, apply the
correction (route the finding through the documented single gate, set policy at the right level,
restore the two-tier board-and-committee structure, separate a channel's long-term owner from its
short-term spender, replicate a working model instead of centralising further), state the
residual uncertainty the correction leaves — including who could still be deceiving whom, and
what coordination remains unconfirmed — and end with a concrete next step. Order findings
highest-impact first. Never close a review with a bare go/no-go in place of this structure; the
operation's owner makes that call.

## Anti-patterns to flag

- Reading a run of coincidental or scattered adversary activity as one coordinated deception with
  no top-level direction the pieces could plausibly be answering to (P017).
- Crediting a single controlled channel or a two-tier governance structure on evidence that is
  actually inconsistent, undocumented, or shows no single-authority sign-off (P033, P028).
- A record with no differentiation between who sets policy, who handles the case, who runs the
  technical or comms side, who keeps records, and who exploits what comes back — on either side
  of the case (P006).
- Taking a genuine-seeming, sometimes costly disclosure at face value as proof of a channel's
  good faith, without checking whether it reads as a calculated case-by-case release (P016).
- A single officer or analyst setting case policy out of attachment to their own record, instead
  of routing it to the section or board level (P025).
- Treating a channel's long-term strategic value and its short-term tactical use as
  interchangeable, burning a patiently-built asset for a quick win, on either side of the
  deception (P027).
- Assuming coordination is present without checking for the inter-departmental or inter-service
  cooperation a genuinely coordinated effort requires — or letting the reviewing team's own
  siloing blind it to the coordination it is looking for (P049).
- Crediting a governance body's soundness to a clean charter rather than checking whether its
  members actually put the shared goal ahead of department turf (P056), or overlooking
  self-interest, profit, or prestige as the likeliest exploitable flaw on either side (P042).
- A reviewer staying quiet about a significant, uncomfortable deduction, or an approval step that
  has become a body that only ever says no and never actively enables the mission (P076, P079).
- Routing a growing review or approval workload back through a single overloaded hub instead of
  replicating a governance model already proven to work (P092).

## References

See `../../references/deception-detection-principles-index.md` for the full principle
catalogue. For adjacent concerns, see the sibling skills: `network-security-and-compartmentation`
covers the compartmentation this governance approves traffic across; `strategic-stewardship-and-timing`
covers the top-level strategic direction this coordination signature serves;
`counter-deception-and-the-mirror` covers whether the reviewing side itself is being deceived,
which this skill's own-process checks feed into.

## Provenance

Derived solely from P006, P016, P017, P025, P027, P028, P033, P042, P049, P056, P076, P079, and
P092 (J. C. Masterman, *The Double-Cross System*; distillation-only). See the frontmatter
`provenance` block above for the full principle and claim id list, which resolve into
`principles/principles.yaml` and `analysis/claims.jsonl`.
