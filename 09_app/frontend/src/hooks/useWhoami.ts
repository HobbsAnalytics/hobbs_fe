import { useQuery } from '@tanstack/react-query';
import { apiGet } from '../lib/api';
import type { Whoami } from '../types/api';

export function useWhoami() {
  return useQuery({
    queryKey: ['whoami'],
    queryFn: ({ signal }) => apiGet<Whoami>('/api/whoami', signal),
    staleTime: 10 * 60 * 1000,
  });
}
