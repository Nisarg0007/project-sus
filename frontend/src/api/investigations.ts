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

// ---------------------------------------------------------------------------
// Investigation History types (GET /investigations, GET /investigations/{id})
// ---------------------------------------------------------------------------

export interface BackendInvestigationListItem {
  investigation_id: string;
  status: string;
  created_at: string;
  total_results: number;
  spikes_detected: number;
  fraud_incidents: number;
  organic_incidents: number;
  review_required: number;
  baseline_windows: number;
  spike_rate: number;
  processing_note: string;
}

export interface BackendInvestigationListResponse {
  total: number;
  limit: number;
  offset: number;
  items: BackendInvestigationListItem[];
}

export interface BackendPersistedIncident {
  incident_id: string;
  merchant_id: string;
  date: string;
  severity: string;
  status: string;
  classification: string;
  predicted_cause: string | null;
  fraud_probability: number;
  confidence: number;
  confidence_band: string;
  anomaly_score: number;
  decision_reason: string;
  anomaly_summary: string;
  top_signals: string[];
  recommended_action: string;
  created_at: string;
}

export interface BackendInvestigationDetailSummary {
  total_results: number;
  spikes_detected: number;
  fraud_incidents: number;
  organic_incidents: number;
  review_required: number;
  baseline_windows: number;
  spike_rate: number;
  processing_note: string;
}

export interface BackendInvestigationDetail {
  investigation_id: string;
  status: string;
  created_at: string;
  transactions_path: string;
  window_labels_path: string;
  model_path: string | null;
  z_threshold: number;
  min_history_days: number;
  merchant_filter: string | null;
  summary: BackendInvestigationDetailSummary;
  incidents: BackendPersistedIncident[];
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

// ---------------------------------------------------------------------------
// Investigation History API Methods
// ---------------------------------------------------------------------------

export async function getInvestigationHistory(
  limit: number = 20,
  offset: number = 0,
): Promise<ApiResponse<BackendInvestigationListResponse>> {
  const query = new URLSearchParams();
  query.set('limit', String(limit));
  query.set('offset', String(offset));
  return apiClient.get<BackendInvestigationListResponse>(
    `/api/v1/investigations?${query.toString()}`,
  );
}

export async function getInvestigationById(
  investigationId: string,
): Promise<ApiResponse<BackendInvestigationDetail>> {
  return apiClient.get<BackendInvestigationDetail>(
    `/api/v1/investigations/${encodeURIComponent(investigationId)}`,
  );
}

// ---------------------------------------------------------------------------
// Health
// ---------------------------------------------------------------------------

export async function getHealth(): Promise<ApiResponse<BackendHealthResponse>> {
  return apiClient.get<BackendHealthResponse>('/health');
}
