import { useState } from 'react';
import { Bot, Workflow } from 'lucide-react';
import UniverseHome from './UniverseHome';
import SudarshanUniverse from './SudarshanUniverse';

export default function App() {
  const [activeNav, setActiveNav] = useState<'krishna' | 'sudarshan'>('krishna');

  return (
    <div className="app-shell universe-shell-root">
      <aside className="sidebar universe-sidebar">
        <div className="brand universe-brand"><span className="universe-brand-mark">ॐ</span><span>KRISHNA</span></div>
        <div className="universe-brand-subtitle">AUTONOMOUS INTELLIGENCE OS</div>
        <nav aria-label="Main Menu" className="universe-primary-nav">
          <button
            type="button"
            className={activeNav === 'krishna' ? 'nav-item nav-item--active' : 'nav-item'}
            onClick={() => setActiveNav('krishna')}
            aria-current={activeNav === 'krishna' ? 'page' : undefined}
          >
            <Bot size={18} /><span><strong>KRISHNA</strong><small>Talk · Think · Research</small></span>
          </button>
          <button
            type="button"
            className={activeNav === 'sudarshan' ? 'nav-item nav-item--active' : 'nav-item'}
            onClick={() => setActiveNav('sudarshan')}
            aria-current={activeNav === 'sudarshan' ? 'page' : undefined}
          >
            <Workflow size={18} /><span><strong>SUDARSHAN</strong><small>Execute · Verify · Deliver</small></span>
          </button>
        </nav>
        <div className="universe-side-note">
          <span>LOCAL FIRST · PRIVATE · FREE</span>
          <span>INTERNAL AGENTS: PIPELINE VIEW</span>
          <span>OWNER INTERFACE: KRISHNA</span>
        </div>
      </aside>
      <main className="workspace universe-workspace">
        {activeNav === 'krishna' ? <UniverseHome /> : <SudarshanUniverse />}
      </main>
    </div>
  );
}
