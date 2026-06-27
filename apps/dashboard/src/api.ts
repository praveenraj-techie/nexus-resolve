import type { PolicyCheck, RunEvent, ScenarioSummary } from './types';

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000';
const STATIC_BASE = import.meta.env.BASE_URL;

export async function healthCheck(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE}/api/health`);
    return response.ok;
  } catch {
    return false;
  }
}

export async function fetchScenarios(): Promise<ScenarioSummary[]> {
  const response = await fetch(`${STATIC_BASE}data/scenarios/catalog.json`);
  if (!response.ok) {
    throw new Error('Scenario catalog is unavailable.');
  }
  const catalog = (await response.json()) as Array<{
    scenario_id: string;
    team: string;
    alert_type: string;
    incident: {
      incident_id: string;
      priority: string;
      title: string;
      business_service: string;
      affected_ci: string;
      current_state: string;
      requested_outcome: string;
    };
  }>;
  return catalog.map((scenario) => ({
    scenario_id: scenario.scenario_id,
    team: scenario.team,
    alert_type: scenario.alert_type,
    incident_id: scenario.incident.incident_id,
    priority: scenario.incident.priority,
    title: scenario.incident.title,
    business_service: scenario.incident.business_service,
    affected_ci: scenario.incident.affected_ci,
    current_state: scenario.incident.current_state,
    requested_outcome: scenario.incident.requested_outcome,
  }));
}

export async function startIncident(
  scenarioId: string,
): Promise<{ run_id: string; status: string }> {
  const response = await fetch(`${API_BASE}/api/incidents`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scenario_id: scenarioId }),
  });
  if (!response.ok) {
    throw new Error('Unable to start local run.');
  }
  return response.json();
}

export async function approveRun(runId: string): Promise<void> {
  await fetch(`${API_BASE}/api/runs/${runId}/approve`, { method: 'POST' });
}

export async function rejectRun(runId: string): Promise<void> {
  await fetch(`${API_BASE}/api/runs/${runId}/reject`, { method: 'POST' });
}

export async function closeRun(runId: string): Promise<void> {
  await fetch(`${API_BASE}/api/runs/${runId}/close`, { method: 'POST' });
}

export async function observeRun(runId: string): Promise<void> {
  await fetch(`${API_BASE}/api/runs/${runId}/observe`, { method: 'POST' });
}

export async function fetchPolicyDemoBlock(): Promise<PolicyCheck[]> {
  const response = await fetch(`${API_BASE}/api/policy/demo-block`, {
    cache: 'no-store',
  });
  if (!response.ok) {
    throw new Error('Unable to load protected-resource policy demo.');
  }
  const payload = (await response.json()) as { checks: PolicyCheck[] };
  return payload.checks;
}

export function connectRunStream(
  runId: string,
  onEvent: (event: RunEvent) => void,
  onClose: () => void,
): WebSocket {
  const url = new URL(API_BASE);
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
  url.pathname = `/ws/runs/${runId}`;
  const socket = new WebSocket(url);
  socket.onmessage = (message) => onEvent(JSON.parse(message.data) as RunEvent);
  socket.onclose = onClose;
  return socket;
}
