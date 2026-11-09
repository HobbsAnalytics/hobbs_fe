import React, { useEffect } from 'react';
import PageTransition from '../layout/PageTransition';
import KpiStrip from '../dashboards/KpiStrip';
import RiskForecastCard from '../dashboards/RiskForecastCard';
import LateMilestonesCard from '../dashboards/LateMilestonesCard';
import { ChatProvider, useChatSession, type ChatSession } from './ChatContext';
import ChatPanel from './ChatPanel';
import SuggestedActions from './SuggestedActions';
import ComplianceSummaryTile from './ComplianceSummaryTile';
import ProjectKnowledge from './ProjectKnowledge';
import { useKpis } from '../../hooks/useKpis';
import { useAppStore } from '../../stores/appStore';
import { formatShortDate } from '../../lib/format';

const LiveIndicator: React.FC = () => {
  const { data, isError } = useKpis();
  return (
    <div className="flex items-center gap-1.5 text-xs text-slate-400 whitespace-nowrap">
      <span className={isError ? 'w-2 h-2 rounded-full bg-red-400' : 'live-pulse'} />
      {isError ? 'Snapshot unavailable' : data ? `Live · snapshot ${formatShortDate(data.snapshot_date)} · Lakebase` : 'Connecting…'}
    </div>
  );
};

const CopilotLayout: React.FC<{ chat: ChatSession }> = ({ chat }) => {
  const pendingPrompt = useAppStore((s) => s.pendingPrompt);
  const setPendingPrompt = useAppStore((s) => s.setPendingPrompt);

  // A question typed in the top-bar search lands here.
  useEffect(() => {
    if (pendingPrompt && !chat.isStreaming) {
      setPendingPrompt(null);
      void chat.send(pendingPrompt);
    }
  }, [pendingPrompt, chat, setPendingPrompt]);

  return (
    <PageTransition>
      <div className="p-6 space-y-5" data-testid="page-copilot">
        <div className="flex justify-between items-start">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Project Co-Pilot</h1>
            <p className="text-sm text-slate-500 mt-1">Blue Ridge LNG Terminal — Phase 2 · Ask anything about drawings, schedule, cost and safety</p>
          </div>
          <LiveIndicator />
        </div>

        <KpiStrip />

        <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-5 lg:h-[calc(100vh-64px-48px-60px-20px-84px)] min-h-[560px]">
          <ChatPanel chat={chat} />
          <aside className="flex flex-col gap-4 lg:overflow-y-auto min-h-0 pr-0.5" aria-label="Project context">
            <SuggestedActions onAsk={(p) => void chat.send(p)} disabled={chat.isStreaming} />
            <ComplianceSummaryTile />
            <RiskForecastCard />
            <LateMilestonesCard />
            <ProjectKnowledge />
          </aside>
        </div>
      </div>
    </PageTransition>
  );
};

const WithSession: React.FC = () => {
  const chat = useChatSession();
  return chat ? <CopilotLayout chat={chat} /> : null;
};

/** `/`: chat home. Uses the app-level chat session when present (App.tsx), else its own (tests, embeds). */
const CopilotPage: React.FC = () => {
  const chat = useChatSession();
  if (chat) return <CopilotLayout chat={chat} />;
  return (
    <ChatProvider>
      <WithSession />
    </ChatProvider>
  );
};

export default CopilotPage;
