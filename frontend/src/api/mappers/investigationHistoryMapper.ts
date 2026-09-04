/**
 * Investigation History Mapper
 *
 * Converts backend investigation history API responses to frontend domain models.
 * Handles snake_case → camelCase transformation and JSON deserialization.
 *
 * Follows the same pattern as investigationMapper.ts.
 */

import type {
  BackendInvestigationListItem,
  BackendInvestigationListResponse,
  BackendPersistedIncident,
  BackendInvestigationDetail,
} from '../investigations';
import type {
  InvestigationSummary,
  FullIncident,
} from '../../types';

// ---------------------------------------------------------------------------
// Frontend domain types for investigation history
// ---------------------------------------------------------------------------

export interface InvestigationHistoryItem {
  investigationId: string;
  status: string;
  createdAt: string;
  createdAtFormatted: string;
  totalResults: number;
  spikesDetected: number;
  fraudIncidents: number;
  organicIncidents: number;
  reviewRequired: number;
  baselineWindows: number;
  spikeRate: number;
  processingNote: string;
  datasetFilename: string | null;
  dataSourceType: string | null;
}

export interface InvestigationHistoryList {
  total: number;
  limit: number;
  offset: number;
  items: InvestigationHistoryItem[];
}

export interface InvestigationHistoryDetail {
  investigationId: string;
  status: string;
  createdAt: string;
  createdAtFormatted: string;
  datasetId: string | null;
  datasetFilename: string | null;
  dataSourceType: string | null;
  transactionsPath: string;
  windowLabelsPath: string;
  modelPath: string | null;
  zThreshold: number;
  minHistoryDays: number;
  merchantFilter: string | null;
  summary: InvestigationSummary;
  incidents: FullIncident[];
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatDateShort(isoDate: string): string {
  try {
    const d = new Date(isoDate);
    return d.toLocaleDateString('en-US', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return isoDate;
  }
}

function deriveActionType(
  severity: string,
  classification: string,
): 'immediate' | 'review' | 'monitor' {
  if (classification === 'fraud_spike' && (severity === 'critical' || severity === 'high')) {
    return 'immediate';
  }
  if (classification === 'review_required' || severity === 'medium') {
    return 'review';
  }
  return 'monitor';
}

// ---------------------------------------------------------------------------
// List item mapping
// ---------------------------------------------------------------------------

export function mapInvestigationListItem(
  backend: BackendInvestigationListItem,
): InvestigationHistoryItem {
  return {
    investigationId: backend.investigation_id,
    status: backend.status,
    createdAt: backend.created_at,
    createdAtFormatted: formatDateShort(backend.created_at),
    totalResults: backend.total_results,
    spikesDetected: backend.spikes_detected,
    fraudIncidents: backend.fraud_incidents,
    organicIncidents: backend.organic_incidents,
    reviewRequired: backend.review_required,
    baselineWindows: backend.baseline_windows,
    spikeRate: backend.spike_rate,
    processingNote: backend.processing_note,
    datasetFilename: backend.dataset_filename ?? null,
    dataSourceType: backend.data_source_type ?? null,
  };
}

export function mapInvestigationList(
  backend: BackendInvestigationListResponse,
): InvestigationHistoryList {
  return {
    total: backend.total,
    limit: backend.limit,
    offset: backend.offset,
    items: backend.items.map(mapInvestigationListItem),
  };
}

// ---------------------------------------------------------------------------
// Persisted incident mapping
// ---------------------------------------------------------------------------

function mapPersistedIncident(backend: BackendPersistedIncident): FullIncident {
  const classification = backend.classification || 'review_required';
  const severity = backend.severity || 'low';

  return {
    id: backend.incident_id,
    merchantId: backend.merchant_id,
    merchantName: backend.merchant_id,
    date: backend.date,
    dateFormatted: formatDateShort(backend.date),
    severity: severity as FullIncident['severity'],
    status: (backend.status || 'open') as FullIncident['status'],
    predictedCause: classification as FullIncident['predictedCause'],
    fraudProbability: backend.fraud_probability,
    confidence: backend.confidence,
    confidenceBand: backend.confidence_band as FullIncident['confidenceBand'],
    anomalyScore: backend.anomaly_score,
    transactionCount: 0,
    baselineVolume: 0,
    volumeMultiple: 0,
    zScore: backend.anomaly_score,
    headline: backend.anomaly_summary || 'Anomaly detected',
    summary: backend.anomaly_summary || backend.decision_reason,
    classificationSummary: backend.decision_reason,
    recommendedAction: backend.recommended_action,
    actionType: deriveActionType(severity, classification),
    behavioralEvidence: [],
    modelContributions: [],
    timeline: [
      { label: 'DETECTED', detail: backend.anomaly_summary || 'Anomaly detected', color: '#38BDF8' },
      {
        label: classification === 'fraud_spike'
          ? 'FRAUD CLASSIFIED'
          : classification === 'organic_spike'
            ? 'ORGANIC CLASSIFIED'
            : 'REVIEW FLAGGED',
        detail: `${(backend.fraud_probability * 100).toFixed(1)}% fraud probability, ${backend.confidence_band.replace('_', ' ')}`,
        color: classification === 'fraud_spike' ? '#FF5C5C' : classification === 'organic_spike' ? '#34D399' : '#FBBF24',
      },
    ],
    topSignals: backend.top_signals,
  };
}

// ---------------------------------------------------------------------------
// Detail mapping
// ---------------------------------------------------------------------------

export function mapInvestigationDetail(
  backend: BackendInvestigationDetail,
): InvestigationHistoryDetail {
  return {
    investigationId: backend.investigation_id,
    status: backend.status,
    createdAt: backend.created_at,
    createdAtFormatted: formatDateShort(backend.created_at),
    datasetId: backend.dataset_id ?? null,
    datasetFilename: backend.dataset_filename ?? null,
    dataSourceType: backend.data_source_type ?? null,
    transactionsPath: backend.transactions_path,
    windowLabelsPath: backend.window_labels_path,
    modelPath: backend.model_path,
    zThreshold: backend.z_threshold,
    minHistoryDays: backend.min_history_days,
    merchantFilter: backend.merchant_filter,
    summary: {
      totalWindows: backend.summary.total_results,
      spikesDetected: backend.summary.spikes_detected,
      spikeRate: backend.summary.spike_rate,
      fraudIncidents: backend.summary.fraud_incidents,
      organicIncidents: backend.summary.organic_incidents,
      reviewRequired: backend.summary.review_required,
      baselineWindows: backend.summary.baseline_windows,
    },
    incidents: backend.incidents.map(mapPersistedIncident),
  };
}
