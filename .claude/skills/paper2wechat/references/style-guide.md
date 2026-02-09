# Style Guide

Use this reference only when selecting or validating style tone.
Default workflow: let Agent decide final style, using script signals as evidence.

## Style Selection

| Style | Use When | Writing Focus | Avoid |
| --- | --- | --- | --- |
| `academic-science` | User asks for rigor, methods, reproducibility, theory | Assumptions, experiment design, evidence chain | Marketing tone, exaggerated claims |
| `academic-tech` | User asks for engineering implementation, system design, developer takeaways | Architecture, trade-offs, complexity, deployment hints | Overly abstract discussion |
| `academic-trend` | User asks for frontier direction, strategic impact, future implications | Paradigm shift, ecosystem impact, next 1-3 year outlook | Groundless hype |
| `academic-applied` | User asks for business/application value, ROI, practical scenarios | Use cases, cost/benefit, rollout constraints, KPIs | Pure theory without application |

## Quick Mapping Hints

- “严谨/理论/可复现/方法细节” -> `academic-science`
- “工程/架构/实现/开发者” -> `academic-tech`
- “趋势/前沿/未来/战略影响” -> `academic-trend`
- “落地/业务/应用/ROI/成本” -> `academic-applied`

Default to `academic-tech` when user intent is ambiguous.

## Agent-Driven Decision Policy

1. User explicitly specifies style: use user style.
2. User does not specify style: read `detect_style.py --json` output.
3. If `confidence_band=high`: usually pick top-1 style.
4. If `confidence_band=medium|low`: pick top-1/top-2 by content fit, readability, and audience.
5. If top-2 close: allow hybrid style (example: `academic-tech + academic-applied`).

## Style Axes (1-5)

Use these axes to tune writing even when keeping one label:

- `rigor`: theory depth, assumptions, proof strictness
- `engineering`: implementation detail, system trade-offs, deployment focus
- `trend`: frontier context, ecosystem impact, future implications
- `applied`: business value, KPI/ROI, rollout constraints

When a paper spans multiple dimensions, keep one primary label and tune paragraph emphasis by axes.

## Content-Based Signals

Use these paper-content signals (title, abstract, sections, captions):

- `academic-science`: theorem/proof/convergence/ablation/reproducibility density is high.
- `academic-tech`: architecture/pipeline/implementation/latency/deployment signals dominate.
- `academic-trend`: frontier/foundation model/multimodal/agent/paradigm signals dominate.
- `academic-applied`: business/clinical/industry/cost/ROI/case-study signals dominate.

If top-1 and top-2 are close, prefer readability and audience fit over strict label purity.

## Style Validation Checklist

- Tone matches reader intent.
- Paragraph depth matches requested audience.
- Key metrics and caveats are preserved.
- Headings remain scannable in WeChat.
- Wording does not drift into another style.
- If hybrid style is used, transitions are natural and not contradictory.
