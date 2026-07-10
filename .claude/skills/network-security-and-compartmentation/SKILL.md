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

# Network Security and Compartmentation

## Purpose

Review the structure of a controlled network for the security that keeps one blown agent from collapsing the rest. Deception is built on many agents, and its greatest vulnerability is linkage: agents who can deduce each other, a coup resting on one channel, or a secret so widely shared it must eventually leak. This skill checks independence, firewalling, and the disciplined restriction of the decisive material to the safest channels.

## Procedure

1. Check every agent is kept clear and independent of the others so that one blown agent does not bring down the rest and a single agent can be risked alone; allow a linkage only when unavoidable, remembering that parallel agents tend to deduce each other's status over time (P010).
2. Confirm the decisive deception restricts definite material to the most-trusted channels while lesser agents run for corroboration and confusion — because even the most trusted channel can collapse unexpectedly and no operation should rest on one (P005).
3. Compartment the crown jewels: the best secret-source intelligence is withheld from any agent who may re-enter enemy hands, since a returned agent may be coerced into betraying the association or take unforeseeable initiatives (P007).
4. Confirm control of an entire network is asserted only gradually, from secret sources and cross-references between agents, not assumed (P015).
5. Manage cross-agent knowledge: control what each of your men is allowed to believe about the others — two controlled agents unaware of each other's true allegiance can misread one another and escalate enough to blow both — and retire a notional subagent positioned to observe what you must not report (P054, P024).
6. When a linked asset could collapse a deception midway, consider terminating the compromised case at once, even withholding the best channel from the operation, run the riskiest deceptions through the most expendable least-linked agents, and remember a secret shared among many will inevitably leak (P063, P069, P062).

## Principles to apply

Each rule below is a promoted principle of this package; cite its ID in a finding.

- **P005** (high) — For the decisive deception, restrict definite deception material to your most-trusted channels while keeping lesser agents running for corroboration and confusion, because even the most trusted channel can collapse unexpectedly and no operation should rest on one.
- **P007** (high) — Compartmentalise your best secret-source intelligence from any agent who will re-enter enemy hands, because a returned agent may be coerced or persuaded into betraying your association and may take unforeseeable initiatives whose loyalty you can never be certain of.
- **P010** (high) — Keep every agent clear and independent of the others, so that one blown agent does not bring down the rest and a single agent can be risked alone; allow a linkage only when it cannot be avoided, and remember that agents run in parallel tend to deduce each other's status over time.
- **P015** (high) — Confirm that you control an entire enemy network only gradually, by accumulating evidence from secret sources and cross-references between agents, such as the enemy routing payments or emergency lifelines through your controlled men or one agent naming another as his best.
- **P024** (high) — Retire a notional subagent positioned to observe something you must not report by giving him a plausible illness or death backed by real corroboration such as a planted obituary, and structure a notional network so subagents report outward but all receive their tasking through the controlled head.
- **P054** (high) — Manage what each of your controlled men is allowed to believe about the other, because two controlled agents unaware of each other's true allegiance can misread one another and escalate dangerously enough to blow both.
- **P062** (high) — Recognise that a secret shared among many people will inevitably leak given enough time; the growth of an operation multiplies its exposure, and if the enemy learns the scale of your double-cross system he will suspect every agent.
- **P063** (high) — When a linked asset could collapse a deception midway, consider terminating the compromised case at once and even withholding your best channel from the operation, to firewall the rest of the network.
- **P069** (high) — Use your most isolated, least-connected, and most-expendable agents for the riskiest deceptions, because their collapse will not bring down the network; keep valuable and linked agents away from high-risk lies.

## Anti-patterns to flag

- Resting a decisive coup on a single channel with no independent corroboration.
- Feeding the best secret intelligence to an agent who may re-enter enemy hands.
- Linking agents so that blowing one exposes the network, or assuming full control before secret sources confirm it.

## Output

One finding per problem surfaced above, highest-risk first, each naming the tradecraft flaw and the principle it violates, the correction, the residual uncertainty (including who could still be deceiving whom), and a concrete next step. Never issue the caller's go/no-go: the corrected judgment and the residual risk are handed back to the operation's owner.

## Review checklist

For the case under review, confirm each applicable principle holds; when one is violated, name the flaw, the correction, and the residual uncertainty.

- [ ] (P005) For the decisive deception, restrict definite deception material to your most-trusted…
- [ ] (P007) Compartmentalise your best secret-source intelligence from any agent who will re-enter…
- [ ] (P010) Keep every agent clear and independent of the others, so that one blown agent does not…
- [ ] (P015) Confirm that you control an entire enemy network only gradually, by accumulating…
- [ ] (P024) Retire a notional subagent positioned to observe something you must not report by…
- [ ] (P054) Manage what each of your controlled men is allowed to believe about the other, because…
- [ ] (P062) Recognise that a secret shared among many people will inevitably leak given enough…
- [ ] (P063) When a linked asset could collapse a deception midway, consider terminating the…
- [ ] (P069) Use your most isolated, least-connected, and most-expendable agents for the riskiest…

## References

- [`../../references/deception-detection-principles-index.md`](../../references/deception-detection-principles-index.md) — the package-wide index of every promoted principle, with its full statement, confidence, and grounding. Read it rather than paraphrasing from memory.

## Provenance

This skill's checks derive from P005, P007, P010, P015, P024, P054, P062, P063, P069, grounded in J. C. Masterman's *The Double-Cross System*; the frontmatter `provenance` block lists the exact principle and claim ids, which resolve into `principles/principles.yaml` and `analysis/claims.jsonl`.
