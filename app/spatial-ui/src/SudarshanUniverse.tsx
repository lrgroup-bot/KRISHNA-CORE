import { useCallback, useEffect, useMemo, useState } from 'react';
import { Background, Controls, MarkerType, ReactFlow, type Edge, type Node } from '@xyflow/react';
import { Activity, CheckCircle2, CircleAlert, Network, RefreshCw, ShieldCheck } from 'lucide-react';
import '@xyflow/react/dist/style.css';
import './pipeline.css';

type JsonMap = Record<string, unknown>;
type PipelineState = 'pending' | 'working' | 'verified' | 'healing' | 'blocked' | 'failed' | 'unknown';

const STATUS_COLOR: Record<PipelineState, string> = {
  pending: '#708694', working: '#45BDF5', verified: '#53E7A3', healing: '#F4B860', blocked: '#FA7E85', failed: '#FA7E85', unknown: '#6B7280',
};

function stateOf(task: JsonMap): PipelineState {
  const raw = String(task.status ?? '').toLowerCase();
  if (['working', 'running', 'executing', 'queued', 'verifying'].includes(raw)) return 'working';
  if (['verified', 'done', 'completed', 'complete', 'passed'].includes(raw)) return 'verified';
  if (['healing', 'recovering', 'retrying'].includes(raw)) return 'healing';
  if (['blocked', 'waiting_approval'].includes(raw)) return 'blocked';
  if (['failed', 'error'].includes(raw)) return 'failed';
  if (['pending', 'waiting', 'ready', 'idle'].includes(raw)) return 'pending';
  return 'unknown';
}

function idOf(task: JsonMap, index: number): string {
  return String(task.id ?? task.task_id ?? task.taskId ?? `task-${index}`);
}

function titleOf(task: JsonMap, index: number): string {
  return String(task.title ?? task.name ?? task.summary ?? task.description ?? `Task ${index + 1}`);
}

function ownerOf(task: JsonMap): string {
  return String(task.assigned_specialist ?? task.assignedSpecialist ?? task.specialist ?? task.agent ?? task.owner ?? task.worker ?? task.assignee ?? 'Unassigned');
}

function progressOf(task: JsonMap, state: PipelineState): number | null {
  const value = task.progress ?? task.progress_percent ?? task.percent;
  const numeric = typeof value === 'number' ? value : typeof value === 'string' ? Number(value) : NaN;
  if (Number.isFinite(numeric)) return Math.max(0, Math.min(100, numeric));
  if (state === 'verified') return 100;
  return null;
}

function dependenciesOf(task: JsonMap): string[] {
  const raw = task.dependencies ?? task.depends_on ?? task.dependency_ids ?? task.dependsOn;
  if (!Array.isArray(raw)) return [];
  return raw.map(String).filter(Boolean);
}

export default function SudarshanUniverse() {
  const [tasks, setTasks] = useState<JsonMap[]>([]);
  const [projectGraph, setProjectGraph] = useState<unknown>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [error, setError] = useState('');
  const [lastRefresh, setLastRefresh] = useState<number | null>(null);

  const refresh = useCallback(async () => {
    setError('');
    const [tasksResult, graphResult] = await Promise.allSettled([
      fetch('/api/tasks?project=KRISHNA&limit=300', { cache: 'no-store' }).then(async (response) => {
        const text = await response.text();
        if (!response.ok) throw new Error(`Tasks HTTP ${response.status}`);
        return JSON.parse(text) as JsonMap;
      }),
      fetch('/api/project-graph', { cache: 'no-store' }).then(async (response) => {
        const text = await response.text();
        if (!response.ok) throw new Error(`Project graph HTTP ${response.status}`);
        return JSON.parse(text) as unknown;
      }),
    ]);
    if (tasksResult.status === 'fulfilled') {
      const list = Array.isArray(tasksResult.value.tasks) ? tasksResult.value.tasks as JsonMap[] : [];
      setTasks(list);
      setSelectedId((current) => current && list.some((task, index) => idOf(task, index) === current) ? current : (list[0] ? idOf(list[0], 0) : null));
    } else {
      setTasks([]);
      setError(tasksResult.reason instanceof Error ? tasksResult.reason.message : String(tasksResult.reason));
    }
    if (graphResult.status === 'fulfilled') setProjectGraph(graphResult.value);
    else setProjectGraph(null);
    setLastRefresh(Date.now());
  }, []);

  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => void refresh(), 3500);
    return () => window.clearInterval(timer);
  }, [refresh]);

  const nodes = useMemo<Node[]>(() => tasks.map((task, index) => {
    const id = idOf(task, index);
    const state = stateOf(task);
    const color = STATUS_COLOR[state];
    const progress = progressOf(task, state);
    const column = index % 4;
    const row = Math.floor(index / 4);
    return {
      id,
      position: { x: 45 + column * 280, y: 65 + row * 180 },
      data: { label: <div className="task-node-inner"><div><span>{ownerOf(task)}</span><b style={{ color }}>{state.toUpperCase()}</b></div><strong>{titleOf(task, index)}</strong><small>{progress == null ? 'Progress unavailable' : `${progress}% complete`}</small>{progress != null ? <i><em style={{ width: `${progress}%`, background: color }} /></i> : null}</div> },
      style: { width: 245, border: `1.5px solid ${selectedId === id ? '#EDCB83' : color}`, borderRadius: 14, padding: 0, background: 'rgba(7,23,35,.95)', color: '#E9F3F8', boxShadow: state === 'working' ? `0 0 22px ${color}55` : '0 8px 24px rgba(0,0,0,.28)' },
    };
  }), [selectedId, tasks]);

  const taskIds = useMemo(() => new Set(nodes.map((node) => node.id)), [nodes]);
  const edges = useMemo<Edge[]>(() => {
    const result: Edge[] = [];
    tasks.forEach((task, index) => {
      const id = idOf(task, index);
      const state = stateOf(task);
      const active = state === 'working' || state === 'healing';
      const color = active ? '#45BDF5' : STATUS_COLOR[state];
      dependenciesOf(task).forEach((dependencyId) => {
        if (!taskIds.has(dependencyId)) return;
        result.push({
          id: `e-${dependencyId}-${id}`, source: dependencyId, target: id, animated: active,
          className: active ? 'pipeline-flow-active' : undefined,
          style: { stroke: color, strokeWidth: active ? 2.5 : 1.7 }, markerEnd: { type: MarkerType.ArrowClosed, color },
        });
      });
    });
    return result;
  }, [taskIds, tasks]);

  const selectedEntry = useMemo(() => {
    if (!selectedId) return null;
    const index = tasks.findIndex((task, taskIndex) => idOf(task, taskIndex) === selectedId);
    return index >= 0 ? { task: tasks[index], index } : null;
  }, [selectedId, tasks]);

  const counts = useMemo(() => {
    const output = { working: 0, verified: 0, healing: 0, blocked: 0 };
    tasks.forEach((task) => {
      const state = stateOf(task);
      if (state === 'working') output.working++;
      else if (state === 'verified') output.verified++;
      else if (state === 'healing') output.healing++;
      else if (state === 'blocked' || state === 'failed') output.blocked++;
    });
    return output;
  }, [tasks]);

  return <section className="sudarshan-universe">
    <header className="sudarshan-header"><div><span className="pipeline-kicker">AUTONOMOUS EXECUTION · VERIFIED DELIVERY</span><h1>SUDARSHAN <em>PIPELINE</em></h1><p>Real task ledger visualization. Dependency arrows appear only when dependencies are present in backend task data.</p></div><button type="button" onClick={() => void refresh()}><RefreshCw size={17} />Refresh</button></header>
    <div className="sudarshan-statbar"><div><Activity size={16} /><span>Working</span><strong>{counts.working}</strong></div><div><CheckCircle2 size={16} /><span>Verified</span><strong>{counts.verified}</strong></div><div><RefreshCw size={16} /><span>Healing</span><strong>{counts.healing}</strong></div><div><CircleAlert size={16} /><span>Blocked/failed</span><strong>{counts.blocked}</strong></div><div><ShieldCheck size={16} /><span>Total ledger</span><strong>{tasks.length}</strong></div></div>
    {error ? <div className="pipeline-error sudarshan-error">{error}</div> : null}
    <div className="sudarshan-grid"><div className="pipeline-canvas sudarshan-canvas">{nodes.length ? <ReactFlow nodes={nodes} edges={edges} fitView minZoom={0.35} maxZoom={1.8} nodesDraggable onNodeClick={(_, node) => setSelectedId(node.id)} proOptions={{ hideAttribution: true }}><Background color="#17425d" gap={28} size={1} /><Controls position="bottom-right" /></ReactFlow> : <div className="pipeline-empty"><Network size={38} /><h3>No KRISHNA task ledger entries</h3><p>The pipeline will populate from /api/tasks when Sudarshan has real work.</p></div>}</div><aside className="pipeline-inspector sudarshan-inspector"><div className="inspector-title"><Network size={18} /><div><span>PIPELINE INSPECTOR</span><h3>{selectedEntry ? titleOf(selectedEntry.task, selectedEntry.index) : 'Select a task'}</h3></div></div>{selectedEntry ? <><div className="inspector-stat"><Activity size={15} /><span>Status</span><strong style={{ color: STATUS_COLOR[stateOf(selectedEntry.task)] }}>{stateOf(selectedEntry.task).toUpperCase()}</strong></div><div className="inspector-stat"><ShieldCheck size={15} /><span>Owner</span><strong>{ownerOf(selectedEntry.task)}</strong></div><section className="inspector-section"><h4>DEPENDENCIES</h4>{dependenciesOf(selectedEntry.task).length ? dependenciesOf(selectedEntry.task).map((dep) => <div className="inspector-task" key={dep}><b>{dep}</b><span>required</span></div>) : <p>No dependency IDs are exposed for this task.</p>}</section><section className="inspector-section"><h4>LIVE TASK RECORD</h4><pre>{JSON.stringify(selectedEntry.task, null, 2)}</pre></section></> : <p className="inspector-role">Click any task node to inspect its exact backend record.</p>}<section className="inspector-section"><h4>PROJECT GRAPH SOURCE</h4>{projectGraph ? <details><summary>View backend project graph snapshot</summary><pre>{JSON.stringify(projectGraph, null, 2)}</pre></details> : <p>Project graph endpoint unavailable or empty.</p>}</section><div className="inspector-foot">Last refresh: {lastRefresh ? new Date(lastRefresh).toLocaleTimeString() : '—'}</div></aside></div>
  </section>;
}
