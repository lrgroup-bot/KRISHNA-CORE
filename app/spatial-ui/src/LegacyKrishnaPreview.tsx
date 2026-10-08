import { useCallback, useRef, useState } from 'react';

type PreviewWindow = Window & {
  __KRISHNA_BRAHMAND_MAIN__?: boolean;
  __KRISHNA_BRAHMAND_PREVIEW__?: boolean;
  __KRISHNA_OWNER_UI__?: boolean;
  KRISHNA_BRAHMAND_DATA?: { nodes?: Record<string, unknown> };
  LR_UNIVERSE_SOURCE_DATA?: Record<string, unknown>;
  KRISHNA_BRAHMAND_PREFLIGHT?: {
    ok?: boolean;
    failed?: Array<{ name?: string; detail?: string }>;
  };
};

export default function LegacyKrishnaPreview() {
  const frameRef = useRef<HTMLIFrameElement>(null);
  const [state, setState] = useState<'loading' | 'ready' | 'error'>('loading');
  const [error, setError] = useState('');

  const inject = useCallback(() => {
    try {
      const frame = frameRef.current;
      const doc = frame?.contentDocument;
      const win = frame?.contentWindow as PreviewWindow | null;
      if (!doc?.head || !doc.body || !win) throw new Error('Legacy dashboard document is not accessible.');

      setState('loading');
      setError('');
      doc.documentElement.dataset.krishnaBrahmandPreview = '1';

      const requiredLegacySelectors = [
        '#home', '#assistantOm', '#sudarshan', '#projects', '#plugins',
        '.mainMenuNav', '.side', '.sideFoot', '.opsVitals', 'main.main',
      ];
      const missingLegacy = requiredLegacySelectors.filter((selector) => !doc.querySelector(selector));
      if (missingLegacy.length) throw new Error(`Legacy KRISHNA base mismatch. Missing: ${missingLegacy.join(', ')}`);

      delete win.__KRISHNA_BRAHMAND_MAIN__;
      delete win.__KRISHNA_BRAHMAND_PREVIEW__;
      delete win.__KRISHNA_OWNER_UI__;
      delete win.KRISHNA_BRAHMAND_PREFLIGHT;

      const ensureStyle = (id: string, href: string) => {
        if (doc.getElementById(id)) return;
        const link = doc.createElement('link');
        link.id = id;
        link.rel = 'stylesheet';
        link.href = href;
        doc.head.appendChild(link);
      };
      ensureStyle('krishna-brahmand-style', '/spatial/krishna-brahmand.css');
      ensureStyle('krishna-live-motion-style', '/spatial/krishna-live-motion.css');
      ensureStyle('krishna-owner-ui-style', '/spatial/krishna-owner-ui.css');

      [
        'krishna-brahmand-data-script',
        'krishna-brahmand-normalize-script',
        'lr-universe-source-script',
        'krishna-brahmand-main-script',
        'krishna-owner-ui-script',
        'krishna-brahmand-preflight-script',
      ].forEach((id) => doc.getElementById(id)?.remove());

      const loadScript = (id: string, src: string) => new Promise<void>((resolve, reject) => {
        const script = doc.createElement('script');
        script.id = id;
        script.src = `${src}?v=${Date.now()}`;
        script.onload = () => resolve();
        script.onerror = () => reject(new Error(`${src} failed to load.`));
        doc.body.appendChild(script);
      });

      const waitForOwnerDom = () => new Promise<void>((resolve, reject) => {
        const started = win.performance.now();
        const check = () => {
          const ready = Boolean(
            doc.getElementById('kbNavLR') &&
            doc.getElementById('kbNavBrahmand') &&
            doc.querySelector('.kb-core-shell') &&
            doc.getElementById('brahmand') &&
            doc.getElementById('lrUniverse') &&
            doc.getElementById('kbOwnerLoad') &&
            doc.getElementById('kbMobileCard') &&
            doc.getElementById('kbBrowserToggle') &&
            doc.getElementById('kbBrowserDrawer')
          );
          if (ready) return resolve();
          if (win.performance.now() - started > 3500) return reject(new Error('KRISHNA owner UI loaded but did not inject its DOM within 3.5 seconds.'));
          win.setTimeout(check, 50);
        };
        check();
      });

      void (async () => {
        let runtimeError = '';
        const onRuntimeError = (event: ErrorEvent) => { runtimeError = event.message || 'Unknown browser runtime error'; };
        win.addEventListener('error', onRuntimeError);
        try {
          await loadScript('krishna-brahmand-data-script', '/spatial/krishna-brahmand-data.js');
          await loadScript('krishna-brahmand-normalize-script', '/spatial/krishna-brahmand-normalize.js');
          await loadScript('lr-universe-source-script', '/spatial/lr-universe-source-data.js');
          await loadScript('krishna-brahmand-main-script', '/spatial/krishna-brahmand-main.js');
          await loadScript('krishna-owner-ui-script', '/spatial/krishna-owner-ui.js');
          try {
            await waitForOwnerDom();
          } catch (reason) {
            const base = reason instanceof Error ? reason.message : String(reason);
            throw new Error(runtimeError ? `${base} Browser error: ${runtimeError}` : base);
          }
          await loadScript('krishna-brahmand-preflight-script', '/spatial/krishna-brahmand-preflight.js');
          const preflight = win.KRISHNA_BRAHMAND_PREFLIGHT;
          if (preflight?.ok === false) {
            const failed = preflight.failed?.map((item) => item.detail ? `${item.name}: ${item.detail}` : item.name).filter(Boolean).join(', ') || 'unknown checks';
            throw new Error(`KRISHNA Brahmand preflight failed: ${failed}`);
          }
          setState('ready');
        } catch (reason) {
          setError(reason instanceof Error ? reason.message : String(reason));
          setState('error');
        } finally {
          win.removeEventListener('error', onRuntimeError);
        }
      })();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
      setState('error');
    }
  }, []);

  return (
    <div className="legacy-preview-shell">
      <iframe ref={frameRef} className="legacy-preview-frame" src="/legacy-dashboard-preview" title="KRISHNA Brahmand frontend preview" onLoad={inject} />
      {state === 'loading' ? <div className="legacy-preview-status">Loading KRISHNA frontend…</div> : null}
      {state === 'error' ? <div className="legacy-preview-status legacy-preview-error">{error}</div> : null}
    </div>
  );
}
