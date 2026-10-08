import { useEffect, useMemo, useState } from 'react';
import { Bot, BriefcaseBusiness, Cpu, Gauge, Globe2, MessageSquareText, PackageOpen, PlugZap, Smartphone, Sun, Workflow } from 'lucide-react';

type JsonMap = Record<string, unknown>;
export type MainView = 'krishna' | 'sudarshan' | 'lr-universe' | 'projects' | 'chats' | 'plugins';

type Props = { active: MainView; onSelect: (view: MainView) => void };

type SideState = {
  core: boolean;
  cpu: number | null;
  gpu: number | null;
  internet: boolean;
  surya: 'running' | 'idle' | 'blocked' | 'unverified';
  suryaSystems: number;
  mobile: 'connected' | 'idle' | 'disconnected' | 'unverified';
  projects: number;
  chats: number;
};

const initial: SideState = { core: false, cpu: null, gpu: null, internet: typeof navigator !== 'undefined' ? navigator.onLine : false, surya: 'unverified', suryaSystems: 0, mobile: 'unverified', projects: 0, chats: 0 };

function walkNumbers(value: unknown, names: string[]): number | null {
  const queue: unknown[] = [value];
  while (queue.length) {
    const item = queue.shift();
    if (!item || typeof item !== 'object') continue;
    for (const [key, raw] of Object.entries(item as JsonMap)) {
      const normalized = key.toLowerCase().replaceAll('_', '').replaceAll('-', '');
      if (names.some((name) => normalized.includes(name))) {
        const numeric = typeof raw === 'number' ? raw : typeof raw === 'string' ? Number(raw.replace('%', '')) : NaN;
        if (Number.isFinite(numeric) && numeric >= 0 && numeric <= 100) return numeric;
      }
      if (raw && typeof raw === 'object') queue.push(raw);
    }
  }
  return null;
}

function ownerText(task: JsonMap) {
  return [task.assigned_specialist, task.assignedSpecialist, task.specialist, task.agent, task.owner, task.worker, task.assignee].filter((v) => typeof v === 'string').join(' ').toLowerCase();
}
function statusText(task: JsonMap) { return String(task.status ?? '').toLowerCase(); }
function systemKey(task: JsonMap) {
  const value = task.system ?? task.system_id ?? task.device ?? task.device_id ?? task.host ?? task.target ?? task.machine;
  return typeof value === 'string' && value.trim() ? value.trim() : null;
}
function mobileState(value: unknown): SideState['mobile'] {
  if (!value || typeof value !== 'object') return 'unverified';
  const text = JSON.stringify(value).toLowerCase();
  if (/"connected"\s*:\s*true|"online"\s*:\s*true|"active"\s*:\s*true/.test(text)) return 'connected';
  if (/"paired"\s*:\s*true|"known"\s*:\s*true|"idle"/.test(text)) return 'idle';
  if (/"connected"\s*:\s*false|"online"\s*:\s*false|disconnected|offline/.test(text)) return 'disconnected';
  return 'unverified';
}

export default function LiveSidebar({ active, onSelect }: Props) {
  const [state, setState] = useState(initial);
  useEffect(() => {
    let mounted = true;
    const refresh = async () => {
      const [statusR, tasksR, chatsR, mobileR] = await Promise.allSettled([
        fetch('/api/status', { cache: 'no-store' }).then((r) => r.ok ? r.json() : Promise.reject()),
        fetch('/api/tasks?limit=300', { cache: 'no-store' }).then((r) => r.ok ? r.json() : Promise.reject()),
        fetch('/api/chats?project=KRISHNA', { cache: 'no-store' }).then((r) => r.ok ? r.json() : Promise.reject()),
        fetch('/api/mobile/connection', { cache: 'no-store' }).then((r) => r.ok ? r.json() : Promise.reject()),
      ]);
      if (!mounted) return;
      const status = statusR.status === 'fulfilled' ? statusR.value as JsonMap : {};
      const taskBody = tasksR.status === 'fulfilled' ? tasksR.value as JsonMap : {};
      const tasks = Array.isArray(taskBody.tasks) ? taskBody.tasks as JsonMap[] : [];
      const suryaTasks = tasks.filter((t) => ownerText(t).includes('surya'));
      const activeSurya = suryaTasks.filter((t) => ['queued','running','working','executing','verifying'].includes(statusText(t)));
      const blockedSurya = suryaTasks.some((t) => ['blocked','failed','error'].includes(statusText(t)));
      const systems = new Set(activeSurya.map(systemKey).filter((v): v is string => Boolean(v)));
      const core = status.core === 'ONLINE' || status.ok === true;
      const chats = chatsR.status === 'fulfilled' && Array.isArray((chatsR.value as JsonMap).chats) ? ((chatsR.value as JsonMap).chats as unknown[]).length : 0;
      setState({
        core,
        cpu: walkNumbers(status.resources ?? status.pc_observer ?? status, ['cpu','processor']),
        gpu: walkNumbers(status.resources ?? status.pc_observer ?? status, ['gpu','graphics']),
        internet: navigator.onLine,
        surya: !core ? 'unverified' : blockedSurya ? 'blocked' : activeSurya.length ? 'running' : 'idle',
        suryaSystems: systems.size || (activeSurya.length ? 1 : 0),
        mobile: mobileR.status === 'fulfilled' ? mobileState(mobileR.value) : mobileState(status.mobile_connection),
        projects: new Set(tasks.map((t) => String(t.project ?? '')).filter(Boolean)).size,
        chats,
      });
    };
    void refresh();
    const timer = window.setInterval(() => void refresh(), 5000);
    const online = () => setState((prev) => ({ ...prev, internet: navigator.onLine }));
    window.addEventListener('online', online); window.addEventListener('offline', online);
    return () => { mounted = false; window.clearInterval(timer); window.removeEventListener('online', online); window.removeEventListener('offline', online); };
  }, []);

  const nav = useMemo(() => [
    ['krishna', 'KRISHNA', <Bot size={17} />],
    ['sudarshan', 'Sudarshan', <Workflow size={17} />],
    ['lr-universe', 'LR Universe Dashboard', <Globe2 size={17} />],
  ] as Array<[MainView, string, JSX.Element]>, []);

  const detail = useMemo(() => [
    ['projects', `Projects${state.projects ? ` · ${state.projects}` : ''}`, <BriefcaseBusiness size={16} />],
    ['chats', `Chats${state.chats ? ` · ${state.chats}` : ''}`, <MessageSquareText size={16} />],
    ['plugins', 'Plugins', <PlugZap size={16} />],
  ] as Array<[MainView, string, JSX.Element]>, [state.chats, state.projects]);

  return <aside className="live-sidebar">
    <div className="live-brand"><span>ॐ</span><div><strong>KRISHNA</strong><small>ALMIGHTY · LOCAL COMMAND CORE</small></div></div>
    <div className="sidebar-label">MAIN MENU</div>
    <nav className="sidebar-main-nav" aria-label="Main Menu">{nav.map(([id,label,icon]) => <button key={id} className={active === id ? 'active' : ''} onClick={() => onSelect(id)}>{icon}<span>{label}</span></button>)}</nav>
    <div className="sidebar-label sidebar-label-space">WORKSPACE</div>
    <nav className="sidebar-detail-nav">{detail.map(([id,label,icon]) => <button key={id} className={active === id ? 'active' : ''} onClick={() => onSelect(id)}>{icon}<span>{label}</span></button>)}</nav>
    <div className="sidebar-live-stack">
      <section className="live-side-card"><div className="side-card-head"><Gauge size={14}/><strong>SYSTEM LOAD</strong></div><div className="mini-metrics"><span><Cpu size={12}/>CPU <b>{state.cpu == null ? '—' : `${Math.round(state.cpu)}%`}</b></span><span>GPU <b>{state.gpu == null ? '—' : `${Math.round(state.gpu)}%`}</b></span><span className={state.internet ? 'tone-green' : 'tone-red'}>NET <b>{state.internet ? 'ONLINE' : 'OFFLINE'}</b></span></div></section>
      <section className="live-side-card"><div className="side-card-head"><Sun size={14}/><strong>SURYA DEV</strong><i className={`live-dot ${state.surya}`}/></div><div className={`side-state ${state.surya}`}>{state.surya.toUpperCase()}</div><small>Systems working now: <b>{state.suryaSystems}</b></small></section>
      <section className="live-side-card"><div className="side-card-head"><Smartphone size={14}/><strong>MOBILE</strong><i className={`live-dot ${state.mobile}`}/></div><div className={`side-state ${state.mobile}`}>{state.mobile.toUpperCase()}</div><small>{state.mobile === 'connected' ? 'Live companion link' : state.mobile === 'idle' ? 'Known device · idle' : 'No confirmed live link'}</small></section>
    </div>
    <div className={`core-footer ${state.core ? 'online' : 'offline'}`}><i/><span>{state.core ? 'Core online' : 'Core unverified'}</span></div>
  </aside>;
}
