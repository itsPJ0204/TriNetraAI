import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true,
    watch: {
      usePolling: true,
      interval: 1000
    },
    proxy: {
      '/search': 'http://127.0.0.1:8000',
      '/tiles': 'http://127.0.0.1:8000',
      '/tile-preview': 'http://127.0.0.1:8000',
      '/ingest': 'http://127.0.0.1:8000',
      '/temporal': 'http://127.0.0.1:8000',
      '/ai-assistant': 'http://127.0.0.1:8000',
      '/health': 'http://127.0.0.1:8000',
      '/compare': 'http://127.0.0.1:8000',
      '/detect-changes': 'http://127.0.0.1:8000',
      '/data': 'http://127.0.0.1:8000',
    }
  }
});
