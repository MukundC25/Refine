import { useEffect, useState } from 'react';
import { CandidateDetailResponse } from './types';
import { fetchCandidateDetail } from './utils';

// Loads /api/ranking/candidate/{id} whenever *candidateId* changes.
// Cancels the in-flight update if the id changes before the response arrives,
// so a fast click-through in the ranked table cannot render stale data.
export function useCandidateDetail(candidateId: string | null) {
  const [data, setData] = useState<CandidateDetailResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!candidateId) {
      setData(null);
      setError(null);
      setIsLoading(false);
      return;
    }

    let cancelled = false;
    setIsLoading(true);
    setError(null);

    fetchCandidateDetail(candidateId)
      .then(result => {
        if (!cancelled) setData(result);
      })
      .catch(e => {
        if (!cancelled) setError(e.message ?? 'Failed to load candidate');
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [candidateId]);

  return { data, isLoading, error };
}
