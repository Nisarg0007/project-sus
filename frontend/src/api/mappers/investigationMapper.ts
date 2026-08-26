/**
 * Investigation Mapper
 *
 * Converts backend API response types to frontend domain models.
 * This is the ONLY place where snake_case → camelCase transformation
 * happens, and where backend field names map to frontend field names.
 *
 * React components never see raw backend JSON.
 */

import type {
  BackendInvestigationResponse,
  BackendIncidentResponse,
  BackendPipelineSummary,
} from '../investigations';
import type {
  InvestigationSummary,
  Incident as FrontendIncident,
  FullIncident,
  ActivityEvent,
  Anomaly,
  DashboardMetrics,
} from '../../types';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatDate(isoDate: string): string {
  const d = new Date(isoDate + 'T00:00:00');
  return d.toLocaleDateString('en-US', { day: 'numeric', month: 'short', year: 'numeric' }).toUpperCase();
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
// Summary mapping
// ---------------------------------------------------------------------------

export function mapPipelineSummary(backend: BackendPipelineSummary): InvestigationSummary {
  return {
    totalWindows: backend.total_windows,
    spikesDetected: backend.spikes_detected,
    spikeRate: backend.spike_rate,
    fraudIncidents: backend.fraud_incidents,
    organicIncidents: backend.organic_incidents,
    reviewRequired: backend.review_required,
    baselineWindows: backend.baseline_windows,
  };
}

/** Map to existing DashboardMetrics frontend type for backward compatibility. */
export function mapToDashboardMetrics(backend: BackendPipelineSummary): DashboardMetrics {
  return {
    monitoredWindows: backend.total_windows,
    spikesDetected: backend.spikes_detected,
    fraudIncidents: backend.fraud_incidents,
    needsReview: backend.review_required,
  };
}

// ---------------------------------------------------------------------------
// Incident mapping
// ---------------------------------------------------------------------------

export function mapIncident(backend: BackendIncidentResponse): FrontendIncident {
  return {
    id: backend.id,
    merchantId: backend.merchant_id,
    merchantName: backend.merchant_id, // Backend doesn't provide display name yet
    date: backend.date,
    severity: backend.severity,
    status: backend.status,
    predictedCause: backend.classification === 'baseline' ? 'review_required' : backend.classification,
    fraudProbability: backend.fraud_probability,
    confidence: backend.confidence,
    anomalyScore: backend.anomaly_score,
    recommendedAction: backend.recommended_action,
    topSignals: backend.top_signals,
  };
}

export function mapToFullIncident(backend: BackendIncidentResponse): FullIncident {
  return {
    id: backend.id,
    merchantId: backend.merchant_id,
    merchantName: backend.merchant_id,
    date: backend.date,
    dateFormatted: formatDate(backend.date),
    severity: backend.severity,
    status: backend.status,
    predictedCause: backend.classification === 'baseline' ? 'review_required' : backend.classification,
    fraudProbability: backend.fraud_probability,
    confidence: backend.confidence,
    confidenceBand: backend.confidence_band,
    anomalyScore: backend.anomaly_score,
    // Volume context — backend doesn't provide these yet; use anomaly_score as proxy
    transactionCount: 0,
    baselineVolume: 0,
    volumeMultiple: 0,
    zScore: backend.anomaly_score,
    headline: backend.anomaly_summary || 'Anomaly detected',
    summary: backend.anomaly_summary || backend.decision_reason,
    classificationSummary: backend.decision_reason,
    recommendedAction: backend.recommended_action,
    actionType: deriveActionType(backend.severity, backend.classification),
    // Evidence — backend provides summary strings, not structured evidence yet
    behavioralEvidence: [],
    modelContributions: [],
    timeline: [
      { label: 'DETECTED', detail: backend.anomaly_summary || 'Anomaly detected', color: '#38BDF8' },
      {
        label: backend.classification === 'fraud_spike' ? 'FRAUD CLASSIFIED' : backend.classification === 'organic_spike' ? 'ORGANIC CLASSIFIED' : 'REVIEW FLAGGED',
        detail: `${(backend.fraud_probability * 100).toFixed(1)}% fraud probability, ${backend.confidence_band.replace('_', ' ')}`,
        color: backend.classification === 'fraud_spike' ? '#FF5C5C' : backend.classification === 'organic_spike' ? '#34D399' : '#FBBF24',
      },
    ],
    topSignals: backend.top_signals,
  };
}

// ---------------------------------------------------------------------------
// Activity event mapping
// ---------------------------------------------------------------------------

export function mapToActivityEvent(backend: BackendIncidentResponse): ActivityEvent {
  return {
    id: backend.id,
    merchantId: backend.merchant_id,
    merchantName: backend.merchant_id,
    date: backend.date,
    time: '00:00', // Backend doesn't provide time
    status: (backend.classification === 'baseline' ? 'review_required' : backend.classification) as ActivityEvent['status'],
    severity: backend.severity,
    summary: backend.anomaly_summary || backend.decision_reason,
    transactionCount: 0, // Backend doesn't provide raw counts
    baselineVolume: 0,
    volumeMultiple: 0,
    zScore: backend.anomaly_score,
    fraudProbability: backend.fraud_probability,
    confidence: backend.confidence,
    topSignals: backend.top_signals.map((s) => ({ label: s, value: '', changePercent: 0 })),
    evidenceSignals: [],
  };
}

// ---------------------------------------------------------------------------
// Anomaly mapping
// ---------------------------------------------------------------------------

export function mapToAnomaly(backend: BackendIncidentResponse): Anomaly {
  return {
    id: backend.id,
    merchantId: backend.merchant_id,
    merchantName: backend.merchant_id,
    date: backend.date,
    severity: backend.severity,
    status: (backend.classification === 'baseline' ? 'review_required' : backend.classification) as Anomaly['status'],
    fraudProbability: backend.fraud_probability,
    confidence: backend.confidence,
    confidenceBand: backend.confidence_band,
    anomalyScore: backend.anomaly_score,
    anomalySummary: backend.anomaly_summary,
    topSignals: backend.top_signals,
    decisionReason: backend.decision_reason,
  };
}

// ---------------------------------------------------------------------------
// Full investigation mapping
// ---------------------------------------------------------------------------

export function mapInvestigationResponse(backend: BackendInvestigationResponse) {
  return {
    investigationId: backend.investigation_id,
    summary: mapPipelineSummary(backend.summary),
    dashboardMetrics: mapToDashboardMetrics(backend.summary),
    incidents: backend.incidents.map(mapIncident),
    fullIncidents: backend.incidents.map(mapToFullIncident),
    activityEvents: backend.incidents.map(mapToActivityEvent),
    anomalies: backend.incidents.map(mapToAnomaly),
    totalResults: backend.total_results,
    processingNote: backend.processing_note,
  };
}
