import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  base: '/spatial/',
  plugins: [react()],
  build: {
    outDir: 'dist',
    sourcemap: false,
    emptyOutDir: true,
  },
});
