import { Gauge } from 'lucide-react';
import type { RcaSummary, RunEvent } from '../types';

type Props = {
  events: RunEvent[];
  rca?: RcaSummary;
};

export function MetricsRibbon({ events, rca }: Props) {
  const execution = events.find((event) => event.type === 'execution.mocked');
  const payload = execution?.payload as Record<string, number> | undefined;
  const metrics = rca?.metrics;

  const items = [
    { label: 'Before Free', value: `${payload?.before_free_gb ?? 8} GB` },
    { label: 'After Free', value: `${payload?.after_free_gb ?? 44} GB` },
    { label: 'Reclaimed', value: `${payload?.reclaimed_gb ?? 36} GB` },
    { label: 'MTTR Estimate', value: `${metrics?.mttr_minutes ?? 8} min` },
    { label: 'Audit', value: `${metrics?.audit_completeness_percent ?? 100}%` },
  ];

  return (
    <section className="metrics-ribbon" aria-label="Business and disk metrics">
      <div className="metric-label">
        <Gauge size={17} aria-hidden="true" />
        Metrics
      </div>
      {items.map((item) => (
        <article key={item.label}>
          <strong>{item.value}</strong>
          <span>{item.label}</span>
        </article>
      ))}
    </section>
  );
}

