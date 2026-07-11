# Grounding — `source-evaluation`

Per-step traceability to the distilled corpus via the pipeline of record
(`subagent-factory/docs/intelligence-analysis/PIPELINE-grounded.md`, Step 3 row + store legs).
Loaded on demand — not on every skill invocation.

| Skill element | Source claim |
|---|---|
| Two-axis A–F / 1–6 grading scale | FM 2-22.3 (C428) |
| Evidence types, absence-of-evidence, per-hypothesis expected observables | Heuer, ACH Step 2 |
| Diagnosticity over vividness | Heuer / `analytic-method-reviewer` P013, P014 |
| Grade consistently — motivated-skepticism guardrail | method P009 |
| Deception / plantability awareness | method P010; Masterman C002, C044 |
| Evidence-quality insensitivity, vividness discount, corroboration | Kahneman / Jervis via `bias-perception-reviewer` P001, P022, P073 |
| Source-history read before grading a repeat source | Masterman C044 (source-trust-registry, cross-case store) |

Store legs (PIPELINE-grounded.md:22, :46–49):
- **⟲ store-read = `source-trust-registry`** (cross-case) — source credibility history, Masterman C044.
- **⟳ store-write = `evidence-ledger`** (per-case) — items + A–F/1–6 grades, FM C428.

Pipeline Step 3 is co-owned with the `osint-investigation` skill: that skill collects the
open-source material; this skill grades it once gathered.
