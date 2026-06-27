# Submission Answers

## One-Line Pitch

NEXUS-RESOLVE is a policy-grounded, approval-gated AI remediation console that
turns repetitive synthetic enterprise infrastructure alerts into auditable,
safe, mock-only remediation evidence.

## Problem

Operations teams spend significant time on repetitive P3-P5 tickets, but simple
automation can become risky when it copies unsafe historical precedent or runs
without policy, approval, and validation.

## Solution

The app receives a selected synthetic infra alert across Windows, Database,
IAM, Network, Linux, Firewall, Backup, Service Desk, AD, Command Centre, or
Cloud teams. It retrieves the governing SOP, compares historical tickets, flags
unsafe precedent, generates a safe action review package, waits for human
approval, performs mock remediation, validates before/after scenario metrics,
produces RCA plus audit evidence, and requires the operator to close the
incident or observe it before closure.

## Agent Workflow

1. Receive the selected synthetic scenario, defaulting to `INC-2026-00421`.
2. Retrieve the scenario-specific SOP.
3. Retrieve and classify historical tickets.
4. Emit the visible "SOP beats history" warning for unsafe precedent.
5. Create structured evidence and remediation summaries.
6. Run deterministic policy checks.
7. Pause for human approval.
8. Execute only mock state changes.
9. Validate scenario recovery metrics.
10. Generate RCA and audit events.
11. Request human closure approval or observation.
12. Close with RCA, evidence, and validation attached.
13. Export a hashed audit packet for backend proof when requested.

## OpenAI Stack Usage

The backend uses the OpenAI Responses API wrapper in
`services/backend/app/openai_client.py` for structured evidence summary,
remediation plan, approval summary, and RCA outputs. The default model is
`gpt-5.5`, configurable through `OPENAI_MODEL`. If OpenAI is unavailable, the
workflow emits the fallback notice and uses validated deterministic responses.
The dashboard displays a Live AI Proof strip so judges can see whether the
current evidence came from OpenAI, deterministic fallback, or replay/static
data.

## Safety Model

NEXUS-RESOLVE never executes real host remediation. It blocks protected
resources, requires explicit safeguards, requires a dry-run or mock-only guard,
requires human approval, validates scenario-specific recovery metrics, and
escalates if validation remains below threshold. Closure is also explicit: the
operator can close immediately after RCA or run an observation recheck first.
Approval records include operator, role, reason, and timestamp metadata in the
local live path.

## Judge Proof Surfaces

- Main dashboard: operator workflow, live/replay mode, approval, validation,
  RCA, Live AI Proof, and protected-resource block demo.
- Deep-dive page: real dashboard iframe plus live FastAPI JSON cards for
  health, scenarios, protected-resource block, run snapshot, and audit packet.
- Synthetic enterprise connector: ServiceNow-style mock ticket endpoint for the
  selected scenario.
- Backend API: `/api/runs/{run_id}/audit-packet` returns a SHA-256 hashed
  evidence packet for active runs.

## Business Metrics

- Disk free space improves from 8 GB to 44 GB in the default synthetic flow.
- Other scenarios show recovery metrics such as connection count, packet loss,
  backup RPO age, GPO version, duplicate alert count, and VM health.
- Estimated MTTR is shown per scenario.
- Six manual steps are avoided.
- Audit completeness is shown as 100%.

## Why It Matters

The project demonstrates how AI can accelerate enterprise operations without
removing governance. It is not "AI deletes files"; it is policy-grounded,
approval-gated remediation.
