import { BookOpenText, History } from 'lucide-react';
import type { RunEvent } from '../types';

type Props = {
  events: RunEvent[];
};

export function EvidencePanel({ events }: Props) {
  const sop = events.find((event) => event.type === 'evidence.sop');
  const history = events.find((event) => event.type === 'evidence.history');
  const warning = events.find((event) => event.type === 'policy.warning');

  return (
    <section className="panel evidence-panel" aria-labelledby="evidence-title">
      <div className="panel-heading">
        <BookOpenText size={18} aria-hidden="true" />
        <h2 id="evidence-title">SOP And History</h2>
      </div>
      <div className="evidence-card sop-card">
        <BookOpenText size={16} aria-hidden="true" />
        <div>
          <strong>SOP-WIN-DISK-001</strong>
          <p>{sop?.message ?? 'Waiting for SOP retrieval.'}</p>
        </div>
      </div>
      <div className="evidence-card">
        <History size={16} aria-hidden="true" />
        <div>
          <strong>Similar Tickets</strong>
          <p>{history?.message ?? 'Waiting for historical ticket comparison.'}</p>
        </div>
      </div>
      <div className="blocked-card">
        <strong>SOP beats history</strong>
        <p>
          {warning?.message ??
            'Unsafe precedent will be shown here when detected.'}
        </p>
      </div>
    </section>
  );
}

