import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import AssistantMessage from '../src/components/copilot/AssistantMessage';
import IdentityChip from '../src/components/copilot/IdentityChip';
import CopilotPage from '../src/components/copilot/CopilotPage';
import RiskForecastCard from '../src/components/dashboards/RiskForecastCard';
import { applyChatEvent, newAssistantMessage } from '../src/hooks/useChat';
import { createSseParser } from '../src/lib/sse';
import * as fx from '../src/fixtures/data';
import type { ChatEvent } from '../src/types/api';
import { mockFetch, renderWithProviders, sseResponse } from './utils';

afterEach(() => vi.unstubAllGlobals());

function messageFromFrames(frames: string[]) {
  let m = newAssistantMessage();
  const p = createSseParser((e) => {
    m = applyChatEvent(m, e as ChatEvent);
  });
  frames.forEach((f) => p.push(f));
  return m;
}

const allRoutes = {
  '/api/whoami': fx.whoamiObo,
  '/api/kpi/today': fx.kpiToday,
  '/api/compliance/summary': fx.complianceSummary,
  '/api/risk/top': fx.riskTop,
  '/api/schedule/overdue': fx.scheduleOverdue,
  '/api/brief/today': fx.dailyBrief,
  '/api/citations/*': fx.citations['OSHA 1910.147'],
};

describe('AssistantMessage', () => {
  it('renders answer, SQL card, truncated result table, grouped source chips and the verify footer', async () => {
    const msg = messageFromFrames(fx.chatFramesFailedDrawings);
    mockFetch(allRoutes);
    renderWithProviders(<AssistantMessage message={msg} authMode="OBO" />);

    expect(screen.getByText(/drawings failed review this week/)).toBeInTheDocument();
    expect(screen.getByText('51').tagName).toBe('STRONG'); // Markdown rendered

    const sqlToggle = screen.getByRole('button', { name: /generated sql/i });
    expect(screen.queryByTestId('sql-body')).toBeNull();
    await userEvent.click(sqlToggle);
    expect(screen.getByTestId('sql-body')).toHaveTextContent('SELECT drawing_id, citation, severity');

    const table = screen.getByRole('table');
    expect(within(table).getAllByRole('row')).toHaveLength(1 + 4);
    expect(screen.getByText(/showing first 4 of 85 rows/i)).toBeInTheDocument();

    const chips = screen.getAllByTestId('drawing-chip');
    expect(chips).toHaveLength(3); // grouped by drawing_id
    expect(chips[0]).toHaveAttribute('href', '/drawings/BRL-INS-PID-0580?page=0&finding=BRL-INS-PID-0580-C01');
    expect(chips[0]).toHaveTextContent('2 findings');
    expect(chips[2]).toHaveAttribute('href', '/drawings/BRL-ELE-GA-0023');

    const citeChip = screen.getByRole('button', { name: 'OSHA 1910.147' });
    await userEvent.click(citeChip);
    expect(await screen.findByText('Control of hazardous energy: lockout and tagout')).toBeInTheDocument();

    expect(screen.getByText(/AI-generated — verify before action/)).toBeInTheDocument();
    expect(screen.getByTestId('exec-note')).toHaveTextContent('Genie · as you (OBO) · via MCP');
  });

  it('renders the graceful "I\'m not sure…" answer as a normal answer, with no SQL/table/sources', () => {
    const msg = messageFromFrames(fx.chatFramesEmpty);
    mockFetch(allRoutes);
    renderWithProviders(<AssistantMessage message={msg} authMode="OBO" />);
    expect(screen.getByText(/I'm not sure which milestones you mean/)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /generated sql/i })).toBeNull();
    expect(screen.queryByRole('table')).toBeNull();
    expect(screen.queryByTestId('drawing-chip')).toBeNull();
    expect(screen.queryByRole('alert')).toBeNull();
    expect(screen.getByTestId('exec-note')).toHaveTextContent('Genie · as you (OBO)');
    expect(screen.getByTestId('exec-note')).not.toHaveTextContent('via');
  });

  it('renders the error event message inline', () => {
    const msg = messageFromFrames(fx.chatFramesError);
    mockFetch(allRoutes);
    renderWithProviders(<AssistantMessage message={msg} authMode="OBO" />);
    expect(screen.getByRole('alert')).toHaveTextContent('Genie did not answer within 110 seconds');
  });

  it('drops any slip_probability column from a result table (defense in depth)', () => {
    let msg = newAssistantMessage();
    msg = applyChatEvent(msg, { type: 'result', columns: ['milestone_id', 'Max_Slip_Probability', 'risk_band'], rows: [['MS-335', 0.91, 'High']], row_count: 1, truncated: false });
    msg = applyChatEvent(msg, { type: 'status', value: 'done' });
    mockFetch(allRoutes);
    renderWithProviders(<AssistantMessage message={msg} authMode="OBO" />);
    const table = screen.getByRole('table');
    expect(table).not.toHaveTextContent(/probab/i);
    expect(table).not.toHaveTextContent('0.91');
    expect(table).toHaveTextContent('MS-335');
  });
});

describe('IdentityChip', () => {
  it('OBO: shows the email and says Genie runs as you (on-behalf-of)', async () => {
    mockFetch({ '/api/whoami': fx.whoamiObo });
    renderWithProviders(<IdentityChip />);
    const chip = await screen.findByTestId('identity-chip');
    await waitFor(() => expect(chip).toHaveTextContent('joseph.hobbs@databricks.com'));
    expect(chip).toHaveTextContent('Genie runs as you (on-behalf-of)');
    expect(chip).not.toHaveTextContent(/as the app/i);
  });

  it('SP: says it runs as the app, never claims on-behalf-of', async () => {
    mockFetch({ '/api/whoami': fx.whoamiSp });
    renderWithProviders(<IdentityChip />);
    const chip = await screen.findByTestId('identity-chip');
    await waitFor(() => expect(chip).toHaveTextContent(/as the app/i));
    expect(chip).not.toHaveTextContent(/on-behalf-of/i);
  });
});

describe('risk is shown by band only', () => {
  it('RiskForecastCard shows bands and counts, with no percentage or probability', async () => {
    mockFetch({ '/api/risk/top': { ...fx.riskTop, items: fx.riskTop.items.map((i) => ({ ...i, slip_probability: 0.87 })) } });
    const { container } = renderWithProviders(<RiskForecastCard />);
    await screen.findByText('MS-335');
    expect(screen.getAllByText('High').length).toBeGreaterThanOrEqual(3);
    expect(container).toHaveTextContent('26 High');
    expect(container.textContent).not.toMatch(/%|probab|0\.87|87/i);
  });

  it('nowhere in the rendered Co-Pilot page: "%" appears only in the Budget KPI, "probability" never', async () => {
    mockFetch({ ...allRoutes, '/api/chat': () => sseResponse(fx.chatFramesFailedDrawings) });
    const { container } = renderWithProviders(<CopilotPage />);
    await screen.findByText('MS-335');
    await screen.findByText(/Where would you like to focus first/);
    await screen.findAllByTestId('kpi-card');
    const input = screen.getByRole('textbox', { name: /ask the co-pilot/i });
    fireEvent.change(input, { target: { value: 'What are the top High-risk milestones in the next 90 days?' } });
    fireEvent.keyDown(input, { key: 'Enter' });
    await screen.findAllByTestId('drawing-chip');

    expect(container.textContent).not.toMatch(/probab/i);
    const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT);
    const offenders: string[] = [];
    for (let n = walker.nextNode(); n; n = walker.nextNode()) {
      if (n.textContent?.includes('%') && !n.parentElement?.closest('[data-kpi="budget"]')) offenders.push(n.textContent);
    }
    expect(offenders).toEqual([]);
  });
});

describe('CopilotPage', () => {
  it('seeds the log with the Daily Brief, sends on Enter, keeps Shift+Enter as newline, disables input while streaming', async () => {
    let release: () => void = () => {};
    const gate = new Promise<void>((r) => (release = r));
    const fetchFn = mockFetch({
      ...allRoutes,
      '/api/chat': async () => {
        await gate;
        return sseResponse(fx.chatFramesFailedDrawings);
      },
    });
    renderWithProviders(<CopilotPage />);
    expect(await screen.findByText('Daily Brief')).toBeInTheDocument();
    expect(await screen.findByText(/Where would you like to focus first/)).toBeInTheDocument();

    const input = screen.getByRole('textbox', { name: /ask the co-pilot/i });
    fireEvent.change(input, { target: { value: 'line one' } });
    fireEvent.keyDown(input, { key: 'Enter', shiftKey: true });
    expect(fetchFn.mock.calls.filter(([u]) => String(u).includes('/api/chat'))).toHaveLength(0);

    fireEvent.keyDown(input, { key: 'Enter' });
    await waitFor(() => expect(input).toBeDisabled());
    expect(screen.getByTestId('typing-indicator')).toBeInTheDocument();
    release();
    await screen.findAllByTestId('drawing-chip');
    await waitFor(() => expect(input).not.toBeDisabled());
  });

  it('a Suggested Action sends its pre-filled prompt', async () => {
    const fetchFn = mockFetch({ ...allRoutes, '/api/chat': () => sseResponse(fx.chatFramesEmpty) });
    renderWithProviders(<CopilotPage />);
    await userEvent.click(screen.getByRole('button', { name: /which milestones are late or due today\?/i }));
    await waitFor(() => {
      const chat = fetchFn.mock.calls.find(([u]) => String(u).includes('/api/chat'));
      expect(chat && JSON.parse(String(chat[1]?.body)).message).toBe('Which milestones are late or due today?');
    });
  });
});
