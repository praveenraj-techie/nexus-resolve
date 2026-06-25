# NEXUS-RESOLVE

Policy-grounded AI remediation for synthetic enterprise operations.

NEXUS-RESOLVE resolves a synthetic Windows P4 disk-space alert by retrieving a
governing SOP, comparing historical tickets, rejecting unsafe precedent,
generating an approval-gated PowerShell plan, executing only mock state changes,
validating the result, and producing RCA plus audit evidence.

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

Live OpenAI smoke test after setting a real key:

```powershell
.\scripts\verify-live-openai.cmd
```

## Architecture

The orchestrator owns the workflow state. OpenAI is used for structured plan and
RCA generation when configured, while deterministic local tools retrieve SOPs,
compare historical tickets, enforce policy, mock execute, validate, and emit
audit events. Structured outputs cover evidence summary, remediation plan,
approval summary, and RCA. See `docs/architecture.md` for the diagram and data
flow.

## Demo Flow

1. Receive `INC-2026-00421`, a synthetic P4 disk-space ticket for `APP-WIN-042`.
2. Retrieve `SOP-WIN-DISK-001`.
3. Compare 10 historical tickets.
4. Flag unsafe precedent where active logs were deleted.
5. Generate a safe PowerShell review package.
6. Pause for human approval.
7. Execute only mock state changes.
8. Validate disk improvement from 8 GB free to 44 GB free.
9. Generate RCA and audit evidence.

## Safety Model

This demo never executes real host remediation. It blocks protected paths,
requires a 7-day age filter, requires a dry-run guard, pauses for human approval,
uses mock-only state mutation, and validates free space before producing RCA.

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

Coverage includes golden approval flow, rejection safety, unsafe script block,
protected-path block, event sequencing, replay endpoint, and first-screen console
rendering.

## GitHub Pages

The dashboard build copies `data/replay/disk-space-run.events.jsonl` into Vite's
public folder at build time. GitHub Actions publishes `apps/dashboard/dist`, so
the public page can run Replay Mode without a backend or OpenAI key.

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
- Additional SOP packs for service restarts, temp-file cleanup, and certificate
  expiry triage.
- Evaluation harness for policy violation prompts and regression replay.

## Project Layout

```text
data/                  Synthetic tickets, SOPs, mock state, replay stream
services/backend/      FastAPI workflow, policy gates, tests
apps/dashboard/        React operations console
docs/                  Architecture, scoring map, demo script, risks
.github/workflows/     CI and GitHub Pages deployment
```
