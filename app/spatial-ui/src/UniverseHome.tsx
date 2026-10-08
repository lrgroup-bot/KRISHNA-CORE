import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Activity, ArrowUp, BrainCircuit, CircleDot, Mic, Network, ShieldCheck, Sparkles, Workflow } from 'lucide-react';
import AgentUniverse from './AgentUniverse';
import CosmicOm from './CosmicOm';
import './universe.css';

type ChatLine = { role: 'user' | 'krishna'; text: string };
type CoreState = { ok?: boolean; core?: string; uptime_seconds?: number };
type Task = { id?: string; task_id?: string; title?: string; status?: string };

export default function UniverseHome() {
  const [core, setCore] = useState<CoreState | null>(null);
  const [healthError, setHealthError] = useState('');
  const [tasks, setTasks] = useState<Task[]>([]);
  const [message, setMessage] = useState('');
  const [lines, setLines] = useState<ChatLine[]>([]);
  const [busy, setBusy] = useState(false);
  const [chatId, setChatId] = useState<string | undefined>();
  const [error, setError] = useState('');
  const [voice, setVoice] = useState(false);
  const [showUniverse, setShowUniverse] = useState(false);
  const bottom = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let mounted = true;
    const refresh = async () => {
      try {
        const response = await fetch('/health', { cache: 'no-store' });
        if (!response.ok) throw new Error('Health HTTP ' + response.status);
        const json = await response.json() as CoreState;
        if (!json.ok || json.core !== 'ONLINE') throw new Error('Core not online');
        if (mounted) { setCore(json); setHealthError(''); }
      } catch (reason) {
        if (mounted) { setCore(null); setHealthError(reason instanceof Error ? reason.message : 'Health unavailable'); }
      }
      try {
        const response = await fetch('/api/tasks?project=KRISHNA&limit=100', { cache: 'no-store' });
        if (!response.ok) throw new Error('Tasks unavailable');
        const data = await response.json() as { active?: Task[] };
        if (mounted) setTasks(Array.isArray(data.active) ? data.active : []);
      } catch { if (mounted) setTasks([]); }
    };
    void refresh();
    const timer = window.setInterval(() => void refresh(), 9000);
    return () => { mounted = false; window.clearInterval(timer); };
  }, []);

  useEffect(() => { bottom.current?.scrollIntoView({ block: 'nearest', behavior: 'smooth' }); }, [lines]);

  const send = async (event: FormEvent) => {
    event.preventDefault();
    const value = message.trim();
    if (!value || busy) return;
    setLines((prev) => [...prev, { role: 'user', text: value }]);
    setMessage(''); setBusy(true); setError('');
    try {
      const response = await fetch('/api/core/chat', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: value, mode: 'chat', project: 'KRISHNA', source: 'pc', ...(chatId ? { chat_id: chatId } : {}) }),
      });
      const data = await response.json() as { reply?: string; text?: string; error?: string; chat_id?: string; task_id?: string };
      if (!response.ok) throw new Error(data.error || 'Chat HTTP ' + response.status);
      if (data.chat_id) setChatId(data.chat_id);
      setLines((prev) => [...prev, { role: 'krishna', text: data.reply || data.text || (data.task_id ? 'Task received: ' + data.task_id : 'Request completed; no text response returned.') }]);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
    } finally { setBusy(false); }
  };

  const motionState = busy ? 'thinking' : tasks.length ? 'working' : 'idle';

  return <section className="universe-home live-floating-page">
    <header className="universe-header floating-glass-panel">
      <div><div className="universe-eyebrow">AUTONOMOUS INTELLIGENCE · LOCAL FIRST</div><h1>KRISHNA <em>UNIVERSE</em></h1><p>Understand · Reason · Research · Plan · Guide · Learn</p></div>
      <div className="universe-header-actions"><button type="button" className="universe-map-button" onClick={() => setShowUniverse(true)}><Network size={16} /> Intelligence Pipeline</button><div className={'universe-core-status ' + (core ? 'online' : 'offline')}><span className="universe-light" />{core ? 'CORE ONLINE' : 'CORE UNVERIFIED'}</div></div>
    </header>

    <div className="universe-body">
      <div className="universe-stage floating-glass-panel live-core-stage">
        <div className="universe-orbit"><CosmicOm state={motionState} /></div>
        <div className="universe-stage-title"><Sparkles size={17} /> {busy ? 'KRISHNA IS THINKING' : tasks.length ? 'KRISHNA IS WORKING' : 'KRISHNA · COGNITIVE CORE'}</div>
        <p>Cosmic neural dots live inside and around the 3D ॐ. Pointer movement bends the field; real task activity changes its energy state.</p>
      </div>
      <aside className="universe-insights floating-glass-panel">
        <h2><Activity size={16} /> LIVE INTELLIGENCE</h2>
        <div><ShieldCheck size={16} /> Core <strong>{core ? 'Online' : 'Unverified'}</strong></div>
        <div><BrainCircuit size={16} /> Authority <strong>KRISHNA</strong></div>
        <div><Workflow size={16} /> Execution <strong>Sudarshan</strong></div>
        <div><CircleDot size={16} /> Active tasks <strong>{core ? tasks.length : '—'}</strong></div>
        <button type="button" className="universe-open-map" onClick={() => setShowUniverse(true)}><Network size={15} /> Open live pipeline map</button>
        <p>{healthError || (core ? 'Connected to the KRISHNA core.' : 'Connect through the core origin to use live AI.')}</p>
      </aside>
    </div>

    <section className="universe-chat floating-glass-panel">
      <div className="universe-chat-heading"><span>✦ CONVERSATION WITH KRISHNA</span><span>{busy ? 'Processing request…' : 'Local intelligence interface'}</span></div>
      <div className="universe-messages" aria-live="polite">{lines.length ? lines.map((line, index) => <div className={'universe-line ' + line.role} key={index}><strong>{line.role === 'user' ? 'YOU' : 'KRISHNA'}</strong><p>{line.text}</p></div>) : <p className="universe-empty">Ask a question, start research, or describe a project for Sudarshan.</p>}<div ref={bottom} /></div>
      {error ? <div className="universe-error" role="alert">{error} — your message was not confirmed. Retry if appropriate.</div> : null}
      <form onSubmit={send}><label className="universe-sr" htmlFor="universe-message">Message to KRISHNA</label><textarea id="universe-message" value={message} onChange={(event) => setMessage(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); event.currentTarget.form?.requestSubmit(); } }} placeholder="Talk to KRISHNA…" rows={2} disabled={busy} /><button type="button" className="universe-voice" onClick={() => setVoice((value) => !value)} aria-pressed={voice} title="Voice integration status"><Mic size={19} /></button><button type="submit" disabled={!message.trim() || busy} aria-label="Send to KRISHNA"><ArrowUp size={20} /></button></form>
      {voice ? <p className="universe-note">Voice input is not wired in this release. Use text chat until the existing voice API is verified.</p> : null}
    </section>

    <footer className="universe-footer">Live UI states come from backend health/task data. The animated cosmic field is visualization; it does not imply physical sensing.</footer>
    <AgentUniverse open={showUniverse} onClose={() => setShowUniverse(false)} />
  </section>;
}
