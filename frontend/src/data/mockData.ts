import { 
  Merchant, 
  Anomaly, 
  Incident, 
  ActivityDataPoint, 
  DashboardMetrics,
  InvestigationAnomaly,
  ActivityEvent 
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

// Navigation items
export const navigationItems: { id: string; label: string; path: string }[] = [
  { id: 'mission-control', label: 'MISSION', path: '/' },
  { id: 'activity', label: 'ACTIVITY', path: '/activity' },
  { id: 'incidents', label: 'INCIDENTS', path: '/incidents' },
  { id: 'merchants', label: 'MERCHANTS', path: '/merchants' },
];
