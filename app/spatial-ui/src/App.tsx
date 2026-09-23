import { useEffect, useMemo, useRef } from 'react';
import { DockviewReact, themeDark } from 'dockview-react';
import { Background, Controls, ReactFlow, type Edge, type Node } from '@xyflow/react';
import { Canvas } from '@react-three/fiber';
import { Terminal } from '@xterm/xterm';
import { Bot, Boxes, PlugZap, ShieldCheck, Workflow } from 'lucide-react';
import { Button } from './components/ui/Button';

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
      <Button disabled title="Runtime endpoint binding is verified during deployment">Start verified work</Button>
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

function AvatarPanel() {
  return (
    <div className="avatar-panel">
      <Canvas camera={{ position: [0, 0, 4], fov: 45 }}>
        <ambientLight intensity={1.4} />
        <directionalLight position={[3, 4, 5]} intensity={2} />
        <mesh>
          <icosahedronGeometry args={[1, 2]} />
          <meshStandardMaterial roughness={0.28} metalness={0.22} />
        </mesh>
      </Canvas>
      <div className="avatar-caption">
        Spatial runtime ready. The private child GLB is loaded only after the production rig/viseme inspector passes.
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
  const components = useMemo(() => ({
    krishna: KrishnaHome,
    sudarshan: SudarshanPanel,
    graph: NeuralGraphPanel,
    avatar: AvatarPanel,
    terminal: TerminalPanel,
    plugins: PluginsPanel,
  }), []);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand"><Bot size={22} /><span>KRISHNA</span></div>
        <nav>
          <button className="nav-item nav-item--active"><Bot size={18} />KRISHNA</button>
          <button className="nav-item"><Workflow size={18} />Sudarshan</button>
          <div className="nav-spacer" />
          <button className="nav-item"><PlugZap size={18} />Plugins</button>
        </nav>
      </aside>
      <main className="workspace">
        <DockviewReact
          theme={themeDark}
          components={components}
          onReady={(event) => {
            event.api.addPanel({ id: 'krishna-home', component: 'krishna', title: 'KRISHNA' });
            event.api.addPanel({ id: 'sudarshan-work', component: 'sudarshan', title: 'Sudarshan' });
            event.api.addPanel({ id: 'action-graph', component: 'graph', title: 'Action Graph' });
            event.api.addPanel({ id: 'avatar-stage', component: 'avatar', title: 'Avatar' });
            event.api.addPanel({ id: 'terminal', component: 'terminal', title: 'Terminal' });
            event.api.addPanel({ id: 'plugins', component: 'plugins', title: 'Plugins' });
          }}
        />
      </main>
    </div>
  );
}
