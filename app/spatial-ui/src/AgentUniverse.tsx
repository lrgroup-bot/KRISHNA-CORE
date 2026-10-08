import { useCallback, useEffect, useMemo, useState } from 'react';
import { Background, Controls, MarkerType, ReactFlow, type Edge, type Node } from '@xyflow/react';
import { Activity, BrainCircuit, Network, RefreshCw, ShieldCheck, X } from 'lucide-react';
import '@xyflow/react/dist/style.css';
import './pipeline.css';

type AgentState = 'working' | 'healing' | 'blocked' | 'verified' | 'quiet' | 'unverified';
type JsonMap = Record<string, unknown>;

type AgentDefinition = {
  id: string;
  label: string;
  role: string;
  endpoint?: string;
  position: { x: number; y: number };
};

const AGENTS: AgentDefinition[] = [
  { id: 'krishna', label: 'KRISHNA', role: 'Authority · conversation · orchestration', endpoint: '/api/status', position: { x: 620, y: 300 } },
  { id: 'sudarshan', label: 'SUDARSHAN', role: 'Execution · testing · verification', endpoint: '/api/tasks?project=KRISHNA&limit=100', position: { x: 940, y: 300 } },
  { id: 'brahma', label: 'BRAHMA', role: 'Knowledge process · Rishi coordination', endpoint: '/api/brahma/status', position: { x: 300, y: 90 } },
  { id: 'brahmagyan', label: 'BRAHMAGYAN', role: 'Deep research · synthesis', position: { x: 60, y: 30 } },
  { id: 'rishi-council', label: 'RISHI COUNCIL', role: 'Specialist reasoning council', position: { x: 60, y: 160 } },
  { id: 'gyan-bhandar', label: 'GYAN-BHANDAR', role: 'Verified knowledge archive', endpoint: '/api/gyan-bhandar/archive/status', position: { x: 60, y: 290 } },
  { id: 'garudanetra', label: 'GARUDANETRA', role: 'Browser · web research · evidence', endpoint: '/api/garudanetra/fabric', position: { x: 300, y: 500 } },
  { id: 'hawkeye', label: 'HAWKEYE', role: 'Vision · mobile · field sensing', endpoint: '/api/hawkeye/ruview/status', position: { x: 60, y: 560 } },
  { id: 'suryadev', label: 'SURYADEV', role: 'Screen/audio learning', position: { x: 60, y: 690 } },
  { id: 'chandradev', label: 'CHANDRADEV', role: 'Camera observation', position: { x: 300, y: 690 } },
  { id: 'kabach', label: 'KABACH', role: 'Security · privacy · boundaries', endpoint: '/api/kabach/privacy/status', position: { x: 1180, y: 30 } },
  { id: 'mrityunjaya', label: 'MRITYUNJAYA', role: 'Diagnosis · recovery · self-heal', endpoint: '/api/mrityunjay/status', position: { x: 1420, y: 160 } },
  { id: 'ui-guardian', label: 'UI GUARDIAN', role: 'Rendered UI verification', endpoint: '/api/ui-guardian/registry?project=KRISHNA', position: { x: 1420, y: 420 } },
  { id: 'vishwakarma', label: 'VISHWAKARMA', role: 'Engineering · repair · design verification', endpoint: '/api/design/status', position: { x: 1180, y: 560 } },
  { id: 'narad', label: 'NARAD', role: 'Messaging · workflows · automation', position: { x: 1420, y: 690 } },
];

const LINKS: Array<[string, string]> = [
  ['krishna', 'sudarshan'],
  ['krishna', 'brahma'], ['brahma', 'brahmagyan'], ['brahma', 'rishi-council'], ['brahma', 'gyan-bhandar'],
  ['krishna', 'garudanetra'], ['garudanetra', 'hawkeye'], ['garudanetra', 'suryadev'], ['garudanetra', 'chandradev'],
  ['krishna', 'kabach'], ['kabach', 'mrityunjaya'], ['sudarshan', 'ui-guardian'], ['sudarshan', 'vishwakarma'], ['sudarshan', 'narad'],
  ['mrityunjaya', 'sudarshan'], ['ui-guardian', 'krishna'], ['vishwakarma', 'sudarshan'], ['narad', 'krishna'],
];

const STATE_COLOR: Record<AgentState, string> = {
  working: '#45BDF5', healing: '#F4B860', blocked: '#FA7E85', verified: '#53E7A3', quiet: '#708694', unverified: '#6B7280',
};

function statusText(value: unknown): string {
  return typeof value === 'string' ? value.toLowerCase() : '';
}

function ownerText(task: JsonMap): string {
  const candidates = [task.assigned_specialist, task.assignedSpecialist, task.specialist, task.agent, task.owner, task.worker, task.assignee];
  return candidates.filter((value) => typeof value === 'string').join(' ').toLowerCase();
}

function deriveTaskState(task: JsonMap): AgentState {
  const status = statusText(task.status);
  if (['working', 'running', 'executing', 'verifying', 'queued'].includes(status)) return 'working';
  if (['healing', 'recovering', 'retrying'].includes(status)) return 'healing';
  if (['blocked', 'failed', 'error'].includes(status)) return 'blocked';
  if (['verified', 'done', 'completed', 'complete', 'passed'].includes(status)) return 'verified';
  return 'quiet';
}

function agentMatches(agent: AgentDefinition, task: JsonMap): boolean {
  const owner = ownerText(task).replaceAll('_', ' ').replaceAll('-', ' ');
  const candidates = [agent.id, agent.label].map((value) => value.toLowerCase().replaceAll('_', ' ').replaceAll('-', ' '));
  return Boolean(owner) && candidates.some((candidate) => owner.includes(candidate));
}

export default function AgentUniverse({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [tasks, setTasks] = useState<JsonMap[]>([]);
  const [coreOnline, setCoreOnline] = useState(false);
  const [mrityunjayaBusy, setMrityunjayaBusy] = useState(false);
  const [selectedId, setSelectedId] = useState('krishna');
  const [snapshot, setSnapshot] = useState<unknown>(null);
  const [snapshotError, setSnapshotError] = useState('');
  const [loadingSnapshot, setLoadingSnapshot] = useState(false);
  const [lastRefresh, setLastRefresh] = useState<number | null>(null);

  const refresh = useCallback(async () => {
    const [healthResult, taskResult, statusResult] = await Promise.allSettled([
      fetch('/health', { cache: 'no-store' }).then(async (response) => response.ok ? response.json() : Promise.reject(new Error(`HTTP ${response.status}`))),
      fetch('/api/tasks?project=KRISHNA&limit=200', { cache: 'no-store' }).then(async (response) => response.ok ? response.json() : Promise.reject(new Error(`HTTP ${response.status}`))),
      fetch('/api/status', { cache: 'no-store' }).then(async (response) => response.ok ? response.json() : Promise.reject(new Error(`HTTP ${response.status}`))),
    ]);
    if (healthResult.status === 'fulfilled') {
      const value = healthResult.value as JsonMap;
      setCoreOnline(value.ok === true && value.core === 'ONLINE');
    } else setCoreOnline(false);
    if (taskResult.status === 'fulfilled') {
      const value = taskResult.value as JsonMap;
      setTasks(Array.isArray(value.tasks) ? value.tasks as JsonMap[] : []);
    } else setTasks([]);
    if (statusResult.status === 'fulfilled') {
      const value = statusResult.value as JsonMap;
      const mrityunjay = value.mrityunjay as JsonMap | undefined;
      setMrityunjayaBusy(Boolean(mrityunjay?.busy));
    } else setMrityunjayaBusy(false);
    setLastRefresh(Date.now());
  }, []);

  useEffect(() => {
    if (!open) return;
    void refresh();
    const timer = window.setInterval(() => void refresh(), 4000);
    return () => window.clearInterval(timer);
  }, [open, refresh]);

  const agentStates = useMemo(() => {
    const map = new Map<string, AgentState>();
    AGENTS.forEach((agent) => {
      const matched = tasks.filter((task) => agentMatches(agent, task));
      const states = matched.map(deriveTaskState);
      let state: AgentState = 'quiet';
      if (states.includes('blocked')) state = 'blocked';
      else if (states.includes('healing')) state = 'healing';
      else if (states.includes('working')) state = 'working';
      else if (states.includes('verified')) state = 'verified';
      if (agent.id === 'krishna') state = coreOnline ? (tasks.some((task) => deriveTaskState(task) === 'working') ? 'working' : 'verified') : 'unverified';
      if (agent.id === 'sudarshan' && tasks.some((task) => deriveTaskState(task) === 'working')) state = 'working';
      if (agent.id === 'mrityunjaya' && mrityunjayaBusy) state = 'healing';
      map.set(agent.id, state);
    });
    return map;
  }, [coreOnline, mrityunjayaBusy, tasks]);

  const nodes = useMemo<Node[]>(() => AGENTS.map((agent) => {
    const state = agentStates.get(agent.id) ?? 'unverified';
    const selected = selectedId === agent.id;
    const color = STATE_COLOR[state];
    const matched = tasks.filter((task) => agentMatches(agent, task));
    return {
      id: agent.id,
      position: agent.position,
      data: { label: <div className="agent-node-inner"><span>{agent.label}</span><small>{agent.role}</small><b style={{ color }}>{state.toUpperCase()}</b>{matched.length ? <i>{matched.length} task{matched.length === 1 ? '' : 's'}</i> : null}</div> },
      style: {
        width: agent.id === 'krishna' || agent.id === 'sudarshan' ? 230 : 205,
        border: `1.5px solid ${selected ? '#EDCB83' : color}`,
        background: agent.id === 'krishna' ? 'linear-gradient(145deg,rgba(237,203,131,.16),rgba(7,25,38,.96))' : 'rgba(7,24,36,.94)',
        color: '#E9F3F8', borderRadius: 16, padding: 0,
        boxShadow: state === 'working' ? `0 0 26px ${color}55` : selected ? '0 0 22px rgba(237,203,131,.24)' : '0 8px 24px rgba(0,0,0,.28)',
      },
    };
  }), [agentStates, selectedId, tasks]);

  const edges = useMemo<Edge[]>(() => LINKS.map(([source, target]) => {
    const sourceState = agentStates.get(source) ?? 'unverified';
    const targetState = agentStates.get(target) ?? 'unverified';
    const active = ['working', 'healing'].includes(sourceState) || ['working', 'healing'].includes(targetState);
    const color = active ? '#45BDF5' : 'rgba(104,157,178,.42)';
    return {
      id: `agent-${source}-${target}`, source, target, animated: active,
      className: active ? 'pipeline-flow-active' : undefined,
      style: { stroke: color, strokeWidth: active ? 2.6 : 1.4 },
      markerEnd: { type: MarkerType.ArrowClosed, color },
    };
  }), [agentStates]);

  const selected = AGENTS.find((agent) => agent.id === selectedId) ?? AGENTS[0];
  const selectedTasks = tasks.filter((task) => agentMatches(selected, task));

  useEffect(() => {
    if (!open) return;
    setSnapshot(null); setSnapshotError('');
    if (!selected.endpoint) return;
    let cancelled = false;
    setLoadingSnapshot(true);
    fetch(selected.endpoint, { cache: 'no-store' })
      .then(async (response) => {
        const body = await response.text();
        if (!response.ok) throw new Error(`HTTP ${response.status}${body ? ` · ${body.slice(0, 140)}` : ''}`);
        try { return JSON.parse(body) as unknown; } catch { throw new Error('Endpoint returned non-JSON data'); }
      })
      .then((data) => { if (!cancelled) setSnapshot(data); })
      .catch((reason: unknown) => { if (!cancelled) setSnapshotError(reason instanceof Error ? reason.message : String(reason)); })
      .finally(() => { if (!cancelled) setLoadingSnapshot(false); });
    return () => { cancelled = true; };
  }, [open, selected]);

  if (!open) return null;

  return <div className="pipeline-overlay" role="dialog" aria-modal="true" aria-label="KRISHNA Intelligence Universe">
    <div className="pipeline-shell agent-universe-shell">
      <header className="pipeline-header"><div><span className="pipeline-kicker">INTERNAL INTELLIGENCE MAP</span><h2><Network size={20} /> KRISHNA Intelligence Universe</h2><p>Live task-derived activity. Quiet nodes are not claimed healthy unless their own endpoint verifies them.</p></div><div className="pipeline-header-actions"><button type="button" onClick={() => void refresh()} title="Refresh intelligence map"><RefreshCw size={17} /></button><button type="button" onClick={onClose} title="Close"><X size={19} /></button></div></header>
      <div className="pipeline-grid">
        <div className="pipeline-canvas"><ReactFlow nodes={nodes} edges={edges} fitView minZoom={0.35} maxZoom={1.7} nodesDraggable={false} onNodeClick={(_, node) => setSelectedId(node.id)} proOptions={{ hideAttribution: true }}><Background color="#17425d" gap={28} size={1} /><Controls position="bottom-right" /></ReactFlow><div className="pipeline-legend"><span><i className="state working" />Working</span><span><i className="state verified" />Verified/online</span><span><i className="state healing" />Healing</span><span><i className="state blocked" />Blocked</span><span><i className="state quiet" />Quiet/unobserved</span></div></div>
        <aside className="pipeline-inspector"><div className="inspector-title"><BrainCircuit size={18} /><div><span>SELECTED INTELLIGENCE</span><h3>{selected.label}</h3></div></div><p className="inspector-role">{selected.role}</p><div className="inspector-stat"><Activity size={15} /><span>Pipeline state</span><strong style={{ color: STATE_COLOR[agentStates.get(selected.id) ?? 'unverified'] }}>{(agentStates.get(selected.id) ?? 'unverified').toUpperCase()}</strong></div><div className="inspector-stat"><ShieldCheck size={15} /><span>Mapped tasks</span><strong>{selectedTasks.length}</strong></div>
          <section className="inspector-section"><h4>CURRENT TASK TELEMETRY</h4>{selectedTasks.length ? selectedTasks.slice(0, 8).map((task, index) => <div className="inspector-task" key={String(task.id ?? task.task_id ?? index)}><b>{String(task.title ?? task.name ?? task.id ?? task.task_id ?? 'Task')}</b><span>{String(task.status ?? 'unknown')}</span></div>) : <p>No active ledger task is currently attributed to this agent.</p>}</section>
          <section className="inspector-section"><h4>AGENT DASHBOARD SNAPSHOT</h4>{loadingSnapshot ? <p>Loading verified endpoint…</p> : snapshotError ? <p className="pipeline-error">{snapshotError}</p> : snapshot ? <pre>{JSON.stringify(snapshot, null, 2)}</pre> : <p>{selected.endpoint ? 'No snapshot returned.' : 'No dedicated endpoint mapped yet. Task telemetry remains available.'}</p>}</section>
          <div className="inspector-foot">Last graph refresh: {lastRefresh ? new Date(lastRefresh).toLocaleTimeString() : '—'}</div>
        </aside>
      </div>
    </div>
  </div>;
}
