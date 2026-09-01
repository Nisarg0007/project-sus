/**
 * Incident Service (Frontend)
 *
 * Handles fetching incidents from the pipeline and persisted incidents
 * from the database, with mapping to frontend domain models.
 */

import {
  getIncidents,
  getIncidentDetail,
  updateIncident,
  getPersistedIncidents,
  type IncidentUpdatePayload,
  type BackendIncidentDetail,
  type IncidentFilters,
} from '../api/incidentList';
import { mapIncidentListItem, mapToFullIncident } from '../api/mappers/incidentMapper';
import type { Incident, FullIncident } from '../types';
import type { ServiceResult } from './investigationService';

// ---------------------------------------------------------------------------
// Pipeline-derived incidents (existing)
// ---------------------------------------------------------------------------

export async function fetchIncidents(params?: {
  merchantId?: string;
  severity?: string;
  classification?: string;
  status?: string;
  limit?: number;
}): Promise<ServiceResult<Incident[]>> {
  const response = await getIncidents(params);
  if (!response.ok || !response.data) {
    return { data: null, error: response.error || { status: 0, message: 'Failed to fetch incidents' } };
  }
  return {
    data: response.data.incidents.map(mapIncidentListItem),
    error: null,
  };
}

export async function fetchFullIncidents(params?: {
  merchantId?: string;
  severity?: string;
  classification?: string;
  limit?: number;
}): Promise<ServiceResult<FullIncident[]>> {
  const response = await getIncidents(params);
  if (!response.ok || !response.data) {
    return { data: null, error: response.error || { status: 0, message: 'Failed to fetch incidents' } };
  }
  return {
    data: response.data.incidents.map(mapToFullIncident),
    error: null,
  };
}

// ---------------------------------------------------------------------------
// Persisted incidents (database-backed)
// ---------------------------------------------------------------------------

export interface IncidentDetail {
  incidentId: string;
  merchantId: string;
  date: string;
  severity: string;
  classification: string;
  predictedCause: string | null;
  fraudProbability: number;
  confidence: number;
  confidenceBand: string;
  anomalyScore: number;
  decisionReason: string;
  anomalySummary: string;
  topSignals: string[];
  recommendedAction: string;
  workflowStatus: string;
  assignedAnalyst: string | null;
  analystNotes: string | null;
  resolution: string | null;
  createdAt: string;
  updatedAt: string;
  statusHistory: Array<{
    oldStatus: string;
    newStatus: string;
    changedBy: string | null;
    note: string | null;
    createdAt: string;
  }>;
}

export interface IncidentListItem {
  incidentId: string;
  merchantId: string;
  date: string;
  severity: string;
  classification: string;
  workflowStatus: string;
  fraudProbability: number;
  confidence: number;
  confidenceBand: string;
  assignedAnalyst: string | null;
  resolution: string | null;
  createdAt: string;
  updatedAt: string;
}

function mapIncidentDetail(b: BackendIncidentDetail): IncidentDetail {
  return {
    incidentId: b.incident_id,
    merchantId: b.merchant_id,
    date: b.date,
    severity: b.severity,
    classification: b.classification,
    predictedCause: b.predicted_cause,
    fraudProbability: b.fraud_probability,
    confidence: b.confidence,
    confidenceBand: b.confidence_band,
    anomalyScore: b.anomaly_score,
    decisionReason: b.decision_reason,
    anomalySummary: b.anomaly_summary,
    topSignals: b.top_signals ?? [],
    recommendedAction: b.recommended_action,
    workflowStatus: b.workflow_status,
    assignedAnalyst: b.assigned_analyst,
    analystNotes: b.analyst_notes,
    resolution: b.resolution,
    createdAt: b.created_at,
    updatedAt: b.updated_at,
    statusHistory: (b.status_history ?? []).map(h => ({
      oldStatus: h.old_status,
      newStatus: h.new_status,
      changedBy: h.changed_by,
      note: h.note,
      createdAt: h.created_at,
    })),
  };
}

export async function fetchIncidentDetail(
  incidentId: string,
): Promise<ServiceResult<IncidentDetail>> {
  const response = await getIncidentDetail(incidentId);
  if (!response.ok || !response.data) {
    return { data: null, error: response.error || { status: 0, message: `Incident '${incidentId}' not found` } };
  }
  return { data: mapIncidentDetail(response.data), error: null };
}

export async function saveIncidentUpdate(
  incidentId: string,
  payload: IncidentUpdatePayload,
): Promise<ServiceResult<IncidentDetail>> {
  const response = await updateIncident(incidentId, payload);
  if (!response.ok || !response.data) {
    return { data: null, error: response.error || { status: 0, message: 'Failed to update incident' } };
  }
  return { data: mapIncidentDetail(response.data), error: null };
}

export interface PersistedIncidentListResult {
  incidents: IncidentListItem[];
  total: number;
  limit: number;
  offset: number;
}

export async function fetchPersistedIncidents(
  filters?: IncidentFilters,
): Promise<ServiceResult<PersistedIncidentListResult>> {
  const response = await getPersistedIncidents(filters);
  if (!response.ok || !response.data) {
    return { data: null, error: response.error || { status: 0, message: 'Failed to fetch persisted incidents' } };
  }
  const incidents: IncidentListItem[] = response.data.incidents.map(inc => ({
    incidentId: inc.incident_id,
    merchantId: inc.merchant_id,
    date: inc.date,
    severity: inc.severity,
    classification: inc.classification,
    workflowStatus: inc.workflow_status,
    fraudProbability: inc.fraud_probability,
    confidence: inc.confidence,
    confidenceBand: inc.confidence_band,
    assignedAnalyst: inc.assigned_analyst,
    resolution: inc.resolution,
    createdAt: inc.created_at,
    updatedAt: inc.updated_at,
  }));
  return {
    data: { incidents, total: response.data.total, limit: response.data.limit, offset: response.data.offset },
    error: null,
  };
}
