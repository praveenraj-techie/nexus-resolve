# Submission Answers

## One-Line Pitch

NEXUS-RESOLVE is a policy-grounded, approval-gated AI remediation console that
turns repetitive synthetic enterprise disk-space tickets into auditable, safe,
mock-only remediation evidence.

## Problem

Operations teams spend significant time on repetitive P3-P5 tickets, but simple
automation can become risky when it copies unsafe historical precedent or runs
without policy, approval, and validation.

## Solution

The app receives a synthetic Windows P4 disk-space alert, retrieves the governing
SOP, compares historical tickets, flags unsafe precedent, generates a safe
PowerShell review package, waits for human approval, performs mock remediation,
validates before/after disk state, and produces RCA plus audit evidence.

## Agent Workflow

1. Receive `INC-2026-00421`.
2. Retrieve `SOP-WIN-DISK-001`.
3. Retrieve and classify historical tickets.
4. Emit the visible "SOP beats history" warning for unsafe precedent.
5. Create structured evidence and remediation summaries.
6. Run deterministic policy checks.
7. Pause for human approval.
8. Execute only mock state changes.
9. Validate free space.
10. Generate RCA and audit events.

## OpenAI Stack Usage

The backend uses the OpenAI Responses API wrapper in
`services/backend/app/openai_client.py` for structured evidence summary,
remediation plan, approval summary, and RCA outputs. The default model is
`gpt-5.5`, configurable through `OPENAI_MODEL`. If OpenAI is unavailable, the
workflow emits the fallback notice and uses validated deterministic responses.

## Safety Model

NEXUS-RESOLVE never executes real host remediation. It blocks protected paths,
requires a 7-day age filter, requires a WhatIf or mock-only guard, requires
human approval, validates free space, and escalates if the result remains below
15% free space.

## Business Metrics

- Free space improves from 8 GB to 44 GB in the synthetic flow.
- Estimated MTTR is 8 minutes.
- Six manual steps are avoided.
- Audit completeness is shown as 100%.

## Why It Matters

The project demonstrates how AI can accelerate enterprise operations without
removing governance. It is not "AI deletes files"; it is policy-grounded,
approval-gated remediation.

