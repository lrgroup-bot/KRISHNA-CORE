import { useEffect, useMemo, useRef, useState } from 'react';
import { DockviewReact, themeDark } from 'dockview-react';
import { Background, Controls, ReactFlow, type Edge, type Node } from '@xyflow/react';
import { Canvas } from '@react-three/fiber';
import { Terminal } from '@xterm/xterm';
import { Bot, Boxes, PlugZap, ShieldCheck, Workflow } from 'lucide-react';

function KrishnaHome() {
  return (
    <section className="panel-content">
      <div className="eyebrow">KRISHNA CORE</div>
      <h1>One authority. Verified execution.</h1>
      <p className="muted">
        Internal agents, research, browser control, automation and diagnostics stay behind KRISHNA and Sudarshan.
      </p>
      <div className="bento">
        <article className="card"><ShieldCheck /><strong>Policy</strong><span>Permissioned actions and independent verification.</span></article>
        <article className="card"><Workflow /><strong>Action Graph</strong><span>Jobs, agents and tools share one execution spine.</span></article>
        <article className="card"><Boxes /><strong>Local-first</strong><span>Private evidence and credentials remain local by default.</span></article>
      </div>
    </section>
  );
}

function SudarshanPanel() {
  return (
    <section className="panel-content">
      <div className="eyebrow">SUDARSHAN</div>
      <h2>Work console</h2>
      <p className="muted">Projects, chats, verification, browser work and action receipts render here through authenticated runtime contracts.</p>
      <div className="status-strip">
        <span>Active Work</span><span>Verification</span><span>System Load</span>
      </div>
      <p className="muted">Operational controls are injected only after their Shared Action contract is available; this shell does not render fake action buttons.</p>
    </section>
  );
}

type DesignStatus = {
  design?: { version?: string; knowledge_bound?: boolean; hard_acceptance_checks?: string[] };
  vishvakarma?: { name?: string; verified?: number; candidate?: number };
  project_lifecycle?: { design_engine_bound?: boolean };
  model_scout?: { evaluated?: number; active_candidates?: number; cloud_billing_authority?: boolean };
};

function DesignPanel() {
  const [status, setStatus] = useState<DesignStatus | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    fetch('/api/design/status', { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.json() as Promise<DesignStatus>;
      })
      .then((data) => setStatus(data))
      .catch((reason: unknown) => {
        if ((reason as { name?: string })?.name !== 'AbortError') {
          setError(reason instanceof Error ? reason.message : String(reason));
        }
      });
    return () => controller.abort();
  }, []);

  return (
    <section className="panel-content">
      <div className="eyebrow">SUDARSHAN DESIGN · INTERNAL</div>
      <h2>Design Intelligence</h2>
      <p className="muted">
        Rishi Vishvakarma knowledge remains provenance-backed. Candidate lessons are not trusted until verified,
        and UI completion requires rendered functional, visual, responsive, accessibility and security evidence.
      </p>
      {error ? <p className="muted">Runtime status unavailable: {error}</p> : null}
      <div className="bento">
        <article className="card">
          <strong>{status?.vishvakarma?.name ?? 'Rishi Vishvakarma'}</strong>
          <span>Verified: {status?.vishvakarma?.verified ?? '—'} · Candidate: {status?.vishvakarma?.candidate ?? '—'}</span>
        </article>
        <article className="card">
          <strong>Design Engine</strong>
          <span>{status?.design?.knowledge_bound ? 'Verified knowledge bound' : 'Awaiting runtime status'} · hard gates: {status?.design?.hard_acceptance_checks?.length ?? '—'}</span>
        </article>
        <article className="card">
          <strong>Local Model Scout</strong>
          <span>Accepted: {status?.model_scout?.active_candidates ?? '—'} · cloud billing authority: {status?.model_scout?.cloud_billing_authority ? 'yes' : 'no'}</span>
        </article>
      </div>
    </section>
  );
}

function NaradPanel() {
  return (
    <section className="panel-content">
      <div className="eyebrow">NARAD · INTERNAL</div>
      <h2>Automation + messages</h2>
      <p className="muted">
        Workflows, triggers, connections, checkpoints, dead letters, history, inbox and outbox share one provider-neutral surface.
        Sending remains a separate approval-gated provider action.
      </p>
      <div className="bento">
        <article className="card"><strong>Workflows</strong><span>Typed DAG + checkpoints + bounded retries.</span></article>
        <article className="card"><strong>Inbox / Outbox</strong><span>Durable message state with secret redaction.</span></article>
        <article className="card"><strong>Connections</strong><span>Credential references only; no plaintext secrets in UI state.</span></article>
      </div>
    </section>
  );
}

const graphNodes: Node[] = [
  { id: 'user', position: { x: 0, y: 80 }, data: { label: 'Owner' } },
  { id: 'krishna', position: { x: 220, y: 80 }, data: { label: 'KRISHNA' } },
  { id: 'sudarshan', position: { x: 440, y: 10 }, data: { label: 'Sudarshan' } },
  { id: 'agents', position: { x: 440, y: 150 }, data: { label: 'Agents / Jobs' } },
  { id: 'verify', position: { x: 660, y: 80 }, data: { label: 'Independent Verifier' } },
];
const graphEdges: Edge[] = [
  { id: 'e1', source: 'user', target: 'krishna' },
  { id: 'e2', source: 'krishna', target: 'sudarshan' },
  { id: 'e3', source: 'krishna', target: 'agents' },
  { id: 'e4', source: 'sudarshan', target: 'verify' },
  { id: 'e5', source: 'agents', target: 'verify' },
];

function NeuralGraphPanel() {
  return (
    <div className="flow-panel">
      <ReactFlow defaultNodes={graphNodes} defaultEdges={graphEdges} fitView>
        <Background />
        <Controls />
      </ReactFlow>
    </div>
  );
}

function VrindavanEnvironment() {
  return (
    <>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -1.15, 0]}>
        <circleGeometry args={[7, 64]} />
        <meshStandardMaterial roughness={0.95} />
      </mesh>
      <mesh position={[-2.2, -0.65, -1.8]}>
        <cylinderGeometry args={[0.16, 0.22, 1.7, 18]} />
        <meshStandardMaterial roughness={1} />
      </mesh>
      <mesh position={[-2.2, 0.45, -1.8]}>
        <sphereGeometry args={[0.85, 24, 18]} />
        <meshStandardMaterial roughness={0.9} />
      </mesh>
      <mesh position={[2.2, -0.9, -1.9]} scale={[2.6, 0.12, 0.9]}>
        <boxGeometry />
        <meshStandardMaterial metalness={0.05} roughness={0.32} />
      </mesh>
    </>
  );
}

function AvatarPanel() {
  return (
    <div className="avatar-panel">
      <Canvas camera={{ position: [0, 0.2, 4.8], fov: 45 }}>
        <ambientLight intensity={1.4} />
        <directionalLight position={[3, 4, 5]} intensity={2} />
        <VrindavanEnvironment />
        <mesh position={[0, 0, 0]}>
          <icosahedronGeometry args={[0.9, 2]} />
          <meshStandardMaterial roughness={0.28} metalness={0.22} />
        </mesh>
      </Canvas>
      <div className="avatar-caption">
        Vrindavan-inspired local spatial stage. The private child GLB replaces the placeholder only after the production rig/viseme/animation inspector passes.
      </div>
    </div>
  );
}

function TerminalPanel() {
  const host = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!host.current) return;
    const terminal = new Terminal({
      convertEol: true,
      cursorBlink: false,
      disableStdin: true,
      fontSize: 13,
    });
    terminal.open(host.current);
    terminal.writeln('KRISHNA permissioned terminal surface');
    terminal.writeln('No raw shell is attached by default.');
    terminal.writeln('A backend session must be authorized through the Shared Action Bus.');
    return () => terminal.dispose();
  }, []);
  return <div className="terminal-host" ref={host} />;
}

function PluginsPanel() {
  return (
    <section className="panel-content">
      <div className="eyebrow">PLUGINS</div>
      <h2>Capability connections</h2>
      <p className="muted">Enabled integrations remain project-scoped, permissioned and credential-referenced.</p>
    </section>
  );
}

export default function App() {
  const dockApi = useRef<any>(null);
  const [activeNav, setActiveNav] = useState<'krishna' | 'sudarshan' | 'plugins'>('krishna');
  const focusPanel = (panelId: string, nav: 'krishna' | 'sudarshan' | 'plugins') => {
    const panel = dockApi.current?.getPanel?.(panelId);
    panel?.api?.setActive?.();
    setActiveNav(nav);
  };

  const components = useMemo(() => ({
    krishna: KrishnaHome,
    sudarshan: SudarshanPanel,
    narad: NaradPanel,
    design: DesignPanel,
    graph: NeuralGraphPanel,
    avatar: AvatarPanel,
    terminal: TerminalPanel,
    plugins: PluginsPanel,
  }), []);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand"><Bot size={22} /><span>KRISHNA</span></div>
        <nav aria-label="Main Menu">
          <button type="button" className={activeNav === 'krishna' ? 'nav-item nav-item--active' : 'nav-item'} onClick={() => focusPanel('krishna-home', 'krishna')}>
            <Bot size={18} /><span>KRISHNA</span>
          </button>
          <button type="button" className={activeNav === 'sudarshan' ? 'nav-item nav-item--active' : 'nav-item'} onClick={() => focusPanel('sudarshan-work', 'sudarshan')}>
            <Workflow size={18} /><span>Sudarshan</span>
          </button>
          <div className="nav-spacer" />
          <button type="button" className={activeNav === 'plugins' ? 'nav-item nav-item--active' : 'nav-item'} onClick={() => focusPanel('plugins', 'plugins')}>
            <PlugZap size={18} /><span>Plugins</span>
          </button>
        </nav>
      </aside>
      <main className="workspace">
        <DockviewReact
          theme={themeDark}
          components={components}
          onReady={(event) => {
            dockApi.current = event.api;
            event.api.addPanel({ id: 'krishna-home', component: 'krishna', title: 'KRISHNA' });
            event.api.addPanel({ id: 'sudarshan-work', component: 'sudarshan', title: 'Sudarshan' });
            event.api.addPanel({ id: 'action-graph', component: 'graph', title: 'Action Graph' });
            event.api.addPanel({ id: 'narad', component: 'narad', title: 'Automations' });
            event.api.addPanel({ id: 'design-intelligence', component: 'design', title: 'Design Intelligence' });
            event.api.addPanel({ id: 'avatar-stage', component: 'avatar', title: 'Avatar / Spatial' });
            event.api.addPanel({ id: 'terminal', component: 'terminal', title: 'Terminal' });
            event.api.addPanel({ id: 'plugins', component: 'plugins', title: 'Plugins' });
          }}
        />
      </main>
    </div>
  );
}
