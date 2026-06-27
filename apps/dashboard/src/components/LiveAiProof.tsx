import { Activity, BadgeCheck, BrainCircuit, Clock3, Server } from 'lucide-react';
import type { AiGeneratedPayload, Mode, RunEvent } from '../types';

type Props = {
  backendOnline: boolean;
  events: RunEvent[];
  mode: Mode;
  runId: string | null;
};

type GeneratedPayload = AiGeneratedPayload & Record<string, unknown>;

const AI_EVENT_TYPES = new Set([
  'evidence.summary',
  'plan.generated',
  'approval.summary',
  'rca.generated',
]);

function latestAiEvent(events: RunEvent[]): RunEvent | undefined {
  return [...events]
    .reverse()
    .find((event) => AI_EVENT_TYPES.has(event.type) && event.payload);
}

function sourceText(payload?: GeneratedPayload): string {
  if (!payload?.ai_source) return 'Replay/static evidence';
  if (payload.ai_source === 'openai') return payload.generated_by ?? 'OpenAI Responses API';
  return payload.generated_by ?? 'Deterministic fallback';
}

function sourceTone(payload?: GeneratedPayload): 'openai' | 'fallback' | 'replay' | 'pending' {
  if (!payload) return 'pending';
  return payload.ai_source ?? 'replay';
}

function formatTime(value?: string): string {
  if (!value) return 'Waiting';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

export function LiveAiProof({ backendOnline, events, mode, runId }: Props) {
  const latest = latestAiEvent(events);
  const payload = latest?.payload as GeneratedPayload | undefined;
  const fallbackCount = events.filter((event) => event.type === 'openai.fallback').length;
  const tone = sourceTone(payload);
  const source = sourceText(payload);
  const model = payload?.model ? String(payload.model) : mode === 'live' ? 'Waiting' : 'Replay';
  const fallbackStatus =
    fallbackCount > 0 ? `${fallbackCount} fallback event${fallbackCount === 1 ? '' : 's'}` : 'No fallback';

  return (
    <section className="live-ai-proof" data-state={tone} aria-label="Live AI proof">
      <div className="proof-title">
        <BrainCircuit size={18} aria-hidden="true" />
        <div>
          <strong>Live AI Proof</strong>
          <span>{mode === 'live' ? 'Local backend evidence' : 'Replay evidence'}</span>
        </div>
      </div>
      <article>
        <BadgeCheck size={16} aria-hidden="true" />
        <span>Source</span>
        <strong>{source}</strong>
      </article>
      <article>
        <Server size={16} aria-hidden="true" />
        <span>Model / Backend</span>
        <strong>{model} / {backendOnline ? 'online' : 'offline'}</strong>
      </article>
      <article>
        <Activity size={16} aria-hidden="true" />
        <span>Run / Events</span>
        <strong>{runId ?? 'not started'} / {events.length}</strong>
      </article>
      <article>
        <Clock3 size={16} aria-hidden="true" />
        <span>Timestamp / Fallback</span>
        <strong>{formatTime(latest?.timestamp)} / {fallbackStatus}</strong>
      </article>
    </section>
  );
}
