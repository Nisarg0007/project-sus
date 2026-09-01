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

// ---------------------------------------------------------------------------
// Persisted incident detail and workflow management
// ---------------------------------------------------------------------------

export interface BackendStatusHistoryEntry {
  old_status: string;
  new_status: string;
  changed_by: string | null;
  note: string | null;
  created_at: string;
}

export interface BackendIncidentDetail {
  incident_id: string;
  merchant_id: string;
  date: string;
  severity: string;
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
  workflow_status: string;
  assigned_analyst: string | null;
  analyst_notes: string | null;
  resolution: string | null;
  created_at: string;
  updated_at: string;
  status_history: BackendStatusHistoryEntry[];
}

export interface BackendPersistedIncidentListItem {
  incident_id: string;
  merchant_id: string;
  date: string;
  severity: string;
  classification: string;
  workflow_status: string;
  fraud_probability: number;
  confidence: number;
  confidence_band: string;
  assigned_analyst: string | null;
  resolution: string | null;
  created_at: string;
  updated_at: string;
}

export interface BackendPersistedIncidentListResponse {
  incidents: BackendPersistedIncidentListItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface IncidentUpdatePayload {
  workflow_status?: string | null;
  assigned_analyst?: string | null;
  analyst_notes?: string | null;
  resolution?: string | null;
}

export async function getIncidentDetail(
  incidentId: string,
): Promise<ApiResponse<BackendIncidentDetail>> {
  return apiClient.get<BackendIncidentDetail>(
    `/api/v1/incidents/${encodeURIComponent(incidentId)}`,
  );
}

export async function updateIncident(
  incidentId: string,
  payload: IncidentUpdatePayload,
): Promise<ApiResponse<BackendIncidentDetail>> {
  const url = `/api/v1/incidents/${encodeURIComponent(incidentId)}`;
  const response = await fetch(url, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    let detail: unknown;
    try {
      detail = await response.json();
    } catch {
      detail = await response.text();
    }
    return {
      data: null as unknown as BackendIncidentDetail,
      ok: false,
      error: {
        status: response.status,
        message: `HTTP ${response.status}: ${response.statusText}`,
        detail,
      },
    };
  }
  const data: BackendIncidentDetail = await response.json();
  return { data, ok: true };
}

export async function getIncidentStatusHistory(
  incidentId: string,
): Promise<ApiResponse<BackendStatusHistoryEntry[]>> {
  return apiClient.get<BackendStatusHistoryEntry[]>(
    `/api/v1/incidents/${encodeURIComponent(incidentId)}/history`,
  );
}

export interface IncidentFilters {
  search?: string;
  merchantId?: string;
  severity?: string;
  classification?: string;
  workflowStatus?: string;
  assignedAnalyst?: string;
  investigationId?: string;
  createdFrom?: string;
  createdTo?: string;
  sortBy?: string;
  sortOrder?: string;
  limit?: number;
  offset?: number;
}

export async function getPersistedIncidents(
  filters?: IncidentFilters,
): Promise<ApiResponse<BackendPersistedIncidentListResponse>> {
  const query = new URLSearchParams();
  if (filters?.search) query.set('search', filters.search);
  if (filters?.merchantId) query.set('merchant_id', filters.merchantId);
  if (filters?.severity) query.set('severity', filters.severity);
  if (filters?.classification) query.set('classification', filters.classification);
  if (filters?.workflowStatus) query.set('workflow_status', filters.workflowStatus);
  if (filters?.assignedAnalyst) query.set('assigned_analyst', filters.assignedAnalyst);
  if (filters?.investigationId) query.set('investigation_id', filters.investigationId);
  if (filters?.createdFrom) query.set('created_from', filters.createdFrom);
  if (filters?.createdTo) query.set('created_to', filters.createdTo);
  if (filters?.sortBy) query.set('sort_by', filters.sortBy);
  if (filters?.sortOrder) query.set('sort_order', filters.sortOrder);
  if (filters?.limit) query.set('limit', String(filters.limit));
  if (filters?.offset !== undefined) query.set('offset', String(filters.offset));
  const qs = query.toString();
  return apiClient.get<BackendPersistedIncidentListResponse>(
    `/api/v1/incidents/persisted${qs ? '?' + qs : ''}`,
  );
}
