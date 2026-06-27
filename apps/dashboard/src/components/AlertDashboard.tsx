import {
  Activity,
  AlertTriangle,
  ArrowRight,
  Cloud,
  Database,
  Flame,
  Gauge,
  HardDrive,
  Network,
  Server,
  Shield,
  Users,
} from 'lucide-react';
import type { ScenarioSummary } from '../types';

type Props = {
  scenarios: ScenarioSummary[];
  selectedScenarioId: string;
  onOpenScenario: (scenarioId: string) => void;
};

const iconByTeam: Record<string, typeof Server> = {
  'Windows Infra': HardDrive,
  Database,
  'Security / IAM': Shield,
  Network,
  Linux: Server,
  Firewall: Flame,
  Backup: Activity,
  'Service Desk': Users,
  AD: Shield,
  'Command Centre': Gauge,
  Cloud,
};

function urgency(priority: string): string {
  if (priority === 'P2') return 'Critical';
  if (priority === 'P3') return 'High';
  return 'Moderate';
}

export function AlertDashboard({
  scenarios,
  selectedScenarioId,
  onOpenScenario,
}: Props) {
  const critical = scenarios.filter((scenario) => scenario.priority === 'P2').length;
  const high = scenarios.filter((scenario) => scenario.priority === 'P3').length;

  return (
    <section className="dashboard-view" aria-label="Alert dashboard">
      <div className="dashboard-hero">
        <div>
          <span className="eyebrow">HCL Managed Infrastructure Command View</span>
          <h1>Active Operations Alerts</h1>
          <p>
            Select an alert to open the incident workspace, review SOP evidence,
            start simulation, approve remediation, and close with audit evidence.
          </p>
        </div>
        <div className="hero-metrics" aria-label="Alert summary">
          <article>
            <strong>{scenarios.length}</strong>
            <span>Open alerts</span>
          </article>
          <article>
            <strong>{critical}</strong>
            <span>Critical</span>
          </article>
          <article>
            <strong>{high}</strong>
            <span>High</span>
          </article>
        </div>
      </div>

      <div className="alert-board">
        {scenarios.map((scenario) => {
          const Icon = iconByTeam[scenario.team] ?? AlertTriangle;
          const active = scenario.scenario_id === selectedScenarioId;
          return (
            <button
              className="alert-card"
              data-active={active}
              key={scenario.scenario_id}
              type="button"
              onClick={() => onOpenScenario(scenario.scenario_id)}
            >
              <span className="alert-glow" aria-hidden="true" />
              <div className="alert-card-top">
                <span className="team-icon">
                  <Icon size={19} aria-hidden="true" />
                </span>
                <span className={`severity severity-${scenario.priority.toLowerCase()}`}>
                  {scenario.priority}
                </span>
              </div>
              <div className="alert-card-main">
                <span>{scenario.team}</span>
                <strong>{scenario.alert_type}</strong>
                <p>{scenario.current_state}</p>
              </div>
              <div className="alert-card-bottom">
                <span>{scenario.incident_id}</span>
                <span>{urgency(scenario.priority)}</span>
                <ArrowRight size={16} aria-hidden="true" />
              </div>
            </button>
          );
        })}
      </div>
    </section>
  );
}
