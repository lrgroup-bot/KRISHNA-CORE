import { useCallback, useRef, useState } from 'react';

export default function LegacyKrishnaPreview() {
  const frameRef = useRef<HTMLIFrameElement>(null);
  const [state, setState] = useState<'loading' | 'ready' | 'error'>('loading');
  const [error, setError] = useState('');

  const inject = useCallback(() => {
    try {
      const frame = frameRef.current;
      const doc = frame?.contentDocument;
      if (!doc?.head || !doc.body) throw new Error('Legacy dashboard document is not accessible.');

      doc.documentElement.dataset.krishnaBrahmandPreview = '1';

      if (!doc.getElementById('krishna-brahmand-style')) {
        const link = doc.createElement('link');
        link.id = 'krishna-brahmand-style';
        link.rel = 'stylesheet';
        link.href = '/spatial/krishna-brahmand.css';
        doc.head.appendChild(link);
      }

      const old = doc.getElementById('krishna-brahmand-script');
      if (old) old.remove();
      const script = doc.createElement('script');
      script.id = 'krishna-brahmand-script';
      script.src = `/spatial/krishna-brahmand.js?v=${Date.now()}`;
      script.onload = () => setState('ready');
      script.onerror = () => {
        setError('KRISHNA Brahmand enhancement script failed to load.');
        setState('error');
      };
      doc.body.appendChild(script);
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
