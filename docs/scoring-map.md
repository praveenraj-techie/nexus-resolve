# Hackathon Scoring Map

## Innovation

NEXUS-RESOLVE is not a chatbot. It is an operations console where AI reasoning
is constrained by SOP retrieval, unsafe precedent detection, policy gates,
approval, mock execution, validation, and audit evidence.

## Impact

The target problem is repetitive P3-P5 remediation work. The demo shows manual
steps avoided, estimated MTTR reduction, and audit completeness.

## HCLTech Relevance

The scenario maps to enterprise managed operations: alerts, SOPs, incident
history, change approval, safe execution, validation, and RCA.

## OpenAI Capabilities

- Responses API for application-owned runtime reasoning.
- Structured output wrapper for remediation plans and RCA.
- Configurable `gpt-5.5` default model.
- Deterministic fallback for resilient demos.

## Technical Excellence

- FastAPI backend with tests.
- React/Vite dashboard with replay and live modes.
- WebSocket event stream with ordered audit events.
- Explicit policy module and protected-path tests.
- No secrets or real enterprise data.

## Scalability

The roadmap extends the pattern to ServiceNow, Intune or WinRM execution
connectors, change management approval, SIEM export, and additional remediation
playbooks.

