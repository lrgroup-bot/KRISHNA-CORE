import { useEffect, useRef, useState, type FormEvent } from 'react';
import './SudarshanWorkPanel.css';

type Project = { name: string; role?: string; privacy?: string; verification_checks?: string[] };
type Receipt = { agent: string; action: string; action_id: string };
type Outcome = { status?: string; stage_receipts?: Receipt[]; tests?: { passed?: boolean }; learning?: { approval_required?: boolean } };

async function api(path: string, body?: unknown) {
  const response = await fetch(path, body === undefined ? undefined : {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || `Request failed (${response.status})`);
  return data;
}

export default function SudarshanWorkPanel() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [project, setProject] = useState('');
  const [message, setMessage] = useState('');
  const [chat, setChat] = useState<{ role: string; text: string }[]>([]);
  const [task, setTask] = useState('');
  const [approve, setApprove] = useState(false);
  const [publicQuery, setPublicQuery] = useState('');
  const [publicApproved, setPublicApproved] = useState(false);
  const [cloudApproved, setCloudApproved] = useState(false);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const [outcome, setOutcome] = useState<Outcome | null>(null);
  const inFlight = useRef(false);
  const selected = projects.find((item) => item.name === project);
  const localPC = ['localhost', '127.0.0.1', '[::1]'].includes(window.location.hostname);

  useEffect(() => {
    let active = true;
    api('/api/projects').then((data) => {
      if (!active) return;
      const rows: Project[] = Array.isArray(data.projects) ? data.projects : [];
      setProjects(rows);
      setProject(rows.find((item) => item.role === 'active')?.name || rows[0]?.name || '');
    }).catch((reason: unknown) => { if (active) setError(String(reason)); });
    return () => { active = false; };
  }, []);

  const send = async (event: FormEvent) => {
    event.preventDefault();
    if (inFlight.current || !message.trim()) return;
    const text = message.trim();
    inFlight.current = true; setBusy('Waiting for local Krishna'); setError(''); setMessage('');
    setChat((rows) => [...rows, { role: 'You', text }]);
    try {
      const data = await api('/api/core/chat', { message: text, project: project || 'general', mode: 'chat' });
      setChat((rows) => [...rows, { role: 'Krishna', text: data.text || data.reply || 'No final response was returned.' }]);
    } catch (reason) { setError(String(reason)); }
    finally { inFlight.current = false; setBusy(''); }
  };

  const run = async (event: FormEvent) => {
    event.preventDefault();
    if (inFlight.current || !localPC || !approve || !selected || selected.role !== 'active' || !task.trim()) return;
    if (publicApproved && !publicQuery.trim()) { setError('Enter the separate public research query.'); return; }
    inFlight.current = true; setBusy('Running registered candidate checks; keep this panel open'); setError(''); setOutcome(null);
    try {
      const data = await api('/api/action-bus/dispatch', {
        action: 'hybrid.implementation.run', project, actor: 'owner-ui', approved: true,
        idempotency_key: crypto.randomUUID(),
        payload: { task: task.trim(), approve_build: true,
          approved_public_context: publicApproved, public_query: publicApproved ? publicQuery.trim() : '',
          use_free_cloud: publicApproved && cloudApproved },
      });
      setOutcome(data.result);
    } catch (reason) { setError(String(reason)); }
    finally { inFlight.current = false; setBusy(''); setApprove(false); }
  };

  return <section className="panel-content work-console" aria-label="Sudarshan work console">
    <div className="eyebrow">SUDARSHAN</div><h2>Work with Krishna</h2>
    <label>Registered project<select aria-label="Registered project" value={project} disabled={!!busy} onChange={(event) => {
      setProject(event.target.value); setApprove(false); setPublicApproved(false); setCloudApproved(false); setOutcome(null);
    }}>{!projects.length && <option value="">No registered projects</option>}{projects.map((item) => <option key={item.name} value={item.name}>{item.name} · {item.role || 'unknown role'}</option>)}</select></label>
    <div className="work-chat" aria-label="Conversation" aria-live="polite">{chat.length ? chat.map((row, index) => <p key={index}><strong>{row.role}</strong><span>{row.text}</span></p>) : <p className="muted">Ask Krishna a question. Engineering changes use the separate approval below.</p>}</div>
    <form onSubmit={(event) => void send(event)}><label>Message<textarea aria-label="Message to Krishna" maxLength={2000} value={message} onChange={(event) => setMessage(event.target.value)} /></label><button disabled={!!busy || !message.trim()}>Send message</button></form>
    <details><summary>Isolated engineering candidate</summary>
      <p className="muted">Uses existing agents and the project's registered checks. Candidate files are copied locally; this is not an operating-system sandbox. Nothing is promoted or deployed.</p>
      <form onSubmit={(event) => void run(event)}>
        <label>Task<textarea aria-label="Engineering task" maxLength={2000} value={task} disabled={!!busy} onChange={(event) => setTask(event.target.value)} /></label>
        <p>Registered checks: {selected?.verification_checks?.join(', ') || 'None — register checks before running.'}</p>
        <label className="work-check"><input type="checkbox" checked={publicApproved} disabled={!!busy} onChange={(event) => { setPublicApproved(event.target.checked); setCloudApproved(false); }} />Allow GARUDA to search the separate public query</label>
        {publicApproved && <><label>Public query only<input aria-label="Public research query" maxLength={500} value={publicQuery} disabled={!!busy} onChange={(event) => setPublicQuery(event.target.value)} /></label>
          <label className="work-check"><input type="checkbox" checked={cloudApproved} disabled={!!busy || selected?.privacy !== 'approved_cloud'} onChange={(event) => setCloudApproved(event.target.checked)} />Allow a verified zero-cost cloud cross-check of this public query</label>
          <p className="muted">Cloud requires an approved-cloud project and a verified $0 key cap. Private project context stays local. Source leads still require independent review.</p></>}
        <label className="work-check"><input type="checkbox" checked={approve} disabled={!!busy} onChange={(event) => setApprove(event.target.checked)} />I approve local model use, isolated source replacements, registered test execution and a pending learning proposal for this task</label>
        <button disabled={!!busy || !localPC || !approve || selected?.role !== 'active' || !selected?.verification_checks?.length || !task.trim()}>Run candidate workflow</button>
        {!localPC && <p>Engineering approval is available on the local Krishna PC.</p>}
      </form>
    </details>
    {busy && <p role="status">{busy}</p>}{error && <p role="alert">{error}</p>}
    {outcome && <div className="work-outcome" aria-label="Workflow outcome"><strong>{outcome.status?.replaceAll('_', ' ') || 'No completion status'}</strong>
      <p>Registered checks: {outcome.tests?.passed ? 'passed' : 'not verified'}. Original project unchanged. Learning requires review.</p>
      <ol>{outcome.stage_receipts?.map((row) => <li key={row.action_id}>{row.agent} · {row.action}<small>{row.action_id}</small></li>)}</ol>
    </div>}
  </section>;
}
