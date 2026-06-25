export type Mode = 'replay' | 'live';

export type EventPayload = Record<string, unknown> | null;

export type RunEvent = {
  run_id: string;
  sequence: number;
  timestamp: string;
  type: string;
  title: string;
  message: string;
  payload?: EventPayload;
};

export type PolicyCheck = {
  name: string;
  status: 'pass' | 'blocked' | 'requires_approval';
  message: string;
  evidence?: Record<string, unknown>;
};

export type RemediationPlan = {
  summary: string;
  target_paths: string[];
  estimated_reclaim_gb: number;
  age_filter_days: number;
  powershell: string;
  approval_required: boolean;
  approval_granted: boolean;
  uses_whatif: boolean;
  mock_only: boolean;
  validation_steps: string[];
  escalation_condition: string;
};

export type RcaSummary = {
  root_cause: string;
  actions_taken: string[];
  validation: string;
  business_impact: string;
  follow_up: string[];
  metrics: Record<string, number | string | boolean>;
};

export type TicketDetails = {
  incident_id: string;
  priority: string;
  ci: string;
  service: string;
};

