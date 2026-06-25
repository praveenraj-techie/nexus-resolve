import type { RunEvent } from './types';

export async function loadReplayEvents(): Promise<RunEvent[]> {
  const response = await fetch('/data/replay/disk-space-run.events.jsonl');
  if (!response.ok) {
    throw new Error('Replay data is unavailable.');
  }
  const text = await response.text();
  return text
    .split('\n')
    .filter(Boolean)
    .map((line) => JSON.parse(line) as RunEvent);
}

export function playReplayEvents(
  events: RunEvent[],
  onEvent: (event: RunEvent) => void,
): () => void {
  let index = 0;
  const timer = window.setInterval(() => {
    const event = events[index];
    if (!event) {
      window.clearInterval(timer);
      return;
    }
    onEvent(event);
    index += 1;
  }, 520);

  return () => window.clearInterval(timer);
}

