import { useCallback, useRef, useState } from 'react';

export default function LegacyKrishnaPreview() {
  const frameRef = useRef<HTMLIFrameElement>(null);
  const [state, setState] = useState<'loading' | 'ready' | 'error'>('loading');
  const [error, setError] = useState('');

  const inject = useCallback(() => {
    try {
      const frame = frameRef.current;
      const doc = frame?.contentDocument;
      const win = frame?.contentWindow as (Window & { KRISHNA_BRAHMAND_DATA?: { nodes?: Record<string, Record<string, unknown>> } }) | null;
      if (!doc?.head || !doc.body || !win) throw new Error('Legacy dashboard document is not accessible.');

      doc.documentElement.dataset.krishnaBrahmandPreview = '1';

      if (!doc.getElementById('krishna-brahmand-style')) {
        const link = doc.createElement('link');
        link.id = 'krishna-brahmand-style';
        link.rel = 'stylesheet';
        link.href = '/spatial/krishna-brahmand.css';
        doc.head.appendChild(link);
      }

      ['krishna-brahmand-data-script', 'krishna-brahmand-main-script'].forEach((id) => doc.getElementById(id)?.remove());

      const dataScript = doc.createElement('script');
      dataScript.id = 'krishna-brahmand-data-script';
      dataScript.src = `/spatial/krishna-brahmand-data.js?v=${Date.now()}`;
      dataScript.onerror = () => {
        setError('KRISHNA Brahmand pipeline data failed to load.');
        setState('error');
      };
      dataScript.onload = () => {
        const nodes = win.KRISHNA_BRAHMAND_DATA?.nodes;
        if (nodes) Object.entries(nodes).forEach(([id, definition]) => { definition.id = id; });

        const mainScript = doc.createElement('script');
        mainScript.id = 'krishna-brahmand-main-script';
        mainScript.src = `/spatial/krishna-brahmand-main.js?v=${Date.now()}`;
        mainScript.onload = () => setState('ready');
        mainScript.onerror = () => {
          setError('KRISHNA Brahmand enhancement runtime failed to load.');
          setState('error');
        };
        doc.body.appendChild(mainScript);
      };
      doc.body.appendChild(dataScript);
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
