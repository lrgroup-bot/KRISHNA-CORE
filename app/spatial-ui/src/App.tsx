import { useEffect, useMemo, useRef, useState, type FormEvent } from 'react';
import { DockviewReact, themeDark } from 'dockview-react';
import { Background, Controls, ReactFlow, type Edge, type Node } from '@xyflow/react';
import { Canvas } from '@react-three/fiber';
import { Terminal } from '@xterm/xterm';
import { Activity, Bot, Boxes, PlugZap, Radio, ShieldCheck, Wifi, Workflow } from 'lucide-react';

type RuViewStatus = {
  mode?: 'csi' | 'rssi_only' | 'unconfigured' | string;
  wifi?: {
    available?: boolean;
    connected?: boolean;
    ssid?: string | null;
    signal_percent?: number | null;
    channel?: string | null;
    radio_type?: string | null;
  };
  ruview?: {
    python_client_installed?: boolean;
    reachable?: boolean;
    csi_detected?: boolean;
    latest?: {
      payload?: {
        presence?: boolean | null;
        motion?: number | null;
        motion_energy?: number | null;
        person_count?: number;
        presence_score?: number | null;
        signal_quality?: number | null;
        rssi?: number | null;
        persons?: unknown[];
        pose_keypoints?: number[][];
      };
    } | null;
  };
  credentials?: {
    entry_surface?: string;
    mobile_entry_allowed?: boolean;
    storage?: string;
  };
  capability_limit?: string;
};

function HawkeyeRfPanel() {
  const [status, setStatus] = useState<RuViewStatus | null>(null);
  const [error, setError] = useState('');
  const [ssid, setSsid] = useState('');
  const [password, setPassword] = useState('');
  const [auth, setAuth] = useState('WPA2PSK');
  const [remember, setRemember] = useState(true);
  const [connecting, setConnecting] = useState(false);
  const [rfSessionId, setRfSessionId] = useState('');
  const [sampling, setSampling] = useState(false);

  const localCredentialSurface = useMemo(() => {
    const host = window.location.hostname.toLowerCase();
    return host === '127.0.0.1' || host === 'localhost' || host === '::1';
  }, []);

  const refresh = async () => {
    try {
      const response = await fetch('/api/hawkeye/ruview/status?refresh=1', { cache: 'no-store' });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json() as RuViewStatus;
      setStatus(data);
      setError('');
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : String(reason));
    }
  };

  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => void refresh(), 2500);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    if (!rfSessionId || !localCredentialSurface) return;
    let cancelled = false;
    const capture = async () => {
      if (cancelled) return;
      try {
        await fetch('/api/hawkeye/ruview/sample', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ session_id: rfSessionId }),
        });
      } catch {
        // Status refresh surfaces connectivity failures; keep capture loop bounded.
      }
    };
    void capture();
    const timer = window.setInterval(() => void capture(), 2000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [rfSessionId, localCredentialSurface]);

  const startRfCapture = async () => {
    if (!localCredentialSurface || sampling || rfSessionId) return;
    setSampling(true);
    setError('');
    try {
      const response = await fetch('/api/hawkeye/live/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project: 'KRISHNA',
          purpose: 'RuView Wi-Fi RF sensing',
          scene_hint: 'wifi-rf',
          coordinates: {},
        }),
      });
      const data = await response.json() as { session_id?: string; error?: string };
      if (!response.ok || !data.session_id) throw new Error(data.error || `HTTP ${response.status}`);
      setRfSessionId(data.session_id);
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : String(reason));
    } finally {
      setSampling(false);
    }
  };

  const connectWifi = async (event: FormEvent) => {
    event.preventDefault();
    if (!localCredentialSurface || !ssid.trim() || !password) return;
    setConnecting(true);
    setError('');
    try {
      const response = await fetch('/api/hawkeye/ruview/wifi/connect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ssid: ssid.trim(),
          password,
          auth,
          cipher: 'AES',
          remember,
          approved: true,
        }),
      });
      const data = await response.json() as { error?: string };
      if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
      setPassword('');
      await refresh();
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : String(reason));
    } finally {
      setConnecting(false);
    }
  };

  const latest = status?.ruview?.latest?.payload;
  const inferredCount = Math.max(
    0,
    Number(latest?.person_count ?? ((latest?.presence === true) ? 1 : 0)) || 0,
  );
  const posePoints = (latest?.pose_keypoints ?? [])
    .filter((point): point is number[] => Array.isArray(point) && point.length >= 2)
    .slice(0, 17)
    .map((point) => ({
      x: Math.max(0, Math.min(100, Number(point[0]) * 100)),
      y: Math.max(0, Math.min(100, Number(point[1]) * 100)),
      confidence: point.length >= 4 ? Number(point[3]) : 1,
    }));
  const poseEdges: Array<[number, number]> = [
    [0, 1], [0, 2], [1, 3], [2, 4],
    [5, 6], [5, 7], [7, 9], [6, 8], [8, 10],
    [5, 11], [6, 12], [11, 12], [11, 13], [13, 15], [12, 14], [14, 16],
  ];
  const hasPose = posePoints.length >= 5;
  const modeLabel = status?.mode === 'csi'
    ? 'CSI sensing'
    : status?.mode === 'rssi_only'
      ? 'RSSI only'
      : 'Not connected';

  return (
    <section className="rf-console" aria-label="HAWKEYE RuView Wi-Fi sensing">
      <div className="rf-console__header">
        <div>
          <div className="eyebrow">HAWKEYE · RUVIEW · PC CONTROL</div>
          <h2>Wi-Fi RF sensing</h2>
          <p className="muted">
            Wi-Fi credentials are entered and stored only on the KRISHNA PC. Mobile never receives or submits the password.
          </p>
        </div>
        <div className="rf-actions">
          {localCredentialSurface ? (
            <button
              type="button"
              className={rfSessionId ? 'kr-button kr-button--ghost' : 'kr-button'}
              onClick={() => rfSessionId ? setRfSessionId('') : void startRfCapture()}
              disabled={sampling}
            >
              {sampling ? 'Starting…' : rfSessionId ? 'Stop RF capture' : 'Start RF capture'}
            </button>
          ) : null}
          <button type="button" className="kr-button kr-button--ghost" onClick={() => void refresh()}>
            Refresh
          </button>
        </div>
      </div>

      <div className="bento rf-bento">
        <article className="card">
          <Wifi />
          <strong>{status?.wifi?.connected ? status.wifi.ssid : 'Wi-Fi disconnected'}</strong>
          <span>Signal: {status?.wifi?.signal_percent ?? '—'}% · Channel: {status?.wifi?.channel ?? '—'}</span>
        </article>
        <article className="card">
          <Radio />
          <strong>{modeLabel}</strong>
          <span>RuView local server: {status?.ruview?.reachable ? 'online' : 'not detected'} · CSI: {status?.ruview?.csi_detected ? 'detected' : 'not detected'}</span>
        </article>
        <article className="card">
          <ShieldCheck />
          <strong>Credential boundary</strong>
          <span>{status?.credentials?.storage ?? 'Windows DPAPI'} · mobile entry: disabled</span>
        </article>
      </div>

      <div className="rf-layout">
        <div className="rf-stage" aria-label="RF scene">
          <div className="rf-stage__title"><Activity size={16} /> RF Scene</div>
          {status?.mode === 'csi' ? (
            <div className="rf-people">
              {hasPose ? (
                <svg className="rf-pose" viewBox="0 0 100 100" role="img" aria-label="RuView inferred RF pose">
                  {poseEdges.map(([a, b]) => {
                    const p1 = posePoints[a];
                    const p2 = posePoints[b];
                    if (!p1 || !p2 || p1.confidence < 0.1 || p2.confidence < 0.1) return null;
                    return <line key={`${a}-${b}`} x1={p1.x} y1={p1.y} x2={p2.x} y2={p2.y} />;
                  })}
                  {posePoints.map((point, index) => point.confidence >= 0.1
                    ? <circle key={index} cx={point.x} cy={point.y} r="1.7" />
                    : null)}
                </svg>
              ) : silhouettes > 0
                ? Array.from({ length: silhouettes }, (_, index) => <div key={index} className="rf-person" aria-label="inferred person" />)
                : <span className="muted">No presence inferred in the latest RuView frame.</span>}
            </div>
          ) : (
            <div className="rf-rssi">
              <span className="rf-rssi__value">{status?.wifi?.signal_percent ?? '—'}%</span>
              <span className="muted">RSSI radio level only — no body or pose reconstruction.</span>
            </div>
          )}
          <div className="status-strip">
            <span>Presence: {latest?.presence == null ? '—' : latest.presence ? 'yes' : 'no'}</span>
            <span>People: {latest?.person_count ?? '—'}</span>
            <span>Motion: {latest?.motion ?? latest?.motion_energy ?? '—'}</span>
            <span>Quality: {latest?.signal_quality ?? latest?.presence_score ?? '—'}</span>
            <span>HAWKEYE capture: {rfSessionId ? 'recording' : 'off'}</span>
          </div>
        </div>

        <div className="rf-connect-card">
          <div className="eyebrow">LOCAL PC WI-FI</div>
          {localCredentialSurface ? (
            <form onSubmit={connectWifi} className="rf-form">
              <label>
                SSID
                <input value={ssid} onChange={(event) => setSsid(event.target.value)} autoComplete="off" />
              </label>
              <label>
                Password
                <input
                  type="password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  autoComplete="new-password"
                />
              </label>
              <label>
                Security
                <select value={auth} onChange={(event) => setAuth(event.target.value)}>
                  <option value="WPA2PSK">WPA2-Personal</option>
                  <option value="WPA3SAE">WPA3-Personal</option>
                  <option value="WPAPSK">WPA-Personal</option>
                </select>
              </label>
              <label className="rf-check">
                <input type="checkbox" checked={remember} onChange={(event) => setRemember(event.target.checked)} />
                Store encrypted with Windows DPAPI
              </label>
              <button className="kr-button" disabled={connecting || !ssid.trim() || !password}>
                {connecting ? 'Connecting…' : 'Connect on KRISHNA PC'}
              </button>
            </form>
          ) : (
            <p className="muted">
              Wi-Fi credential entry is disabled on remote/mobile sessions. Open KRISHNA locally on the PC to connect a network.
            </p>
          )}
        </div>
      </div>

      {error ? <p className="rf-error">RuView/Wi-Fi: {error}</p> : null}
      <p className="muted rf-limit">
        {status?.capability_limit ?? 'Full RuView sensing requires CSI-capable hardware; a normal laptop Wi-Fi adapter is RSSI-only.'}
      </p>
    </section>
  );
}

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
      <HawkeyeRfPanel />
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
