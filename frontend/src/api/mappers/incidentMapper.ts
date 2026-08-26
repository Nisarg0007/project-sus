/**
 * Incident Mapper
 *
 * Converts backend incident list API responses to frontend domain models.
 */

import type { BackendIncidentListItem } from '../incidentList';
import type { Incident, FullIncident } from '../../types';

function formatDate(isoDate: string): string {
  const d = new Date(isoDate + 'T00:00:00');
  return d.toLocaleDateString('en-US', { day: 'numeric', month: 'short', year: 'numeric' }).toUpperCase();
}

function deriveActionType(severity: string, classification: string): 'immediate' | 'review' | 'monitor' {
  if (classification === 'fraud_spike' && (severity === 'critical' || severity === 'high')) {
    return 'immediate';
  }
  if (classification === 'review_required' || severity === 'medium') {
    return 'review';
  }
  return 'monitor';
}

export function mapIncidentListItem(backend: BackendIncidentListItem): Incident {
  return {
    id: backend.id,
    merchantId: backend.merchantId,
    merchantName: backend.merchantId,
    date: backend.date,
    severity: backend.severity as Incident['severity'],
    status: backend.status as Incident['status'],
    predictedCause: backend.classification as Incident['predictedCause'],
    fraudProbability: backend.fraudProbability,
    confidence: backend.confidence,
    anomalyScore: backend.anomalyScore,
    recommendedAction: backend.recommendedAction,
    topSignals: backend.topSignals,
  };
}

export function mapToFullIncident(backend: BackendIncidentListItem): FullIncident {
  return {
    id: backend.id,
    merchantId: backend.merchantId,
    merchantName: backend.merchantId,
    date: backend.date,
    dateFormatted: formatDate(backend.date),
    severity: backend.severity as FullIncident['severity'],
    status: backend.status as FullIncident['status'],
    predictedCause: backend.classification as FullIncident['predictedCause'],
    fraudProbability: backend.fraudProbability,
    confidence: backend.confidence,
    confidenceBand: backend.confidenceBand as FullIncident['confidenceBand'],
    anomalyScore: backend.anomalyScore,
    transactionCount: 0,
    baselineVolume: 0,
    volumeMultiple: 0,
    zScore: backend.anomalyScore,
    headline: backend.anomalySummary || 'Anomaly detected',
    summary: backend.anomalySummary || backend.decisionReason,
    classificationSummary: backend.decisionReason,
    recommendedAction: backend.recommendedAction,
    actionType: deriveActionType(backend.severity, backend.classification),
    behavioralEvidence: [],
    modelContributions: [],
    timeline: [
      { label: 'DETECTED', detail: backend.anomalySummary || 'Anomaly detected', color: '#38BDF8' },
      {
        label: backend.classification === 'fraud_spike' ? 'FRAUD CLASSIFIED'
          : backend.classification === 'organic_spike' ? 'ORGANIC CLASSIFIED'
          : 'REVIEW FLAGGED',
        detail: `${(backend.fraudProbability * 100).toFixed(1)}% fraud probability`,
        color: backend.classification === 'fraud_spike' ? '#FF5C5C'
          : backend.classification === 'organic_spike' ? '#34D399'
          : '#FBBF24',
      },
    ],
    topSignals: backend.topSignals,
  };
}
