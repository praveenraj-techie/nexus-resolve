export type Mode = 'replay' | 'live';

export type EventPayload = Record<string, unknown> | null;

export type AiSource = 'openai' | 'fallback';

export type AiGeneratedPayload = {
  ai_source?: AiSource;
  generated_by?: string;
  model?: string;
};

export type ScenarioSummary = {
  scenario_id: string;
  team: string;
  alert_type: string;
  incident_id: string;
  priority: string;
  title: string;
  business_service: string;
  affected_ci: string;
  current_state: string;
  requested_outcome: string;
};

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
  target_resources: string[];
  action_preview: string;
  estimated_effect: string;
  safeguards: string[];
  approval_required: boolean;
  approval_granted: boolean;
  uses_dry_run: boolean;
  mock_only: boolean;
  validation_steps: string[];
  escalation_condition: string;
} & AiGeneratedPayload;

export type RcaSummary = {
  root_cause: string;
  actions_taken: string[];
  validation: string;
  business_impact: string;
  follow_up: string[];
  metrics: Record<string, number | string | boolean>;
};

export type ApprovalSummary = {
  decision_required: boolean;
  operator_message: string;
  expected_safe_effect: string;
  blocked_until_approved: boolean;
  replay_side_effects_disabled: boolean;
};

export type TicketDetails = {
  scenario_id: string;
  team: string;
  alert_type: string;
  incident_id: string;
  priority: string;
  ci: string;
  service: string;
  current_state: string;
  requested_outcome: string;
};
