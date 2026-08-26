/**
 * Activity API client.
 */

import { apiClient, type ApiResponse } from './client';

export interface BackendActivityEvent {
  id: string;
  merchantId: string;
  date: string;
  status: string;
  severity: string;
  transactionCount: number;
  baselineVolume: number;
  zScore: number;
  fraudProbability: number;
  confidence: number;
  confidenceBand: string;
  summary: string;
  topSignals: string[];
}

export interface BackendActivityListResponse {
  events: BackendActivityEvent[];
  total: number;
}

export async function getActivityEvents(params?: {
  merchantId?: string;
  dateFrom?: string;
  dateTo?: string;
  status?: string;
  limit?: number;
}): Promise<ApiResponse<BackendActivityListResponse>> {
  const query = new URLSearchParams();
  if (params?.merchantId) query.set('merchant_id', params.merchantId);
  if (params?.dateFrom) query.set('date_from', params.dateFrom);
  if (params?.dateTo) query.set('date_to', params.dateTo);
  if (params?.status) query.set('status', params.status);
  if (params?.limit) query.set('limit', String(params.limit));
  const qs = query.toString();
  return apiClient.get<BackendActivityListResponse>(
    `/api/v1/activity/events${qs ? '?' + qs : ''}`,
  );
}
