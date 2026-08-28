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
// Investigation Comparison types
// ---------------------------------------------------------------------------

export interface BackendMetricComparison {
  label: string;
  base_value: number;
  compare_value: number;
  absolute_change: number;
  percentage_change: number | null;
}

export interface BackendSummaryComparison {
  total_results: BackendMetricComparison;
  spikes_detected: BackendMetricComparison;
  fraud_incidents: BackendMetricComparison;
  organic_incidents: BackendMetricComparison;
  review_required: BackendMetricComparison;
  baseline_windows: BackendMetricComparison;
  spike_rate: BackendMetricComparison;
}

export interface BackendIncidentChange {
  incident_id: string;
  merchant_id: string;
  severity_changed: boolean;
  old_severity: string | null;
  new_severity: string | null;
  classification_changed: boolean;
  old_classification: string | null;
  new_classification: string | null;
  fraud_probability_changed: boolean;
  old_fraud_probability: number | null;
  new_fraud_probability: number | null;
  confidence_changed: boolean;
  old_confidence: number | null;
  new_confidence: number | null;
  anomaly_score_changed: boolean;
  old_anomaly_score: number | null;
  new_anomaly_score: number | null;
  predicted_cause_changed: boolean;
  old_predicted_cause: string | null;
  new_predicted_cause: string | null;
}

export interface BackendIncidentComparison {
  only_in_base: string[];
  only_in_compare: string[];
  in_both: string[];
  changed: BackendIncidentChange[];
  unchanged_count: number;
}

export interface BackendInvestigationMeta {
  investigation_id: string;
  created_at: string;
  status: string;
}

export interface BackendComparisonResponse {
  base: BackendInvestigationMeta;
  compare: BackendInvestigationMeta;
  summary: BackendSummaryComparison;
  incidents: BackendIncidentComparison;
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

export interface InvestigationHistoryFilters {
  investigation_id?: string;
  status?: string;
  merchant_filter?: string;
  created_from?: string;
  created_to?: string;
  sort_by?: string;
  sort_order?: string;
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
  filters?: InvestigationHistoryFilters,
): Promise<ApiResponse<BackendInvestigationListResponse>> {
  const query = new URLSearchParams();
  query.set('limit', String(limit));
  query.set('offset', String(offset));

  if (filters) {
    if (filters.investigation_id) query.set('investigation_id', filters.investigation_id);
    if (filters.status) query.set('status', filters.status);
    if (filters.merchant_filter) query.set('merchant_filter', filters.merchant_filter);
    if (filters.created_from) query.set('created_from', filters.created_from);
    if (filters.created_to) query.set('created_to', filters.created_to);
    if (filters.sort_by) query.set('sort_by', filters.sort_by);
    if (filters.sort_order) query.set('sort_order', filters.sort_order);
  }

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

export async function rerunInvestigation(
  investigationId: string,
): Promise<ApiResponse<BackendInvestigationResponse>> {
  return apiClient.post<BackendInvestigationResponse>(
    `/api/v1/investigations/${encodeURIComponent(investigationId)}/rerun`,
  );
}

// ---------------------------------------------------------------------------
// Configurable Rerun
// ---------------------------------------------------------------------------

export interface RerunConfigOverrides {
  z_threshold?: number | null;
  min_history_days?: number | null;
  merchant_filter?: string | null;
}

export async function rerunInvestigationWithConfig(
  investigationId: string,
  config: RerunConfigOverrides,
): Promise<ApiResponse<BackendInvestigationResponse>> {
  return apiClient.post<BackendInvestigationResponse>(
    `/api/v1/investigations/${encodeURIComponent(investigationId)}/rerun-with-config`,
    config,
  );
}

export async function compareInvestigations(
  baseId: string,
  compareId: string,
): Promise<ApiResponse<BackendComparisonResponse>> {
  const query = new URLSearchParams();
  query.set('base_id', baseId);
  query.set('compare_id', compareId);
  return apiClient.get<BackendComparisonResponse>(
    `/api/v1/investigations/compare?${query.toString()}`,
  );
}

// ---------------------------------------------------------------------------
// Health
// ---------------------------------------------------------------------------

export async function getHealth(): Promise<ApiResponse<BackendHealthResponse>> {
  return apiClient.get<BackendHealthResponse>('/health');
}
