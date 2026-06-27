# Demo Script

## 0:00-0:20 Problem

Enterprise teams lose time on repetitive low-priority infrastructure tickets.
Simple alerts become risky when automation copies unsafe precedent or skips
approval and validation.

## 0:20-0:45 Trigger

Start on the active operations dashboard. Open the default disk-space alert,
then return to the dashboard or selector to show Database, IAM, VPN, Linux,
Firewall, Backup, Service Desk, AD, Command Centre, and Cloud scenarios. In the
incident workspace, show ticket details at the top and use Start Simulation from
the alert context.

For a judge Q and A, open `http://localhost:5174/apps/deep-dive/#both` beside
the dashboard. Explain that the iframe is the real dashboard and that the API
cards switch to live FastAPI JSON when the backend is online.

## 0:45-1:20 Evidence

Show SOP retrieval and historical tickets. Point out that each scenario has safe
precedents, one unsafe precedent, and one escalation precedent.

## 1:20-1:50 Governance Moment

Highlight "SOP beats history." The unsafe precedent is blocked even though it
came from a past ticket.

## 1:50-2:30 Plan

Review the action package. It shows the target resource, expected effect,
mock/dry-run guard, required approval, and validation steps.

## 2:30-3:10 Approval

Show the human approval gate. Explain that replay mode disables side effects and
local live mode continues only after approval.

## 3:10-3:45 Mock Execution

Approve the run. Show mock execution improving the selected scenario metrics,
such as disk free space, DB connection count, packet loss, backup status, or VM
health.

## 3:45-4:15 RCA

Show RCA, metrics, audit trail, the Live AI Proof strip, and the hashed audit
packet in the deep-dive API board.

## 4:15-4:30 Closure

Show the Close INC and Observe options. Use Observe to demonstrate the recheck,
then show the incident closing with RCA and validation attached. Close with the
message: this is not "AI deletes files"; it is policy-grounded, approval-gated
remediation.

## Local Live Vs Public Replay

- Public Pages: safe replay only, no backend and no API key.
- Local live: backend on port 8000, dashboard on 5173, deep-dive on 5174, and
  OpenAI calls remain server-side.
- Start all local demo surfaces with `.\scripts\start-demo.cmd`.
