/**
 * Incident list API client.
 */

import { apiClient, type ApiResponse } from './client';

export interface BackendIncidentListItem {
  id: string;
  merchantId: string;
  date: string;
  severity: string;
  status: string;
  classification: string;
  fraudProbability: number;
  confidence: number;
  confidenceBand: string;
  anomalyScore: number;
  decisionReason: string;
  anomalySummary: string;
  topSignals: string[];
  recommendedAction: string;
}

export interface BackendIncidentListResponse {
  incidents: BackendIncidentListItem[];
  total: number;
}

export async function getIncidents(params?: {
  merchantId?: string;
  severity?: string;
  classification?: string;
  status?: string;
  limit?: number;
}): Promise<ApiResponse<BackendIncidentListResponse>> {
  const query = new URLSearchParams();
  if (params?.merchantId) query.set('merchant_id', params.merchantId);
  if (params?.severity) query.set('severity', params.severity);
  if (params?.classification) query.set('classification', params.classification);
  if (params?.status) query.set('status', params.status);
  if (params?.limit) query.set('limit', String(params.limit));
  const qs = query.toString();
  return apiClient.get<BackendIncidentListResponse>(
    `/api/v1/incidents${qs ? '?' + qs : ''}`,
  );
}
