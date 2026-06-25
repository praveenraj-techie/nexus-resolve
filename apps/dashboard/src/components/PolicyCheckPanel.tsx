import { ShieldCheck } from 'lucide-react';
import type { PolicyCheck } from '../types';

type Props = {
  checks: PolicyCheck[];
};

export function PolicyCheckPanel({ checks }: Props) {
  return (
    <section className="panel policy-panel" aria-labelledby="policy-title">
      <div className="panel-heading">
        <ShieldCheck size={18} aria-hidden="true" />
        <h2 id="policy-title">Policy Checks</h2>
      </div>
      <div className="check-list">
        {checks.map((check) => (
          <article className="check-row" data-status={check.status} key={check.name}>
            <span>{check.status.replace('_', ' ')}</span>
            <div>
              <strong>{check.name}</strong>
              <p>{check.message}</p>
            </div>
          </article>
        ))}
        <article className="check-row" data-status="blocked">
          <span>blocked</span>
          <div>
            <strong>Protected-path demo</strong>
            <p>C:\Windows\System32 cleanup is blocked as an unsafe remediation.</p>
          </div>
        </article>
      </div>
    </section>
  );
}

