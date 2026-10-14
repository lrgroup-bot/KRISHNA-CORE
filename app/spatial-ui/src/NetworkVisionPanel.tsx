import { useCallback, useEffect, useMemo, useState } from 'react';
import { Activity, ArrowUpRight, Cable, CheckCircle2, CircleHelp, Globe2, HardDrive, LockKeyhole, Monitor, Network, RefreshCw, Router, Search, Server, ShieldCheck, Wifi, XCircle } from 'lucide-react';

type Device = { id?: string; name?: string; ip?: string; kind?: string; status?: string; bandwidth_mbps?: number; console_url?: string; console_type?: string };
type Snapshot = { devices?: Device[]; source?: string; updated_at?: string; gateway?: string; subnet?: string };
type Section = 'overview' | 'devices' | 'servers' | 'traffic' | 'integrations';
const sections: { id: Section; label: string }[] = [
  { id: 'overview', label: 'Overview' }, { id: 'devices', label: 'Devices & IPs' },
  { id: 'servers', label: 'Server wall' }, { id: 'traffic', label: 'Traffic & DNS' },
  { id: 'integrations', label: 'Integrations' },
];
const integrations = [
  { name: 'NetAlertX', role: 'Discovery and device changes' },
  { name: 'NetMap / NetBox', role: 'Topology and IP inventory' },
  { name: 'ntopng', role: 'Network traffic telemetry' },
  { name: 'AdGuard Home', role: 'DNS and domain insights' },
  { name: 'Apache Guacamole', role: 'Browser-based RDP / VNC / SSH' },
  { name: 'Redfish / BMC', role: 'Out-of-band server console' },
];
const deviceIcon = (kind?: string) => /router|gateway/i.test(kind ?? '') ? <Router size={18} /> : /switch/i.test(kind ?? '') ? <Cable size={18} /> : /server/i.test(kind ?? '') ? <Server size={18} /> : /wifi|access point/i.test(kind ?? '') ? <Wifi size={18} /> : <Monitor size={18} />;
const isServer = (d: Device) => /server/i.test(d.kind ?? '');
const isInfrastructure = (d: Device) => /router|gateway|switch|access point/i.test(d.kind ?? '');
const safeConsoleUrl = (url?: string) => {
  if (!url) return null;
  try {
    const parsed = new URL(url, window.location.origin);
    if (parsed.origin !== window.location.origin || !parsed.pathname.startsWith('/')) return null;
    return parsed.href;
  } catch { return null; }
};
export default function NetworkVisionPanel() {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [tab, setTab] = useState<Section>('overview');
  const [query, setQuery] = useState('');
  const refresh = useCallback(async (signal?: AbortSignal) => {
    setLoading(true);
    try {
      const response = await fetch('/api/network/overview', { cache: 'no-store', signal });
      if (!response.ok) throw new Error(response.status === 404 ? 'Discovery backend is not connected' : `Inventory request failed (HTTP ${response.status})`);
      const payload: unknown = await response.json();
      if (!payload || typeof payload !== 'object' || !Array.isArray((payload as Snapshot).devices)) throw new Error('Invalid network inventory response');
      if (signal?.aborted) return;
      setSnapshot(payload as Snapshot);
      setError('');
    } catch (reason) {
      if (signal?.aborted) return;
      setSnapshot(null);
      setError(reason instanceof Error ? reason.message : String(reason));
    } finally { if (!signal?.aborted) setLoading(false); }
  }, []);
  useEffect(() => { const controller = new AbortController(); void refresh(controller.signal); return () => controller.abort(); }, [refresh]);
  const devices = snapshot?.devices ?? [];
  const servers = devices.filter(isServer);
  const infrastructure = devices.filter(isInfrastructure);
  const online = devices.filter(d => /^(online|up|active)$/i.test(d.status ?? '')).length;
  const filtered = useMemo(() => devices.filter(d => [d.name, d.ip, d.kind, d.status].join(' ').toLowerCase().includes(query.toLowerCase().trim())), [devices, query]);
  const time = snapshot?.updated_at ? new Date(snapshot.updated_at) : null;
  const updated = time && !Number.isNaN(time.getTime()) ? time.toLocaleString() : 'Not yet synchronized';
  const statCards = [
    { label: 'Discovered devices', value: String(devices.length), hint: snapshot ? `${online} confirmed online` : 'Awaiting discovery', icon: <Network size={20} /> },
    { label: 'Network equipment', value: String(infrastructure.length), hint: 'Routers · switches · access points', icon: <Router size={20} /> },
    { label: 'Headless servers', value: String(servers.length), hint: 'Authorized remote consoles', icon: <Server size={20} /> },
    { label: 'Data source', value: snapshot?.source || 'Not connected', hint: 'Live telemetry only', icon: <Activity size={20} /> },
  ];
  return (
    <section className="nv-shell" aria-label="Network and Vision">
      <header className="nv-header">
        <div><div className="nv-kicker"><span className="nv-kicker-dot" /> KRISHNA / INFRASTRUCTURE</div><h1>Network <span>&amp;</span> Vision</h1><p>Observe every connection. Control authorized servers from one place.</p></div>
        <div className="nv-header-actions"><span className={snapshot ? 'nv-pill nv-pill--live' : 'nv-pill'}>{snapshot ? <CheckCircle2 size={14} /> : <XCircle size={14} />}{snapshot ? 'Inventory connected' : 'Not connected'}</span><button type="button" className="nv-refresh" onClick={() => void refresh()} disabled={loading}><RefreshCw size={16} className={loading ? 'nv-spin' : ''} /> Refresh</button></div>
      </header>
      <div className="nv-toolbar"><nav className="nv-tabs" aria-label="Network and Vision sections">{sections.map(item => <button key={item.id} type="button" className={tab === item.id ? 'nv-tab nv-tab--active' : 'nv-tab'} onClick={() => setTab(item.id)}>{item.label}</button>)}</nav><span className="nv-updated">Updated: {updated}</span></div>
      {error && <div className="nv-notice" role="status"><CircleHelp size={19} /><div><strong>Live inventory unavailable</strong><p>{error}. Connect a compatible discovery service to display verified devices. No simulated data is shown.</p></div></div>}
      {(tab === 'overview' || tab === 'devices') && <div className="nv-stats">{statCards.map(card => <article key={card.label} className="nv-stat"><span className="nv-stat-icon">{card.icon}</span><span className="nv-stat-label">{card.label}</span><strong>{card.value}</strong><small>{card.hint}</small></article>)}</div>}
      {tab === 'overview' && <div className="nv-main-grid">
        <article className="nv-surface nv-topology"><div className="nv-section-head"><div><span className="nv-overline">CONNECTION MAP</span><h2>Network topology</h2></div><span className="nv-quiet">Logical overview</span></div>
          <div className="nv-map"><div className="nv-map-node nv-map-node--internet"><Globe2 size={23}/><strong>Internet</strong></div><div className="nv-map-link"/><div className="nv-map-node nv-map-node--gateway"><Router size={25}/><strong>Gateway</strong><small>{snapshot?.gateway || 'IP unverified'}</small></div><div className="nv-map-link"/><div className="nv-map-branches"><div className="nv-map-node"><Cable size={23}/><strong>Network equipment</strong><small>{infrastructure.length} reported</small></div><div className="nv-map-node"><Server size={23}/><strong>Servers</strong><small>{servers.length} reported</small></div><div className="nv-map-node"><Monitor size={23}/><strong>Other devices</strong><small>{Math.max(0, devices.length - servers.length - infrastructure.length)} reported</small></div></div></div>
          <p className="nv-footnote">Topology is a logical summary, not a verified physical wiring diagram. Switch-port relationships require SNMP/LLDP or router telemetry.</p>
        </article>
        <article className="nv-surface nv-side"><div className="nv-section-head"><div><span className="nv-overline">OPERATIONS</span><h2>Control readiness</h2></div><ShieldCheck size={19}/></div><div className="nv-readiness">{[['Discovery',snapshot ? 'Connected' : 'Setup required'],['IP reservations','Router integration required'],['Traffic monitoring','Gateway / flow feed required'],['Remote consoles','Authorized gateway required'],['Tailscale','Separate integration required']].map(([name,state]) => <div key={name} className="nv-readiness-row"><span>{name}</span><small>{state}</small></div>)}</div><div className="nv-security"><LockKeyhole size={17}/><span>Read-only by default. Network changes require approval.</span></div></article>
      </div>}
      {tab === 'devices' && <article className="nv-surface"><div className="nv-section-head"><div><span className="nv-overline">ASSET INVENTORY</span><h2>Connected devices &amp; IP addresses</h2></div><label className="nv-search"><Search size={16}/><input aria-label="Filter devices" value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search IP, name, type…" /></label></div><div className="nv-table-wrap"><table className="nv-table"><thead><tr><th>Device</th><th>IP address</th><th>Type</th><th>Status</th><th>Bandwidth</th></tr></thead><tbody>{filtered.map((d,i)=><tr key={d.id || d.ip || i}><td><span className="nv-device-name">{deviceIcon(d.kind)}{d.name || 'Unnamed device'}</span></td><td className="nv-mono">{d.ip || '—'}</td><td>{d.kind || 'Unknown'}</td><td>{d.status || 'Unknown'}</td><td>{typeof d.bandwidth_mbps === 'number' ? `${d.bandwidth_mbps.toFixed(1)} Mbps` : 'Not measured'}</td></tr>)}</tbody></table>{filtered.length===0 && <div className="nv-empty">{query ? 'No devices match this filter.' : 'No devices reported. Connect discovery to populate this table.'}</div>}</div></article>}
      {tab === 'servers' && <article className="nv-surface"><div className="nv-section-head"><div><span className="nv-overline">REMOTE OPERATIONS</span><h2>Server wall</h2></div><span className="nv-quiet">{servers.length} registered</span></div><p className="nv-explain">Access headless servers through an authenticated same-origin console gateway. Live thumbnails require a separately configured streaming service.</p><div className="nv-server-grid">{servers.map((d,i)=>{const url=safeConsoleUrl(d.console_url);return <article key={d.id||d.ip||i} className="nv-server-card"><div className="nv-server-preview"><Monitor size={36}/><span>Preview not connected</span></div><div className="nv-server-meta"><strong>{d.name||`Server ${i+1}`}</strong><span>{d.ip||'IP unknown'} · {d.status||'Unknown'}</span></div>{url ? <a className="nv-console-link" href={url} target="_blank" rel="noopener noreferrer">Open authorized console <ArrowUpRight size={15}/></a> : <span className="nv-console-disabled"><LockKeyhole size={14}/> Console not configured</span>}</article>})}</div>{servers.length===0 && <div className="nv-empty"><HardDrive size={28}/> No servers registered yet. Add verified server inventory and configure a secure remote console gateway.</div>}</article>}
      {tab === 'traffic' && <div className="nv-main-grid"><article className="nv-surface"><span className="nv-overline">NETWORK OBSERVABILITY</span><h2>Traffic intelligence</h2><div className="nv-empty"><Activity size={30}/> Per-device usage requires traffic exported from your router, gateway or monitored switch port. This dashboard will not infer traffic from an ordinary LAN client.</div></article><article className="nv-surface"><span className="nv-overline">DNS VISIBILITY</span><h2>Domain activity</h2><div className="nv-empty"><Globe2 size={30}/> Connect AdGuard Home for authorized DNS query reporting. DNS logs do not reveal full HTTPS URLs.</div></article></div>}
      {tab === 'integrations' && <article className="nv-surface"><div className="nv-section-head"><div><span className="nv-overline">EXTENSIBLE INFRASTRUCTURE</span><h2>Integration catalog</h2></div><span className="nv-quiet">Configuration required</span></div><div className="nv-integration-grid">{integrations.map(item=><div className="nv-integration" key={item.name}><div className="nv-integration-icon"><Network size={19}/></div><div><strong>{item.name}</strong><p>{item.role}</p></div><span>Not verified</span></div>)}</div></article>}
      <footer className="nv-footer"><ShieldCheck size={15}/> Local-first · no fabricated telemetry · explicit authorization for remote control and IP changes</footer>
    </section>
  );
}
