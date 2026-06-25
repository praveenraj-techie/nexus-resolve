import { Server } from 'lucide-react';
import type { TicketDetails } from '../types';

type Props = {
  ticket: TicketDetails;
};

export function TicketPanel({ ticket }: Props) {
  return (
    <section className="panel ticket-panel" aria-labelledby="ticket-title">
      <div className="panel-heading">
        <Server size={18} aria-hidden="true" />
        <h2 id="ticket-title">Ticket Details</h2>
      </div>
      <dl className="ticket-grid">
        <div>
          <dt>Incident</dt>
          <dd>{ticket.incident_id}</dd>
        </div>
        <div>
          <dt>Priority</dt>
          <dd className="priority">{ticket.priority}</dd>
        </div>
        <div>
          <dt>Affected CI</dt>
          <dd>{ticket.ci}</dd>
        </div>
        <div>
          <dt>Business Service</dt>
          <dd>{ticket.service}</dd>
        </div>
        <div>
          <dt>Current State</dt>
          <dd>C: 96% used, 8 GB free</dd>
        </div>
        <div>
          <dt>Outcome</dt>
          <dd>Reclaim space with SOP-approved cleanup</dd>
        </div>
      </dl>
    </section>
  );
}

