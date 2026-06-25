# Demo Script

## 0:00-0:20 Problem

Enterprise teams lose time on repetitive low-priority tickets. Disk-space alerts
look simple, but unsafe remediation can remove active logs or touch protected
paths.

## 0:20-0:45 Trigger

Start the synthetic ticket `INC-2026-00421`. Show `APP-WIN-042`, `P4`, `C:` at
96% used, and the Internal Claims Portal context.

## 0:45-1:20 Evidence

Show SOP retrieval and historical tickets. Point out that most tickets support
archived log cleanup, but one historical ticket is unsafe.

## 1:20-1:50 Governance Moment

Highlight "SOP beats history." The unsafe precedent deleted active logs, so it is
blocked even though it came from a past ticket.

## 1:50-2:30 Plan

Review the PowerShell. It targets `C:\App\Logs`, filters files older than 7 days,
uses `-WhatIf`, requires approval, and includes validation.

## 2:30-3:10 Approval

Show the human approval gate. Explain that replay mode disables side effects and
local live mode continues only after approval.

## 3:10-3:45 Mock Execution

Approve the run. Show mock cleanup improving from 8 GB free to 44 GB free and
from 96% used to 78% used.

## 3:45-4:30 RCA

Show RCA, metrics, audit trail, and scoring map. Close with the message: this is
not "AI deletes files"; it is policy-grounded, approval-gated remediation.

