import React from 'react';
import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import CompliancePage from '../src/components/compliance/CompliancePage';
import DrawingPage from '../src/components/drawings/DrawingPage';
import * as fx from '../src/fixtures/data';
import { calledUrls, mockFetch, renderWithProviders } from './utils';

vi.mock('react-pdf', () => ({
  pdfjs: { GlobalWorkerOptions: {} },
  Document: ({ file, children }: { file: string; children: React.ReactNode }) => (
    <div data-testid="pdf-document" data-file={file}>
      {children}
    </div>
  ),
  Page: ({ pageNumber }: { pageNumber: number }) => <div data-testid="pdf-page" data-page={pageNumber} />,
}));

afterEach(() => vi.unstubAllGlobals());

const findingsTotal85 = (u: URL) => {
  const limit = Number(u.searchParams.get('limit'));
  const offset = Number(u.searchParams.get('offset'));
  const items = Array.from({ length: Math.min(limit, 85 - offset) }, (_, i) => ({
    ...fx.findings[i % fx.findings.length],
    finding_id: `F-${offset + i}`,
  }));
  return new Response(
    JSON.stringify({ items, total: 85, limit, offset, scope: u.searchParams.get('scope'), status: u.searchParams.get('status') }),
    { status: 200, headers: { 'Content-Type': 'application/json' } },
  );
};

describe('CompliancePage / FindingsTable', () => {
  it('paginates through the API (limit/offset/total), and scope/status reset to offset 0', async () => {
    const f = mockFetch({
      '/api/compliance/summary': fx.complianceSummary,
      '/api/compliance/findings': findingsTotal85,
      '/api/citations/*': fx.citations['ASME B31.3 §341'],
    });
    renderWithProviders(<CompliancePage />, { route: '/compliance' });
    expect(await screen.findByText(/1–25 of 85/)).toBeInTheDocument();
    const findingsCalls = () => calledUrls(f).filter((u) => u.pathname === '/api/compliance/findings');
    expect(findingsCalls()[0].search).toBe('?scope=week&status=FAIL&limit=25&offset=0');

    await userEvent.click(screen.getByRole('button', { name: /next page/i }));
    expect(await screen.findByText(/26–50 of 85/)).toBeInTheDocument();
    expect(findingsCalls().at(-1)!.searchParams.get('offset')).toBe('25');

    await userEvent.click(screen.getByRole('button', { name: /^all$/i }));
    await waitFor(() => {
      const last = findingsCalls().at(-1)!;
      expect(last.searchParams.get('scope')).toBe('all');
      expect(last.searchParams.get('offset')).toBe('0');
    });

    await userEvent.click(screen.getByRole('button', { name: /^review$/i }));
    await waitFor(() => expect(findingsCalls().at(-1)!.searchParams.get('status')).toBe('REVIEW'));
  });

  it('table columns: mono drawing id, discipline/type, citation, severity pill, reason and Open PDF link', async () => {
    mockFetch({
      '/api/compliance/summary': fx.complianceSummary,
      '/api/compliance/findings': (u: URL) =>
        new Response(JSON.stringify(fx.findingsPage('week', 'FAIL', Number(u.searchParams.get('limit')), 0)), { status: 200 }),
    });
    renderWithProviders(<CompliancePage />, { route: '/compliance' });
    const cell = await screen.findAllByText('BRL-PIP-ISO-0664');
    expect(cell[0].className).toMatch(/font-mono/);
    const row = cell[0].closest('tr')!;
    expect(within(row).getByText('Piping')).toBeInTheDocument();
    expect(within(row).getByText('Isometric')).toBeInTheDocument();
    expect(within(row).getByText('ASME B31.3 §341')).toBeInTheDocument();
    expect(within(row).getByText('medium')).toBeInTheDocument();
    expect(within(row).getByRole('link', { name: /open pdf/i })).toHaveAttribute(
      'href',
      '/drawings/BRL-PIP-ISO-0664?page=0&finding=BRL-PIP-ISO-0664-C01',
    );
    expect(screen.getByText('51')).toBeInTheDocument(); // failed tile from summary
  });

  it('row click opens the FindingDrawer with evidence and an honest bbox_source label', async () => {
    mockFetch({
      '/api/compliance/summary': fx.complianceSummary,
      '/api/compliance/findings': (u: URL) =>
        new Response(JSON.stringify(fx.findingsPage('week', 'FAIL', Number(u.searchParams.get('limit')), 0)), { status: 200 }),
      '/api/citations/*': fx.citations['ASME B31.3 §341'],
    });
    renderWithProviders(<CompliancePage />, { route: '/compliance' });
    await userEvent.click((await screen.findAllByText('BRL-STR-GA-0534'))[0]);
    const drawer = await screen.findByRole('dialog');
    expect(drawer).toHaveTextContent('EXIT 3 MAIN HALL 48 36 36');
    expect(drawer).toHaveTextContent('Highlight: whole page');
    await userEvent.click(within(drawer).getByRole('button', { name: /close/i }));
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull());
    await userEvent.click((await screen.findAllByText('BRL-PIP-ISO-0664'))[0]);
    expect(await screen.findByRole('dialog')).toHaveTextContent('Highlight: synthetic ground truth');
    await userEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: /close/i }));
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull());
    await userEvent.click((await screen.findAllByText('BRL-INS-PID-0580'))[0]);
    expect(await screen.findByRole('dialog')).toHaveTextContent('Highlight: parsed element (approximate)');
  });
});

describe('CompliancePage REVIEW card', () => {
  it('labels REVIEW as judge output unusable, not low-confidence findings', async () => {
    mockFetch({ '/api/compliance/summary': { ...fx.complianceSummary, review: 3 }, '/api/compliance/findings': findingsTotal85, '/api/citations/*': fx.citations['ASME B31.3 §341'] });
    renderWithProviders(<CompliancePage />, { route: '/compliance' });
    expect(await screen.findByText('Needs review (judge output unusable)')).toBeInTheDocument();
    expect(screen.queryByText(/Low-confidence/)).not.toBeInTheDocument();
  });
});

describe('DrawingPage', () => {
  it('builds /api/drawings/:id/pdf from the route param and renders ?page (0-based) as pdf page 1', async () => {
    const f = mockFetch({ '/api/drawings/BRL-PIP-ISO-0664': fx.drawingDetail });
    renderWithProviders(<DrawingPage />, { route: '/drawings/BRL-PIP-ISO-0664?page=0&finding=BRL-PIP-ISO-0664-C01', path: '/drawings/:id' });
    const doc = await screen.findByTestId('pdf-document');
    expect(doc).toHaveAttribute('data-file', '/api/drawings/BRL-PIP-ISO-0664/pdf');
    expect(screen.getByTestId('pdf-page')).toHaveAttribute('data-page', '1');
    expect(calledUrls(f).map((u) => u.pathname)).toContain('/api/drawings/BRL-PIP-ISO-0664');
    expect(await screen.findByText(/Weld W3 is a fillet weld/)).toBeInTheDocument();
  });

  it('counts only FAIL/REVIEW rows: a PASS-only drawing shows "Findings (0)" and "No violations found"', async () => {
    const pass = { ...fx.findings[0], finding_id: 'BRL-PIP-ISO-0001-PASS', drawing_id: 'BRL-PIP-ISO-0001', status: 'PASS' as const };
    mockFetch({ '/api/drawings/BRL-PIP-ISO-0001': { ...fx.drawingDetail, drawing_id: 'BRL-PIP-ISO-0001', fail_count: 0, findings: [pass] } });
    renderWithProviders(<DrawingPage />, { route: '/drawings/BRL-PIP-ISO-0001', path: '/drawings/:id' });
    expect(await screen.findByText('Findings (0)')).toBeInTheDocument();
    expect(screen.getByText('No violations found')).toBeInTheDocument();
  });

  it('a 404 from the drawing API shows an inline error, not a blank page', async () => {
    mockFetch({});
    renderWithProviders(<DrawingPage />, { route: '/drawings/BRL-PIP-ISO-9999', path: '/drawings/:id' });
    expect(await screen.findByRole('alert')).toBeInTheDocument();
  });
});
