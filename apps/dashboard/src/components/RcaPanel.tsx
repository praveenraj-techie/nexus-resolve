import { ClipboardCheck } from 'lucide-react';
import type { RcaSummary } from '../types';

type Props = {
  rca?: RcaSummary;
};

export function RcaPanel({ rca }: Props) {
  return (
    <section className="panel rca-panel" aria-labelledby="rca-title">
      <div className="panel-heading">
        <ClipboardCheck size={18} aria-hidden="true" />
        <h2 id="rca-title">RCA Summary</h2>
      </div>
      <strong>{rca?.root_cause ?? 'RCA will appear after validation.'}</strong>
      <p>{rca?.validation ?? 'Awaiting mock execution and free-space validation.'}</p>
      <ul>
        {(rca?.follow_up ?? ['Tune log rotation', 'Keep approval evidence']).map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </section>
  );
}

