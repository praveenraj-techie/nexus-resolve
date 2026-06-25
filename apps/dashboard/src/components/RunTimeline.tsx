import { CheckCircle2, Clock3, ShieldAlert } from 'lucide-react';
import type { RunEvent } from '../types';

type Props = {
  events: RunEvent[];
};

function eventIcon(type: string) {
  if (type.includes('blocked') || type.includes('warning')) {
    return <ShieldAlert size={17} aria-hidden="true" />;
  }
  if (type.includes('passed') || type.includes('generated') || type.includes('mocked')) {
    return <CheckCircle2 size={17} aria-hidden="true" />;
  }
  return <Clock3 size={17} aria-hidden="true" />;
}

export function RunTimeline({ events }: Props) {
  return (
    <section className="panel timeline-panel" aria-labelledby="timeline-title">
      <div className="panel-heading">
        <Clock3 size={18} aria-hidden="true" />
        <h2 id="timeline-title">Agent Timeline</h2>
      </div>
      <div className="timeline-list">
        {events.map((event) => (
          <article className="timeline-event" data-type={event.type} key={event.sequence}>
            <div className="event-icon">{eventIcon(event.type)}</div>
            <div>
              <div className="event-row">
                <strong>{event.title}</strong>
                <span>#{event.sequence}</span>
              </div>
              <p>{event.message}</p>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

