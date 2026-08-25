import { useState } from 'react';
import { motion } from 'framer-motion';
import { AlertTriangle, HelpCircle, Eye, ArrowRight, Check } from 'lucide-react';

interface RecommendedActionProps {
  actionType: 'immediate' | 'review' | 'monitor';
  recommendedAction: string;
}

const actionConfig = {
  immediate: {
    color: '#FF5C5C',
    bgColor: 'rgba(255, 92, 92, 0.08)',
    borderColor: 'rgba(255, 92, 92, 0.2)',
    label: 'IMMEDIATE ACTION REQUIRED',
    icon: <AlertTriangle className="w-3.5 h-3.5" />,
    buttons: [
      { label: 'REVIEW TRANSACTIONS', primary: true },
      { label: 'VIEW MERCHANT', primary: false },
    ],
  },
  review: {
    color: '#FBBF24',
    bgColor: 'rgba(251, 191, 36, 0.08)',
    borderColor: 'rgba(251, 191, 36, 0.2)',
    label: 'HUMAN REVIEW RECOMMENDED',
    icon: <HelpCircle className="w-3.5 h-3.5" />,
    buttons: [
      { label: 'OPEN INVESTIGATION', primary: true },
    ],
  },
  monitor: {
    color: '#34D399',
    bgColor: 'rgba(52, 211, 153, 0.08)',
    borderColor: 'rgba(52, 211, 153, 0.2)',
    label: 'NO ACTION REQUIRED',
    icon: <Eye className="w-3.5 h-3.5" />,
    buttons: [
      { label: 'VIEW DETAILS', primary: false },
    ],
  },
};

export function RecommendedAction({ actionType, recommendedAction }: RecommendedActionProps) {
  const config = actionConfig[actionType];
  const [clickedButton, setClickedButton] = useState<string | null>(null);

  const handleButtonClick = (label: string) => {
    setClickedButton(label);
    // Reset after 2s
    setTimeout(() => setClickedButton(null), 2000);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.3 }}
      className="rounded-sm border overflow-hidden"
      style={{ borderColor: config.borderColor, backgroundColor: config.bgColor }}
    >
      {/* Header */}
      <div className="px-5 py-3 border-b" style={{ borderColor: config.borderColor }}>
        <div className="flex items-center gap-2">
          <span style={{ color: config.color }}>{config.icon}</span>
          <span
            className="text-[10px] font-mono tracking-[0.15em] font-medium"
            style={{ color: config.color }}
          >
            {config.label}
          </span>
        </div>
      </div>

      {/* Content */}
      <div className="px-5 py-4">
        <p className="text-sm text-[#8A94A6] leading-relaxed mb-4">
          {recommendedAction}
        </p>

        {/* Action buttons */}
        <div className="flex flex-wrap gap-2">
          {config.buttons.map(btn => {
            const wasClicked = clickedButton === btn.label;
            return (
              <motion.button
                key={btn.label}
                whileTap={{ scale: 0.97 }}
                onClick={() => handleButtonClick(btn.label)}
                className="flex items-center gap-2 px-3 py-2 text-[10px] font-mono tracking-wider rounded-sm transition-all duration-200"
                style={{
                  color: wasClicked ? '#34D399' : (btn.primary ? config.color : '#8A94A6'),
                  backgroundColor: wasClicked ? 'rgba(52, 211, 153, 0.1)' : (btn.primary ? `${config.color}15` : '#0D111A'),
                  border: `1px solid ${wasClicked ? 'rgba(52, 211, 153, 0.3)' : (btn.primary ? config.borderColor : '#1a1f2e')}`,
                }}
              >
                {wasClicked ? (
                  <Check className="w-3 h-3" />
                ) : btn.primary ? (
                  <ArrowRight className="w-3 h-3" />
                ) : null}
                <span>{wasClicked ? 'CONFIRMED' : btn.label}</span>
              </motion.button>
            );
          })}
        </div>
      </div>
    </motion.div>
  );
}
