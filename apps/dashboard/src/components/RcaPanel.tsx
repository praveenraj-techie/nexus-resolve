import { ClipboardCheck } from 'lucide-react';
import type { AiGeneratedPayload, RcaSummary } from '../types';

type Props = {
  rca?: RcaSummary & AiGeneratedPayload;
};

function sourceLabel(rca?: AiGeneratedPayload): string {
  if (!rca?.ai_source) return 'Replay / static RCA';
  if (rca.ai_source === 'openai') {
    return `${rca.generated_by ?? 'OpenAI Responses API'}${
      rca.model ? ` (${rca.model})` : ''
    }`;
  }
  return `${rca.generated_by ?? 'Deterministic fallback'}${
    rca.model ? ` (${rca.model})` : ''
  }`;
}

export function RcaPanel({ rca }: Props) {
  return (
    <section className="panel rca-panel" aria-labelledby="rca-title">
      <div className="panel-heading">
        <ClipboardCheck size={18} aria-hidden="true" />
        <h2 id="rca-title">RCA Summary</h2>
      </div>
      <span className="ai-source-chip">{sourceLabel(rca)}</span>
      <strong>{rca?.root_cause ?? 'RCA will appear after validation.'}</strong>
      <p>{rca?.validation ?? 'Awaiting mock execution and free-space validation.'}</p>
      {rca?.business_impact ? <p>{rca.business_impact}</p> : null}
      <ul>
        {(rca?.follow_up ?? ['Tune log rotation', 'Keep approval evidence']).map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </section>
  );
}
