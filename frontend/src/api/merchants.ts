/**
 * Merchant API client.
 *
 * Typed methods for calling the SUS backend merchant endpoints.
 */

import { apiClient, type ApiResponse } from './client';

// ---------------------------------------------------------------------------
// Backend response types
// ---------------------------------------------------------------------------

export interface BackendMerchantListItem {
  id: string;
  name: string;
  dailyVolume: number;
  riskLevel: 'low' | 'medium' | 'high';
  totalWindows: number;
  spikesDetected: number;
  fraudCount: number;
  organicCount: number;
  reviewCount: number;
}

export interface BackendMerchantListResponse {
  merchants: BackendMerchantListItem[];
  total: number;
}

export interface BackendMerchantIncident {
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

export interface BackendMerchantProfileResponse {
  id: string;
  name: string;
  dailyVolume: number;
  riskLevel: 'low' | 'medium' | 'high';
  riskPosture: 'normal' | 'watch' | 'high_attention';
  riskLabel: string;
  summary: string;
  totalWindows: number;
  spikesDetected: number;
  fraudCount: number;
  organicCount: number;
  reviewCount: number;
  incidents: BackendMerchantIncident[];
}

// ---------------------------------------------------------------------------
// API Methods
// ---------------------------------------------------------------------------

export async function getMerchants(
  params?: { search?: string; limit?: number },
): Promise<ApiResponse<BackendMerchantListResponse>> {
  const query = new URLSearchParams();
  if (params?.search) query.set('search', params.search);
  if (params?.limit) query.set('limit', String(params.limit));
  const qs = query.toString();
  return apiClient.get<BackendMerchantListResponse>(
    `/api/v1/merchants${qs ? '?' + qs : ''}`,
  );
}

export async function getMerchantProfile(
  merchantId: string,
): Promise<ApiResponse<BackendMerchantProfileResponse>> {
  return apiClient.get<BackendMerchantProfileResponse>(
    `/api/v1/merchants/${encodeURIComponent(merchantId)}`,
  );
}
