import { useEffect, useMemo, useRef, useState } from 'react';
import { ShieldCheck } from 'lucide-react';
import { approveRun, connectRunStream, healthCheck, rejectRun, startIncident } from './api';
import { loadReplayEvents, playReplayEvents } from './replay';
import { ApprovalBar } from './components/ApprovalBar';
import { AuditTrail } from './components/AuditTrail';
import { EvidencePanel } from './components/EvidencePanel';
import { MetricsRibbon } from './components/MetricsRibbon';
import { ModeSwitch } from './components/ModeSwitch';
import { PolicyCheckPanel } from './components/PolicyCheckPanel';
import { RcaPanel } from './components/RcaPanel';
import { RunTimeline } from './components/RunTimeline';
import { ScriptReviewPanel } from './components/ScriptReviewPanel';
import { TicketPanel } from './components/TicketPanel';
import type { Mode, PolicyCheck, RcaSummary, RemediationPlan, RunEvent, TicketDetails } from './types';

const initialTicket: TicketDetails = {
  incident_id: 'INC-2026-00421',
  priority: 'P4',
  ci: 'APP-WIN-042',
  service: 'Internal Claims Portal',
};

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
    return mode === 'replay' ? 'Replay queued' : 'Live idle';
  }
  if (last.type === 'approval.requested') return 'Waiting approval';
  if (last.type === 'rca.generated') return 'Resolved';
  if (last.type.includes('blocked')) return 'Blocked';
  if (last.type.includes('rejected')) return 'Rejected';
  return 'Running';
}

function App() {
  const [mode, setMode] = useState<Mode>('replay');
  const [events, setEvents] = useState<RunEvent[]>([]);
  const [backendOnline, setBackendOnline] = useState(false);
  const [runId, setRunId] = useState<string | null>('replay-disk-space');
  const [notice, setNotice] = useState('Replay Mode');
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    healthCheck().then(setBackendOnline);
  }, []);

  useEffect(() => {
    if (mode !== 'replay') return undefined;
    let stop: () => void = () => undefined;
    let cancelled = false;
    loadReplayEvents()
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
  }, [mode]);

  useEffect(() => {
    return () => socketRef.current?.close();
  }, []);

  const plan = useMemo(() => extractPlan(events), [events]);
  const checks = useMemo(() => extractChecks(events), [events]);
  const rca = useMemo(() => extractRca(events), [events]);
  const status = runStatus(events, mode);
  const waitingForApproval = events.at(-1)?.type === 'approval.requested';

  async function startLive() {
    setMode('live');
    setEvents([]);
    setNotice('Starting Local Live Mode');
    const run = await startIncident();
    setRunId(run.run_id);
    socketRef.current?.close();
    socketRef.current = connectRunStream(
      run.run_id,
      (event) => setEvents((current) => [...current, event]),
      () => setNotice('Live stream closed'),
    );
    setNotice('Local Live Mode');
  }

  function activateReplay() {
    socketRef.current?.close();
    setEvents([]);
    setRunId('replay-disk-space');
    setNotice('Replay Mode');
    setMode('replay');
  }

  async function approve() {
    if (runId) await approveRun(runId);
  }

  async function reject() {
    if (runId) await rejectRun(runId);
  }

  return (
    <main className="console-shell">
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
        <ModeSwitch
          mode={mode}
          backendOnline={backendOnline}
          onModeChange={(nextMode) => {
            if (nextMode === 'replay') {
              activateReplay();
            } else {
              setMode('live');
              setNotice(backendOnline ? 'Local Live Mode' : 'Backend offline');
            }
          }}
          onStartLive={startLive}
        />
      </header>

      <MetricsRibbon events={events} rca={rca} />

      <div className="console-grid">
        <TicketPanel ticket={initialTicket} />
        <RunTimeline events={events} />
        <div className="right-stack">
          <EvidencePanel events={events} />
          <PolicyCheckPanel checks={checks} />
        </div>
      </div>

      <div className="bottom-grid">
        <ScriptReviewPanel plan={plan} />
        <div className="decision-stack">
          <ApprovalBar
            mode={mode}
            waitingForApproval={waitingForApproval}
            onApprove={approve}
            onReject={reject}
          />
          <RcaPanel rca={rca} />
        </div>
        <AuditTrail events={events} />
      </div>
    </main>
  );
}

export default App;
