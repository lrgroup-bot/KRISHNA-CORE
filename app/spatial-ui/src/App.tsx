import { useState } from 'react';
import UniverseHome from './UniverseHome';
import SudarshanUniverse from './SudarshanUniverse';
import LiveSidebar, { type MainView } from './LiveSidebar';
import { ChatsDashboard, LRUniverseDashboard, PluginsDashboard, ProjectsDashboard } from './AuxDashboards';

export default function App() {
  const [activeNav, setActiveNav] = useState<MainView>('krishna');

  return (
    <div className="app-shell live-shell-root">
      <LiveSidebar active={activeNav} onSelect={setActiveNav} />
      <main className="workspace live-workspace">
        <div className="live-ambient-grid" aria-hidden="true" />
        <div className="live-ambient-orb live-ambient-orb-a" aria-hidden="true" />
        <div className="live-ambient-orb live-ambient-orb-b" aria-hidden="true" />
        <div className="live-view-stage" key={activeNav}>
          {activeNav === 'krishna' ? <UniverseHome /> : null}
          {activeNav === 'sudarshan' ? <SudarshanUniverse /> : null}
          {activeNav === 'lr-universe' ? <LRUniverseDashboard /> : null}
          {activeNav === 'projects' ? <ProjectsDashboard /> : null}
          {activeNav === 'chats' ? <ChatsDashboard /> : null}
          {activeNav === 'plugins' ? <PluginsDashboard /> : null}
        </div>
      </main>
    </div>
  );
}
