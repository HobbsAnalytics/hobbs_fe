import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { afterEach, vi } from 'vitest';
import App from './App';

vi.mock('react-pdf', () => ({
  pdfjs: { GlobalWorkerOptions: {} },
  Document: () => <div data-testid="pdf-document" />,
  Page: () => null,
}));

function renderAt(route: string) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => new Response(JSON.stringify({ error: 'not_found', detail: 'Not found' }), { status: 404 })),
  );
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[route]}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

afterEach(() => vi.unstubAllGlobals());

describe('App shell', () => {
  it('renders the sidebar logo block and the co-pilot page at /', async () => {
    renderAt('/');
    expect(screen.getByText('Blue Ridge LNG')).toBeInTheDocument();
    expect(screen.getByText('BR')).toBeInTheDocument();
    expect(screen.getAllByText('Project Intelligence').length).toBeGreaterThanOrEqual(1);
    expect(await screen.findByTestId('page-copilot')).toBeInTheDocument();
  });

  it('routes /compliance and /drawings/:id to their pages', async () => {
    const { unmount } = renderAt('/compliance');
    expect(await screen.findByTestId('page-compliance')).toBeInTheDocument();
    unmount();
    renderAt('/drawings/BRL-PIP-ISO-0004');
    expect(await screen.findByTestId('page-drawing')).toHaveTextContent('BRL-PIP-ISO-0004');
  });

  it('unknown routes get a not-found page, not a blank screen', async () => {
    renderAt('/nope');
    expect(await screen.findByTestId('page-notfound')).toBeInTheDocument();
  });
});
