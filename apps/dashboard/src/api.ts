import type { RunEvent } from './types';

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000';

export async function healthCheck(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE}/api/health`);
    return response.ok;
  } catch {
    return false;
  }
}

export async function startIncident(): Promise<{ run_id: string; status: string }> {
  const response = await fetch(`${API_BASE}/api/incidents`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
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

