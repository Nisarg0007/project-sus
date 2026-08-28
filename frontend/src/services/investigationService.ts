/**
 * Investigation Service (Frontend)
 *
 * High-level service that the UI layer calls to run investigations.
 * Handles: API call → receive response → map to frontend models → return.
 *
 * Components call this service. They never call fetch() or mappers directly.
 */

import type { InvestigationRequest, InvestigationHistoryFilters } from '../api/investigations';
import {
  runInvestigation as apiRunInvestigation,
  getInvestigationHistory as apiGetInvestigationHistory,
  getInvestigationById as apiGetInvestigationById,
} from '../api/investigations';
import { mapInvestigationResponse } from '../api/mappers/investigationMapper';
import {
  mapInvestigationList,
  mapInvestigationDetail,
  type InvestigationHistoryList,
  type InvestigationHistoryDetail,
} from '../api/mappers/investigationHistoryMapper';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface InvestigationResult {
  investigationId: string;
  summary: {
    totalWindows: number;
    spikesDetected: number;
    spikeRate: number;
    fraudIncidents: number;
    organicIncidents: number;
    reviewRequired: number;
    baselineWindows: number;
  };
  dashboardMetrics: {
    monitoredWindows: number;
    spikesDetected: number;
    fraudIncidents: number;
    needsReview: number;
  };
  incidents: ReturnType<typeof import('../api/mappers/investigationMapper').mapIncident>[];
  fullIncidents: ReturnType<typeof import('../api/mappers/investigationMapper').mapToFullIncident>[];
  activityEvents: ReturnType<typeof import('../api/mappers/investigationMapper').mapToActivityEvent>[];
  anomalies: ReturnType<typeof import('../api/mappers/investigationMapper').mapToAnomaly>[];
  totalResults: number;
  processingNote: string;
}

export interface ServiceError {
  status: number;
  message: string;
  detail?: unknown;
}

export interface ServiceResult<T> {
  data: T | null;
  error: ServiceError | null;
}

// ---------------------------------------------------------------------------
// Service
// ---------------------------------------------------------------------------

export async function runInvestigation(
  request: InvestigationRequest = {},
): Promise<ServiceResult<InvestigationResult>> {
  const response = await apiRunInvestigation(request);

  if (!response.ok || !response.data) {
    return {
      data: null,
      error: response.error || {
        status: 0,
        message: 'Unknown error occurred',
      },
    };
  }

  try {
    const mapped = mapInvestigationResponse(response.data);
    return { data: mapped as InvestigationResult, error: null };
  } catch (err) {
    return {
      data: null,
      error: {
        status: 0,
        message: `Failed to process investigation response: ${err instanceof Error ? err.message : 'Unknown error'}`,
      },
    };
  }
}

// ---------------------------------------------------------------------------
// Investigation History
// ---------------------------------------------------------------------------

export async function getInvestigationHistory(
  limit: number = 20,
  offset: number = 0,
  filters?: InvestigationHistoryFilters,
): Promise<ServiceResult<InvestigationHistoryList>> {
  const response = await apiGetInvestigationHistory(limit, offset, filters);

  if (!response.ok || !response.data) {
    return {
      data: null,
      error: response.error || {
        status: 0,
        message: 'Failed to fetch investigation history',
      },
    };
  }

  try {
    const mapped = mapInvestigationList(response.data);
    return { data: mapped, error: null };
  } catch (err) {
    return {
      data: null,
      error: {
        status: 0,
        message: `Failed to process investigation history: ${err instanceof Error ? err.message : 'Unknown error'}`,
      },
    };
  }
}

export async function getInvestigationById(
  investigationId: string,
): Promise<ServiceResult<InvestigationHistoryDetail>> {
  const response = await apiGetInvestigationById(investigationId);

  if (!response.ok || !response.data) {
    return {
      data: null,
      error: response.error || {
        status: 0,
        message: `Failed to fetch investigation ${investigationId}`,
      },
    };
  }

  try {
    const mapped = mapInvestigationDetail(response.data);
    return { data: mapped, error: null };
  } catch (err) {
    return {
      data: null,
      error: {
        status: 0,
        message: `Failed to process investigation detail: ${err instanceof Error ? err.message : 'Unknown error'}`,
      },
    };
  }
}
