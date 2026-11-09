import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), 'VITE_');
  // Compile-time constant: fixtures only in non-production modes with VITE_USE_FIXTURES=true. In `vite build`
  // (mode=production) this is the literal `false`, so the fixture branch in main.tsx and its dynamic import are
  // removed and no fixture chunk/asset is emitted. scripts/check-no-fixtures.mjs verifies dist/ after every build.
  const useFixtures = mode !== 'production' && (env.VITE_USE_FIXTURES ?? process.env.VITE_USE_FIXTURES) === 'true';
  return {
    plugins: [react()],
    define: { __USE_FIXTURES__: JSON.stringify(useFixtures) },
    server: {
      port: 3000,
      proxy: {
        '/api': {
          target: 'http://localhost:8000',
          changeOrigin: true,
        },
      },
    },
    build: {
      outDir: 'dist',
      sourcemap: false,
    },
  };
});
