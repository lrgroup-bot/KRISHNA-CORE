import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Development-only same-origin bridge to the already-running local KRISHNA core.
// The backend still enforces authority and permission checks. The /dashboard proxy
// lets the isolated spatial preview render the existing verified frontend unchanged
// and layer the Brahmand UI on top without deploying it into the runtime.
const coreProxy = {
  target: 'http://127.0.0.1:8766',
  changeOrigin: true,
  configure: (proxy: { on: (event: string, handler: (req: { setHeader: (name: string, value: string) => void }) => void) => void }) => {
    proxy.on('proxyReq', (req) => req.setHeader('origin', 'http://127.0.0.1:8766'));
  },
};

export default defineConfig({
  base: '/spatial/',
  plugins: [react()],
  server: { proxy: { '/health': coreProxy, '/api': coreProxy, '/v1': coreProxy, '/dashboard': coreProxy, '/orchestration': coreProxy } },
  build: { outDir: 'dist', sourcemap: false, emptyOutDir: true },
});
