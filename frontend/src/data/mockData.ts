import { 
  Merchant, 
  Anomaly, 
  Incident, 
  ActivityDataPoint, 
  DashboardMetrics,
  InvestigationAnomaly,
  ActivityEvent,
  FullIncident,
  MerchantProfile,
  MerchantDirectoryItem
} from '../types';

// Merchants
export const merchants: Merchant[] = [
  { id: 'merchant_001', name: 'Merchant 001', dailyVolume: 650, riskLevel: 'medium' },
  { id: 'merchant_002', name: 'Merchant 002', dailyVolume: 420, riskLevel: 'low' },
  { id: 'merchant_003', name: 'Merchant 003', dailyVolume: 850, riskLevel: 'high' },
  { id: 'merchant_004', name: 'Merchant 004', dailyVolume: 300, riskLevel: 'low' },
  { id: 'merchant_005', name: 'Merchant 005', dailyVolume: 580, riskLevel: 'medium' },
  { id: 'merchant_006', name: 'Merchant 006', dailyVolume: 480, riskLevel: 'low' },
  { id: 'merchant_007', name: 'Merchant 007', dailyVolume: 720, riskLevel: 'medium' },
  { id: 'merchant_008', name: 'Merchant 008', dailyVolume: 520, riskLevel: 'medium' },
];

// Dashboard Metrics
export const dashboardMetrics: DashboardMetrics = {
  monitoredWindows: 360,
  spikesDetected: 73,
  fraudIncidents: 31,
  needsReview: 3,
};

// Investigation anomalies with detailed evidence
export const investigationAnomalies: InvestigationAnomaly[] = [
  {
    id: 'anomaly_024',
    anomalyNumber: '024',
    merchantId: 'merchant_001',
    merchantName: 'merchant_001',
    date: '2025-07-24',
    dateFormatted: '24 JUL 2025',
    severity: 'critical',
    status: 'fraud_spike',
    transactionCount: 1563,
    baselineVolume: 650,
    volumeMultiple: 2.4,
    zScore: 1.44,
    fraudProbability: 0.961,
    confidence: 0.961,
    confidenceBand: 'high_confidence',
    behavioralEvidence: [
      {
        feature: 'failed_payment_rate',
        label: 'Failed Payment Rate',
        normalValue: 3.8,
        currentValue: 9.8,
        unit: '%',
        changePercent: 157,
        changeDirection: 'increased',
        signalStrength: 'strong',
        signalType: 'fraud',
        description: 'Payment failures are significantly elevated, suggesting card testing or stolen credentials.',
      },
      {
        feature: 'ip_diversity_ratio',
        label: 'IP Diversity',
        normalValue: 68,
        currentValue: 48,
        unit: '%',
        changePercent: -29,
        changeDirection: 'decreased',
        signalStrength: 'strong',
        signalType: 'fraud',
        description: 'Fewer unique IP addresses are responsible for a larger share of transactions.',
      },
      {
        feature: 'device_diversity_ratio',
        label: 'Device Diversity',
        normalValue: 73,
        currentValue: 56,
        unit: '%',
        changePercent: -23,
        changeDirection: 'decreased',
        signalStrength: 'moderate',
        signalType: 'fraud',
        description: 'Transactions are concentrated across fewer devices than normal.',
      },
      {
        feature: 'new_customer_share',
        label: 'New Customer Activity',
        normalValue: 56,
        currentValue: 40,
        unit: '%',
        changePercent: -29,
        changeDirection: 'decreased',
        signalStrength: 'moderate',
        signalType: 'fraud',
        description: 'Unusually low new customer activity during a volume spike suggests existing compromised accounts.',
      },
    ],
    modelContributions: [
      { feature: 'failed_payment_rate', label: 'Failed Payments', contribution: 0.82, direction: 'fraud' },
      { feature: 'ip_diversity_ratio', label: 'IP Concentration', contribution: 0.65, direction: 'fraud' },
      { feature: 'retry_rate', label: 'Retry Behavior', contribution: 0.54, direction: 'fraud' },
      { feature: 'device_diversity_ratio', label: 'Device Concentration', contribution: 0.48, direction: 'fraud' },
      { feature: 'new_customer_share', label: 'New Customer Activity', contribution: 0.32, direction: 'organic' },
      { feature: 'sku_diversity_ratio', label: 'SKU Diversity', contribution: 0.18, direction: 'organic' },
    ],
    anomalySummary: 'Transaction volume surged to 2.4× the historical baseline with simultaneous degradation in payment success and network diversity.',
    classificationSummary: 'The combination of elevated payment failures and concentrated device/IP patterns is strongly indicative of coordinated fraud activity.',
    recommendedAction: 'Review affected transactions and investigate abnormal payment and network behavior.',
    incidentId: 'INC-merchant_001-20250724',
  },
  {
    id: 'anomaly_018',
    anomalyNumber: '018',
    merchantId: 'merchant_003',
    merchantName: 'merchant_003',
    date: '2025-07-18',
    dateFormatted: '18 JUL 2025',
    severity: 'low',
    status: 'organic_spike',
    transactionCount: 1870,
    baselineVolume: 850,
    volumeMultiple: 2.2,
    zScore: 1.65,
    fraudProbability: 0.12,
    confidence: 0.88,
    confidenceBand: 'high_confidence',
    behavioralEvidence: [
      {
        feature: 'transaction_count',
        label: 'Transaction Volume',
        normalValue: 850,
        currentValue: 1870,
        unit: 'txns',
        changePercent: 120,
        changeDirection: 'increased',
        signalStrength: 'moderate',
        signalType: 'organic',
        description: 'Volume increased substantially but customer behavior patterns remain normal.',
      },
      {
        feature: 'new_customer_share',
        label: 'New Customer Activity',
        normalValue: 42,
        currentValue: 61,
        unit: '%',
        changePercent: 45,
        changeDirection: 'increased',
        signalStrength: 'moderate',
        signalType: 'organic',
        description: 'Elevated new customer acquisition suggests promotional or viral activity.',
      },
      {
        feature: 'sku_diversity_ratio',
        label: 'SKU Diversity',
        normalValue: 12,
        currentValue: 14,
        unit: 'items',
        changePercent: 17,
        changeDirection: 'increased',
        signalStrength: 'weak',
        signalType: 'organic',
        description: 'Product diversity increased naturally with the volume surge.',
      },
      {
        feature: 'failed_payment_rate',
        label: 'Failed Payment Rate',
        normalValue: 4.2,
        currentValue: 4.8,
        unit: '%',
        changePercent: 14,
        changeDirection: 'increased',
        signalStrength: 'weak',
        signalType: 'neutral',
        description: 'Payment success rates remain within normal range.',
      },
    ],
    modelContributions: [
      { feature: 'new_customer_share', label: 'New Customer Activity', contribution: 0.72, direction: 'organic' },
      { feature: 'sku_diversity_ratio', label: 'SKU Diversity', contribution: 0.45, direction: 'organic' },
      { feature: 'customer_diversity_ratio', label: 'Customer Diversity', contribution: 0.38, direction: 'organic' },
      { feature: 'failed_payment_rate', label: 'Failed Payments', contribution: 0.15, direction: 'fraud' },
      { feature: 'ip_diversity_ratio', label: 'IP Diversity', contribution: 0.12, direction: 'organic' },
    ],
    anomalySummary: 'Transaction volume doubled with healthy new customer acquisition and normal payment patterns.',
    classificationSummary: 'The behavioral profile matches organic demand growth — likely a successful promotion or viral moment.',
    recommendedAction: 'Monitor merchant activity. No intervention required.',
  },
  {
    id: 'anomaly_015',
    anomalyNumber: '015',
    merchantId: 'merchant_002',
    merchantName: 'merchant_002',
    date: '2025-07-15',
    dateFormatted: '15 JUL 2025',
    severity: 'medium',
    status: 'review_required',
    transactionCount: 630,
    baselineVolume: 420,
    volumeMultiple: 1.5,
    zScore: 0.89,
    fraudProbability: 0.58,
    confidence: 0.65,
    confidenceBand: 'ambiguous',
    behavioralEvidence: [
      {
        feature: 'transaction_count',
        label: 'Transaction Volume',
        normalValue: 420,
        currentValue: 630,
        unit: 'txns',
        changePercent: 50,
        changeDirection: 'increased',
        signalStrength: 'weak',
        signalType: 'neutral',
        description: 'Moderate volume increase that could indicate either organic growth or early-stage fraud.',
      },
      {
        feature: 'retry_rate',
        label: 'Retry Behavior',
        normalValue: 1.2,
        currentValue: 1.6,
        unit: '%',
        changePercent: 33,
        changeDirection: 'increased',
        signalStrength: 'moderate',
        signalType: 'fraud',
        description: 'Slightly elevated retry attempts may indicate payment issues.',
      },
      {
        feature: 'ip_diversity_ratio',
        label: 'IP Diversity',
        normalValue: 71,
        currentValue: 65,
        unit: '%',
        changePercent: -8,
        changeDirection: 'decreased',
        signalStrength: 'weak',
        signalType: 'fraud',
        description: 'Minor decrease in IP diversity, not yet at concerning levels.',
      },
    ],
    modelContributions: [
      { feature: 'retry_rate', label: 'Retry Behavior', contribution: 0.42, direction: 'fraud' },
      { feature: 'ip_diversity_ratio', label: 'IP Diversity', contribution: 0.28, direction: 'fraud' },
      { feature: 'new_customer_share', label: 'New Customer Activity', contribution: 0.22, direction: 'organic' },
      { feature: 'sku_diversity_ratio', label: 'SKU Diversity', contribution: 0.15, direction: 'organic' },
    ],
    anomalySummary: 'Moderate volume increase with ambiguous behavioral signals requiring human review.',
    classificationSummary: 'The model cannot confidently distinguish between organic growth and early fraud patterns. Manual investigation recommended.',
    recommendedAction: 'Human review recommended: Anomaly detected but cause classification is ambiguous.',
  },
];

// Generate deterministic activity data for the chart
export const generateActivityData = (): ActivityDataPoint[] => {
  const data: ActivityDataPoint[] = [];
  const startDate = new Date('2025-07-01');
  
  // Use fixed seed for deterministic data
  const seededRandom = (seed: number) => {
    const x = Math.sin(seed) * 10000;
    return x - Math.floor(x);
  };

  // Create fixed anomaly points
  const anomalyPoints: Record<string, { date: string; merchant: string; type: 'organic' | 'fraud' | 'review' }> = {
    '2025-07-24_merchant_001': { date: '2025-07-24', merchant: 'merchant_001', type: 'fraud' },
    '2025-07-18_merchant_003': { date: '2025-07-18', merchant: 'merchant_003', type: 'organic' },
    '2025-07-15_merchant_002': { date: '2025-07-15', merchant: 'merchant_002', type: 'review' },
    '2025-07-08_merchant_005': { date: '2025-07-08', merchant: 'merchant_005', type: 'fraud' },
    '2025-07-12_merchant_007': { date: '2025-07-12', merchant: 'merchant_007', type: 'organic' },
  };

  for (let day = 0; day < 45; day++) {
    const date = new Date(startDate);
    date.setDate(date.getDate() + day);
    const dateStr = date.toISOString().split('T')[0];

    merchants.forEach((merchant, merchantIdx) => {
      const seed = day * 8 + merchantIdx;
      const baseline = Math.round(merchant.dailyVolume * (0.85 + seededRandom(seed) * 0.3));
      
      const anomalyKey = `${dateStr}_${merchant.id}`;
      const anomaly = anomalyPoints[anomalyKey];
      
      let actual = baseline;
      let type: 'normal' | 'organic' | 'fraud' | 'review' = 'normal';
      
      if (anomaly) {
        type = anomaly.type;
        if (type === 'fraud') {
          actual = Math.round(baseline * (2.2 + seededRandom(seed + 100) * 0.4));
        } else if (type === 'organic') {
          actual = Math.round(baseline * (1.8 + seededRandom(seed + 200) * 0.3));
        } else {
          actual = Math.round(baseline * (1.4 + seededRandom(seed + 300) * 0.2));
        }
      }

      data.push({
        date: dateStr,
        baseline,
        actual,
        merchant: merchant.id,
        type,
        isSelected: anomalyKey === '2025-07-24_merchant_001',
        anomalyId: anomaly ? `anomaly_${anomalyKey}` : undefined,
      });
    });
  }

  return data;
};

// Static chart data for the selected merchant (merchant_001)
export const getMerchant001Timeline = (): ActivityDataPoint[] => {
  const data: ActivityDataPoint[] = [];
  const startDate = new Date('2025-07-01');
  
  const seededRandom = (seed: number) => {
    const x = Math.sin(seed) * 10000;
    return x - Math.floor(x);
  };

  // Anomaly dates for merchant_001
  const anomalyDates: Record<string, 'organic' | 'fraud' | 'review'> = {
    '2025-07-24': 'fraud',
    '2025-07-08': 'fraud',
    '2025-07-19': 'organic',
  };

  for (let day = 0; day < 45; day++) {
    const date = new Date(startDate);
    date.setDate(date.getDate() + day);
    const dateStr = date.toISOString().split('T')[0];
    
    const baseline = Math.round(650 * (0.85 + seededRandom(day) * 0.3));
    const anomalyType = anomalyDates[dateStr];
    
    let actual = baseline;
    if (anomalyType === 'fraud' && dateStr === '2025-07-24') {
      actual = Math.round(baseline * 2.4);
    } else if (anomalyType === 'fraud') {
      actual = Math.round(baseline * (1.8 + seededRandom(day + 50) * 0.4));
    } else if (anomalyType === 'organic') {
      actual = Math.round(baseline * (1.6 + seededRandom(day + 100) * 0.3));
    }

    data.push({
      date: dateStr,
      baseline,
      actual,
      merchant: 'merchant_001',
      type: anomalyType || 'normal',
      isSelected: dateStr === '2025-07-24',
      anomalyId: anomalyType ? `anomaly_${dateStr}_merchant_001` : undefined,
    });
  }

  return data;
};

// Anomalies (for secondary display)
export const anomalies: Anomaly[] = [
  {
    id: 'anomaly_001',
    merchantId: 'merchant_001',
    merchantName: 'Merchant 001',
    date: '2025-07-24',
    severity: 'critical',
    status: 'fraud_spike',
    fraudProbability: 0.961,
    confidence: 0.961,
    confidenceBand: 'high_confidence',
    anomalyScore: 2.5,
    anomalySummary: 'Transaction volume is 2.4x the merchant\'s baseline; Failed payment rate elevated by 157%; IP diversity reduced',
    topSignals: ['failed_payment_rate (+157%)', 'ip_diversity_ratio (-42%)', 'device_diversity_ratio (-35%)'],
    decisionReason: 'High confidence fraud_spike (confidence=0.961)',
  },
  {
    id: 'anomaly_002',
    merchantId: 'merchant_003',
    merchantName: 'Merchant 003',
    date: '2025-07-18',
    severity: 'low',
    status: 'organic_spike',
    fraudProbability: 0.12,
    confidence: 0.88,
    confidenceBand: 'high_confidence',
    anomalyScore: 1.8,
    anomalySummary: 'Transaction volume is 2.2x the merchant\'s baseline; Customer diversity remains healthy',
    topSignals: ['transaction_count (+120%)', 'new_customer_share (+45%)'],
    decisionReason: 'High confidence organic_spike (confidence=0.880)',
  },
  {
    id: 'anomaly_003',
    merchantId: 'merchant_002',
    merchantName: 'Merchant 002',
    date: '2025-07-15',
    severity: 'medium',
    status: 'review_required',
    fraudProbability: 0.58,
    confidence: 0.65,
    confidenceBand: 'ambiguous',
    anomalyScore: 1.5,
    anomalySummary: 'Transaction volume is 1.5x the merchant\'s baseline; Mixed behavioral signals',
    topSignals: ['transaction_count (+50%)', 'retry_rate (+30%)'],
    decisionReason: 'Ambiguous classification (confidence=0.650), requires review',
  },
];

// Incidents
export const incidents: Incident[] = [
  {
    id: 'INC-merchant_001-20250724',
    merchantId: 'merchant_001',
    merchantName: 'Merchant 001',
    date: '2025-07-24',
    severity: 'critical',
    status: 'open',
    predictedCause: 'fraud_spike',
    fraudProbability: 0.961,
    confidence: 0.961,
    anomalyScore: 2.5,
    recommendedAction: 'IMMEDIATE ACTION REQUIRED: Review affected transactions, investigate abnormal payment/device/IP behavior',
    topSignals: ['failed_payment_rate (+157%)', 'ip_diversity_ratio (-42%)'],
  },
  {
    id: 'INC-merchant_003-20250718',
    merchantId: 'merchant_003',
    merchantName: 'Merchant 003',
    date: '2025-07-18',
    severity: 'low',
    status: 'resolved',
    predictedCause: 'organic_spike',
    fraudProbability: 0.12,
    confidence: 0.88,
    anomalyScore: 1.8,
    recommendedAction: 'Monitor merchant activity for changes',
    topSignals: ['transaction_count (+120%)'],
  },
  {
    id: 'INC-merchant_002-20250715',
    merchantId: 'merchant_002',
    merchantName: 'Merchant 002',
    date: '2025-07-15',
    severity: 'medium',
    status: 'investigating',
    predictedCause: 'review_required',
    fraudProbability: 0.58,
    confidence: 0.65,
    anomalyScore: 1.5,
    recommendedAction: 'Human review recommended: Anomaly detected but cause classification is ambiguous',
    topSignals: ['transaction_count (+50%)', 'retry_rate (+30%)'],
  },
];

// Activity feed events — chronological intelligence log
export const activityEvents: ActivityEvent[] = [
  {
    id: 'evt_001',
    merchantId: 'merchant_001',
    merchantName: 'merchant_001',
    date: '2025-07-24',
    time: '14:00',
    status: 'fraud_spike',
    severity: 'critical',
    summary: 'Transaction volume surged to 2.4× baseline with simultaneous degradation in payment success and network diversity.',
    transactionCount: 1563,
    baselineVolume: 650,
    volumeMultiple: 2.4,
    zScore: 1.44,
    fraudProbability: 0.961,
    confidence: 0.961,
    topSignals: [
      { label: 'Failed Payment Rate', value: '9.8%', changePercent: 157 },
      { label: 'IP Diversity', value: '48%', changePercent: -29 },
      { label: 'Device Diversity', value: '56%', changePercent: -23 },
    ],
    evidenceSignals: [
      {
        feature: 'failed_payment_rate', label: 'Failed Payment Rate',
        normalValue: 3.8, currentValue: 9.8, unit: '%', changePercent: 157,
        changeDirection: 'increased', signalStrength: 'strong', signalType: 'fraud',
        description: 'Payment failures significantly elevated, suggesting card testing or stolen credentials.',
      },
      {
        feature: 'ip_diversity_ratio', label: 'IP Diversity',
        normalValue: 68, currentValue: 48, unit: '%', changePercent: -29,
        changeDirection: 'decreased', signalStrength: 'strong', signalType: 'fraud',
        description: 'Fewer unique IP addresses responsible for a larger share of transactions.',
      },
      {
        feature: 'device_diversity_ratio', label: 'Device Diversity',
        normalValue: 73, currentValue: 56, unit: '%', changePercent: -23,
        changeDirection: 'decreased', signalStrength: 'moderate', signalType: 'fraud',
        description: 'Transactions concentrated across fewer devices than normal.',
      },
    ],
    incidentId: 'INC-merchant_001-20250724',
  },
  {
    id: 'evt_002',
    merchantId: 'merchant_003',
    merchantName: 'merchant_003',
    date: '2025-07-18',
    time: '09:30',
    status: 'organic_spike',
    severity: 'low',
    summary: 'Transaction volume doubled with healthy new customer acquisition and normal payment patterns.',
    transactionCount: 1870,
    baselineVolume: 850,
    volumeMultiple: 2.2,
    zScore: 1.65,
    fraudProbability: 0.12,
    confidence: 0.88,
    topSignals: [
      { label: 'New Customer Activity', value: '61%', changePercent: 45 },
      { label: 'SKU Diversity', value: '14 items', changePercent: 17 },
      { label: 'Failed Payment Rate', value: '4.8%', changePercent: 14 },
    ],
    evidenceSignals: [
      {
        feature: 'new_customer_share', label: 'New Customer Activity',
        normalValue: 42, currentValue: 61, unit: '%', changePercent: 45,
        changeDirection: 'increased', signalStrength: 'moderate', signalType: 'organic',
        description: 'Elevated new customer acquisition suggests promotional or viral activity.',
      },
      {
        feature: 'sku_diversity_ratio', label: 'SKU Diversity',
        normalValue: 12, currentValue: 14, unit: 'items', changePercent: 17,
        changeDirection: 'increased', signalStrength: 'weak', signalType: 'organic',
        description: 'Product diversity increased naturally with the volume surge.',
      },
    ],
  },
  {
    id: 'evt_003',
    merchantId: 'merchant_002',
    merchantName: 'merchant_002',
    date: '2025-07-15',
    time: '16:20',
    status: 'review_required',
    severity: 'medium',
    summary: 'Moderate volume increase with ambiguous behavioral signals requiring human review.',
    transactionCount: 630,
    baselineVolume: 420,
    volumeMultiple: 1.5,
    zScore: 0.89,
    fraudProbability: 0.58,
    confidence: 0.65,
    topSignals: [
      { label: 'Retry Behavior', value: '1.6%', changePercent: 33 },
      { label: 'IP Diversity', value: '65%', changePercent: -8 },
    ],
    evidenceSignals: [
      {
        feature: 'retry_rate', label: 'Retry Behavior',
        normalValue: 1.2, currentValue: 1.6, unit: '%', changePercent: 33,
        changeDirection: 'increased', signalStrength: 'moderate', signalType: 'fraud',
        description: 'Slightly elevated retry attempts may indicate payment issues.',
      },
      {
        feature: 'ip_diversity_ratio', label: 'IP Diversity',
        normalValue: 71, currentValue: 65, unit: '%', changePercent: -8,
        changeDirection: 'decreased', signalStrength: 'weak', signalType: 'fraud',
        description: 'Minor decrease in IP diversity, not yet at concerning levels.',
      },
    ],
  },
  {
    id: 'evt_004',
    merchantId: 'merchant_005',
    merchantName: 'merchant_005',
    date: '2025-07-08',
    time: '11:45',
    status: 'fraud_spike',
    severity: 'high',
    summary: 'Sudden transaction surge with concentrated device fingerprints and elevated payment retries.',
    transactionCount: 1340,
    baselineVolume: 580,
    volumeMultiple: 2.3,
    zScore: 1.52,
    fraudProbability: 0.87,
    confidence: 0.87,
    topSignals: [
      { label: 'Device Concentration', value: '42%', changePercent: -42 },
      { label: 'Retry Rate', value: '4.1%', changePercent: 89 },
    ],
    evidenceSignals: [
      {
        feature: 'device_diversity_ratio', label: 'Device Diversity',
        normalValue: 72, currentValue: 42, unit: '%', changePercent: -42,
        changeDirection: 'decreased', signalStrength: 'strong', signalType: 'fraud',
        description: 'Severe drop in device diversity indicates automated or scripted access.',
      },
      {
        feature: 'retry_rate', label: 'Retry Rate',
        normalValue: 2.1, currentValue: 4.1, unit: '%', changePercent: 89,
        changeDirection: 'increased', signalStrength: 'strong', signalType: 'fraud',
        description: 'High retry rate suggests card testing or credential stuffing.',
      },
    ],
  },
  {
    id: 'evt_005',
    merchantId: 'merchant_007',
    merchantName: 'merchant_007',
    date: '2025-07-12',
    time: '08:15',
    status: 'organic_spike',
    severity: 'low',
    summary: 'Gradual volume increase tracking with new marketing campaign launch and seasonal trends.',
    transactionCount: 1296,
    baselineVolume: 720,
    volumeMultiple: 1.8,
    zScore: 1.12,
    fraudProbability: 0.08,
    confidence: 0.92,
    topSignals: [
      { label: 'Customer Diversity', value: '78%', changePercent: 22 },
      { label: 'New Customer Share', value: '58%', changePercent: 31 },
    ],
    evidenceSignals: [
      {
        feature: 'customer_diversity_ratio', label: 'Customer Diversity',
        normalValue: 64, currentValue: 78, unit: '%', changePercent: 22,
        changeDirection: 'increased', signalStrength: 'moderate', signalType: 'organic',
        description: 'Broad customer base expansion consistent with marketing activity.',
      },
      {
        feature: 'new_customer_share', label: 'New Customer Share',
        normalValue: 44, currentValue: 58, unit: '%', changePercent: 31,
        changeDirection: 'increased', signalStrength: 'moderate', signalType: 'organic',
        description: 'Healthy new customer acquisition aligns with campaign timing.',
      },
    ],
  },
  {
    id: 'evt_006',
    merchantId: 'merchant_004',
    merchantName: 'merchant_004',
    date: '2025-07-05',
    time: '13:10',
    status: 'organic_spike',
    severity: 'low',
    summary: 'Volume increase driven by a flash sale event with normal payment behavior.',
    transactionCount: 570,
    baselineVolume: 300,
    volumeMultiple: 1.9,
    zScore: 1.28,
    fraudProbability: 0.05,
    confidence: 0.95,
    topSignals: [
      { label: 'SKU Diversity', value: '16 items', changePercent: 33 },
      { label: 'Transaction Amount', value: '$48 avg', changePercent: -12 },
    ],
    evidenceSignals: [
      {
        feature: 'sku_diversity_ratio', label: 'SKU Diversity',
        normalValue: 12, currentValue: 16, unit: 'items', changePercent: 33,
        changeDirection: 'increased', signalStrength: 'moderate', signalType: 'organic',
        description: 'Increased product variety consistent with promotional event.',
      },
    ],
  },
  {
    id: 'evt_007',
    merchantId: 'merchant_006',
    merchantName: 'merchant_006',
    date: '2025-07-20',
    time: '17:30',
    status: 'review_required',
    severity: 'medium',
    summary: 'Unusual evening activity spike with mixed signals across behavioral features.',
    transactionCount: 720,
    baselineVolume: 480,
    volumeMultiple: 1.5,
    zScore: 0.95,
    fraudProbability: 0.52,
    confidence: 0.58,
    topSignals: [
      { label: 'Time Distribution', value: '72% PM', changePercent: 40 },
      { label: 'IP Concentration', value: '58%', changePercent: -18 },
    ],
    evidenceSignals: [
      {
        feature: 'hour_distribution', label: 'Time Distribution',
        normalValue: 51, currentValue: 72, unit: '%', changePercent: 40,
        changeDirection: 'increased', signalStrength: 'moderate', signalType: 'neutral',
        description: 'Unusual concentration of activity in evening hours.',
      },
      {
        feature: 'ip_diversity_ratio', label: 'IP Diversity',
        normalValue: 71, currentValue: 58, unit: '%', changePercent: -18,
        changeDirection: 'decreased', signalStrength: 'moderate', signalType: 'fraud',
        description: 'Moderate IP concentration, warrants further investigation.',
      },
    ],
  },
  {
    id: 'evt_008',
    merchantId: 'merchant_001',
    merchantName: 'merchant_001',
    date: '2025-07-08',
    time: '10:20',
    status: 'fraud_spike',
    severity: 'high',
    summary: 'Secondary fraud pattern detected with similar behavioral fingerprint to the Jul 24 incident.',
    transactionCount: 1170,
    baselineVolume: 650,
    volumeMultiple: 1.8,
    zScore: 1.08,
    fraudProbability: 0.82,
    confidence: 0.82,
    topSignals: [
      { label: 'Failed Payments', value: '7.2%', changePercent: 89 },
      { label: 'IP Diversity', value: '52%', changePercent: -24 },
    ],
    evidenceSignals: [
      {
        feature: 'failed_payment_rate', label: 'Failed Payment Rate',
        normalValue: 3.8, currentValue: 7.2, unit: '%', changePercent: 89,
        changeDirection: 'increased', signalStrength: 'strong', signalType: 'fraud',
        description: 'Elevated payment failures mirror the pattern seen in the later Jul 24 incident.',
      },
      {
        feature: 'ip_diversity_ratio', label: 'IP Diversity',
        normalValue: 68, currentValue: 52, unit: '%', changePercent: -24,
        changeDirection: 'decreased', signalStrength: 'moderate', signalType: 'fraud',
        description: 'Reduced IP diversity suggesting coordinated access.',
      },
    ],
    incidentId: 'INC-merchant_001-20250708',
  },
];

// Full incident data with investigation details
export const fullIncidents: FullIncident[] = [
  {
    id: 'INC-merchant_001-20250724',
    merchantId: 'merchant_001',
    merchantName: 'merchant_001',
    date: '2025-07-24',
    dateFormatted: '24 JUL 2025',
    severity: 'critical',
    status: 'open',
    predictedCause: 'fraud_spike',
    fraudProbability: 0.961,
    confidence: 0.961,
    confidenceBand: 'high_confidence',
    anomalyScore: 2.5,
    transactionCount: 1563,
    baselineVolume: 650,
    volumeMultiple: 2.4,
    zScore: 1.44,
    headline: 'Coordinated payment failure pattern',
    summary: 'Transaction volume surged to 2.4× the historical baseline with simultaneous degradation in payment success and network diversity.',
    classificationSummary: 'The combination of elevated payment failures and concentrated device/IP patterns is strongly indicative of coordinated fraud activity.',
    recommendedAction: 'Review affected transactions and investigate abnormal payment, device, and IP behavior.',
    actionType: 'immediate',
    behavioralEvidence: [
      {
        feature: 'failed_payment_rate', label: 'Failed Payment Rate',
        normalValue: 3.8, currentValue: 9.8, unit: '%', changePercent: 157,
        changeDirection: 'increased', signalStrength: 'strong', signalType: 'fraud',
        description: 'Payment failures are significantly elevated, suggesting card testing or stolen credentials.',
      },
      {
        feature: 'ip_diversity_ratio', label: 'IP Diversity',
        normalValue: 68, currentValue: 48, unit: '%', changePercent: -29,
        changeDirection: 'decreased', signalStrength: 'strong', signalType: 'fraud',
        description: 'Fewer unique IP addresses responsible for a larger share of transactions.',
      },
      {
        feature: 'device_diversity_ratio', label: 'Device Diversity',
        normalValue: 73, currentValue: 56, unit: '%', changePercent: -23,
        changeDirection: 'decreased', signalStrength: 'moderate', signalType: 'fraud',
        description: 'Transactions concentrated across fewer devices than normal.',
      },
    ],
    modelContributions: [
      { feature: 'failed_payment_rate', label: 'Failed Payments', contribution: 0.82, direction: 'fraud' },
      { feature: 'ip_diversity_ratio', label: 'IP Concentration', contribution: 0.65, direction: 'fraud' },
      { feature: 'retry_rate', label: 'Retry Behavior', contribution: 0.54, direction: 'fraud' },
      { feature: 'device_diversity_ratio', label: 'Device Concentration', contribution: 0.48, direction: 'fraud' },
      { feature: 'new_customer_share', label: 'New Customer Activity', contribution: 0.32, direction: 'organic' },
    ],
    timeline: [
      { label: 'NORMAL BASELINE', detail: 'Transaction volume within expected range', color: '#8A94A6' },
      { label: 'VOLUME INCREASE', detail: '2.4× baseline detected on Jul 24', color: '#38BDF8' },
      { label: 'PAYMENT FAILURES RISE', detail: 'Failed payment rate reached 9.8%', color: '#FF5C5C' },
      { label: 'IP CONCENTRATION', detail: 'IP diversity dropped to 48%', color: '#FF5C5C' },
      { label: 'FRAUD CLASSIFIED', detail: '96.1% fraud probability, high confidence', color: '#FF5C5C' },
    ],
    topSignals: ['failed_payment_rate (+157%)', 'ip_diversity_ratio (-29%)', 'device_diversity_ratio (-23%)'],
  },
  {
    id: 'INC-merchant_005-20250708',
    merchantId: 'merchant_005',
    merchantName: 'merchant_005',
    date: '2025-07-08',
    dateFormatted: '08 JUL 2025',
    severity: 'critical',
    status: 'open',
    predictedCause: 'fraud_spike',
    fraudProbability: 0.87,
    confidence: 0.87,
    confidenceBand: 'high_confidence',
    anomalyScore: 2.2,
    transactionCount: 1340,
    baselineVolume: 580,
    volumeMultiple: 2.3,
    zScore: 1.52,
    headline: 'IP concentration anomaly with device fingerprint clustering',
    summary: 'Sudden transaction surge with concentrated device fingerprints and elevated payment retries.',
    classificationSummary: 'Device and IP concentration patterns strongly suggest automated or scripted fraud rather than organic demand.',
    recommendedAction: 'Investigate device fingerprints and IP patterns for signs of automated fraud tooling.',
    actionType: 'immediate',
    behavioralEvidence: [
      {
        feature: 'device_diversity_ratio', label: 'Device Diversity',
        normalValue: 72, currentValue: 42, unit: '%', changePercent: -42,
        changeDirection: 'decreased', signalStrength: 'strong', signalType: 'fraud',
        description: 'Severe drop in device diversity indicates automated or scripted access.',
      },
      {
        feature: 'retry_rate', label: 'Retry Rate',
        normalValue: 2.1, currentValue: 4.1, unit: '%', changePercent: 89,
        changeDirection: 'increased', signalStrength: 'strong', signalType: 'fraud',
        description: 'High retry rate suggests card testing or credential stuffing.',
      },
    ],
    modelContributions: [
      { feature: 'device_diversity_ratio', label: 'Device Concentration', contribution: 0.78, direction: 'fraud' },
      { feature: 'retry_rate', label: 'Retry Behavior', contribution: 0.68, direction: 'fraud' },
      { feature: 'ip_diversity_ratio', label: 'IP Concentration', contribution: 0.45, direction: 'fraud' },
      { feature: 'new_customer_share', label: 'New Customer Activity', contribution: 0.21, direction: 'organic' },
    ],
    timeline: [
      { label: 'NORMAL BASELINE', detail: 'Expected transaction patterns', color: '#8A94A6' },
      { label: 'VOLUME SURGE', detail: '2.3× baseline with rapid onset', color: '#38BDF8' },
      { label: 'DEVICE CLUSTERING', detail: 'Device diversity fell to 42%', color: '#FF5C5C' },
      { label: 'RETRY SPIKE', detail: 'Payment retry rate doubled', color: '#FF5C5C' },
      { label: 'FRAUD CLASSIFIED', detail: '87.0% fraud probability, high confidence', color: '#FF5C5C' },
    ],
    topSignals: ['device_diversity_ratio (-42%)', 'retry_rate (+89%)'],
  },
  {
    id: 'INC-merchant_001-20250708',
    merchantId: 'merchant_001',
    merchantName: 'merchant_001',
    date: '2025-07-08',
    dateFormatted: '08 JUL 2025',
    severity: 'high',
    status: 'investigating',
    predictedCause: 'fraud_spike',
    fraudProbability: 0.82,
    confidence: 0.82,
    confidenceBand: 'high_confidence',
    anomalyScore: 1.9,
    transactionCount: 1170,
    baselineVolume: 650,
    volumeMultiple: 1.8,
    zScore: 1.08,
    headline: 'Secondary fraud pattern with behavioral fingerprint match',
    summary: 'Secondary fraud pattern detected with similar behavioral fingerprint to the Jul 24 incident.',
    classificationSummary: 'Elevated payment failures and reduced IP diversity mirror the pattern seen in the later Jul 24 incident, suggesting the same fraud vector.',
    recommendedAction: 'Cross-reference with INC-merchant_001-20250724 for linked investigation.',
    actionType: 'review',
    behavioralEvidence: [
      {
        feature: 'failed_payment_rate', label: 'Failed Payment Rate',
        normalValue: 3.8, currentValue: 7.2, unit: '%', changePercent: 89,
        changeDirection: 'increased', signalStrength: 'strong', signalType: 'fraud',
        description: 'Elevated payment failures mirror the pattern seen in the later Jul 24 incident.',
      },
      {
        feature: 'ip_diversity_ratio', label: 'IP Diversity',
        normalValue: 68, currentValue: 52, unit: '%', changePercent: -24,
        changeDirection: 'decreased', signalStrength: 'moderate', signalType: 'fraud',
        description: 'Reduced IP diversity suggesting coordinated access.',
      },
    ],
    modelContributions: [
      { feature: 'failed_payment_rate', label: 'Failed Payments', contribution: 0.72, direction: 'fraud' },
      { feature: 'ip_diversity_ratio', label: 'IP Concentration', contribution: 0.55, direction: 'fraud' },
      { feature: 'retry_rate', label: 'Retry Behavior', contribution: 0.38, direction: 'fraud' },
    ],
    timeline: [
      { label: 'NORMAL BASELINE', detail: 'Expected transaction patterns', color: '#8A94A6' },
      { label: 'VOLUME INCREASE', detail: '1.8× baseline detected', color: '#38BDF8' },
      { label: 'PAYMENT FAILURES', detail: 'Failed payment rate at 7.2%', color: '#FBBF24' },
      { label: 'FRAUD CLASSIFIED', detail: '82.0% fraud probability, high confidence', color: '#FF5C5C' },
    ],
    topSignals: ['failed_payment_rate (+89%)', 'ip_diversity_ratio (-24%)'],
  },
  {
    id: 'INC-merchant_002-20250715',
    merchantId: 'merchant_002',
    merchantName: 'merchant_002',
    date: '2025-07-15',
    dateFormatted: '15 JUL 2025',
    severity: 'medium',
    status: 'investigating',
    predictedCause: 'review_required',
    fraudProbability: 0.58,
    confidence: 0.65,
    confidenceBand: 'ambiguous',
    anomalyScore: 1.5,
    transactionCount: 630,
    baselineVolume: 420,
    volumeMultiple: 1.5,
    zScore: 0.89,
    headline: 'Ambiguous behavioral signals require human judgment',
    summary: 'Moderate volume increase with ambiguous behavioral signals requiring human review.',
    classificationSummary: 'The model cannot confidently distinguish between organic growth and early fraud patterns. Manual investigation recommended.',
    recommendedAction: 'Human review recommended: Anomaly detected but cause classification is ambiguous.',
    actionType: 'review',
    behavioralEvidence: [
      {
        feature: 'retry_rate', label: 'Retry Behavior',
        normalValue: 1.2, currentValue: 1.6, unit: '%', changePercent: 33,
        changeDirection: 'increased', signalStrength: 'moderate', signalType: 'fraud',
        description: 'Slightly elevated retry attempts may indicate payment issues.',
      },
      {
        feature: 'ip_diversity_ratio', label: 'IP Diversity',
        normalValue: 71, currentValue: 65, unit: '%', changePercent: -8,
        changeDirection: 'decreased', signalStrength: 'weak', signalType: 'fraud',
        description: 'Minor decrease in IP diversity, not yet at concerning levels.',
      },
    ],
    modelContributions: [
      { feature: 'retry_rate', label: 'Retry Behavior', contribution: 0.42, direction: 'fraud' },
      { feature: 'ip_diversity_ratio', label: 'IP Diversity', contribution: 0.28, direction: 'fraud' },
      { feature: 'new_customer_share', label: 'New Customer Activity', contribution: 0.22, direction: 'organic' },
      { feature: 'sku_diversity_ratio', label: 'SKU Diversity', contribution: 0.15, direction: 'organic' },
    ],
    timeline: [
      { label: 'NORMAL BASELINE', detail: 'Expected transaction patterns', color: '#8A94A6' },
      { label: 'VOLUME INCREASE', detail: '1.5× baseline on Jul 15', color: '#38BDF8' },
      { label: 'MIXED SIGNALS', detail: 'Retry rate up, IP diversity slightly down', color: '#FBBF24' },
      { label: 'REVIEW FLAGGED', detail: '58.0% fraud probability, ambiguous confidence', color: '#FBBF24' },
    ],
    topSignals: ['retry_rate (+33%)', 'ip_diversity_ratio (-8%)'],
  },
  {
    id: 'INC-merchant_003-20250718',
    merchantId: 'merchant_003',
    merchantName: 'merchant_003',
    date: '2025-07-18',
    dateFormatted: '18 JUL 2025',
    severity: 'low',
    status: 'resolved',
    predictedCause: 'organic_spike',
    fraudProbability: 0.12,
    confidence: 0.88,
    confidenceBand: 'high_confidence',
    anomalyScore: 1.8,
    transactionCount: 1870,
    baselineVolume: 850,
    volumeMultiple: 2.2,
    zScore: 1.65,
    headline: 'Organic demand surge with healthy behavioral profile',
    summary: 'Transaction volume doubled with healthy new customer acquisition and normal payment patterns.',
    classificationSummary: 'The behavioral profile matches organic demand growth — likely a successful promotion or viral moment.',
    recommendedAction: 'Monitor merchant activity. No intervention required.',
    actionType: 'monitor',
    behavioralEvidence: [
      {
        feature: 'new_customer_share', label: 'New Customer Activity',
        normalValue: 42, currentValue: 61, unit: '%', changePercent: 45,
        changeDirection: 'increased', signalStrength: 'moderate', signalType: 'organic',
        description: 'Elevated new customer acquisition suggests promotional or viral activity.',
      },
      {
        feature: 'sku_diversity_ratio', label: 'SKU Diversity',
        normalValue: 12, currentValue: 14, unit: 'items', changePercent: 17,
        changeDirection: 'increased', signalStrength: 'weak', signalType: 'organic',
        description: 'Product diversity increased naturally with the volume surge.',
      },
      {
        feature: 'failed_payment_rate', label: 'Failed Payment Rate',
        normalValue: 4.2, currentValue: 4.8, unit: '%', changePercent: 14,
        changeDirection: 'increased', signalStrength: 'weak', signalType: 'neutral',
        description: 'Payment success rates remain within normal range.',
      },
    ],
    modelContributions: [
      { feature: 'new_customer_share', label: 'New Customer Activity', contribution: 0.72, direction: 'organic' },
      { feature: 'sku_diversity_ratio', label: 'SKU Diversity', contribution: 0.45, direction: 'organic' },
      { feature: 'customer_diversity_ratio', label: 'Customer Diversity', contribution: 0.38, direction: 'organic' },
      { feature: 'failed_payment_rate', label: 'Failed Payments', contribution: 0.15, direction: 'fraud' },
    ],
    timeline: [
      { label: 'NORMAL BASELINE', detail: 'Expected transaction patterns', color: '#8A94A6' },
      { label: 'VOLUME SURGE', detail: '2.2× baseline detected', color: '#38BDF8' },
      { label: 'HEALTHY SIGNALS', detail: 'New customer acquisition elevated, payments normal', color: '#34D399' },
      { label: 'ORGANIC CLASSIFIED', detail: '12.0% fraud probability, high confidence', color: '#34D399' },
    ],
    topSignals: ['new_customer_share (+45%)', 'sku_diversity_ratio (+17%)'],
  },
  {
    id: 'INC-merchant_006-20250720',
    merchantId: 'merchant_006',
    merchantName: 'merchant_006',
    date: '2025-07-20',
    dateFormatted: '20 JUL 2025',
    severity: 'medium',
    status: 'open',
    predictedCause: 'review_required',
    fraudProbability: 0.52,
    confidence: 0.58,
    confidenceBand: 'ambiguous',
    anomalyScore: 1.4,
    transactionCount: 720,
    baselineVolume: 480,
    volumeMultiple: 1.5,
    zScore: 0.95,
    headline: 'Unusual temporal pattern with IP concentration',
    summary: 'Unusual evening activity spike with mixed signals across behavioral features.',
    classificationSummary: 'The temporal distribution shift combined with moderate IP concentration creates an ambiguous signal that requires manual assessment.',
    recommendedAction: 'Review transaction timestamps and IP geolocation data for patterns.',
    actionType: 'review',
    behavioralEvidence: [
      {
        feature: 'hour_distribution', label: 'Time Distribution',
        normalValue: 51, currentValue: 72, unit: '%', changePercent: 40,
        changeDirection: 'increased', signalStrength: 'moderate', signalType: 'neutral',
        description: 'Unusual concentration of activity in evening hours.',
      },
      {
        feature: 'ip_diversity_ratio', label: 'IP Diversity',
        normalValue: 71, currentValue: 58, unit: '%', changePercent: -18,
        changeDirection: 'decreased', signalStrength: 'moderate', signalType: 'fraud',
        description: 'Moderate IP concentration, warrants further investigation.',
      },
    ],
    modelContributions: [
      { feature: 'hour_distribution', label: 'Time Distribution', contribution: 0.38, direction: 'fraud' },
      { feature: 'ip_diversity_ratio', label: 'IP Concentration', contribution: 0.32, direction: 'fraud' },
      { feature: 'new_customer_share', label: 'New Customer Activity', contribution: 0.18, direction: 'organic' },
    ],
    timeline: [
      { label: 'NORMAL BASELINE', detail: 'Expected transaction patterns', color: '#8A94A6' },
      { label: 'VOLUME INCREASE', detail: '1.5× baseline on Jul 20', color: '#38BDF8' },
      { label: 'TEMPORAL SHIFT', detail: '72% of activity in evening hours', color: '#FBBF24' },
      { label: 'REVIEW FLAGGED', detail: '52.0% fraud probability, ambiguous confidence', color: '#FBBF24' },
    ],
    topSignals: ['time_distribution (+40%)', 'ip_diversity_ratio (-18%)'],
  },
  {
    id: 'INC-merchant_007-20250712',
    merchantId: 'merchant_007',
    merchantName: 'merchant_007',
    date: '2025-07-12',
    dateFormatted: '12 JUL 2025',
    severity: 'low',
    status: 'resolved',
    predictedCause: 'organic_spike',
    fraudProbability: 0.08,
    confidence: 0.92,
    confidenceBand: 'high_confidence',
    anomalyScore: 1.6,
    transactionCount: 1296,
    baselineVolume: 720,
    volumeMultiple: 1.8,
    zScore: 1.12,
    headline: 'Marketing campaign driving legitimate traffic growth',
    summary: 'Gradual volume increase tracking with new marketing campaign launch and seasonal trends.',
    classificationSummary: 'Behavioral signals are entirely consistent with organic marketing-driven growth.',
    recommendedAction: 'No action required. This is expected traffic from the Jul campaign.',
    actionType: 'monitor',
    behavioralEvidence: [
      {
        feature: 'customer_diversity_ratio', label: 'Customer Diversity',
        normalValue: 64, currentValue: 78, unit: '%', changePercent: 22,
        changeDirection: 'increased', signalStrength: 'moderate', signalType: 'organic',
        description: 'Broad customer base expansion consistent with marketing activity.',
      },
      {
        feature: 'new_customer_share', label: 'New Customer Share',
        normalValue: 44, currentValue: 58, unit: '%', changePercent: 31,
        changeDirection: 'increased', signalStrength: 'moderate', signalType: 'organic',
        description: 'Healthy new customer acquisition aligns with campaign timing.',
      },
    ],
    modelContributions: [
      { feature: 'customer_diversity_ratio', label: 'Customer Diversity', contribution: 0.65, direction: 'organic' },
      { feature: 'new_customer_share', label: 'New Customer Activity', contribution: 0.52, direction: 'organic' },
      { feature: 'sku_diversity_ratio', label: 'SKU Diversity', contribution: 0.28, direction: 'organic' },
    ],
    timeline: [
      { label: 'NORMAL BASELINE', detail: 'Expected transaction patterns', color: '#8A94A6' },
      { label: 'GRADUAL INCREASE', detail: '1.8× baseline over several days', color: '#38BDF8' },
      { label: 'HEALTHY SIGNALS', detail: 'Customer diversity and new customer share up', color: '#34D399' },
      { label: 'ORGANIC CLASSIFIED', detail: '8.0% fraud probability, high confidence', color: '#34D399' },
    ],
    topSignals: ['customer_diversity_ratio (+22%)', 'new_customer_share (+31%)'],
  },
  {
    id: 'INC-merchant_004-20250705',
    merchantId: 'merchant_004',
    merchantName: 'merchant_004',
    date: '2025-07-05',
    dateFormatted: '05 JUL 2025',
    severity: 'low',
    status: 'resolved',
    predictedCause: 'organic_spike',
    fraudProbability: 0.05,
    confidence: 0.95,
    confidenceBand: 'high_confidence',
    anomalyScore: 1.3,
    transactionCount: 570,
    baselineVolume: 300,
    volumeMultiple: 1.9,
    zScore: 1.28,
    headline: 'Flash sale event with normal payment behavior',
    summary: 'Volume increase driven by a flash sale event with normal payment behavior.',
    classificationSummary: 'All behavioral signals point to organic promotional activity with healthy customer patterns.',
    recommendedAction: 'No action required. Expected behavior from promotional event.',
    actionType: 'monitor',
    behavioralEvidence: [
      {
        feature: 'sku_diversity_ratio', label: 'SKU Diversity',
        normalValue: 12, currentValue: 16, unit: 'items', changePercent: 33,
        changeDirection: 'increased', signalStrength: 'moderate', signalType: 'organic',
        description: 'Increased product variety consistent with promotional event.',
      },
    ],
    modelContributions: [
      { feature: 'sku_diversity_ratio', label: 'SKU Diversity', contribution: 0.58, direction: 'organic' },
      { feature: 'new_customer_share', label: 'New Customer Activity', contribution: 0.35, direction: 'organic' },
    ],
    timeline: [
      { label: 'NORMAL BASELINE', detail: 'Expected transaction patterns', color: '#8A94A6' },
      { label: 'VOLUME SPIKE', detail: '1.9× baseline from flash sale', color: '#38BDF8' },
      { label: 'HEALTHY SIGNALS', detail: 'Product diversity up, payments normal', color: '#34D399' },
      { label: 'ORGANIC CLASSIFIED', detail: '5.0% fraud probability, high confidence', color: '#34D399' },
    ],
    topSignals: ['sku_diversity_ratio (+33%)'],
  },
];

// Merchant directory items
export const merchantDirectory: MerchantDirectoryItem[] = [
  { id: 'merchant_001', name: 'merchant_001', dailyVolume: 650, riskLevel: 'medium', statusLabel: '2 FRAUD INCIDENTS', statusColor: '#FF5C5C', incidentCount: 2, riskLabel: 'HIGH ATTENTION', riskColor: '#FF5C5C' },
  { id: 'merchant_002', name: 'merchant_002', dailyVolume: 420, riskLevel: 'low', statusLabel: '1 REVIEW CASE', statusColor: '#FBBF24', incidentCount: 1, riskLabel: 'WATCH', riskColor: '#FBBF24' },
  { id: 'merchant_003', name: 'merchant_003', dailyVolume: 850, riskLevel: 'high', statusLabel: '1 ORGANIC SPIKE', statusColor: '#34D399', incidentCount: 1, riskLabel: 'STABLE', riskColor: '#34D399' },
  { id: 'merchant_004', name: 'merchant_004', dailyVolume: 300, riskLevel: 'low', statusLabel: '1 ORGANIC SPIKE', statusColor: '#34D399', incidentCount: 1, riskLabel: 'NORMAL', riskColor: '#38BDF8' },
  { id: 'merchant_005', name: 'merchant_005', dailyVolume: 580, riskLevel: 'medium', statusLabel: '1 FRAUD INCIDENT', statusColor: '#FF5C5C', incidentCount: 1, riskLabel: 'HIGH ATTENTION', riskColor: '#FF5C5C' },
  { id: 'merchant_006', name: 'merchant_006', dailyVolume: 480, riskLevel: 'low', statusLabel: '1 REVIEW CASE', statusColor: '#FBBF24', incidentCount: 1, riskLabel: 'WATCH', riskColor: '#FBBF24' },
  { id: 'merchant_007', name: 'merchant_007', dailyVolume: 720, riskLevel: 'medium', statusLabel: '1 ORGANIC SPIKE', statusColor: '#34D399', incidentCount: 1, riskLabel: 'STABLE', riskColor: '#34D399' },
  { id: 'merchant_008', name: 'merchant_008', dailyVolume: 520, riskLevel: 'medium', statusLabel: 'NO ANOMALIES', statusColor: '#8A94A6', incidentCount: 0, riskLabel: 'NORMAL', riskColor: '#38BDF8' },
];

// Merchant behavioral profiles
export const merchantProfiles: Record<string, MerchantProfile> = {
  merchant_001: {
    merchantId: 'merchant_001',
    riskPosture: 'high_attention',
    riskLabel: 'HIGH ATTENTION',
    summary: 'Transaction activity is generally stable, but recent behavior shows elevated payment failures and reduced network diversity. Two fraud-related anomalies detected within the monitoring period.',
    totalWindows: 45,
    spikeCount: 3,
    fraudCount: 2,
    organicCount: 1,
    reviewCount: 0,
    behavioralDimensions: [
      { key: 'transaction_volume', label: 'TRANSACTION VOLUME', baselineNormal: 650, baselineCurrent: 1563, unit: 'txns', normalRange: [550, 750], currentRange: [1170, 1563], signalType: 'fraud', changePercent: 140 },
      { key: 'payment_success', label: 'PAYMENT SUCCESS', baselineNormal: 96.2, baselineCurrent: 90.2, unit: '%', normalRange: [94, 98], currentRange: [88, 92], signalType: 'fraud', changePercent: -6 },
      { key: 'customer_diversity', label: 'CUSTOMER DIVERSITY', baselineNormal: 64, baselineCurrent: 52, unit: '%', normalRange: [58, 72], currentRange: [45, 58], signalType: 'fraud', changePercent: -19 },
      { key: 'device_diversity', label: 'DEVICE DIVERSITY', baselineNormal: 73, baselineCurrent: 56, unit: '%', normalRange: [65, 82], currentRange: [48, 62], signalType: 'fraud', changePercent: -23 },
      { key: 'ip_diversity', label: 'IP DIVERSITY', baselineNormal: 68, baselineCurrent: 48, unit: '%', normalRange: [60, 76], currentRange: [40, 55], signalType: 'fraud', changePercent: -29 },
      { key: 'retry_behavior', label: 'RETRY BEHAVIOR', baselineNormal: 1.4, baselineCurrent: 2.8, unit: '%', normalRange: [1.0, 2.0], currentRange: [2.2, 3.5], signalType: 'fraud', changePercent: 100 },
    ],
    anomalyHistory: [
      {
        id: 'anomaly_024', date: '2025-07-24', dateFormatted: '24 JUL 2025', status: 'fraud_spike', severity: 'critical',
        headline: 'Coordinated payment failure pattern',
        summary: 'Transaction volume surged to 2.4× baseline with simultaneous degradation in payment success and network diversity.',
        fraudProbability: 0.961, confidence: 0.961, confidenceBand: 'high_confidence',
        evidenceSignals: [
          { feature: 'failed_payment_rate', label: 'Failed Payment Rate', normalValue: 3.8, currentValue: 9.8, unit: '%', changePercent: 157, changeDirection: 'increased', signalStrength: 'strong', signalType: 'fraud', description: 'Payment failures significantly elevated, suggesting card testing or stolen credentials.' },
          { feature: 'ip_diversity_ratio', label: 'IP Diversity', normalValue: 68, currentValue: 48, unit: '%', changePercent: -29, changeDirection: 'decreased', signalStrength: 'strong', signalType: 'fraud', description: 'Fewer unique IP addresses responsible for a larger share of transactions.' },
        ],
      },
      {
        id: 'anomaly_009', date: '2025-07-08', dateFormatted: '08 JUL 2025', status: 'fraud_spike', severity: 'high',
        headline: 'Secondary fraud pattern with behavioral fingerprint match',
        summary: 'Secondary fraud pattern detected with similar behavioral fingerprint to the Jul 24 incident.',
        fraudProbability: 0.82, confidence: 0.82, confidenceBand: 'high_confidence',
        evidenceSignals: [
          { feature: 'failed_payment_rate', label: 'Failed Payment Rate', normalValue: 3.8, currentValue: 7.2, unit: '%', changePercent: 89, changeDirection: 'increased', signalStrength: 'strong', signalType: 'fraud', description: 'Elevated payment failures mirror the pattern seen in the later Jul 24 incident.' },
          { feature: 'ip_diversity_ratio', label: 'IP Diversity', normalValue: 68, currentValue: 52, unit: '%', changePercent: -24, changeDirection: 'decreased', signalStrength: 'moderate', signalType: 'fraud', description: 'Reduced IP diversity suggesting coordinated access.' },
        ],
      },
      {
        id: 'anomaly_007', date: '2025-07-03', dateFormatted: '03 JUL 2025', status: 'organic_spike', severity: 'low',
        headline: 'Promotional event driving organic growth',
        summary: 'Volume increase consistent with promotional activity, healthy behavioral signals.',
        fraudProbability: 0.08, confidence: 0.92, confidenceBand: 'high_confidence',
        evidenceSignals: [
          { feature: 'new_customer_share', label: 'New Customer Share', normalValue: 44, currentValue: 58, unit: '%', changePercent: 32, changeDirection: 'increased', signalStrength: 'moderate', signalType: 'organic', description: 'Healthy new customer acquisition consistent with promotion.' },
        ],
      },
    ],
  },
  merchant_002: {
    merchantId: 'merchant_002',
    riskPosture: 'watch',
    riskLabel: 'WATCH',
    summary: 'Generally stable merchant with one ambiguous behavioral signal. Moderate volume increase with slightly elevated retry behavior requires observation.',
    totalWindows: 45,
    spikeCount: 1,
    fraudCount: 0,
    organicCount: 0,
    reviewCount: 1,
    behavioralDimensions: [
      { key: 'transaction_volume', label: 'TRANSACTION VOLUME', baselineNormal: 420, baselineCurrent: 630, unit: 'txns', normalRange: [350, 500], currentRange: [550, 680], signalType: 'neutral', changePercent: 50 },
      { key: 'payment_success', label: 'PAYMENT SUCCESS', baselineNormal: 95.8, baselineCurrent: 94.2, unit: '%', normalRange: [93, 98], currentRange: [92, 96], signalType: 'neutral', changePercent: -2 },
      { key: 'customer_diversity', label: 'CUSTOMER DIVERSITY', baselineNormal: 58, baselineCurrent: 54, unit: '%', normalRange: [50, 66], currentRange: [48, 60], signalType: 'neutral', changePercent: -7 },
      { key: 'device_diversity', label: 'DEVICE DIVERSITY', baselineNormal: 65, baselineCurrent: 62, unit: '%', normalRange: [56, 74], currentRange: [54, 68], signalType: 'neutral', changePercent: -5 },
      { key: 'ip_diversity', label: 'IP DIVERSITY', baselineNormal: 71, baselineCurrent: 65, unit: '%', normalRange: [62, 80], currentRange: [58, 72], signalType: 'fraud', changePercent: -8 },
      { key: 'retry_behavior', label: 'RETRY BEHAVIOR', baselineNormal: 1.2, baselineCurrent: 1.6, unit: '%', normalRange: [0.8, 1.8], currentRange: [1.2, 2.2], signalType: 'fraud', changePercent: 33 },
    ],
    anomalyHistory: [
      {
        id: 'anomaly_015', date: '2025-07-15', dateFormatted: '15 JUL 2025', status: 'review_required', severity: 'medium',
        headline: 'Ambiguous behavioral signals require human judgment',
        summary: 'Moderate volume increase with ambiguous behavioral signals requiring human review.',
        fraudProbability: 0.58, confidence: 0.65, confidenceBand: 'ambiguous',
        evidenceSignals: [
          { feature: 'retry_rate', label: 'Retry Behavior', normalValue: 1.2, currentValue: 1.6, unit: '%', changePercent: 33, changeDirection: 'increased', signalStrength: 'moderate', signalType: 'fraud', description: 'Slightly elevated retry attempts may indicate payment issues.' },
          { feature: 'ip_diversity_ratio', label: 'IP Diversity', normalValue: 71, currentValue: 65, unit: '%', changePercent: -8, changeDirection: 'decreased', signalStrength: 'weak', signalType: 'fraud', description: 'Minor decrease in IP diversity, not yet at concerning levels.' },
        ],
      },
    ],
  },
  merchant_003: {
    merchantId: 'merchant_003',
    riskPosture: 'normal',
    riskLabel: 'STABLE',
    summary: 'High-volume merchant with healthy behavioral patterns. Recent organic traffic surge driven by new customer acquisition and promotional activity.',
    totalWindows: 45,
    spikeCount: 1,
    fraudCount: 0,
    organicCount: 1,
    reviewCount: 0,
    behavioralDimensions: [
      { key: 'transaction_volume', label: 'TRANSACTION VOLUME', baselineNormal: 850, baselineCurrent: 1870, unit: 'txns', normalRange: [720, 980], currentRange: [1500, 2000], signalType: 'organic', changePercent: 120 },
      { key: 'payment_success', label: 'PAYMENT SUCCESS', baselineNormal: 95.8, baselineCurrent: 95.2, unit: '%', normalRange: [93, 98], currentRange: [92, 97], signalType: 'neutral', changePercent: -1 },
      { key: 'customer_diversity', label: 'CUSTOMER DIVERSITY', baselineNormal: 62, baselineCurrent: 74, unit: '%', normalRange: [54, 70], currentRange: [66, 82], signalType: 'organic', changePercent: 19 },
      { key: 'device_diversity', label: 'DEVICE DIVERSITY', baselineNormal: 70, baselineCurrent: 72, unit: '%', normalRange: [62, 78], currentRange: [64, 80], signalType: 'neutral', changePercent: 3 },
      { key: 'ip_diversity', label: 'IP DIVERSITY', baselineNormal: 66, baselineCurrent: 68, unit: '%', normalRange: [58, 74], currentRange: [60, 76], signalType: 'neutral', changePercent: 3 },
      { key: 'retry_behavior', label: 'RETRY BEHAVIOR', baselineNormal: 1.8, baselineCurrent: 1.6, unit: '%', normalRange: [1.2, 2.4], currentRange: [1.0, 2.2], signalType: 'organic', changePercent: -11 },
    ],
    anomalyHistory: [
      {
        id: 'anomaly_018', date: '2025-07-18', dateFormatted: '18 JUL 2025', status: 'organic_spike', severity: 'low',
        headline: 'Organic demand surge with healthy behavioral profile',
        summary: 'Transaction volume doubled with healthy new customer acquisition and normal payment patterns.',
        fraudProbability: 0.12, confidence: 0.88, confidenceBand: 'high_confidence',
        evidenceSignals: [
          { feature: 'new_customer_share', label: 'New Customer Activity', normalValue: 42, currentValue: 61, unit: '%', changePercent: 45, changeDirection: 'increased', signalStrength: 'moderate', signalType: 'organic', description: 'Elevated new customer acquisition suggests promotional or viral activity.' },
          { feature: 'sku_diversity_ratio', label: 'SKU Diversity', normalValue: 12, currentValue: 14, unit: 'items', changePercent: 17, changeDirection: 'increased', signalStrength: 'weak', signalType: 'organic', description: 'Product diversity increased naturally with the volume surge.' },
        ],
      },
    ],
  },
  merchant_004: {
    merchantId: 'merchant_004',
    riskPosture: 'normal',
    riskLabel: 'NORMAL',
    summary: 'Low-volume merchant with consistent behavioral patterns. One flash sale event produced an organic spike with healthy customer signals.',
    totalWindows: 45,
    spikeCount: 1,
    fraudCount: 0,
    organicCount: 1,
    reviewCount: 0,
    behavioralDimensions: [
      { key: 'transaction_volume', label: 'TRANSACTION VOLUME', baselineNormal: 300, baselineCurrent: 570, unit: 'txns', normalRange: [250, 360], currentRange: [450, 620], signalType: 'organic', changePercent: 90 },
      { key: 'payment_success', label: 'PAYMENT SUCCESS', baselineNormal: 96.5, baselineCurrent: 96.1, unit: '%', normalRange: [94, 99], currentRange: [93, 98], signalType: 'neutral', changePercent: 0 },
      { key: 'customer_diversity', label: 'CUSTOMER DIVERSITY', baselineNormal: 55, baselineCurrent: 58, unit: '%', normalRange: [46, 64], currentRange: [48, 66], signalType: 'organic', changePercent: 5 },
      { key: 'device_diversity', label: 'DEVICE DIVERSITY', baselineNormal: 68, baselineCurrent: 70, unit: '%', normalRange: [58, 78], currentRange: [60, 80], signalType: 'neutral', changePercent: 3 },
      { key: 'ip_diversity', label: 'IP DIVERSITY', baselineNormal: 72, baselineCurrent: 71, unit: '%', normalRange: [62, 82], currentRange: [61, 81], signalType: 'neutral', changePercent: -1 },
      { key: 'retry_behavior', label: 'RETRY BEHAVIOR', baselineNormal: 1.1, baselineCurrent: 1.0, unit: '%', normalRange: [0.6, 1.6], currentRange: [0.5, 1.5], signalType: 'neutral', changePercent: -9 },
    ],
    anomalyHistory: [
      {
        id: 'anomaly_005', date: '2025-07-05', dateFormatted: '05 JUL 2025', status: 'organic_spike', severity: 'low',
        headline: 'Flash sale event with normal payment behavior',
        summary: 'Volume increase driven by a flash sale event with normal payment behavior.',
        fraudProbability: 0.05, confidence: 0.95, confidenceBand: 'high_confidence',
        evidenceSignals: [
          { feature: 'sku_diversity_ratio', label: 'SKU Diversity', normalValue: 12, currentValue: 16, unit: 'items', changePercent: 33, changeDirection: 'increased', signalStrength: 'moderate', signalType: 'organic', description: 'Increased product variety consistent with promotional event.' },
        ],
      },
    ],
  },
  merchant_005: {
    merchantId: 'merchant_005',
    riskPosture: 'high_attention',
    riskLabel: 'HIGH ATTENTION',
    summary: 'Medium-volume merchant with a critical fraud incident. Device fingerprint clustering and elevated retry rates indicate automated fraud tooling.',
    totalWindows: 45,
    spikeCount: 1,
    fraudCount: 1,
    organicCount: 0,
    reviewCount: 0,
    behavioralDimensions: [
      { key: 'transaction_volume', label: 'TRANSACTION VOLUME', baselineNormal: 580, baselineCurrent: 1340, unit: 'txns', normalRange: [490, 670], currentRange: [1100, 1400], signalType: 'fraud', changePercent: 131 },
      { key: 'payment_success', label: 'PAYMENT SUCCESS', baselineNormal: 96.0, baselineCurrent: 91.8, unit: '%', normalRange: [93, 99], currentRange: [88, 94], signalType: 'fraud', changePercent: -4 },
      { key: 'customer_diversity', label: 'CUSTOMER DIVERSITY', baselineNormal: 60, baselineCurrent: 48, unit: '%', normalRange: [52, 68], currentRange: [40, 55], signalType: 'fraud', changePercent: -20 },
      { key: 'device_diversity', label: 'DEVICE DIVERSITY', baselineNormal: 72, baselineCurrent: 42, unit: '%', normalRange: [63, 81], currentRange: [35, 50], signalType: 'fraud', changePercent: -42 },
      { key: 'ip_diversity', label: 'IP DIVERSITY', baselineNormal: 64, baselineCurrent: 50, unit: '%', normalRange: [55, 73], currentRange: [42, 58], signalType: 'fraud', changePercent: -22 },
      { key: 'retry_behavior', label: 'RETRY BEHAVIOR', baselineNormal: 2.1, baselineCurrent: 4.1, unit: '%', normalRange: [1.5, 2.8], currentRange: [3.2, 5.0], signalType: 'fraud', changePercent: 95 },
    ],
    anomalyHistory: [
      {
        id: 'anomaly_008', date: '2025-07-08', dateFormatted: '08 JUL 2025', status: 'fraud_spike', severity: 'high',
        headline: 'IP concentration anomaly with device fingerprint clustering',
        summary: 'Sudden transaction surge with concentrated device fingerprints and elevated payment retries.',
        fraudProbability: 0.87, confidence: 0.87, confidenceBand: 'high_confidence',
        evidenceSignals: [
          { feature: 'device_diversity_ratio', label: 'Device Diversity', normalValue: 72, currentValue: 42, unit: '%', changePercent: -42, changeDirection: 'decreased', signalStrength: 'strong', signalType: 'fraud', description: 'Severe drop in device diversity indicates automated or scripted access.' },
          { feature: 'retry_rate', label: 'Retry Rate', normalValue: 2.1, currentValue: 4.1, unit: '%', changePercent: 89, changeDirection: 'increased', signalStrength: 'strong', signalType: 'fraud', description: 'High retry rate suggests card testing or credential stuffing.' },
        ],
      },
    ],
  },
  merchant_006: {
    merchantId: 'merchant_006',
    riskPosture: 'watch',
    riskLabel: 'WATCH',
    summary: 'Low-volume merchant with an unusual temporal pattern. Evening activity concentration and moderate IP concentration warrant further observation.',
    totalWindows: 45,
    spikeCount: 1,
    fraudCount: 0,
    organicCount: 0,
    reviewCount: 1,
    behavioralDimensions: [
      { key: 'transaction_volume', label: 'TRANSACTION VOLUME', baselineNormal: 480, baselineCurrent: 720, unit: 'txns', normalRange: [400, 560], currentRange: [600, 780], signalType: 'neutral', changePercent: 50 },
      { key: 'payment_success', label: 'PAYMENT SUCCESS', baselineNormal: 96.2, baselineCurrent: 95.1, unit: '%', normalRange: [94, 98], currentRange: [93, 97], signalType: 'neutral', changePercent: -1 },
      { key: 'customer_diversity', label: 'CUSTOMER DIVERSITY', baselineNormal: 56, baselineCurrent: 50, unit: '%', normalRange: [48, 64], currentRange: [42, 58], signalType: 'neutral', changePercent: -11 },
      { key: 'device_diversity', label: 'DEVICE DIVERSITY', baselineNormal: 62, baselineCurrent: 55, unit: '%', normalRange: [53, 71], currentRange: [46, 62], signalType: 'neutral', changePercent: -11 },
      { key: 'ip_diversity', label: 'IP DIVERSITY', baselineNormal: 71, baselineCurrent: 58, unit: '%', normalRange: [62, 80], currentRange: [50, 66], signalType: 'fraud', changePercent: -18 },
      { key: 'retry_behavior', label: 'RETRY BEHAVIOR', baselineNormal: 1.5, baselineCurrent: 1.8, unit: '%', normalRange: [1.0, 2.0], currentRange: [1.3, 2.4], signalType: 'neutral', changePercent: 20 },
    ],
    anomalyHistory: [
      {
        id: 'anomaly_020', date: '2025-07-20', dateFormatted: '20 JUL 2025', status: 'review_required', severity: 'medium',
        headline: 'Unusual temporal pattern with IP concentration',
        summary: 'Unusual evening activity spike with mixed signals across behavioral features.',
        fraudProbability: 0.52, confidence: 0.58, confidenceBand: 'ambiguous',
        evidenceSignals: [
          { feature: 'hour_distribution', label: 'Time Distribution', normalValue: 51, currentValue: 72, unit: '%', changePercent: 40, changeDirection: 'increased', signalStrength: 'moderate', signalType: 'neutral', description: 'Unusual concentration of activity in evening hours.' },
          { feature: 'ip_diversity_ratio', label: 'IP Diversity', normalValue: 71, currentValue: 58, unit: '%', changePercent: -18, changeDirection: 'decreased', signalStrength: 'moderate', signalType: 'fraud', description: 'Moderate IP concentration, warrants further investigation.' },
        ],
      },
    ],
  },
  merchant_007: {
    merchantId: 'merchant_007',
    riskPosture: 'normal',
    riskLabel: 'STABLE',
    summary: 'Medium-volume merchant with healthy behavioral profile. Recent organic spike consistent with marketing campaign and seasonal demand.',
    totalWindows: 45,
    spikeCount: 1,
    fraudCount: 0,
    organicCount: 1,
    reviewCount: 0,
    behavioralDimensions: [
      { key: 'transaction_volume', label: 'TRANSACTION VOLUME', baselineNormal: 720, baselineCurrent: 1296, unit: 'txns', normalRange: [610, 830], currentRange: [1050, 1400], signalType: 'organic', changePercent: 80 },
      { key: 'payment_success', label: 'PAYMENT SUCCESS', baselineNormal: 95.5, baselineCurrent: 95.2, unit: '%', normalRange: [93, 98], currentRange: [92, 97], signalType: 'neutral', changePercent: 0 },
      { key: 'customer_diversity', label: 'CUSTOMER DIVERSITY', baselineNormal: 64, baselineCurrent: 78, unit: '%', normalRange: [55, 73], currentRange: [68, 86], signalType: 'organic', changePercent: 22 },
      { key: 'device_diversity', label: 'DEVICE DIVERSITY', baselineNormal: 68, baselineCurrent: 70, unit: '%', normalRange: [58, 78], currentRange: [60, 80], signalType: 'neutral', changePercent: 3 },
      { key: 'ip_diversity', label: 'IP DIVERSITY', baselineNormal: 66, baselineCurrent: 68, unit: '%', normalRange: [57, 75], currentRange: [59, 77], signalType: 'neutral', changePercent: 3 },
      { key: 'retry_behavior', label: 'RETRY BEHAVIOR', baselineNormal: 1.6, baselineCurrent: 1.4, unit: '%', normalRange: [1.0, 2.2], currentRange: [0.8, 2.0], signalType: 'organic', changePercent: -13 },
    ],
    anomalyHistory: [
      {
        id: 'anomaly_012', date: '2025-07-12', dateFormatted: '12 JUL 2025', status: 'organic_spike', severity: 'low',
        headline: 'Marketing campaign driving legitimate traffic growth',
        summary: 'Gradual volume increase tracking with new marketing campaign launch and seasonal trends.',
        fraudProbability: 0.08, confidence: 0.92, confidenceBand: 'high_confidence',
        evidenceSignals: [
          { feature: 'customer_diversity_ratio', label: 'Customer Diversity', normalValue: 64, currentValue: 78, unit: '%', changePercent: 22, changeDirection: 'increased', signalStrength: 'moderate', signalType: 'organic', description: 'Broad customer base expansion consistent with marketing activity.' },
          { feature: 'new_customer_share', label: 'New Customer Share', normalValue: 44, currentValue: 58, unit: '%', changePercent: 31, changeDirection: 'increased', signalStrength: 'moderate', signalType: 'organic', description: 'Healthy new customer acquisition aligns with campaign timing.' },
        ],
      },
    ],
  },
  merchant_008: {
    merchantId: 'merchant_008',
    riskPosture: 'normal',
    riskLabel: 'NORMAL',
    summary: 'Medium-volume merchant with completely stable behavioral patterns. No anomalies detected during the entire monitoring period.',
    totalWindows: 45,
    spikeCount: 0,
    fraudCount: 0,
    organicCount: 0,
    reviewCount: 0,
    behavioralDimensions: [
      { key: 'transaction_volume', label: 'TRANSACTION VOLUME', baselineNormal: 520, baselineCurrent: 540, unit: 'txns', normalRange: [440, 600], currentRange: [460, 620], signalType: 'neutral', changePercent: 4 },
      { key: 'payment_success', label: 'PAYMENT SUCCESS', baselineNormal: 96.0, baselineCurrent: 95.8, unit: '%', normalRange: [93, 99], currentRange: [93, 98], signalType: 'neutral', changePercent: 0 },
      { key: 'customer_diversity', label: 'CUSTOMER DIVERSITY', baselineNormal: 60, baselineCurrent: 62, unit: '%', normalRange: [51, 69], currentRange: [53, 71], signalType: 'neutral', changePercent: 3 },
      { key: 'device_diversity', label: 'DEVICE DIVERSITY', baselineNormal: 66, baselineCurrent: 65, unit: '%', normalRange: [56, 76], currentRange: [55, 75], signalType: 'neutral', changePercent: -2 },
      { key: 'ip_diversity', label: 'IP DIVERSITY', baselineNormal: 68, baselineCurrent: 67, unit: '%', normalRange: [59, 77], currentRange: [58, 76], signalType: 'neutral', changePercent: -1 },
      { key: 'retry_behavior', label: 'RETRY BEHAVIOR', baselineNormal: 1.3, baselineCurrent: 1.2, unit: '%', normalRange: [0.8, 1.8], currentRange: [0.7, 1.7], signalType: 'neutral', changePercent: -8 },
    ],
    anomalyHistory: [],
  },
};

// Navigation items
export const navigationItems: { id: string; label: string; path: string }[] = [
  { id: 'mission-control', label: 'MISSION', path: '/' },
  { id: 'activity', label: 'ACTIVITY', path: '/activity' },
  { id: 'incidents', label: 'INCIDENTS', path: '/incidents' },
  { id: 'merchants', label: 'MERCHANTS', path: '/merchants' },
];
