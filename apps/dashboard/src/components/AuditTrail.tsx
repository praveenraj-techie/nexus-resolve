import { ListChecks } from 'lucide-react';
import type { RunEvent } from '../types';

type Props = {
  events: RunEvent[];
};

export function AuditTrail({ events }: Props) {
  return (
    <section className="panel audit-panel" aria-labelledby="audit-title">
      <div className="panel-heading">
        <ListChecks size={18} aria-hidden="true" />
        <h2 id="audit-title">Audit Trail</h2>
      </div>
      <ol>
        {events.map((event) => (
          <li key={`${event.run_id}-${event.sequence}`}>
            <span>{event.sequence.toString().padStart(2, '0')}</span>
            <strong>{event.type}</strong>
          </li>
        ))}
      </ol>
    </section>
  );
}

