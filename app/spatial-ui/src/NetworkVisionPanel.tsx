import { useEffect, useState } from 'react';
import { Activity, Monitor, Network, RefreshCw, Router, ShieldCheck } from 'lucide-react';

type NetworkDevice = { id?: string; name?: string; ip?: string; kind?: string; status?: string; bandwidth_mbps?: number };
type NetworkSnapshot = { devices?: NetworkDevice[]; source?: string; updated_at?: string };

export default function NetworkVisionPanel() {
  const [data, setData] = useState<NetworkSnapshot | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const refresh = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/network/overview', { cache: 'no-store' });
      if (!response.ok) throw new Error(response.status === 404 ? 'Network inventory backend not connected yet' : 'Network inventory unavailable (HTTP ' + response.status + ')');
      const snapshot = await response.json() as NetworkSnapshot;
      setData(snapshot);
      setError('');
    } catch (reason) {
      setData(null);
      setError(reason instanceof Error ? reason.message : String(reason));
    } finally { setLoading(false); }
  };
  useEffect(() => { void refresh(); }, []);
  const devices = data?.devices ?? [];
  const servers = devices.filter(device => /server/i.test(device.kind ?? ''));
  return (
    <section className="panel-content" aria-label="Network and Vision">
      <div className="eyebrow">KRISHNA · NETWORK &amp; VISION</div>
      <h1>Network &amp; Vision</h1>
      <p className="muted">One control room for network discovery, IP inventory, bandwidth, DNS insights and authorized headless server consoles. No device changes are performed from this screen.</p>
      <div className="bento">
        <article className="card"><Router /><strong>Routers &amp; switches</strong><span>{devices.filter(d => /router|switch/i.test(d.kind ?? '')).length} reported · SNMP / supported router adapters</span></article>
        <article className="card"><Network /><strong>Device inventory</strong><span>{devices.length} reported · NetAlertX / NetMap adapters</span></article>
        <article className="card"><Activity /><strong>Bandwidth &amp; domains</strong><span>ntopng / flow telemetry and AdGuard Home DNS integration required</span></article>
        <article className="card"><Monitor /><strong>Server vision</strong><span>{servers.length} reported · RDP, VNC, SSH or BMC console after authorization</span></article>
      </div>
      <div className="status-strip"><span>Gateway: 192.168.0.1 (last observed)</span><span>Network: 192.168.0.0/24 (last observed)</span><span>Read-only discovery</span></div>
      <button className="kr-button" type="button" onClick={() => void refresh()} disabled={loading}><RefreshCw size={16} /> {loading ? 'Checking…' : 'Refresh network inventory'}</button>
      {error ? <p className="muted" role="status">{error}. Device and traffic counts are not fabricated.</p> : null}
      <h2>Discovered devices</h2>
      {devices.length ? <div className="bento">{devices.map((device, index) => <article className="card" key={device.id ?? device.ip ?? index}><Network /><strong>{device.name || device.ip || 'Unnamed device'}</strong><span>{device.ip || 'IP unknown'} · {device.kind || 'unknown type'} · {device.status || 'status unknown'}</span></article>)}</div> : <p className="muted">No verified device inventory available yet. Connect the network discovery backend to populate this list.</p>}
      <h2>Headless server screens</h2>
      <p className="muted">Register authorized server endpoints through a secured backend. Select a server to open an authenticated remote console when an RDP, VNC, SSH or BMC gateway is configured. This UI does not expose direct credentials or pretend to stream a screen.</p>
      <div className="status-strip"><span><ShieldCheck size={14} /> Access approval required</span><span>Encrypted connections</span><span>Audit logging</span></div>
      <h2>Integrations</h2>
      <p className="muted">Discovery: NetAlertX · topology/IPAM: NetMap · traffic: ntopng · DNS: AdGuard Home · optional router adapter: NetPulse (OpenWrt) · remote access: Apache Guacamole / MeshCentral. Features depend on compatible hardware and separately configured services.</p>
    </section>
  );
}
