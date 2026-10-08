import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { defineConfig, type Plugin } from 'vite';
import react from '@vitejs/plugin-react';

function localProxy(target: string, label: string, rewrite?: (path: string) => string) {
  return {
    target,
    changeOrigin: true,
    ...(rewrite ? { rewrite } : {}),
    configure: (proxy: any) => {
      proxy.on('proxyReq', (req: { setHeader: (name: string, value: string) => void }) => {
        req.setHeader('origin', target);
      });
      proxy.on('error', (_error: Error, _req: unknown, res: any) => {
        if (!res || res.headersSent || typeof res.writeHead !== 'function') return;
        const body = JSON.stringify({
          ok: false,
          error: `${label} unavailable`,
          target,
          hint: label === 'KRISHNA Core'
            ? 'Start KRISHNA Core on port 8766 before testing live frontend telemetry or Garudanetra.'
            : 'Start the LR Universe service on port 8788 to enable its live read bridge.',
        });
        res.writeHead(502, {
          'Content-Type': 'application/json; charset=utf-8',
          'Cache-Control': 'no-store, max-age=0',
        });
        res.end(body);
      });
    },
  };
}

const coreProxy = localProxy('http://127.0.0.1:8766', 'KRISHNA Core');
const lrUniverseProxy = localProxy(
  'http://127.0.0.1:8788',
  'LR Universe',
  (path: string) => path.replace(/^\/lr-universe-api/, '') || '/',
);

const legacyDashboardPath = fileURLToPath(new URL('../../core/web_validation.html', import.meta.url));

function legacyDashboardPreview(): Plugin {
  return {
    name: 'krishna-legacy-dashboard-preview',
    configureServer(server) {
      server.middlewares.use('/legacy-dashboard-preview', async (_req, res) => {
        try {
          const html = await readFile(legacyDashboardPath, 'utf8');
          res.statusCode = 200;
          res.setHeader('Content-Type', 'text/html; charset=utf-8');
          res.setHeader('Cache-Control', 'no-store, max-age=0');
          res.end(html);
        } catch (reason) {
          res.statusCode = 500;
          res.setHeader('Content-Type', 'application/json; charset=utf-8');
          res.end(JSON.stringify({
            ok: false,
            error: 'Unable to load copied KRISHNA dashboard source',
            detail: reason instanceof Error ? reason.message : String(reason),
          }));
        }
      });
    },
  };
}

export default defineConfig({
  base: '/spatial/',
  plugins: [react(), legacyDashboardPreview()],
  server: {
    proxy: {
      '/health': coreProxy,
      '/api': coreProxy,
      '/v1': coreProxy,
      '/orchestration': coreProxy,
      '/lr-universe-api': lrUniverseProxy,
    },
  },
  build: { outDir: 'dist', sourcemap: false, emptyOutDir: true },
});
