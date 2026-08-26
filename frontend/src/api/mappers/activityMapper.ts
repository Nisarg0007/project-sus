/**
 * Activity Mapper
 *
 * Converts backend activity API responses to frontend domain models.
 */

import type { BackendActivityEvent } from '../activity';
import type { ActivityEvent } from '../../types';

export function mapActivityEvent(backend: BackendActivityEvent): ActivityEvent {
  return {
    id: backend.id,
    merchantId: backend.merchantId,
    merchantName: backend.merchantId,
    date: backend.date,
    time: '00:00',
    status: backend.status as ActivityEvent['status'],
    severity: backend.severity as ActivityEvent['severity'],
    summary: backend.summary,
    transactionCount: backend.transactionCount,
    baselineVolume: backend.baselineVolume,
    volumeMultiple: backend.baselineVolume > 0
      ? Math.round((backend.transactionCount / backend.baselineVolume) * 10) / 10
      : 0,
    zScore: backend.zScore,
    fraudProbability: backend.fraudProbability,
    confidence: backend.confidence,
    topSignals: backend.topSignals.map((s) => ({ label: s, value: '', changePercent: 0 })),
    evidenceSignals: [],
  };
}
