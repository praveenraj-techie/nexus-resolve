import { ShieldCheck } from 'lucide-react';
import type { PolicyCheck } from '../types';

type Props = {
  checks: PolicyCheck[];
  backendOnline: boolean;
  demoChecks: PolicyCheck[];
  demoError?: string;
  demoLoading: boolean;
  onLoadDemo: () => void;
};

export function PolicyCheckPanel({
  backendOnline,
  checks,
  demoChecks,
  demoError,
  demoLoading,
  onLoadDemo,
}: Props) {
  const protectedBlock =
    demoChecks.find((check) => check.name === 'Target scope') ?? demoChecks[0];

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
        <div className="policy-demo-card">
          <div>
            <strong>Protected-Resource Block Demo</strong>
            <p>
              Fetches the real backend policy response for a blocked
              C:\Windows\System32 remediation plan.
            </p>
          </div>
          <button type="button" onClick={onLoadDemo} disabled={!backendOnline || demoLoading}>
            {demoLoading ? 'Checking...' : 'Show Real Block'}
          </button>
          {!backendOnline ? <span>Backend offline: start local live mode to fetch the API.</span> : null}
          {demoError ? <span className="policy-demo-error">{demoError}</span> : null}
        </div>
        {protectedBlock ? (
          <article className="check-row policy-demo-result" data-status={protectedBlock.status}>
            <span>{protectedBlock.status.replace('_', ' ')}</span>
            <div>
              <strong>{protectedBlock.name}</strong>
              <p>{protectedBlock.message}</p>
            </div>
          </article>
        ) : (
          <article className="check-row policy-demo-result" data-status="blocked">
            <span>blocked</span>
            <div>
              <strong>Protected-resource demo pending</strong>
              <p>C:\Windows\System32 will be blocked as an unsafe remediation target.</p>
            </div>
          </article>
        )}
      </div>
    </section>
  );
}
