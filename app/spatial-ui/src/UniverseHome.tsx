import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Activity, ArrowUp, BrainCircuit, CircleDot, Mic, Network, ShieldCheck, Sparkles, Workflow } from 'lucide-react';
import AgentUniverse from './AgentUniverse';
import './universe.css';

type ChatLine = { role: 'user' | 'krishna'; text: string };
type CoreState = { ok?: boolean; core?: string; uptime_seconds?: number };
type Task = { id?: string; task_id?: string; title?: string; status?: string };

function NeuralMotion({ working }: { working: boolean }) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const target = useRef({ x: 0.5, y: 0.5 });
  useEffect(() => {
    const element = canvas.current;
    if (!element) return;
    const ctx = element.getContext('2d');
    if (!ctx) return;
    let frame = 0;
    let raf = 0;
    let alive = true;
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const dots = Array.from({ length: 82 }, (_, i) => {
      const angle = i * Math.PI * (3 - Math.sqrt(5));
      const radius = Math.sqrt((i + 0.5) / 82) * 0.44;
      return { x: 0.5 + Math.cos(angle) * radius, y: 0.5 + Math.sin(angle) * radius, size: i % 9 === 0 ? 2.5 : 1.5 };
    });
    const draw = () => {
      if (!alive) return;
      const rect = element.getBoundingClientRect();
      if (!rect.width || !rect.height) return;
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const width = Math.round(rect.width * dpr), height = Math.round(rect.height * dpr);
      if (element.width !== width || element.height !== height) { element.width = width; element.height = height; }
      ctx.clearRect(0, 0, width, height);
      const scale = Math.min(width, height);
      const time = reduced ? 0 : frame * (working ? 0.023 : 0.009);
      const points = dots.map((dot, i) => {
        const drift = reduced ? 0 : Math.sin(time + i * 0.7) * (working ? 0.018 : 0.008);
        const distanceFromPointer = Math.hypot(dot.x - target.current.x, dot.y - target.current.y);
        const pull = 0.055 * Math.max(0, 1 - distanceFromPointer * 2.2);
        return {
          x: (dot.x + drift + (target.current.x - 0.5) * pull) * width,
          y: (dot.y + Math.cos(time + i) * drift + (target.current.y - 0.5) * pull) * height,
          size: dot.size * dpr,
        };
      });
      const link = scale * 0.13;
      points.forEach((p, i) => {
        for (let j = i + 1; j < points.length; j++) {
          const q = points[j], distance = Math.hypot(p.x - q.x, p.y - q.y);
          if (distance > link) continue;
          ctx.strokeStyle = 'rgba(103,218,245,' + (0.22 * (1 - distance / link)).toFixed(3) + ')';
          ctx.lineWidth = dpr * 0.75;
          ctx.beginPath(); ctx.moveTo(p.x, p.y); ctx.lineTo(q.x, q.y); ctx.stroke();
        }
        ctx.fillStyle = i % 9 === 0 ? '#f0ce83' : '#79dff5';
        ctx.beginPath(); ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2); ctx.fill();
      });
      ctx.strokeStyle = 'rgba(230,196,114,.48)';
      ctx.lineWidth = dpr;
      ctx.beginPath(); ctx.arc(width / 2, height / 2, scale * 0.365, 0, Math.PI * 2); ctx.stroke();
      if (!reduced) { frame++; raf = requestAnimationFrame(draw); }
    };
    draw();
    return () => { alive = false; cancelAnimationFrame(raf); };
  }, [working]);
  return <canvas ref={canvas} className="universe-motion" aria-label="Interactive neural network visualization" role="img" onPointerMove={(event) => {
    const rect = event.currentTarget.getBoundingClientRect();
    target.current = { x: (event.clientX - rect.left) / rect.width, y: (event.clientY - rect.top) / rect.height };
  }} onPointerLeave={() => { target.current = { x: .5, y: .5 }; }} />;
}

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
        const response = await fetch('/api/tasks?project=KRISHNA&limit=10', { cache: 'no-store' });
        if (!response.ok) throw new Error('Tasks unavailable');
        const data = await response.json() as { active?: Task[] };
        if (mounted) setTasks(Array.isArray(data.active) ? data.active : []);
      } catch { if (mounted) setTasks([]); }
    };
    void refresh();
    const timer = window.setInterval(() => void refresh(), 12000);
    return () => { mounted = false; window.clearInterval(timer); };
  }, []);

  useEffect(() => { bottom.current?.scrollIntoView({ block: 'nearest', behavior: 'smooth' }); }, [lines]);

  const send = async (event: FormEvent) => {
    event.preventDefault();
    const value = message.trim();
    if (!value || busy) return;
    setLines(prev => [...prev, { role: 'user', text: value }]);
    setMessage(''); setBusy(true); setError('');
    try {
      const response = await fetch('/api/core/chat', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: value, mode: 'chat', project: 'KRISHNA', source: 'pc', ...(chatId ? { chat_id: chatId } : {}) })
      });
      const data = await response.json() as { reply?: string; text?: string; error?: string; chat_id?: string; task_id?: string };
      if (!response.ok) throw new Error(data.error || 'Chat HTTP ' + response.status);
      if (data.chat_id) setChatId(data.chat_id);
      setLines(prev => [...prev, { role: 'krishna', text: data.reply || data.text || (data.task_id ? 'Task received: ' + data.task_id : 'Request completed; no text response returned.') }]);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
    } finally { setBusy(false); }
  };

  return <section className="universe-home">
    <header className="universe-header"><div><div className="universe-eyebrow">AUTONOMOUS INTELLIGENCE · LOCAL FIRST</div><h1>KRISHNA <em>UNIVERSE</em></h1><p>Understand · Reason · Research · Plan · Guide · Learn</p></div><div className="universe-header-actions"><button type="button" className="universe-map-button" onClick={() => setShowUniverse(true)}><Network size={16} /> Intelligence Universe</button><div className={'universe-core-status ' + (core ? 'online' : 'offline')}><span className="universe-light" />{core ? 'CORE ONLINE' : 'CORE UNVERIFIED'}</div></div></header>
    <div className="universe-body"><div className="universe-stage"><div className="universe-orbit"><NeuralMotion working={busy} /><div className="universe-avatar" aria-label="Avatar placeholder; 3D Bala Krishna integration pending">ॐ</div></div><div className="universe-stage-title"><Sparkles size={17} /> {busy ? 'KRISHNA IS THINKING' : 'KRISHNA · COGNITIVE CORE'}</div><p>Move your pointer across the living neural field. Open Intelligence Universe to inspect internal agent pipelines.</p></div>
    <aside className="universe-insights"><h2><Activity size={16} /> LIVE INTELLIGENCE</h2><div><ShieldCheck size={16} /> Core <strong>{core ? 'Online' : 'Unverified'}</strong></div><div><BrainCircuit size={16} /> Authority <strong>KRISHNA</strong></div><div><Workflow size={16} /> Execution <strong>Sudarshan</strong></div><div><CircleDot size={16} /> Active tasks <strong>{core ? tasks.length : '—'}</strong></div><button type="button" className="universe-open-map" onClick={() => setShowUniverse(true)}><Network size={15} /> Open live pipeline map</button><p>{healthError || (core ? 'Connected to the KRISHNA core.' : 'Connect through the core origin to use live AI.')}</p></aside></div>
    <section className="universe-chat"><div className="universe-chat-heading"><span>✦ CONVERSATION WITH KRISHNA</span><span>{busy ? 'Processing request…' : 'Local intelligence interface'}</span></div><div className="universe-messages" aria-live="polite">{lines.length ? lines.map((line, index) => <div className={'universe-line ' + line.role} key={index}><strong>{line.role === 'user' ? 'YOU' : 'KRISHNA'}</strong><p>{line.text}</p></div>) : <p className="universe-empty">Ask a question, start research, or describe a project for Sudarshan.</p>}<div ref={bottom} /></div>
    {error ? <div className="universe-error" role="alert">{error} — your message was not confirmed. Retry if appropriate.</div> : null}
    <form onSubmit={send}><label className="universe-sr" htmlFor="universe-message">Message to KRISHNA</label><textarea id="universe-message" value={message} onChange={event => setMessage(event.target.value)} onKeyDown={event => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); event.currentTarget.form?.requestSubmit(); } }} placeholder="Talk to KRISHNA…" rows={2} disabled={busy} /><button type="button" className="universe-voice" onClick={() => setVoice(v => !v)} aria-pressed={voice} title="Voice integration status"><Mic size={19} /></button><button type="submit" disabled={!message.trim() || busy} aria-label="Send to KRISHNA"><ArrowUp size={20} /></button></form>
    {voice ? <p className="universe-note">Voice input is not wired in this release. Use text chat until the existing voice API is verified.</p> : null}</section>
    <footer className="universe-footer">Neural motion is an interactive visualization, not physical motion tracking. Agent pipeline status is task-derived unless a dedicated endpoint verifies it.</footer>
    <AgentUniverse open={showUniverse} onClose={() => setShowUniverse(false)} />
  </section>;
}
