import { screen, waitFor, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import KpiStrip from '../src/components/dashboards/KpiStrip';
import Sidebar from '../src/components/layout/Sidebar';
import TopBar from '../src/components/layout/TopBar';
import * as fx from '../src/fixtures/data';
import { jsonResponse, mockFetch, never, renderWithProviders } from './utils';

afterEach(() => vi.unstubAllGlobals());

describe('KpiStrip', () => {
  it('renders 4 cards from /api/kpi/today', async () => {
    mockFetch({ '/api/kpi/today': fx.kpiToday });
    renderWithProviders(<KpiStrip />);
    const cards = await screen.findAllByTestId('kpi-card');
    expect(cards).toHaveLength(4);
    const text = cards.map((c) => c.textContent).join(' | ');
    expect(text).toContain('On track');
    expect(text).toContain('6 of 11');
    expect(text).toContain('+2.3%');
    expect(text).toContain('$4.8M');
    expect(text).toContain('$208.7M');
    expect(text).toContain('28 days');
    expect(text).toContain('24');
    expect(text).toContain('9 compliance');
    expect(text).toContain('15 workmanship');
  });

  it('shows a skeleton while loading', () => {
    mockFetch({ '/api/kpi/today': never });
    renderWithProviders(<KpiStrip />);
    expect(screen.getAllByTestId('kpi-skeleton')).toHaveLength(4);
    expect(screen.queryByTestId('kpi-card')).toBeNull();
  });

  it('shows an inline error alert on failure', async () => {
    mockFetch({ '/api/kpi/today': () => jsonResponse({ error: 'unavailable', detail: 'x' }, 503) });
    renderWithProviders(<KpiStrip />);
    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent(/unavailable/i);
    expect(screen.queryByTestId('kpi-card')).toBeNull();
  });
});

describe('Sidebar', () => {
  it('takes the Doc Compliance badge from /api/compliance/summary (failed count)', async () => {
    mockFetch({ '/api/compliance/summary': { ...fx.complianceSummary, failed: 37 } });
    renderWithProviders(<Sidebar />);
    const item = screen.getByRole('button', { name: /doc compliance/i });
    await waitFor(() => expect(within(item).getByTestId('nav-badge')).toHaveTextContent('37'));
  });

  it('shows no badge (not a made-up number) when the summary fails', async () => {
    const f = mockFetch({ '/api/compliance/summary': () => jsonResponse({ error: 'x' }, 503) });
    renderWithProviders(<Sidebar />);
    await waitFor(() => expect(f).toHaveBeenCalled());
    expect(screen.queryByTestId('nav-badge')).toBeNull();
  });

  it('renders unbuilt pages disabled with a "Soon" tag', () => {
    mockFetch({ '/api/compliance/summary': never });
    renderWithProviders(<Sidebar />);
    for (const label of ['Dashboards', 'Schedule & Risk', 'Cost & Budget', 'Safety & Quality']) {
      const el = screen.getByRole('button', { name: new RegExp(label.replace('&', '\\&'), 'i') });
      expect(el).toBeDisabled();
      expect(el).toHaveAttribute('aria-disabled', 'true');
      expect(within(el).getByText('Soon')).toBeInTheDocument();
    }
    expect(screen.getByRole('button', { name: /ai co-pilot/i })).not.toBeDisabled();
    expect(screen.getByRole('button', { name: /doc compliance/i })).not.toBeDisabled();
  });
});

describe('TopBar', () => {
  it('avatar initials and auth mode come from /api/whoami', async () => {
    mockFetch({ '/api/whoami': fx.whoamiObo, '/api/schedule/overdue': fx.scheduleOverdue, '/api/compliance/summary': fx.complianceSummary });
    renderWithProviders(<TopBar />);
    await waitFor(() => expect(screen.getByTestId('avatar')).toHaveTextContent('JH'));
    expect(screen.getByTestId('avatar-mode')).toHaveTextContent('OBO');
  });

  it('bell count is derived from API data (late, due today, failed drawings), not seeded', async () => {
    mockFetch({ '/api/whoami': fx.whoamiObo, '/api/schedule/overdue': fx.scheduleOverdue, '/api/compliance/summary': fx.complianceSummary });
    renderWithProviders(<TopBar />);
    await waitFor(() => expect(screen.getByTestId('bell-count')).toHaveTextContent('3'));
  });
});
