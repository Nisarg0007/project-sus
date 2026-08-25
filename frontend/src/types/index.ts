// Core domain types for SUS

export interface Merchant {
  id: string;
  name: string;
  dailyVolume: number;
  riskLevel: 'low' | 'medium' | 'high';
}

export interface TransactionWindow {
  merchantId: string;
  date: string;
  transactionCount: number;
  volumeZscore: number;
  isSpike: boolean;
  hasSufficientHistory: boolean;
}

export interface BehavioralEvidence {
  feature: string;
  label: string;
  normalValue: number;
  currentValue: number;
  unit: string;
  changePercent: number;
  changeDirection: 'increased' | 'decreased';
  signalStrength: 'strong' | 'moderate' | 'weak';
  signalType: 'fraud' | 'organic' | 'neutral';
  description: string;
}

export interface ModelContribution {
  feature: string;
  label: string;
  contribution: number;
  direction: 'fraud' | 'organic';
}

export interface InvestigationAnomaly {
  id: string;
  anomalyNumber: string;
  merchantId: string;
  merchantName: string;
  date: string;
  dateFormatted: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  status: 'baseline' | 'organic_spike' | 'fraud_spike' | 'review_required';
  
  // Volume context
  transactionCount: number;
  baselineVolume: number;
  volumeMultiple: number;
  zScore: number;
  
  // Classification
  fraudProbability: number;
  confidence: number;
  confidenceBand: 'high_confidence' | 'ambiguous' | 'low_confidence';
  
  // Evidence
  behavioralEvidence: BehavioralEvidence[];
  modelContributions: ModelContribution[];
  
  // Summary
  anomalySummary: string;
  classificationSummary: string;
  recommendedAction: string;
  incidentId?: string;
}

export interface Anomaly {
  id: string;
  merchantId: string;
  merchantName: string;
  date: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  status: 'baseline' | 'organic_spike' | 'fraud_spike' | 'review_required';
  fraudProbability: number;
  confidence: number;
  confidenceBand: 'high_confidence' | 'ambiguous' | 'low_confidence';
  anomalyScore: number;
  anomalySummary: string;
  topSignals: string[];
  decisionReason: string;
}

export interface Incident {
  id: string;
  merchantId: string;
  merchantName: string;
  date: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  status: 'open' | 'investigating' | 'resolved' | 'dismissed';
  predictedCause: 'organic_spike' | 'fraud_spike' | 'review_required';
  fraudProbability: number;
  confidence: number;
  anomalyScore: number;
  recommendedAction: string;
  topSignals: string[];
}

export interface Classification {
  label: string;
  value: number;
  color: string;
}

export interface ActivityDataPoint {
  date: string;
  baseline: number;
  actual: number;
  merchant?: string;
  type?: 'normal' | 'organic' | 'fraud' | 'review';
  isSelected?: boolean;
  anomalyId?: string;
}

export interface DashboardMetrics {
  monitoredWindows: number;
  spikesDetected: number;
  fraudIncidents: number;
  needsReview: number;
}

export type NavigationItem = {
  id: string;
  label: string;
  path: string;
};

// Activity feed event type
export interface ActivityEvent {
  id: string;
  merchantId: string;
  merchantName: string;
  date: string;
  time: string;
  status: 'fraud_spike' | 'organic_spike' | 'review_required';
  severity: 'critical' | 'high' | 'medium' | 'low';
  summary: string;
  transactionCount: number;
  baselineVolume: number;
  volumeMultiple: number;
  zScore: number;
  fraudProbability: number;
  confidence: number;
  topSignals: Array<{ label: string; value: string; changePercent: number }>;
  evidenceSignals: BehavioralEvidence[];
  incidentId?: string;
}

// Activity filter type
export type ActivityFilter = 'all' | 'fraud' | 'organic' | 'review';

// Activity time range
export type TimeRange = '7d' | '14d' | '30d' | '45d';

// Incident timeline step
export interface IncidentTimelineStep {
  label: string;
  detail: string;
  color: string;
}

// Full incident with investigation data
export interface FullIncident {
  id: string;
  merchantId: string;
  merchantName: string;
  date: string;
  dateFormatted: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  status: 'open' | 'investigating' | 'resolved' | 'dismissed';
  predictedCause: 'organic_spike' | 'fraud_spike' | 'review_required';
  fraudProbability: number;
  confidence: number;
  confidenceBand: 'high_confidence' | 'ambiguous' | 'low_confidence';
  anomalyScore: number;
  transactionCount: number;
  baselineVolume: number;
  volumeMultiple: number;
  zScore: number;
  headline: string;
  summary: string;
  classificationSummary: string;
  recommendedAction: string;
  actionType: 'immediate' | 'review' | 'monitor';
  behavioralEvidence: BehavioralEvidence[];
  modelContributions: ModelContribution[];
  timeline: IncidentTimelineStep[];
  topSignals: string[];
}

// Incident queue filter
export type IncidentSeverityFilter = 'all' | 'critical' | 'high' | 'review';
