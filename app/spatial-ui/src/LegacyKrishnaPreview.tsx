import { useCallback, useRef, useState } from 'react';

type PreviewWindow = Window & {
  KRISHNA_BRAHMAND_PREFLIGHT?: { ok?: boolean; failed?: Array<{ name?: string; detail?: string }> };
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

      [
        'krishna-brahmand-data-script',
        'krishna-brahmand-normalize-script',
        'krishna-brahmand-main-script',
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

      void (async () => {
        try {
          await loadScript('krishna-brahmand-data-script', '/spatial/krishna-brahmand-data.js');
          await loadScript('krishna-brahmand-normalize-script', '/spatial/krishna-brahmand-normalize.js');
          await loadScript('krishna-brahmand-main-script', '/spatial/krishna-brahmand-main.js');
          await new Promise((resolve) => win.setTimeout(resolve, 80));
          await loadScript('krishna-brahmand-preflight-script', '/spatial/krishna-brahmand-preflight.js');
          const preflight = win.KRISHNA_BRAHMAND_PREFLIGHT;
          if (preflight && preflight.ok === false) {
            const failed = preflight.failed?.map((item) => item.name).filter(Boolean).join(', ') || 'unknown checks';
            throw new Error(`KRISHNA Brahmand preflight failed: ${failed}`);
          }
          setState('ready');
        } catch (reason) {
          setError(reason instanceof Error ? reason.message : String(reason));
          setState('error');
        }
      })();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
      setState('error');
    }
  }, []);

  return (
    <div className="legacy-preview-shell">
      <iframe
        ref={frameRef}
        className="legacy-preview-frame"
        src="/dashboard?krishna_brahmand_preview=1"
        title="KRISHNA Brahmand frontend preview"
        onLoad={inject}
      />
      {state === 'loading' ? <div className="legacy-preview-status">Loading KRISHNA frontend…</div> : null}
      {state === 'error' ? <div className="legacy-preview-status legacy-preview-error">{error}</div> : null}
    </div>
  );
}
