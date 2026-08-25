import { motion } from 'framer-motion';
import { FullIncident } from '../../types';

interface IncidentQueueItemProps {
  incident: FullIncident;
  isSelected: boolean;
  onClick: () => void;
  index: number;
}

const severityColors: Record<string, string> = {
  critical: '#FF5C5C',
  high: '#FBBF24',
  medium: '#38BDF8',
  low: '#34D399',
};

const causeColors: Record<string, string> = {
  fraud_spike: '#FF5C5C',
  organic_spike: '#34D399',
  review_required: '#FBBF24',
};

function formatDate(dateStr: string): string {
  const d = new Date(dateStr + 'T00:00:00');
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

export function IncidentQueueItem({ incident, isSelected, onClick, index }: IncidentQueueItemProps) {
  const sevColor = severityColors[incident.severity];
  const causeColor = causeColors[incident.predictedCause];

  return (
    <motion.button
      layout
      initial={{ opacity: 0, y: 5 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -5 }}
      transition={{ duration: 0.2, delay: index * 0.03 }}
      onClick={onClick}
      className={`w-full text-left p-4 border-b border-[#1a1f2e]/50 transition-all duration-150 group ${
        isSelected
          ? 'bg-[#111827]'
          : 'bg-transparent hover:bg-[#0D111A]'
      }`}
    >
      <div className="flex items-start gap-3">
        {/* Severity indicator */}
        <div className="flex-shrink-0 mt-1">
          <div
            className="w-1.5 h-1.5 rounded-full"
            style={{ backgroundColor: sevColor }}
          />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {/* Top line: merchant + date */}
          <div className="flex items-center justify-between mb-1">
            <span className="text-[10px] font-mono text-[#8A94A6] tracking-wider">
              {incident.merchantName}
            </span>
            <span className="text-[10px] font-mono text-[#8A94A6]/60">
              {formatDate(incident.date)}
            </span>
          </div>

          {/* Headline */}
          <p className="text-sm text-[#F3F4F6] leading-snug mb-2 line-clamp-2">
            {incident.headline}
          </p>

          {/* Bottom metrics */}
          <div className="flex items-center gap-4">
            <span className="text-xs font-mono" style={{ color: causeColor }}>
              {(incident.fraudProbability * 100).toFixed(0)}% FRAUD
            </span>
            <span
              className="text-[9px] font-mono tracking-wider px-1.5 py-0.5 rounded-sm"
              style={{
                color: sevColor,
                backgroundColor: `${sevColor}10`,
              }}
            >
              {incident.status.toUpperCase()}
            </span>
          </div>
        </div>
      </div>
    </motion.button>
  );
}
