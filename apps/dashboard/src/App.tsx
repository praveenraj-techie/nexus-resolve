import { useEffect, useMemo, useRef, useState } from 'react';
import { ArrowLeft, PlayCircle, ShieldCheck } from 'lucide-react';
import {
  approveRun,
  closeRun,
  connectRunStream,
  fetchPolicyDemoBlock,
  fetchScenarios,
  healthCheck,
  observeRun,
  rejectRun,
  startIncident,
} from './api';
import { loadReplayEvents, playReplayEvents } from './replay';
import { ApprovalBar } from './components/ApprovalBar';
import { AlertDashboard } from './components/AlertDashboard';
import { AuditTrail } from './components/AuditTrail';
import { ClosureBar } from './components/ClosureBar';
import { DecisionPanel } from './components/DecisionPanel';
import { EvidencePanel } from './components/EvidencePanel';
import { LiveAiProof } from './components/LiveAiProof';
import { MetricsRibbon } from './components/MetricsRibbon';
import { ModeSwitch } from './components/ModeSwitch';
import { PolicyCheckPanel } from './components/PolicyCheckPanel';
import { RcaPanel } from './components/RcaPanel';
import { RunTimeline } from './components/RunTimeline';
import { ScenarioSelector } from './components/ScenarioSelector';
import { ScriptReviewPanel } from './components/ScriptReviewPanel';
import { TicketPanel } from './components/TicketPanel';
import type {
  Mode,
  PolicyCheck,
  RcaSummary,
  RemediationPlan,
  RunEvent,
  ScenarioSummary,
  TicketDetails,
} from './types';

type View = 'dashboard' | 'incident';

const defaultScenario: ScenarioSummary = {
  scenario_id: 'disk-space',
  team: 'Windows Infra',
  alert_type: 'Disk utilization high',
  incident_id: 'INC-2026-00421',
  priority: 'P4',
  title: 'C: drive utilization is above threshold',
  business_service: 'Internal Claims Portal',
  affected_ci: 'APP-WIN-042',
  current_state: 'C: drive is 96% used with 8 GB free.',
  requested_outcome: 'Reclaim space with SOP-approved cleanup.',
};

function routeFromLocation(): { view: View; scenarioId: string } {
  if (typeof window === 'undefined') {
    return { view: 'dashboard', scenarioId: 'disk-space' };
  }
  const match = window.location.hash.match(/^#\/incident\/([^/?#]+)/);
  if (!match) {
    return { view: 'dashboard', scenarioId: 'disk-space' };
  }
  return { view: 'incident', scenarioId: decodeURIComponent(match[1]) };
}

function extractPlan(events: RunEvent[]): RemediationPlan | undefined {
  return events.find((event) => event.type === 'plan.generated')?.payload as
    | RemediationPlan
    | undefined;
}

function extractChecks(events: RunEvent[]): PolicyCheck[] {
  const policyEvent = [...events]
    .reverse()
    .find((event) => event.type === 'policy.checked' || event.type === 'approval.granted');
  const payload = policyEvent?.payload as { checks?: PolicyCheck[] } | undefined;
  return payload?.checks ?? [];
}

function extractRca(events: RunEvent[]): RcaSummary | undefined {
  return events.find((event) => event.type === 'rca.generated')?.payload as
    | RcaSummary
    | undefined;
}

function runStatus(events: RunEvent[], mode: Mode): string {
  const last = events.at(-1);
  if (!last) {
    return mode === 'replay' ? 'Simulation idle' : 'Live idle';
  }
  if (last.type === 'approval.requested') return 'Waiting approval';
  if (last.type === 'closure.requested') return 'Waiting closure';
  if (last.type === 'observation.started') return 'Observing';
  if (last.type === 'incident.closed') return 'Closed';
  if (last.type === 'rca.generated') return 'RCA ready';
  if (last.type.includes('blocked')) return 'Blocked';
  if (last.type.includes('rejected')) return 'Rejected';
  return 'Running';
}

function runIntimation(status: string, mode: Mode, simulationStarted: boolean): string {
  if (!simulationStarted) {
    return mode === 'live'
      ? 'Live mode is ready. Start Simulation will stream backend work one step at a time.'
      : 'Replay mode is ready. Start Simulation will reveal the investigation slowly.';
  }
  if (status === 'Waiting approval') {
    return 'Human approval required: remediation is paused until the plan and evidence are reviewed.';
  }
  if (status === 'Waiting closure') {
    return 'RCA is ready: choose Close INC or Observe before final closure.';
  }
  if (status === 'Observing') {
    return 'Observation is running: recovery metrics are being rechecked before closure.';
  }
  if (status === 'Closed') {
    return 'Incident closed with RCA, validation, and audit evidence attached.';
  }
  return mode === 'live'
    ? 'Live run in progress: the backend is retrieving evidence and emitting each control step.'
    : 'Replay in progress: synthetic events are appearing step by step for review.';
}

function App() {
  const initialRoute = routeFromLocation();
  const [view, setView] = useState<View>(initialRoute.view);
  const [mode, setMode] = useState<Mode>('replay');
  const [scenarios, setScenarios] = useState<ScenarioSummary[]>([defaultScenario]);
  const [selectedScenarioId, setSelectedScenarioId] = useState(initialRoute.scenarioId);
  const [events, setEvents] = useState<RunEvent[]>([]);
  const [simulationStarted, setSimulationStarted] = useState(false);
  const [backendOnline, setBackendOnline] = useState(false);
  const [policyDemoChecks, setPolicyDemoChecks] = useState<PolicyCheck[]>([]);
  const [policyDemoLoading, setPolicyDemoLoading] = useState(false);
  const [policyDemoError, setPolicyDemoError] = useState<string | undefined>();
  const [runId, setRunId] = useState<string | null>(null);
  const [notice, setNotice] = useState('Alert Dashboard');
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    healthCheck().then(setBackendOnline);
    fetchScenarios()
      .then((loaded) => {
        setScenarios(loaded);
        setSelectedScenarioId((current) =>
          loaded.some((scenario) => scenario.scenario_id === current)
            ? current
            : (loaded[0]?.scenario_id ?? 'disk-space'),
        );
      })
      .catch(() => setNotice('Scenario catalog unavailable'));
  }, []);

  useEffect(() => {
    function syncRoute() {
      const route = routeFromLocation();
      socketRef.current?.close();
      setView(route.view);
      setSelectedScenarioId(route.scenarioId);
      setEvents([]);
      setRunId(null);
      setSimulationStarted(false);
      setMode('replay');
      setNotice(route.view === 'incident' ? 'Incident Workspace' : 'Alert Dashboard');
    }

    window.addEventListener('popstate', syncRoute);
    return () => window.removeEventListener('popstate', syncRoute);
  }, []);

  useEffect(() => {
    if (view !== 'incident' || mode !== 'replay' || !simulationStarted) {
      return undefined;
    }
    let stop: () => void = () => undefined;
    let cancelled = false;
    loadReplayEvents(selectedScenarioId)
      .then((loaded) => {
        if (cancelled) return;
        stop = playReplayEvents(loaded, (event) => {
          setEvents((current) => [...current, event]);
        });
      })
      .catch(() => setNotice('Replay data unavailable'));

    return () => {
      cancelled = true;
      stop();
    };
  }, [mode, selectedScenarioId, simulationStarted, view]);

  useEffect(() => {
    return () => socketRef.current?.close();
  }, []);

  const selectedScenario = useMemo(
    () =>
      scenarios.find((scenario) => scenario.scenario_id === selectedScenarioId) ??
      defaultScenario,
    [scenarios, selectedScenarioId],
  );
  const ticket: TicketDetails = useMemo(
    () => ({
      scenario_id: selectedScenario.scenario_id,
      team: selectedScenario.team,
      alert_type: selectedScenario.alert_type,
      incident_id: selectedScenario.incident_id,
      priority: selectedScenario.priority,
      ci: selectedScenario.affected_ci,
      service: selectedScenario.business_service,
      current_state: selectedScenario.current_state,
      requested_outcome: selectedScenario.requested_outcome,
    }),
    [selectedScenario],
  );
  const plan = useMemo(() => extractPlan(events), [events]);
  const checks = useMemo(() => extractChecks(events), [events]);
  const rca = useMemo(() => extractRca(events), [events]);
  const status = runStatus(events, mode);
  const waitingForApproval = events.at(-1)?.type === 'approval.requested';
  const waitingForClosure = events.at(-1)?.type === 'closure.requested';
  const observing = events.at(-1)?.type === 'observation.started';
  const closed = events.some((event) => event.type === 'incident.closed');

  async function startLive() {
    setMode('live');
    setEvents([]);
    setSimulationStarted(true);
    setNotice('Starting Local Live Mode');
    const run = await startIncident(selectedScenarioId);
    setRunId(run.run_id);
    socketRef.current?.close();
    socketRef.current = connectRunStream(
      run.run_id,
      (event) => setEvents((current) => [...current, event]),
      () => setNotice('Live stream closed'),
    );
    setNotice('Local Live Mode');
  }

  function startReplay() {
    socketRef.current?.close();
    setMode('replay');
    setEvents([]);
    setRunId(`replay-${selectedScenarioId}`);
    setSimulationStarted(true);
    setNotice('Replay Simulation');
  }

  async function startSimulation() {
    if (mode === 'live' && backendOnline) {
      await startLive();
      return;
    }
    if (mode === 'live' && !backendOnline) {
      setNotice('Backend offline, running replay simulation');
    }
    startReplay();
  }

  function activateReplay() {
    socketRef.current?.close();
    setEvents([]);
    setRunId(`replay-${selectedScenarioId}`);
    setSimulationStarted(false);
    setNotice('Replay Mode Ready');
    setMode('replay');
  }

  function selectScenario(scenarioId: string) {
    socketRef.current?.close();
    setSelectedScenarioId(scenarioId);
    setEvents([]);
    setRunId(null);
    setSimulationStarted(false);
    setNotice('Incident Workspace');
    setMode('replay');
    if (view === 'incident') {
      window.history.replaceState(null, '', `#/incident/${encodeURIComponent(scenarioId)}`);
    }
  }

  function openScenario(scenarioId: string) {
    selectScenario(scenarioId);
    setView('incident');
    window.history.pushState(null, '', `#/incident/${encodeURIComponent(scenarioId)}`);
  }

  function backToDashboard() {
    socketRef.current?.close();
    setView('dashboard');
    setEvents([]);
    setRunId(null);
    setSimulationStarted(false);
    setNotice('Alert Dashboard');
    window.history.pushState(null, '', window.location.pathname + window.location.search);
  }

  async function approve() {
    if (runId) await approveRun(runId);
  }

  async function reject() {
    if (runId) await rejectRun(runId);
  }

  async function closeIncident() {
    if (runId) await closeRun(runId);
  }

  async function observeIncident() {
    if (runId) await observeRun(runId);
  }

  async function loadPolicyDemo() {
    setPolicyDemoLoading(true);
    setPolicyDemoError(undefined);
    try {
      setPolicyDemoChecks(await fetchPolicyDemoBlock());
    } catch (error) {
      setPolicyDemoError(error instanceof Error ? error.message : 'Policy demo unavailable.');
    } finally {
      setPolicyDemoLoading(false);
    }
  }

  return (
    <main className={`console-shell ${view === 'dashboard' ? 'dashboard-shell' : ''}`}>
      <header className="topbar">
        <div className="brand">
          <ShieldCheck size={22} aria-hidden="true" />
          <div>
            <strong>NEXUS-RESOLVE</strong>
            <span>Policy-Grounded AI Remediation</span>
          </div>
        </div>
        <div className="status-strip">
          <span>{notice}</span>
          <strong>{status}</strong>
          <small>{backendOnline ? 'Backend online' : 'Backend offline'}</small>
        </div>
        {view === 'incident' ? (
          <>
            <ScenarioSelector
              scenarios={scenarios}
              selectedScenarioId={selectedScenarioId}
              onChange={selectScenario}
            />
            <ModeSwitch
              mode={mode}
              backendOnline={backendOnline}
              onModeChange={(nextMode) => {
                if (nextMode === 'replay') {
                  activateReplay();
                } else {
                  setMode('live');
                  setSimulationStarted(false);
                  setEvents([]);
                  setRunId(null);
                  setNotice(backendOnline ? 'Local Live Mode Ready' : 'Backend offline');
                }
              }}
              onStartLive={startSimulation}
            />
          </>
        ) : null}
      </header>

      {view === 'dashboard' ? (
        <AlertDashboard
          scenarios={scenarios}
          selectedScenarioId={selectedScenarioId}
          onOpenScenario={openScenario}
        />
      ) : (
        <>
          <div className="workspace-toolbar">
            <button className="ghost-button" type="button" onClick={backToDashboard}>
              <ArrowLeft size={16} aria-hidden="true" />
              Dashboard
            </button>
            <span>{ticket.incident_id}</span>
            <strong>{ticket.alert_type}</strong>
          </div>

          <div className="incident-command">
            <TicketPanel ticket={ticket} />
            <section className="simulation-panel" aria-label="Simulation controls">
              <div className="simulation-copy">
                <span className="eyebrow">{ticket.team} Alert</span>
                <h1>{ticket.alert_type}</h1>
                <p>{ticket.current_state}</p>
                <div className="simulation-meta">
                  <span>{ticket.incident_id}</span>
                  <span>{ticket.priority}</span>
                  <span>{ticket.ci}</span>
                </div>
              </div>
              <div className="simulation-actions">
                <button
                  className="start-simulation"
                  type="button"
                  onClick={startSimulation}
                  disabled={simulationStarted && !closed}
                >
                  <PlayCircle size={18} aria-hidden="true" />
                  {closed
                    ? 'Restart Simulation'
                    : simulationStarted
                      ? 'Simulation Running'
                      : 'Start Simulation'}
                </button>
                <span className="run-intimation">
                  {runIntimation(status, mode, simulationStarted)}
                </span>
              </div>
            </section>
          </div>

          <MetricsRibbon events={events} mode={mode} rca={rca} />
          <LiveAiProof
            backendOnline={backendOnline}
            events={events}
            mode={mode}
            runId={runId}
          />

          <div className="workbench-grid">
            <RunTimeline events={events} mode={mode} status={status} />
            <DecisionPanel events={events} plan={plan} />
          </div>

          <div className="bottom-grid">
            <ScriptReviewPanel
              plan={plan}
              ticket={ticket}
              waitingForApproval={waitingForApproval}
            />
            <div className="decision-stack">
              <ApprovalBar
                mode={mode}
                waitingForApproval={waitingForApproval}
                onApprove={approve}
                onReject={reject}
              />
              <ClosureBar
                mode={mode}
                waitingForClosure={waitingForClosure}
                observing={observing}
                closed={closed}
                onCloseIncident={closeIncident}
                onObserveIncident={observeIncident}
              />
              <RcaPanel rca={rca} />
            </div>
            <AuditTrail events={events} />
          </div>

          <div className="governance-bottom-grid">
            <EvidencePanel events={events} />
            <PolicyCheckPanel
              backendOnline={backendOnline}
              checks={checks}
              demoChecks={policyDemoChecks}
              demoError={policyDemoError}
              demoLoading={policyDemoLoading}
              onLoadDemo={loadPolicyDemo}
            />
          </div>
        </>
      )}
    </main>
  );
}

export default App;
