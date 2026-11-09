import React from 'react';
import { useDailyBrief } from '../../hooks/useProjectData';
import Markdown from '../shared/Markdown';
import LoadingSkeleton from '../shared/LoadingSkeleton';
import ErrorAlert from '../shared/ErrorAlert';
import VerifyFooter from '../copilot/VerifyFooter';
import { formatShortDate } from '../../lib/format';

/** First message in the chat log: today's brief from GET /api/brief/today, rendered as Markdown (no raw HTML). */
const DailyBriefCard: React.FC = () => {
  const { data, isLoading, isError, error, refetch } = useDailyBrief();

  return (
    <div className="self-start max-w-[85%]" data-testid="daily-brief">
      <div className="flex items-center gap-2 mb-1.5 text-[11px] text-slate-500">
        <span className="msg-meta-tag">Daily Brief</span>
        {data && <span>{formatShortDate(data.brief_date)}</span>}
      </div>
      <div className="msg-bubble">
        {isLoading ? (
          <LoadingSkeleton type="text" />
        ) : isError ? (
          <ErrorAlert compact error={error} onRetry={() => refetch()} title="Today's brief couldn't be loaded" />
        ) : !data?.brief_md ? (
          <p className="text-slate-500">No brief has been generated for today yet. Ask the Co-Pilot a question to get started.</p>
        ) : (
          <>
            <Markdown>{data.brief_md}</Markdown>
            <VerifyFooter note={`Generated from project data · prompt ${data.prompt_version} · validation ${data.validation_status}`} />
          </>
        )}
      </div>
    </div>
  );
};

export default DailyBriefCard;
