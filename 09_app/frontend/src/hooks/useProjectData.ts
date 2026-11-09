// Right-rail and drawing data. All read through the app's service principal on the backend (see API.md).
import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { apiGet, citationUrl } from '../lib/api';
import type {
  CitationHit,
  ComplianceSummary,
  DailyBrief,
  DrawingDetail,
  FindingScope,
  FindingStatus,
  FindingsPage,
  RiskTop,
  ScheduleOverdue,
} from '../types/api';

const FIVE_MIN = 5 * 60 * 1000;

export function useComplianceSummary() {
  return useQuery({
    queryKey: ['compliance', 'summary'],
    queryFn: ({ signal }) => apiGet<ComplianceSummary>('/api/compliance/summary', signal),
    staleTime: FIVE_MIN,
  });
}

export function useFindings(params: { scope: FindingScope; status: FindingStatus; limit: number; offset: number }) {
  const qs = new URLSearchParams({
    scope: params.scope,
    status: params.status,
    limit: String(params.limit),
    offset: String(params.offset),
  });
  return useQuery({
    queryKey: ['compliance', 'findings', params],
    queryFn: ({ signal }) => apiGet<FindingsPage>(`/api/compliance/findings?${qs.toString()}`, signal),
    staleTime: FIVE_MIN,
    placeholderData: keepPreviousData,
  });
}

export function useRiskTop(limit = 3) {
  return useQuery({
    queryKey: ['risk', 'top', limit],
    queryFn: ({ signal }) => apiGet<RiskTop>(`/api/risk/top?limit=${limit}`, signal),
    staleTime: FIVE_MIN,
  });
}

export function useScheduleOverdue() {
  return useQuery({
    queryKey: ['schedule', 'overdue'],
    queryFn: ({ signal }) => apiGet<ScheduleOverdue>('/api/schedule/overdue', signal),
    staleTime: FIVE_MIN,
  });
}

export function useDailyBrief() {
  return useQuery({
    queryKey: ['brief', 'today'],
    queryFn: ({ signal }) => apiGet<DailyBrief>('/api/brief/today', signal),
    staleTime: FIVE_MIN,
  });
}

export function useDrawing(drawingId: string | undefined) {
  return useQuery({
    queryKey: ['drawing', drawingId],
    queryFn: ({ signal }) => apiGet<DrawingDetail>(`/api/drawings/${encodeURIComponent(drawingId ?? '')}`, signal),
    enabled: !!drawingId,
    staleTime: FIVE_MIN,
  });
}

export function useCitation(label: string | null) {
  return useQuery({
    queryKey: ['citation', label],
    queryFn: ({ signal }) => apiGet<CitationHit>(citationUrl(label ?? ''), signal),
    enabled: !!label,
    staleTime: 60 * 60 * 1000,
  });
}
