import { useCallback, useRef, useState } from 'react';

type PreviewWindow = Window & {
  __KRISHNA_BRAHMAND_MAIN__?: boolean;
  __KRISHNA_BRAHMAND_PREVIEW__?: boolean;
  __KRISHNA_OWNER_UI__?: boolean;
  __KRISHNA_PREVIEW_API_COMPAT__?: boolean;
  __KRISHNA_OWNER_HOTFIX__?: boolean;
  __KRISHNA_OWNER_ENHANCEMENTS__?: boolean;
  __KRISHNA_OWNER_CORRECTIONS__?: boolean;
  __KRISHNA_OWNER_CORRECTIONS_V2__?: boolean;
  __KRISHNA_OWNER_CORRECTIONS_V3__?: boolean;
  __KRISHNA_APPLE_SHELL__?: boolean;
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
      if (!doc?.head || !doc.body || !win) throw new Error('KRISHNA dashboard document is not accessible.');

      setState('loading');
      setError('');
      doc.documentElement.dataset.krishnaBrahmandPreview = '1';
      delete doc.documentElement.dataset.krishnaUiDegraded;

      const requiredLegacySelectors = [
        '#home', '#assistantOm', '#sudarshan', '#projects', '#plugins',
        '.mainMenuNav', '.side', '.sideFoot', '.opsVitals', 'main.main',
      ];
      const missingLegacy = requiredLegacySelectors.filter((selector) => !doc.querySelector(selector));
      if (missingLegacy.length) throw new Error(`KRISHNA base UI mismatch. Missing: ${missingLegacy.join(', ')}`);

      delete win.__KRISHNA_BRAHMAND_MAIN__;
      delete win.__KRISHNA_BRAHMAND_PREVIEW__;
      delete win.__KRISHNA_OWNER_UI__;
      delete win.__KRISHNA_PREVIEW_API_COMPAT__;
      delete win.__KRISHNA_OWNER_HOTFIX__;
      delete win.__KRISHNA_OWNER_ENHANCEMENTS__;
      delete win.__KRISHNA_OWNER_CORRECTIONS__;
      delete win.__KRISHNA_OWNER_CORRECTIONS_V2__;
      delete win.__KRISHNA_OWNER_CORRECTIONS_V3__;
      delete win.__KRISHNA_APPLE_SHELL__;
      delete win.KRISHNA_BRAHMAND_PREFLIGHT;

      const cacheToken = Date.now();
      const ensureStyle = (id: string, href: string) => {
        doc.getElementById(id)?.remove();
        const link = doc.createElement('link');
        link.id = id;
        link.rel = 'stylesheet';
        link.href = `${href}?v=${cacheToken}`;
        doc.head.appendChild(link);
      };
      ensureStyle('krishna-brahmand-style', '/spatial/krishna-brahmand.css');
      ensureStyle('krishna-live-motion-style', '/spatial/krishna-live-motion.css');
      ensureStyle('krishna-owner-ui-style', '/spatial/krishna-owner-ui.css');
      ensureStyle('krishna-owner-hotfix-style', '/spatial/krishna-owner-hotfix.css');
      ensureStyle('krishna-owner-enhancements-style', '/spatial/krishna-owner-enhancements.css');
      ensureStyle('krishna-owner-corrections-style', '/spatial/krishna-owner-corrections.css');
      ensureStyle('krishna-apple-shell-style', '/spatial/krishna-apple-shell.css');

      [
        'krishna-brahmand-data-script',
        'krishna-brahmand-normalize-script',
        'lr-universe-source-script',
        'krishna-preview-api-compat-script',
        'krishna-brahmand-main-script',
        'krishna-owner-ui-script',
        'krishna-owner-hotfix-script',
        'krishna-owner-enhancements-script',
        'krishna-owner-corrections-script',
        'krishna-apple-shell-script',
        'krishna-brahmand-preflight-script',
      ].forEach((id) => doc.getElementById(id)?.remove());

      const loadScript = (id: string, src: string, timeoutMs = 2500) => new Promise<void>((resolve, reject) => {
        const script = doc.createElement('script');
        script.id = id;
        script.src = `${src}?v=${cacheToken}`;
        script.async = false;
        let finished = false;
        const finish = (callback: () => void) => {
          if (finished) return;
          finished = true;
          win.clearTimeout(timer);
          callback();
        };
        const timer = win.setTimeout(() => {
          finish(() => {
            script.remove();
            reject(new Error(`${src} timed out after ${timeoutMs} ms.`));
          });
        }, timeoutMs);
        script.onload = () => finish(resolve);
        script.onerror = () => finish(() => {
          script.remove();
          reject(new Error(`${src} failed to load.`));
        });
        doc.body.appendChild(script);
      });

      const loadOptional = async (id: string, src: string) => {
        try {
          await loadScript(id, src, 1800);
          return true;
        } catch (reason) {
          doc.documentElement.dataset.krishnaUiDegraded = '1';
          console.warn('[KRISHNA UI optional layer skipped]', src, reason);
          return false;
        }
      };

      const loadBrahmandMainLowLoad = async () => {
        const originalMatchMedia = win.matchMedia.bind(win);
        const lowLoadMatchMedia: typeof win.matchMedia = (query: string) => {
          const result = originalMatchMedia(query);
          if (query !== '(prefers-reduced-motion: reduce)') return result;
          return new Proxy(result, {
            get(target, property) {
              if (property === 'matches') return true;
              const value = Reflect.get(target, property, target);
              return typeof value === 'function' ? value.bind(target) : value;
            },
          });
        };
        win.matchMedia = lowLoadMatchMedia;
        try {
          await loadScript('krishna-brahmand-main-script', '/spatial/krishna-brahmand-main.js');
        } finally {
          win.matchMedia = originalMatchMedia;
        }
      };

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
            doc.getElementById('kbMobileCard')
          );
          if (ready) return resolve();
          if (win.performance.now() - started > 2500) return reject(new Error('KRISHNA owner UI did not become ready within 2.5 seconds.'));
          win.setTimeout(check, 40);
        };
        check();
      });

      void (async () => {
        let runtimeError = '';
        const onRuntimeError = (event: ErrorEvent) => { runtimeError = event.message || 'Unknown browser runtime error'; };
        win.addEventListener('error', onRuntimeError);
        try {
          // Canonical layers are the only blocking stage. The retired duplicate
          // browser drawer is intentionally not part of this readiness contract.
          await loadScript('krishna-brahmand-data-script', '/spatial/krishna-brahmand-data.js');
          await loadScript('krishna-brahmand-normalize-script', '/spatial/krishna-brahmand-normalize.js');
          await loadScript('lr-universe-source-script', '/spatial/lr-universe-source-data.js');
          await loadScript('krishna-preview-api-compat-script', '/spatial/krishna-preview-api-compat.js');
          await loadBrahmandMainLowLoad();
          await loadScript('krishna-owner-ui-script', '/spatial/krishna-owner-ui.js');
          await loadScript('krishna-owner-hotfix-script', '/spatial/krishna-owner-hotfix.js');
          await waitForOwnerDom();

          // Reveal the functional UI before cosmetic layers. Optional polish can
          // degrade independently but can never trap the owner behind Loading.
          setState('ready');

          await loadOptional('krishna-owner-enhancements-script', '/spatial/krishna-owner-enhancements.js');
          await loadOptional('krishna-owner-corrections-script', '/spatial/krishna-owner-corrections.js');
          await loadOptional('krishna-apple-shell-script', '/spatial/krishna-apple-shell.js');
          await loadOptional('krishna-brahmand-preflight-script', '/spatial/krishna-brahmand-preflight.js');

          const preflight = win.KRISHNA_BRAHMAND_PREFLIGHT;
          if (preflight?.ok === false) {
            doc.documentElement.dataset.krishnaUiDegraded = '1';
            const failed = preflight.failed?.map((item) => item.detail ? `${item.name}: ${item.detail}` : item.name).filter(Boolean).join(', ') || 'unknown checks';
            console.warn(`KRISHNA Brahmand preflight warning: ${failed}`);
          }
        } catch (reason) {
          const base = reason instanceof Error ? reason.message : String(reason);
          setError(runtimeError ? `${base} Browser error: ${runtimeError}` : base);
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
