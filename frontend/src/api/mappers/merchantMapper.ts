/**
 * Merchant Mapper
 *
 * Converts backend merchant API responses to frontend domain models.
 */

import type {
  BackendMerchantListItem,
  BackendMerchantProfileResponse,
  BackendMerchantIncident,
} from '../merchants';
import type {
  Merchant,
  MerchantDirectoryItem,
  MerchantProfile,
  MerchantAnomalyEntry,
} from '../../types';

// ---------------------------------------------------------------------------
// Directory mapping
// ---------------------------------------------------------------------------

export function mapMerchantListItem(backend: BackendMerchantListItem): Merchant {
  return {
    id: backend.id,
    name: backend.name,
    dailyVolume: backend.dailyVolume,
    riskLevel: backend.riskLevel,
  };
}

export function mapMerchantDirectoryItem(backend: BackendMerchantListItem): MerchantDirectoryItem {
  const statusColor =
    backend.fraudCount > 0 ? '#FF5C5C'
    : backend.reviewCount > 0 ? '#FBBF24'
    : backend.organicCount > 0 ? '#34D399'
    : '#8A94A6';

  const statusLabel =
    backend.fraudCount > 0 ? `${backend.fraudCount} FRAUD INCIDENT${backend.fraudCount > 1 ? 'S' : ''}`
    : backend.reviewCount > 0 ? `${backend.reviewCount} REVIEW CASE${backend.reviewCount > 1 ? 'S' : ''}`
    : backend.organicCount > 0 ? `${backend.organicCount} ORGANIC SPIKE${backend.organicCount > 1 ? 'S' : ''}`
    : 'NO ANOMALIES';

  const riskColor =
    backend.riskLevel === 'high' ? '#FF5C5C'
    : backend.riskLevel === 'medium' ? '#FBBF24'
    : '#34D399';

  const riskLabel =
    backend.fraudCount >= 2 ? 'HIGH ATTENTION'
    : backend.fraudCount >= 1 ? 'HIGH ATTENTION'
    : backend.reviewCount >= 1 ? 'WATCH'
    : backend.organicCount > 0 ? 'STABLE'
    : 'NORMAL';

  return {
    id: backend.id,
    name: backend.name,
    dailyVolume: backend.dailyVolume,
    riskLevel: backend.riskLevel,
    statusLabel,
    statusColor,
    incidentCount: backend.fraudCount + backend.reviewCount,
    riskLabel,
    riskColor,
  };
}

// ---------------------------------------------------------------------------
// Profile mapping
// ---------------------------------------------------------------------------

function mapIncidentToAnomalyEntry(inc: BackendMerchantIncident): MerchantAnomalyEntry {
  return {
    id: inc.id,
    date: inc.date,
    dateFormatted: formatDate(inc.date),
    status: inc.classification as MerchantAnomalyEntry['status'],
    severity: inc.severity as MerchantAnomalyEntry['severity'],
    headline: inc.anomalySummary || 'Anomaly detected',
    summary: inc.anomalySummary || inc.decisionReason,
    fraudProbability: inc.fraudProbability,
    confidence: inc.confidence,
    confidenceBand: inc.confidenceBand as MerchantAnomalyEntry['confidenceBand'],
    evidenceSignals: [],
  };
}

export function mapMerchantProfile(backend: BackendMerchantProfileResponse): MerchantProfile {
  return {
    merchantId: backend.id,
    riskPosture: backend.riskPosture,
    riskLabel: backend.riskLabel,
    summary: backend.summary,
    totalWindows: backend.totalWindows,
    spikeCount: backend.spikesDetected,
    fraudCount: backend.fraudCount,
    organicCount: backend.organicCount,
    reviewCount: backend.reviewCount,
    behavioralDimensions: [], // Not available from backend yet
    anomalyHistory: backend.incidents.map(mapIncidentToAnomalyEntry),
  };
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatDate(isoDate: string): string {
  const d = new Date(isoDate + 'T00:00:00');
  return d.toLocaleDateString('en-US', { day: 'numeric', month: 'short', year: 'numeric' }).toUpperCase();
}
