import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  base: '/spatial/',
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    proxy: {
      '/api': 'http://127.0.0.1:8766',
      '/health': 'http://127.0.0.1:8766',
    },
  },
  preview: {
    host: '127.0.0.1',
    proxy: {
      '/api': 'http://127.0.0.1:8766',
      '/health': 'http://127.0.0.1:8766',
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    emptyOutDir: true,
  },
});
