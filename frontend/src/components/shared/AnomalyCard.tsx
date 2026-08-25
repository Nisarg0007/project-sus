import { motion } from 'framer-motion';
import { AlertTriangle, CheckCircle, Clock, ArrowRight } from 'lucide-react';
import { Anomaly } from '../../types';

interface AnomalyCardProps {
  anomaly: Anomaly;
}

export function AnomalyCard({ anomaly }: AnomalyCardProps) {
  const severityConfig = {
    critical: {
      bg: 'bg-sus-red/10',
      border: 'border-sus-red/30',
      text: 'text-sus-red',
      icon: <AlertTriangle className="w-4 h-4" />,
      label: 'CRITICAL',
    },
    high: {
      bg: 'bg-sus-amber/10',
      border: 'border-sus-amber/30',
      text: 'text-sus-amber',
      icon: <AlertTriangle className="w-4 h-4" />,
      label: 'HIGH',
    },
    medium: {
      bg: 'bg-sus-blue/10',
      border: 'border-sus-blue/30',
      text: 'text-sus-blue',
      icon: <Clock className="w-4 h-4" />,
      label: 'MEDIUM',
    },
    low: {
      bg: 'bg-sus-green/10',
      border: 'border-sus-green/30',
      text: 'text-sus-green',
      icon: <CheckCircle className="w-4 h-4" />,
      label: 'LOW',
    },
  };

  const config = severityConfig[anomaly.severity];

  return (
    <motion.div
      whileHover={{ scale: 1.02, y: -2 }}
      className={`relative p-6 rounded-2xl ${config.bg} border ${config.border} backdrop-blur-sm`}
    >
      {/* Severity Badge */}
      <div className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono ${config.text} bg-black/20 mb-4`}>
        {config.icon}
        {config.label}
      </div>

      {/* Merchant Info */}
      <div className="mb-3">
        <h4 className="font-semibold text-sus-text">{anomaly.merchantName}</h4>
        <p className="text-xs text-sus-text-dim font-mono">{anomaly.date}</p>
      </div>

      {/* Summary */}
      <p className="text-sm text-sus-text-dim mb-4 line-clamp-2">
        {anomaly.anomalySummary}
      </p>

      {/* Key Metrics */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        <div className="bg-black/20 rounded-lg p-2">
          <p className="text-xs text-sus-text-dim">Fraud Probability</p>
          <p className={`text-lg font-bold font-mono ${config.text}`}>
            {(anomaly.fraudProbability * 100).toFixed(1)}%
          </p>
        </div>
        <div className="bg-black/20 rounded-lg p-2">
          <p className="text-xs text-sus-text-dim">Confidence</p>
          <p className="text-lg font-bold font-mono text-sus-text">
            {(anomaly.confidence * 100).toFixed(1)}%
          </p>
        </div>
      </div>

      {/* Action Button */}
      <button className={`w-full flex items-center justify-center gap-2 py-2 rounded-lg ${config.bg} ${config.text} hover:bg-black/20 transition-colors`}>
        <span className="text-sm font-medium">INVESTIGATE</span>
        <ArrowRight className="w-4 h-4" />
      </button>
    </motion.div>
  );
}
