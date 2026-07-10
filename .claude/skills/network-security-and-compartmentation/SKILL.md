---
name: network-security-and-compartmentation
description: Review the structure of a controlled network for the security that keeps
  one blown agent from collapsing the rest; use when reviewing this facet of a deception
  or counter-deception case.
kind: skill
status: ready
provenance:
  principles:
  - P005
  - P007
  - P010
  - P015
  - P024
  - P054
  - P062
  - P063
  - P069
  claims:
  - C00013
  - C00019
  - C00026
  - C00027
  - C00047
  - C00048
  - C00085
  - C00106
  - C00107
  - C00126
  - C00129
  - C00139
  evidence: []
  source_anchors: []
  authored_from_digest: 5ab7080b3c9252d2378a82b0ee4585345d87da8a1990285c3e2396fbf15f2a3c
---

# Network Security And Compartmentation

## Purpose

Review the structural security of the network of agents, sources, or reporting channels
behind a deception case or an intelligence assessment — not the credibility of any
single channel, but the shape of the whole: how linked its parts are, how much decisive
weight rests on one point, and how fast a shared secret would leak as the compartment
grows. A controlled network and an analyst's own source base are built the same way, so
this skill carries the mirror question into network shape: several "independent"
reporting streams could themselves be one adversary-run channel dressed up as
corroboration, and an analyst's own collection could be exposed to feedback that lets
the target learn what is being asked and shape the answer accordingly. This skill
audits exposure, linkage, and control-claims — the credibility of any one piece of fed
material belongs to the sibling skills.

## When to use

- A deception plan or double-agent network is being structured or reviewed, and its
  compartmentation, independence, and linkage need checking before it is committed.
- An assessment or case stakes a decisive, load-bearing conclusion — or its riskiest
  deceptive material — on a single source or channel, and whether that concentration is
  safe needs checking.
- Several reporting streams are being read as independent corroboration, and whether
  they might share an undisclosed link, handler, or origin needs checking.
- A claim asserts that an entire network is understood, controlled, or independent, and
  whether that claim rests on accumulated cross-referenced evidence or on assumption
  needs checking.
- A source or channel must be dropped, silenced, or retired from the record, and
  whether the resulting gap is covered by a plausible, corroborated explanation needs
  checking.
- A compromised or doubtful link threatens to collapse confidence in the rest of the
  network, and whether it should be firewalled or cut now — rather than carried forward
  — needs checking.

## Procedure

1. Establish the object under review: the network's agents, sources, or channels; the
   links — shared handlers, routing, or origin — reported between them; and the single
   decisive conclusion or piece of material, if any, the case leans on. Fix this before
   judging whether any concentration or linkage found below is a genuine problem.
2. Check the network's parts are structurally independent rather than tied through an
   avoidable shared point — a shared handler, route, or origin lets one part's collapse
   or compromise take others down with it, and parts run in parallel long enough tend to
   reveal each other's true status regardless of design. Flag any avoidable linkage, and
   flag corroboration drawn from streams that share an undisclosed common root — the
   network's own version of a single controlled hand dressed up as several independent
   voices (P010).
3. Check that a claim the network is fully controlled, independently corroborating, or
   well understood is built from accumulating, cross-referenced evidence — one part's
   routing or reporting matching another's, or one part naming another as reliable —
   rather than simply asserted. Flag premature certainty about the network's shape,
   whether that is the plan's own claim about its agents or the assessment's own claim
   that its sources are independent (P015).
4. When a decisive conclusion, or the riskiest deceptive material, rests on a single
   "most trusted" channel, check that a lesser channel exists for corroboration or as a
   hedge — even the most trusted channel can fail without warning, and no judgment or
   operation should rest on one. Flag any decisive call staked on an unbacked single
   source (P005).
5. Check that the decisive fact or crown-jewel material has not been exposed to a
   channel whose loyalty or control cannot be fully guaranteed — particularly one
   already in renewed contact with the opposing side or an outside audience — since such
   a channel may be pressured, may act unpredictably, and can carry the sensitive fact
   back out. Flag any crown-jewel exposure to an uncertain-loyalty channel (P007).
6. Check whether the channels feeding this case are aware of one another's true
   status, role, or conclusions in a way that could let them misjudge each other,
   cross-contaminate, or converge in a way that only looks like independent agreement.
   Separately, when a channel must be written out of the record, check the gap is
   covered by a plausible, corroborated explanation rather than left unexplained, and
   that the wider structure routes tasking through one accountable point rather than
   many independently steerable ends (P054, P024).
7. Weigh the network's exposure as a function of its size: check whether the case has
   considered that a secret or compartment shared with a growing number of people leaks
   with near-certainty over time, that discovery of the compartment's true scale would
   cast suspicion on every item inside it, and that a link already in doubt should be
   firewalled or cut now rather than carried forward on hope (P062, P063).
8. Check that the riskiest material or highest-exposure tasking sits with the
   network's most isolated, least-connected, most-expendable parts, and flag the
   reverse — a valuable or well-connected channel carrying the network's riskiest
   exposure (P069).
9. Emit findings highest-impact first, in the review's standard name-the-flaw /
   correction / residual-uncertainty / next-step format.

## Inputs

- The network, case, or evidence chain under review — its agents, sources, or
  reporting channels, and any links, shared handlers, or common origins reported
  between them.
- The decisive conclusion or crown-jewel material the case rests on, and which
  channel(s) it is attributed to.
- Any claim that the network is fully controlled, independent, or well understood, and
  the cross-referenced evidence offered to support it.
- The history of who has known the secret or compartment, how that number has grown,
  and whether any channel has already been silenced, dropped, or shows signs of
  compromise.
- The relative value, connectedness, and expendability of each channel, and which risk
  or tasking each currently carries.
- For the mirror read: whether the material under review could itself be corroboration
  manufactured by a single controlled or compromised network rather than genuinely
  independent sources.

## Output

Per finding: name the network-security flaw (harmful linkage between reported-
independent parts, premature certainty about a network's control or independence, a
decisive conclusion staked on one channel, crown-jewel material exposed to an
uncertain-loyalty channel, unmanaged cross-channel awareness, an unexplained gap where a
channel was silenced, an unweighed leak-risk as the compartment grows, or risk
misallocated onto a valuable or well-connected channel), apply the correction (separate
or firewall the linked parts, require cross-referenced evidence before crediting a
control or independence claim, back the decisive channel with a corroborating one,
compartment the crown-jewel material, manage what channels know of each other and of
the case, retire a channel behind a plausible corroborated cover story, cut the
compromised link now, or reroute risk onto isolated and expendable channels), state the
residual uncertainty the correction leaves — including whether the reviewed network
could itself be adversary-controlled — and end with a concrete next step. Order
findings highest-impact first. Never close a review with a bare go/no-go in place of
this structure.

## Anti-patterns to flag

- Crediting several reporting streams as independent corroboration when they share an
  undisclosed handler, route, or origin (P010).
- Asserting a network is fully controlled, independent, or understood without the
  accumulating cross-referenced evidence to back it (P015).
- Staking a decisive conclusion, or the riskiest deceptive material, on a single "most
  trusted" channel with no back-up for corroboration (P005).
- Exposing crown-jewel material to a channel whose loyalty or control cannot be fully
  guaranteed, especially one in renewed contact with the opposing side (P007).
- Letting channels within a case become aware of each other's true status or
  conclusions, risking mutual misjudgment or manufactured-looking convergence (P054).
- Leaving a silenced or dropped channel as an unexplained gap instead of a plausible
  corroborated cover story, or letting a network's sub-channels be steered
  independently instead of through one accountable point (P024).
- Ignoring that a compartment shared with a growing number of people leaks with
  near-certainty, that its exposed scale would taint every item inside it, or carrying
  forward a link already in doubt instead of firewalling it now (P062, P063).
- Routing the network's riskiest exposure through its most valuable or best-connected
  channel instead of its most isolated and expendable one (P069).

## References

See `../../references/deception-detection-principles-index.md` for the full principle
catalogue. For adjacent concerns, see the sibling skills:
`turning-and-running-a-controlled-agent` covers the day-to-day handling of one channel
once it sits inside the network shape checked here; `assessing-enemy-trust-and-belief`
reads how far the adversary actually believes in a channel this skill has checked for
structural exposure; `counter-deception-and-the-mirror` carries the broader mirror
discipline that this skill applies specifically to network shape — whether the
reviewed source network could itself be adversary-controlled.

## Provenance

Derived solely from P005, P007, P010, P015, P024, P054, P062, P063, and P069 (J. C.
Masterman, *The Double-Cross System*; distillation-only). The frontmatter provenance
block above lists the exact principle and claim ids, which resolve into
`principles/principles.yaml` and `analysis/claims.jsonl`.
