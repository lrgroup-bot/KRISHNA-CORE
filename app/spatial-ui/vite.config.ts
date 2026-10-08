import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Development-only same-origin bridge to the already-running local KRISHNA core.
// The backend still enforces authority and permission checks.
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
  server: { proxy: { '/health': coreProxy, '/api': coreProxy, '/v1': coreProxy } },
  build: { outDir: 'dist', sourcemap: false, emptyOutDir: true },
});
