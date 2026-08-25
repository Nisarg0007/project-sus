import { motion } from 'framer-motion';
import { BehavioralDimension } from '../../types';

interface BehaviorChangeProps {
  dimensions: BehavioralDimension[];
}

const signalColors: Record<string, string> = {
  fraud: '#FF5C5C',
  organic: '#34D399',
  neutral: '#8A94A6',
};

export function BehaviorChange({ dimensions }: BehaviorChangeProps) {
  // Only show dimensions that actually changed meaningfully
  const changedDimensions = dimensions.filter(d => Math.abs(d.changePercent) > 5);

  return (
    <div>
      <div className="flex items-center gap-4 mb-4">
        <span className="text-[10px] font-mono text-[#8A94A6] tracking-[0.2em]">
          WHAT CHANGED
        </span>
        <div className="h-px flex-1 bg-[#1a1f2e]" />
      </div>

      <div className="space-y-4">
        {changedDimensions.map((dim, idx) => {
          const color = signalColors[dim.signalType];
          const changeSign = dim.changePercent > 0 ? '+' : '';
          const changeLabel = dim.changePercent > 5 ? 'ABOVE NORMAL' : 'BELOW NORMAL';

          // Calculate bar widths (0-100 scale based on visual range)
          const maxVal = dim.normalRange[1] * 1.3;
          const normalWidth = (dim.normalRange[1] / maxVal) * 100;
          const normalStart = (dim.normalRange[0] / maxVal) * 100;
          const currentWidth = (dim.baselineCurrent / maxVal) * 100;

          return (
            <motion.div
              key={dim.key}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.35, delay: 0.1 + idx * 0.06 }}
              className="bg-[#0D111A] border border-[#1a1f2e] rounded-sm p-5"
            >
              {/* Header row */}
              <div className="flex items-center justify-between mb-4">
                <span className="text-xs font-mono text-[#F3F4F6] tracking-wider">
                  {dim.label}
                </span>
                <span className="text-xs font-mono font-medium" style={{ color }}>
                  {changeSign}{dim.changePercent}% {changeLabel}
                </span>
              </div>

              {/* Values row */}
              <div className="grid grid-cols-2 gap-6 mb-4">
                <div>
                  <div className="text-[9px] font-mono text-[#8A94A6] tracking-wider mb-1">BASELINE</div>
                  <div className="text-xl font-mono text-[#8A94A6]">
                    {dim.baselineNormal}{dim.unit === '%' ? '%' : ''}
                  </div>
                </div>
                <div>
                  <div className="text-[9px] font-mono tracking-wider mb-1" style={{ color }}>CURRENT</div>
                  <div className="text-xl font-mono font-medium" style={{ color }}>
                    {dim.baselineCurrent}{dim.unit === '%' ? '%' : ''}
                  </div>
                </div>
              </div>

              {/* Visual comparison bar */}
              <div className="relative h-3 bg-[#1a1f2e] rounded-full overflow-hidden">
                {/* Normal range background */}
                <div
                  className="absolute h-full bg-[#8A94A6] opacity-15 rounded-full"
                  style={{ left: `${normalStart}%`, width: `${normalWidth - normalStart}%` }}
                />
                {/* Current value bar */}
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${currentWidth}%` }}
                  transition={{ duration: 0.7, delay: 0.2 + idx * 0.08 }}
                  className="absolute h-full rounded-full"
                  style={{ backgroundColor: color, opacity: 0.6 }}
                />
              </div>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
