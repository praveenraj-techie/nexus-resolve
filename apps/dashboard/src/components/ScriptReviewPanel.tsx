import { FileCode2 } from 'lucide-react';
import type { RemediationPlan } from '../types';

type Props = {
  plan?: RemediationPlan;
};

export function ScriptReviewPanel({ plan }: Props) {
  return (
    <section className="panel script-panel" aria-labelledby="script-title">
      <div className="panel-heading">
        <FileCode2 size={18} aria-hidden="true" />
        <h2 id="script-title">PowerShell Review</h2>
      </div>
      <pre>
        <code>
          {plan?.powershell ??
            "Waiting for age-filtered, WhatIf-protected remediation plan."}
        </code>
      </pre>
      <div className="script-meta">
        <span>{plan?.target_paths?.[0] ?? 'No target yet'}</span>
        <span>{plan ? `${plan.age_filter_days}+ day filter` : 'Age filter pending'}</span>
        <span>{plan?.mock_only ? 'Mock only' : 'Pending guard'}</span>
      </div>
    </section>
  );
}

