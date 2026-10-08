import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { defineConfig, type Plugin } from 'vite';
import react from '@vitejs/plugin-react';

// Development-only same-origin bridge to the already-running local KRISHNA core.
// API calls still go to the live core, but the visual base is read directly from
// this branch's core/web_validation.html so KRISHNA_SPATIAL_UI_DEFAULT cannot
// accidentally swap the preview iframe to the React spatial frontend.
const coreProxy = {
  target: 'http://127.0.0.1:8766',
  changeOrigin: true,
  configure: (proxy: { on: (event: string, handler: (req: { setHeader: (name: string, value: string) => void }) => void) => void }) => {
    proxy.on('proxyReq', (req) => req.setHeader('origin', 'http://127.0.0.1:8766'));
  },
};

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
          res.setHeader('Content-Type', 'text/plain; charset=utf-8');
          res.end(`Unable to load core/web_validation.html: ${reason instanceof Error ? reason.message : String(reason)}`);
        }
      });
    },
  };
}

export default defineConfig({
  base: '/spatial/',
  plugins: [react(), legacyDashboardPreview()],
  server: { proxy: { '/health': coreProxy, '/api': coreProxy, '/v1': coreProxy, '/orchestration': coreProxy } },
  build: { outDir: 'dist', sourcemap: false, emptyOutDir: true },
});
