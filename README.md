# NEXUS-RESOLVE

Policy-grounded AI remediation for synthetic enterprise infrastructure operations.

NEXUS-RESOLVE resolves synthetic HCL-style managed-infrastructure alerts by
retrieving a governing SOP, comparing historical tickets, rejecting unsafe
precedent, generating an approval-gated mock remediation plan, executing only
synthetic state changes, validating the result, and producing RCA plus audit
evidence.

## Modes

- Replay Mode: static dashboard flow for GitHub Pages. No backend or secrets.
- Local Live Mode: FastAPI backend, WebSocket timeline, optional OpenAI
  Responses API call when `OPENAI_API_KEY` is present.
- Mock fallback: deterministic golden response if OpenAI is unavailable.

## Quick Start

Copy `.env.example` to `.env` only for local live mode. Do not commit `.env`.

One-command local setup and checks:

```powershell
.\scripts\setup-all.cmd
.\scripts\check-all.cmd
```

One-command judge demo launcher:

```powershell
.\scripts\start-demo.cmd
```

It reuses existing listeners on ports 8000, 5173, and 5174, starts missing
services, checks health, and prints the dashboard and deep-dive URLs.

Backend:

```powershell
cd services\backend
python -m venv .venv
.\.venv\Scripts\python -m pip install -e .[dev]
.\.venv\Scripts\python -m pytest
.\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```

Dashboard:

```powershell
cd apps\dashboard
npm install
npm run test
npm run build
npm run dev
```

Open `http://localhost:5173` for the operations console.

Open `http://localhost:5174/apps/deep-dive/#both` for the judge console. It
embeds the real dashboard and shows live FastAPI JSON when the backend is
running, with labeled trace replay as the safe fallback.

Live OpenAI smoke test after setting a real key:

```powershell
.\scripts\verify-live-openai.cmd
```

## Architecture

The orchestrator owns the workflow state. OpenAI is used for structured plan and
RCA generation when configured, while deterministic local tools retrieve SOPs,
compare historical tickets, enforce policy, mock execute, validate, and emit
audit events. Structured outputs cover evidence summary, remediation plan,
approval summary, and RCA. Approval records include demo operator metadata, and
the backend can return a hashed audit packet for any active run. A
ServiceNow-style mock connector endpoint exposes the synthetic ticket shape a
real ITSM adapter would use. See
`docs/architecture.md` for the diagram and data flow.

## Demo Flow

The dashboard supports these replay/live scenarios:

- Windows Infra: disk utilization high.
- Database: DB connection pool saturation.
- Security / IAM: suspicious admin role assignment.
- Network: VPN tunnel packet loss.
- Linux: high CPU / load average.
- Firewall: rule blocking application traffic.
- Backup: critical server backup failed.
- Service Desk: repeated account lockout.
- AD: Group Policy not applying.
- Command Centre: alert storm / duplicate alerts.
- Cloud: VM failed health/status check.

The first screen is an operations alert dashboard. Selecting an alert opens an
incident workspace with ticket details at the top and a nearby Start Simulation
control. Each scenario then follows the same workflow: receive alert, retrieve
SOP, compare history, flag unsafe precedent, generate an action review package,
pause for human approval, execute mock remediation, validate metrics, generate
RCA, and ask the operator to close the incident or keep it under observation
before closure.

## Safety Model

This demo never executes real host remediation. It blocks protected resources,
requires a dry-run or mock-only guard, pauses for human approval, uses mock-only
state mutation, validates scenario-specific recovery metrics, and requires an
explicit closure decision after RCA.

## OpenAI Usage

Runtime reasoning is wrapped in `services/backend/app/openai_client.py` and uses
the Responses API path when a key is configured. The default model is
configurable with `OPENAI_MODEL` and defaults to `gpt-5.5`. The app falls back to
validated synthetic outputs if the API is unavailable during a demo.

## Codex Usage

Codex is used as the builder, reviewer, debugger, and test-hardening assistant.
It is not used as a runtime API inside the product.

## Tests

Backend:

```powershell
cd services\backend
.\.venv\Scripts\python -m pytest
```

Dashboard:

```powershell
cd apps\dashboard
npm run lint
npm run test
npm run build
```

Coverage includes all 11 catalog scenarios, golden approval flow, observation
and closure flow, rejection safety, unsafe action blocks, protected-resource
blocks, audit packet hashing, event sequencing, replay endpoints, scenario
selector rendering, proof-strip rendering, and first-screen console rendering.

## GitHub Pages

The dashboard build copies `data/scenarios/catalog.json` and every
`data/replay/*.events.jsonl` file into Vite's public folder at build time.
GitHub Actions publishes `apps/dashboard/dist`, so the public page can run
Replay Mode without a backend or OpenAI key.

Public replay: `https://praveenraj-techie.github.io/nexus-resolve/`

Public replay intentionally does not prove a live OpenAI call. For judging,
show the local live dashboard/deep-dive flow after setting `OPENAI_API_KEY` in
`.env`; the UI labels OpenAI, fallback, and replay evidence separately.

Publish steps are in `docs/publish-runbook.md`.

## Demo Video

A local 4:30 captioned demo artifact is available at
`media/nexus-resolve-demo.mp4`. It uses verified dashboard screenshots and
follows the narration in `docs/demo-script.md`.

## Roadmap

- ServiceNow incident adapter.
- Intune or WinRM execution connector with change windows.
- Change-management approval integration.
- SIEM audit export.
- Hosted live mode with server-side secret storage and rate limits.
- Real tool-calling connector path for SOP, history, policy, validation, and
  ticket update tools.
- Additional SOP packs for certificate expiry, DFS replication, and storage
  failover triage.
- Evaluation harness for policy violation prompts and regression replay.

## Project Layout

```text
data/                  Synthetic scenario catalog, SOPs, history, replay streams
services/backend/      FastAPI workflow, policy gates, tests
apps/dashboard/        React operations console
docs/                  Architecture, scoring map, demo script, risks
.github/workflows/     CI and GitHub Pages deployment
```
