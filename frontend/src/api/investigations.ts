/**
 * Investigation API client.
 *
 * Typed methods for calling the SUS backend investigation endpoints.
 * Returns raw backend response types — mapping to frontend models
 * happens in the mapper layer.
 */

import { apiClient, type ApiResponse } from './client';

// ---------------------------------------------------------------------------
// Backend response types (matching the Python API schemas exactly)
// ---------------------------------------------------------------------------

export interface BackendPipelineSummary {
  total_windows: number;
  spikes_detected: number;
  spike_rate: number;
  fraud_incidents: number;
  organic_incidents: number;
  review_required: number;
  baseline_windows: number;
}

export interface BackendIncidentResponse {
  id: string;
  merchant_id: string;
  date: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  status: 'open' | 'investigating' | 'resolved' | 'dismissed';
  classification: 'baseline' | 'organic_spike' | 'fraud_spike' | 'review_required';
  fraud_probability: number;
  confidence: number;
  confidence_band: 'high_confidence' | 'ambiguous' | 'low_confidence';
  anomaly_score: number;
  decision_reason: string;
  anomaly_summary: string;
  top_signals: string[];
  recommended_action: string;
}

export interface BackendInvestigationResponse {
  investigation_id: string;
  summary: BackendPipelineSummary;
  incidents: BackendIncidentResponse[];
  total_results: number;
  processing_note: string;
}

export interface BackendHealthResponse {
  status: string;
  version: string;
  pipeline_loaded: boolean;
}

// ---------------------------------------------------------------------------
// Request types
// ---------------------------------------------------------------------------

export interface InvestigationRequest {
  transactions_path?: string;
  window_labels_path?: string;
  model_path?: string | null;
  z_threshold?: number;
  merchant_filter?: string | null;
}

// ---------------------------------------------------------------------------
// API Methods
// ---------------------------------------------------------------------------

export async function runInvestigation(
  request: InvestigationRequest = {},
): Promise<ApiResponse<BackendInvestigationResponse>> {
  return apiClient.post<BackendInvestigationResponse>(
    '/api/v1/investigations/run',
    request,
  );
}

export async function getHealth(): Promise<ApiResponse<BackendHealthResponse>> {
  return apiClient.get<BackendHealthResponse>('/health');
}
