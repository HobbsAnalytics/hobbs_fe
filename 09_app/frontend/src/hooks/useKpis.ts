import { useQuery } from '@tanstack/react-query';
import { apiGet } from '../lib/api';
import type { KpiToday } from '../types/api';

export function useKpis() {
  return useQuery({
    queryKey: ['kpi', 'today'],
    queryFn: ({ signal }) => apiGet<KpiToday>('/api/kpi/today', signal),
    staleTime: 5 * 60 * 1000,
  });
}
