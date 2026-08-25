import { motion, AnimatePresence } from 'framer-motion';
import { X, ArrowRight, AlertTriangle, CheckCircle, HelpCircle } from 'lucide-react';
import { ActivityEvent } from '../../types';

interface ActivityDetailProps {
  event: ActivityEvent | null;
  onClose: () => void;
}

const statusDisplay: Record<string, { color: string; label: string; icon: React.ReactNode }> = {
  fraud_spike: { color: '#FF5C5C', label: 'FRAUD SPIKE', icon: <AlertTriangle className="w-4 h-4" /> },
  organic_spike: { color: '#34D399', label: 'ORGANIC SURGE', icon: <CheckCircle className="w-4 h-4" /> },
  review_required: { color: '#FBBF24', label: 'REVIEW REQUIRED', icon: <HelpCircle className="w-4 h-4" /> },
};

function formatFullDate(dateStr: string): string {
  const d = new Date(dateStr + 'T00:00:00');
  return d.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });
}

export function ActivityDetail({ event, onClose }: ActivityDetailProps) {
  return (
    <AnimatePresence>
      {event && (
        <>
          {/* Backdrop */}
          <motion.div
            key="backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 bg-black/40 z-40 lg:hidden"
            onClick={onClose}
          />

          {/* Panel */}
          <motion.div
            key="detail-panel"
            initial={{ x: '100%', opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: '100%', opacity: 0 }}
            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
            className="fixed top-0 right-0 bottom-0 w-full sm:w-[420px] bg-[#080B12] border-l border-[#1a1f2e] z-50 overflow-y-auto"
          >
            <DetailContent event={event} onClose={onClose} />
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

function DetailContent({ event, onClose }: { event: ActivityEvent; onClose: () => void }) {
  const status = statusDisplay[event.status];

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-[#1a1f2e]">
        <span className="text-[10px] font-mono text-[#8A94A6] tracking-[0.2em]">
          EVENT DETAIL
        </span>
        <button
          onClick={onClose}
          className="p-1.5 rounded-sm text-[#8A94A6] hover:text-[#F3F4F6] hover:bg-[#1a1f2e] transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-6 py-6">
        {/* Status badge */}
        <div className="mb-6">
          <span
            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-sm text-[11px] font-mono font-medium tracking-wider"
            style={{ color: status.color, backgroundColor: `${status.color}12` }}
          >
            {status.icon}
            {status.label}
          </span>
        </div>

        {/* Overview section */}
        <div className="mb-8">
          <div className="text-[10px] font-mono text-[#8A94A6] tracking-[0.15em] mb-4">
            EVENT OVERVIEW
          </div>
          <div className="h-px bg-[#1a1f2e] mb-4" />

          <div className="space-y-3">
            <DetailRow label="Merchant" value={event.merchantName} />
            <DetailRow label="Date" value={`${formatFullDate(event.date)} · ${event.time}`} />
            <DetailRow
              label="Transactions"
              value={event.transactionCount.toLocaleString()}
              valueColor="#F3F4F6"
            />
            <DetailRow
              label="Baseline"
              value={event.baselineVolume.toLocaleString()}
              valueColor="#8A94A6"
            />
            <DetailRow label="Z-Score" value={event.zScore.toFixed(2)} />
            <DetailRow
              label="Volume Multiple"
              value={`${event.volumeMultiple.toFixed(1)}×`}
              valueColor={status.color}
            />
          </div>
        </div>

        {/* Classification section */}
        <div className="mb-8">
          <div className="text-[10px] font-mono text-[#8A94A6] tracking-[0.15em] mb-4">
            CLASSIFICATION
          </div>
          <div className="h-px bg-[#1a1f2e] mb-4" />

          <div className="bg-[#0D111A] border border-[#1a1f2e] rounded-sm p-5">
            {/* Fraud probability as a visual bar */}
            <div className="mb-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-[10px] font-mono text-[#8A94A6] tracking-wider">FRAUD PROBABILITY</span>
                <span className="text-lg font-mono font-medium" style={{ color: status.color }}>
                  {(event.fraudProbability * 100).toFixed(1)}%
                </span>
              </div>
              <div className="h-1 bg-[#1a1f2e] rounded-full overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${event.fraudProbability * 100}%` }}
                  transition={{ duration: 0.8, delay: 0.2 }}
                  className="h-full rounded-full"
                  style={{ backgroundColor: status.color }}
                />
              </div>
            </div>

            <div className="flex items-center justify-between pt-3 border-t border-[#1a1f2e]">
              <span className="text-[10px] font-mono text-[#8A94A6] tracking-wider">CONFIDENCE</span>
              <span className="text-sm font-mono text-[#F3F4F6]">
                {(event.confidence * 100).toFixed(1)}%
              </span>
            </div>
          </div>
        </div>

        {/* Evidence section */}
        <div className="mb-8">
          <div className="text-[10px] font-mono text-[#8A94A6] tracking-[0.15em] mb-4">
            WHY SUS FLAGGED THIS
          </div>
          <div className="h-px bg-[#1a1f2e] mb-4" />

          <div className="space-y-3">
            {event.evidenceSignals.map((signal, idx) => (
              <motion.div
                key={signal.feature}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, delay: 0.3 + idx * 0.08 }}
                className="bg-[#0D111A] border border-[#1a1f2e] rounded-sm p-4"
              >
                {/* Signal header */}
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[10px] font-mono text-[#8A94A6] tracking-wider">
                    {signal.label.toUpperCase()}
                  </span>
                  <span
                    className="text-xs font-mono font-medium"
                    style={{
                      color: signal.signalType === 'fraud' ? '#FF5C5C'
                        : signal.signalType === 'organic' ? '#34D399'
                        : '#8A94A6',
                    }}
                  >
                    {signal.changePercent > 0 ? '+' : ''}{signal.changePercent}%
                  </span>
                </div>

                {/* Values */}
                <div className="flex items-baseline gap-2 mb-2">
                  <span className="text-lg font-mono text-[#F3F4F6]">
                    {signal.currentValue}{signal.unit === '%' ? '%' : ''}
                  </span>
                  <span className="text-xs text-[#8A94A6]">
                    from {signal.normalValue}{signal.unit === '%' ? '%' : ''}
                  </span>
                </div>

                {/* Visual bar */}
                <div className="h-1 bg-[#1a1f2e] rounded-full overflow-hidden mb-2">
                  <div
                    className="h-full rounded-full transition-all duration-500"
                    style={{
                      width: `${(signal.currentValue / Math.max(signal.normalValue, signal.currentValue)) * 100}%`,
                      backgroundColor: signal.signalType === 'fraud' ? '#FF5C5C'
                        : signal.signalType === 'organic' ? '#34D399'
                        : '#8A94A6',
                      opacity: 0.7,
                    }}
                  />
                </div>

                {/* Description */}
                <p className="text-xs text-[#8A94A6] leading-relaxed">
                  {signal.description}
                </p>
              </motion.div>
            ))}
          </div>
        </div>

        {/* Top signals summary */}
        <div className="mb-8">
          <div className="text-[10px] font-mono text-[#8A94A6] tracking-[0.15em] mb-4">
            TOP SIGNALS
          </div>
          <div className="h-px bg-[#1a1f2e] mb-4" />

          <div className="space-y-2">
            {event.topSignals.map(signal => (
              <div key={signal.label} className="flex items-center justify-between py-2">
                <span className="text-xs text-[#8A94A6]">{signal.label}</span>
                <span
                  className="text-xs font-mono font-medium"
                  style={{
                    color: signal.changePercent > 0
                      ? (event.status === 'organic_spike' ? '#34D399' : '#FF5C5C')
                      : (event.status === 'organic_spike' ? '#34D399' : '#FF5C5C'),
                  }}
                >
                  {signal.value}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Footer CTA */}
      <div className="px-6 py-4 border-t border-[#1a1f2e]">
        <button className="w-full flex items-center justify-center gap-2 py-2.5 text-xs font-mono tracking-wider text-[#38BDF8] bg-[#38BDF8]/8 hover:bg-[#38BDF8]/15 rounded-sm transition-colors">
          <span>VIEW FULL INCIDENT</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
}

function DetailRow({ label, value, valueColor = '#F3F4F6' }: { label: string; value: string; valueColor?: string }) {
  return (
    <div className="flex items-center justify-between py-1.5">
      <span className="text-xs text-[#8A94A6]">{label}</span>
      <span className="text-sm font-mono" style={{ color: valueColor }}>{value}</span>
    </div>
  );
}
