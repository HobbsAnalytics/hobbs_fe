import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import App from './App';
import { ApiError } from './lib/api';
import './styles/globals.css';

const NO_RETRY = new Set([401, 403, 404, 422]);

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,
      retry: (count, err) => !(err instanceof ApiError && NO_RETRY.has(err.status)) && count < 2,
      refetchOnWindowFocus: false,
    },
  },
});

async function boot() {
  // __USE_FIXTURES__ is a compile-time literal (vite.config.ts). It is `false` in production builds, so this branch
  // and the fixtures chunk are dropped from dist/ (verified by scripts/check-no-fixtures.mjs).
  if (__USE_FIXTURES__) {
    const { installFixtureFetch } = await import('./fixtures/install');
    installFixtureFetch();
  }
  ReactDOM.createRoot(document.getElementById('root')!).render(
    <React.StrictMode>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </QueryClientProvider>
    </React.StrictMode>,
  );
}

void boot();
