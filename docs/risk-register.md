# Risk Register

| Risk | Impact | Mitigation |
| --- | --- | --- |
| OpenAI API unavailable | Live demo could stall | Deterministic fallback emits "OpenAI unavailable, using validated fallback response." |
| GitHub Pages deploy fails | Public replay unavailable | Dashboard builds as static Vite output; replay JSONL is copied at build time. |
| Backend not running | Live mode unavailable | Replay mode is the default and needs no backend. |
| Safety concern | Judges worry about destructive automation | Mock-only execution, approval gate, protected-path block, and WhatIf review are visible. |
| Synthetic data concern | Scenario feels too artificial | Data includes SOP, history, unsafe precedent, escalation, and before/after state. |
| Secret exposure | API keys could leak in static site | `.env` is ignored; Pages mode never needs backend secrets. |

