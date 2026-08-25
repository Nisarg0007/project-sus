import { motion } from 'framer-motion';
import { BehavioralDimension } from '../../types';

interface BehavioralFingerprintProps {
  dimensions: BehavioralDimension[];
}

const signalColors: Record<string, string> = {
  fraud: '#FF5C5C',
  organic: '#34D399',
  neutral: '#38BDF8',
};

export function BehavioralFingerprint({ dimensions }: BehavioralFingerprintProps) {
  return (
    <div>
      {/* Section header */}
      <div className="flex items-center gap-4 mb-4">
        <span className="text-[10px] font-mono text-[#8A94A6] tracking-[0.2em]">
          BEHAVIORAL FINGERPRINT
        </span>
        <div className="h-px flex-1 bg-[#1a1f2e]" />
      </div>
      <p className="text-xs text-[#8A94A6] mb-6 max-w-lg">
        Each dimension shows the merchant's normal range and where current behavior sits relative to baseline.
      </p>

      {/* Fingerprint visualization */}
      <div className="bg-[#0D111A] border border-[#1a1f2e] rounded-sm p-6 sm:p-8">
        <svg viewBox="0 0 800 340" className="w-full h-auto">
          {/* Column headers */}
          <text x="0" y="16" fill="#8A94A6" fontSize="9" fontFamily="monospace" letterSpacing="0.1em">
            DIMENSION
          </text>
          <text x="260" y="16" fill="#8A94A6" fontSize="9" fontFamily="monospace" letterSpacing="0.1em">
            NORMAL RANGE
          </text>
          <text x="620" y="16" fill="#8A94A6" fontSize="9" fontFamily="monospace" letterSpacing="0.1em">
            CHANGE
          </text>

          {/* Separator line */}
          <line x1="0" y1="26" x2="800" y2="26" stroke="#1a1f2e" strokeWidth="1" />

          {dimensions.map((dim, idx) => {
            const y = 52 + idx * 50;
            const color = signalColors[dim.signalType];
            const changeSign = dim.changePercent > 0 ? '+' : '';

            // Calculate positions within the visual range (100-760)
            const visMin = 100;
            const visMax = 560;
            const visRange = visMax - visMin;

            // Normal range positions
            const normalLow = visMin + (dim.normalRange[0] / (dim.normalRange[1] * 1.2)) * visRange;
            const normalHigh = visMin + (dim.normalRange[1] / (dim.normalRange[1] * 1.2)) * visRange;
            const normalMid = (normalLow + normalHigh) / 2;

            // Current position (clamped)
            const currentVal = Math.max(dim.normalRange[0] * 0.5, Math.min(dim.normalRange[1] * 1.5, dim.baselineCurrent));
            const currentPos = visMin + (currentVal / (dim.normalRange[1] * 1.2)) * visRange;

            return (
              <g key={dim.key}>
                {/* Row separator */}
                <line x1="0" y1={y - 8} x2="800" y2={y - 8} stroke="#1a1f2e" strokeWidth="0.5" opacity="0.5" />

                {/* Dimension label */}
                <text x="0" y={y + 12} fill="#F3F4F6" fontSize="11" fontFamily="monospace" letterSpacing="0.05em">
                  {dim.label}
                </text>

                {/* Normal range bar */}
                <rect
                  x={normalLow} y={y + 2}
                  width={Math.max(normalHigh - normalLow, 8)} height={6}
                  fill="#8A94A6" opacity={0.2} rx="1"
                />

                {/* Normal range center tick */}
                <line x1={normalMid} y1={y} x2={normalMid} y2={y + 10}
                  stroke="#8A94A6" strokeWidth="1" opacity={0.4} />

                {/* Current position indicator */}
                <motion.g
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.5, delay: 0.2 + idx * 0.06 }}
                >
                  {/* Connecting line from normal to current */}
                  <line
                    x1={normalMid} y1={y + 5}
                    x2={currentPos} y2={y + 5}
                    stroke={color} strokeWidth="1" opacity={0.4}
                    strokeDasharray="2 2"
                  />

                  {/* Current dot */}
                  <circle cx={currentPos} cy={y + 5} r={4} fill={color} stroke="#0D111A" strokeWidth="1.5" />

                  {/* Glow ring */}
                  <circle cx={currentPos} cy={y + 5} r={8} fill={color} opacity={0.12} />
                </motion.g>

                {/* Current value label */}
                <text x={currentPos} y={y - 2} textAnchor="middle"
                  fill={color} fontSize="10" fontFamily="monospace" fontWeight="500">
                  {dim.baselineCurrent}{dim.unit === '%' ? '%' : ''}
                </text>

                {/* Change percentage */}
                <text x="620" y={y + 12} fill={color} fontSize="12" fontFamily="monospace" fontWeight="500">
                  {changeSign}{dim.changePercent}%
                </text>
                <text x="700" y={y + 12} fill="#8A94A6" fontSize="9" fontFamily="monospace">
                  {dim.changePercent > 5 ? 'ABOVE' : dim.changePercent < -5 ? 'BELOW' : 'NORMAL'}
                </text>
              </g>
            );
          })}
        </svg>

        {/* Legend */}
        <div className="flex items-center gap-6 mt-4 pt-4 border-t border-[#1a1f2e]">
          <span className="flex items-center gap-2 text-[10px] font-mono text-[#8A94A6]">
            <span className="w-3 h-[2px] bg-[#8A94A6] opacity-40" />
            NORMAL RANGE
          </span>
          <span className="flex items-center gap-2 text-[10px] font-mono text-[#FF5C5C]">
            <span className="w-2 h-2 rounded-full bg-[#FF5C5C]" />
            FRAUD SIGNAL
          </span>
          <span className="flex items-center gap-2 text-[10px] font-mono text-[#34D399]">
            <span className="w-2 h-2 rounded-full bg-[#34D399]" />
            ORGANIC SIGNAL
          </span>
          <span className="flex items-center gap-2 text-[10px] font-mono text-[#38BDF8]">
            <span className="w-2 h-2 rounded-full bg-[#38BDF8]" />
            NEUTRAL
          </span>
        </div>
      </div>
    </div>
  );
}
