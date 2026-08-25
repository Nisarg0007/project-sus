import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { MerchantAnomalyEntry, BehavioralEvidence } from '../../types';

interface AnomalyHistoryProps {
  entries: MerchantAnomalyEntry[];
}

const statusConfig: Record<string, { color: string; label: string }> = {
  fraud_spike: { color: '#FF5C5C', label: 'FRAUD SPIKE' },
  organic_spike: { color: '#34D399', label: 'ORGANIC SURGE' },
  review_required: { color: '#FBBF24', label: 'REVIEW REQUIRED' },
};

const severityLabels: Record<string, string> = {
  critical: 'CRITICAL',
  high: 'HIGH',
  medium: 'MEDIUM',
  low: 'LOW',
};

export function AnomalyHistory({ entries }: AnomalyHistoryProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  if (entries.length === 0) {
    return (
      <div>
        <div className="flex items-center gap-4 mb-4">
          <span className="text-[10px] font-mono text-[#8A94A6] tracking-[0.2em]">ANOMALY HISTORY</span>
          <div className="h-px flex-1 bg-[#1a1f2e]" />
        </div>
        <div className="bg-[#0D111A] border border-[#1a1f2e] rounded-sm p-8 text-center">
          <p className="text-sm text-[#34D399] font-mono">NO ANOMALIES DETECTED</p>
          <p className="text-xs text-[#8A94A6] mt-2">This merchant has shown stable behavior throughout the monitoring period.</p>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center gap-4 mb-4">
        <span className="text-[10px] font-mono text-[#8A94A6] tracking-[0.2em]">ANOMALY HISTORY</span>
        <div className="h-px flex-1 bg-[#1a1f2e]" />
        <span className="text-[10px] font-mono text-[#8A94A6]/60 tracking-wider">
          {entries.length} EVENT{entries.length !== 1 ? 'S' : ''}
        </span>
      </div>

      <div className="space-y-px">
        {/* Vertical timeline line */}
        <div className="relative">
          <div className="absolute left-[5px] top-3 bottom-3 w-px bg-[#1a1f2e]" />

          {entries.map((entry, idx) => {
            const config = statusConfig[entry.status];
            const isExpanded = expandedId === entry.id;

            return (
              <motion.div
                key={entry.id}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.3, delay: idx * 0.08 }}
                className="relative pl-8 py-4"
              >
                {/* Timeline node */}
                <div className="absolute left-0 top-5 z-10">
                  <div
                    className="w-[11px] h-[11px] rounded-full border-2"
                    style={{ borderColor: config.color, backgroundColor: isExpanded ? config.color : '#0D111A' }}
                  />
                </div>

                {/* Event content */}
                <button
                  onClick={() => setExpandedId(isExpanded ? null : entry.id)}
                  className="w-full text-left group"
                >
                  {/* Date + Status */}
                  <div className="flex items-center gap-3 mb-1.5">
                    <span className="text-[10px] font-mono text-[#8A94A6] tracking-wider">
                      {entry.dateFormatted}
                    </span>
                    <span
                      className="text-[9px] font-mono tracking-wider px-1.5 py-0.5 rounded-sm"
                      style={{ color: config.color, backgroundColor: `${config.color}10` }}
                    >
                      {config.label}
                    </span>
                    <span className="text-[9px] font-mono text-[#8A94A6]">
                      {severityLabels[entry.severity]}
                    </span>
                  </div>

                  {/* Headline */}
                  <p className="text-sm text-[#F3F4F6] leading-snug mb-1 group-hover:text-[#F3F4F6] transition-colors">
                    {entry.headline}
                  </p>

                  {/* Confidence */}
                  <div className="text-[10px] font-mono text-[#8A94A6]">
                    Confidence {(entry.confidence * 100).toFixed(1)}%
                    {entry.fraudProbability > 0.5 && (
                      <span className="ml-2" style={{ color: config.color }}>
                        Fraud prob {(entry.fraudProbability * 100).toFixed(1)}%
                      </span>
                    )}
                  </div>
                </button>

                {/* Expanded detail */}
                <AnimatePresence>
                  {isExpanded && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.25 }}
                      className="overflow-hidden"
                    >
                      <div className="mt-3 bg-[#0D111A] border border-[#1a1f2e] rounded-sm p-4">
                        <p className="text-xs text-[#8A94A6] leading-relaxed mb-3">
                          {entry.summary}
                        </p>

                        {/* Evidence signals */}
                        <div className="space-y-2">
                          {entry.evidenceSignals.map(signal => (
                            <EvidenceRow key={signal.feature} signal={signal} />
                          ))}
                        </div>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function EvidenceRow({ signal }: { signal: BehavioralEvidence }) {
  const color = signal.signalType === 'fraud' ? '#FF5C5C'
    : signal.signalType === 'organic' ? '#34D399'
    : '#8A94A6';

  return (
    <div className="flex items-center justify-between py-2 border-b border-[#1a1f2e]/50 last:border-0">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-mono text-[#8A94A6] tracking-wider">
            {signal.label.toUpperCase()}
          </span>
          <span className="text-[9px] font-mono px-1 rounded-sm"
            style={{ color, backgroundColor: `${color}10` }}>
            {signal.signalStrength.toUpperCase()}
          </span>
        </div>
        <p className="text-[10px] text-[#8A94A6]/70 mt-0.5 truncate">{signal.description}</p>
      </div>
      <div className="text-right flex-shrink-0 ml-4">
        <div className="text-xs font-mono font-medium" style={{ color }}>
          {signal.changePercent > 0 ? '+' : ''}{signal.changePercent}%
        </div>
        <div className="text-[9px] text-[#8A94A6]">
          {signal.normalValue} → {signal.currentValue}{signal.unit}
        </div>
      </div>
    </div>
  );
}
