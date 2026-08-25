import { motion } from 'framer-motion';
import { IncidentTimelineStep } from '../../types';

interface IncidentTimelineProps {
  steps: IncidentTimelineStep[];
}

export function IncidentTimeline({ steps }: IncidentTimelineProps) {
  return (
    <div className="relative">
      {/* Vertical line */}
      <div className="absolute left-[5px] top-2 bottom-2 w-px bg-[#1a1f2e]" />

      <div className="space-y-0">
        {steps.map((step, index) => (
          <motion.div
            key={`${step.label}-${index}`}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.3, delay: 0.1 + index * 0.1 }}
            className="relative flex items-start gap-4 py-3"
          >
            {/* Node */}
            <div className="relative z-10 flex-shrink-0">
              <div
                className="w-[11px] h-[11px] rounded-full border-2"
                style={{
                  borderColor: step.color,
                  backgroundColor: index === steps.length - 1 ? step.color : '#0D111A',
                }}
              />
            </div>

            {/* Content */}
            <div className="flex-1 min-w-0">
              <div className="text-[10px] font-mono tracking-[0.12em] mb-0.5" style={{ color: step.color }}>
                {step.label}
              </div>
              <div className="text-xs text-[#8A94A6]">
                {step.detail}
              </div>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
