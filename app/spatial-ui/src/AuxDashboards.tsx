import { useCallback, useEffect, useMemo, useState } from 'react';
import { Activity, Blocks, CheckCircle2, CircleAlert, Globe2, MessageSquareText, RefreshCw, ShieldCheck, Workflow } from 'lucide-react';

type JsonMap = Record<string, unknown>;

function usePolling(fetcher: () => Promise<unknown>, delay = 6000) {
  const [data, setData] = useState<unknown>(null);
  const [error, setError] = useState('');
  const [lastRefresh, setLastRefresh] = useState<number | null>(null);
  const refresh = useCallback(async () => {
    setError('');
    try { setData(await fetcher()); } catch (reason) { setError(reason instanceof Error ? reason.message : String(reason)); }
    setLastRefresh(Date.now());
  }, [fetcher]);
  useEffect(() => { void refresh(); const timer = window.setInterval(() => void refresh(), delay); return () => window.clearInterval(timer); }, [delay, refresh]);
  return { data, error, lastRefresh, refresh };
}

async function json(url: string) {
  const response = await fetch(url, { cache: 'no-store' });
  const text = await response.text();
  if (!response.ok) throw new Error(`HTTP ${response.status}${text ? ` · ${text.slice(0,120)}` : ''}`);
  try { return JSON.parse(text) as unknown; } catch { throw new Error('Endpoint returned non-JSON data'); }
}

function FloatingHeader({ kicker, title, description, refresh }: { kicker: string; title: string; description: string; refresh: () => void }) {
  return <header className="floating-page-header"><div><span>{kicker}</span><h1>{title}</h1><p>{description}</p></div><button type="button" onClick={refresh}><RefreshCw size={16}/>Refresh</button></header>;
}

function RawDetails({ value }: { value: unknown }) { return value ? <details className="raw-details"><summary>Raw verified telemetry</summary><pre>{JSON.stringify(value,null,2)}</pre></details> : null; }

export function ProjectsDashboard() {
  const fetcher = useCallback(() => json('/api/tasks?limit=300'), []);
  const { data, error, lastRefresh, refresh } = usePolling(fetcher, 5000);
  const tasks = data && typeof data === 'object' && Array.isArray((data as JsonMap).tasks) ? (data as JsonMap).tasks as JsonMap[] : [];
  const projects = useMemo(() => {
    const map = new Map<string, { total: number; active: number; blocked: number }>();
    tasks.forEach((task) => {
      const name = String(task.project ?? 'Unassigned');
      const row = map.get(name) ?? { total:0, active:0, blocked:0 };
      row.total++;
      const status = String(task.status ?? '').toLowerCase();
      if (['queued','running','working','executing','verifying'].includes(status)) row.active++;
      if (['blocked','failed','error','waiting_approval'].includes(status)) row.blocked++;
      map.set(name,row);
    });
    return [...map.entries()];
  }, [tasks]);
  return <section className="floating-page"><FloatingHeader kicker="LIVE PROJECT LEDGER" title="Projects" description="Project cards are generated from KRISHNA's real task ledger." refresh={refresh}/>{error ? <div className="live-error">{error}</div> : null}<div className="floating-card-grid">{projects.length ? projects.map(([name,row]) => <article className="floating-card" key={name}><Workflow/><h3>{name}</h3><div className="floating-metric"><span>Total tasks</span><strong>{row.total}</strong></div><div className="floating-metric"><span>Active</span><strong className="tone-blue">{row.active}</strong></div><div className="floating-metric"><span>Blocked</span><strong className={row.blocked ? 'tone-red' : ''}>{row.blocked}</strong></div></article>) : <article className="floating-card empty-card"><Workflow/><h3>No project telemetry yet</h3><p>Projects will appear when the task ledger exposes project records.</p></article>}</div><div className="refresh-note">Last refresh: {lastRefresh ? new Date(lastRefresh).toLocaleTimeString() : '—'}</div></section>;
}

export function ChatsDashboard() {
  const fetcher = useCallback(() => json('/api/chats?project=KRISHNA'), []);
  const { data, error, lastRefresh, refresh } = usePolling(fetcher, 7000);
  const chats = data && typeof data === 'object' && Array.isArray((data as JsonMap).chats) ? (data as JsonMap).chats as JsonMap[] : [];
  return <section className="floating-page"><FloatingHeader kicker="CONVERSATION MEMORY" title="Chats" description="Live KRISHNA conversation index from the backend." refresh={refresh}/>{error ? <div className="live-error">{error}</div> : null}<div className="floating-list">{chats.length ? chats.map((chat,index) => <article className="floating-row" key={String(chat.id ?? chat.chat_id ?? index)}><MessageSquareText/><div><h3>{String(chat.title ?? chat.name ?? chat.chat_id ?? chat.id ?? `Chat ${index+1}`)}</h3><p>{String(chat.project ?? 'KRISHNA')}</p></div><span>{String(chat.updated ?? chat.updated_at ?? '')}</span></article>) : <div className="pipeline-empty"><MessageSquareText/><h3>No chats returned</h3><p>The backend chat index is empty or this runtime has not created a conversation yet.</p></div>}</div><div className="refresh-note">Last refresh: {lastRefresh ? new Date(lastRefresh).toLocaleTimeString() : '—'}</div></section>;
}

export function PluginsDashboard() {
  const fetcher = useCallback(async () => {
    const candidates = ['/api/plugins','/api/plugin-registry','/api/plugins/status'];
    let last = '';
    for (const url of candidates) {
      try { return { url, body: await json(url) }; } catch (reason) { last = reason instanceof Error ? reason.message : String(reason); }
    }
    throw new Error(`Plugin registry endpoint not available · ${last}`);
  }, []);
  const { data, error, lastRefresh, refresh } = usePolling(fetcher, 10000);
  const envelope = data as { url?: string; body?: unknown } | null;
  return <section className="floating-page"><FloatingHeader kicker="CAPABILITY REGISTRY" title="Plugins" description="Read-only live capability view. Installation or enable actions are intentionally not exposed here." refresh={refresh}/>{error ? <div className="live-error">{error}</div> : <div className="floating-hero-card"><Blocks/><div><h2>Registry connected</h2><p>{envelope?.url}</p></div><CheckCircle2 className="tone-green"/></div>}<RawDetails value={envelope?.body}/><div className="refresh-note">Last refresh: {lastRefresh ? new Date(lastRefresh).toLocaleTimeString() : '—'}</div></section>;
}

export function LRUniverseDashboard() {
  const fetcher = useCallback(async () => {
    const [status, tasks, commitments] = await Promise.allSettled([json('/api/status'), json('/api/tasks?limit=300'), json('/api/commitments?project=LR%20Universe')]);
    return { status: status.status === 'fulfilled' ? status.value : null, tasks: tasks.status === 'fulfilled' ? tasks.value : null, commitments: commitments.status === 'fulfilled' ? commitments.value : null };
  }, []);
  const { data, error, lastRefresh, refresh } = usePolling(fetcher, 6000);
  const value = (data ?? {}) as JsonMap;
  const taskBody = value.tasks as JsonMap | null;
  const allTasks = taskBody && Array.isArray(taskBody.tasks) ? taskBody.tasks as JsonMap[] : [];
  const lrTasks = allTasks.filter((task) => /lr\s*-?\s*universe/i.test(String(task.project ?? '')) || /lr\s*-?\s*universe/i.test(JSON.stringify(task)));
  const active = lrTasks.filter((task) => ['queued','running','working','executing','verifying'].includes(String(task.status ?? '').toLowerCase())).length;
  const blocked = lrTasks.filter((task) => ['blocked','failed','error','waiting_approval'].includes(String(task.status ?? '').toLowerCase())).length;
  return <section className="floating-page lr-dashboard"><FloatingHeader kicker="OWNER BUSINESS UNIVERSE" title="LR Universe Dashboard" description="KRISHNA-side operational view of LR Universe work. No business status is invented when telemetry is absent." refresh={refresh}/>{error ? <div className="live-error">{error}</div> : null}<div className="floating-card-grid"><article className="floating-card"><Globe2/><h3>Observed LR tasks</h3><strong className="big-number">{lrTasks.length}</strong><p>Task ledger records matched to LR Universe.</p></article><article className="floating-card"><Activity/><h3>Working</h3><strong className="big-number tone-blue">{active}</strong><p>Queued/running/executing/verifying.</p></article><article className="floating-card"><CircleAlert/><h3>Needs attention</h3><strong className={`big-number ${blocked ? 'tone-red':''}`}>{blocked}</strong><p>Blocked, failed, error or waiting approval.</p></article><article className="floating-card"><ShieldCheck/><h3>KRISHNA authority</h3><strong>{value.status ? 'Core telemetry linked' : 'Unverified'}</strong><p>Business actions remain governed by KRISHNA authority.</p></article></div>{lrTasks.length ? <div className="floating-list">{lrTasks.slice(0,12).map((task,index) => <article className="floating-row" key={String(task.id ?? task.task_id ?? index)}><Workflow/><div><h3>{String(task.title ?? task.name ?? task.id ?? 'LR task')}</h3><p>{String(task.owner ?? task.agent ?? task.assigned_specialist ?? 'Unassigned')}</p></div><span>{String(task.status ?? 'unknown')}</span></article>)}</div> : <div className="lr-empty-note">No LR Universe task telemetry is currently exposed on this branch. The dashboard stays truthful and waits for backend records.</div>}<RawDetails value={value.commitments}/><div className="refresh-note">Last refresh: {lastRefresh ? new Date(lastRefresh).toLocaleTimeString() : '—'}</div></section>;
}
