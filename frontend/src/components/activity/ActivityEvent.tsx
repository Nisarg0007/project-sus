import { motion } from 'framer-motion';
import { AlertTriangle, CheckCircle, HelpCircle, ArrowRight, ExternalLink } from 'lucide-react';
import { ActivityEvent as ActivityEventType } from '../../types';
import { useNavigation } from '../../hooks/useNavigation';

interface ActivityEventProps {
  event: ActivityEventType;
  isSelected: boolean;
  onClick: () => void;
  index: number;
}

const statusConfig: Record<string, {
  color: string;
  bgColor: string;
  label: string;
  icon: React.ReactNode;
}> = {
  fraud_spike: {
    color: '#FF5C5C',
    bgColor: 'rgba(255, 92, 92, 0.08)',
    label: 'FRAUD SPIKE',
    icon: <AlertTriangle className="w-3 h-3" />,
  },
  organic_spike: {
    color: '#34D399',
    bgColor: 'rgba(52, 211, 153, 0.08)',
    label: 'ORGANIC SURGE',
    icon: <CheckCircle className="w-3 h-3" />,
  },
  review_required: {
    color: '#FBBF24',
    bgColor: 'rgba(251, 191, 36, 0.08)',
    label: 'REVIEW REQUIRED',
    icon: <HelpCircle className="w-3 h-3" />,
  },
};

function formatDate(dateStr: string): string {
  const d = new Date(dateStr + 'T00:00:00');
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

export function ActivityEventItem({ event, isSelected, onClick, index }: ActivityEventProps) {
  const config = statusConfig[event.status];
  const { navigateToMerchantFromActivity } = useNavigation();

  return (
    <motion.button
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.3, delay: index * 0.05 }}
      onClick={onClick}
      className={`w-full text-left p-5 rounded-sm border transition-all duration-200 group ${
        isSelected
          ? 'bg-[#111827] border-[#2a3040]'
          : 'bg-transparent border-transparent hover:bg-[#0D111A] hover:border-[#1a1f2e]'
      }`}
    >
      {/* Top row: status badge + date */}
      <div className="flex items-center justify-between mb-3">
        <span
          className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-sm text-[10px] font-mono font-medium tracking-wider"
          style={{ color: config.color, backgroundColor: config.bgColor }}
        >
          {config.icon}
          {config.label}
        </span>
        <span className="text-[10px] font-mono text-[#8A94A6] tracking-wider">
          {formatDate(event.date)} · {event.time}
        </span>
      </div>

      {/* Merchant — clickable to Merchant Intelligence */}
      <div className="mb-2">
        <button
          onClick={(e) => {
            e.stopPropagation();
            navigateToMerchantFromActivity(event.merchantId);
          }}
          className="flex items-center gap-1.5 text-xs font-mono text-[#8A94A6] tracking-wider hover:text-[#38BDF8] transition-colors"
        >
          {event.merchantName}
          <ExternalLink className="w-2.5 h-2.5 opacity-0 group-hover:opacity-60 transition-opacity" />
        </button>
      </div>

      {/* Summary */}
      <p className="text-sm text-[#8A94A6] leading-relaxed mb-3 line-clamp-2">
        {event.summary}
      </p>

      {/* Bottom row: confidence + expand hint */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-[10px] font-mono text-[#8A94A6]">
            Confidence
          </span>
          <span
            className="text-xs font-mono font-medium"
            style={{ color: config.color }}
          >
            {(event.confidence * 100).toFixed(1)}%
          </span>
        </div>

        <span
          className="flex items-center gap-1 text-[10px] font-mono tracking-wider opacity-0 group-hover:opacity-100 transition-opacity"
          style={{ color: config.color }}
        >
          INSPECT
          <ArrowRight className="w-3 h-3" />
        </span>
      </div>
    </motion.button>
  );
}
