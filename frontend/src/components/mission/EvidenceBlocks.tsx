import { motion } from 'framer-motion';
import { BehavioralEvidence } from '../../types';

interface EvidenceBlocksProps {
  evidence: BehavioralEvidence[];
}

export function EvidenceBlocks({ evidence }: EvidenceBlocksProps) {
  const getSignalColor = (type: 'fraud' | 'organic' | 'neutral') => {
    switch (type) {
      case 'fraud': return '#FF5C5C';
      case 'organic': return '#34D399';
      case 'neutral': return '#8A94A6';
    }
  };

  const getStrengthLabel = (strength: 'strong' | 'moderate' | 'weak') => {
    switch (strength) {
      case 'strong': return 'STRONG FRAUD SIGNAL';
      case 'moderate': return 'MODERATE SIGNAL';
      case 'weak': return 'WEAK SIGNAL';
    }
  };

  return (
    <section className="relative py-12 lg:py-16 px-[var(--content-px)] max-w-[var(--content-max)] mx-auto">
      <div className="flex items-center gap-4 mb-12">
        <span className="text-[11px] font-mono text-[#8A94A6]/60 tracking-[0.12em]">
          EVIDENCE
        </span>
        <div className="h-px flex-1 bg-[#1a1f2e]" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {evidence.map((item, index) => (
          <motion.div
            key={item.feature}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: index * 0.1 }}
            className="bg-[#0D111A] border border-[#1a1f2e] rounded-sm p-8"
          >
            {/* Header */}
            <div className="flex items-start justify-between mb-6">
              <div>
                <h4 className="text-[11px] font-mono text-[#8A94A6]/60 tracking-[0.12em] mb-2">
                  {item.label.toUpperCase()}
                </h4>
              </div>
              <span 
                className="text-xs font-mono px-2 py-1 rounded-sm"
                style={{ 
                  backgroundColor: `${getSignalColor(item.signalType)}15`,
                  color: getSignalColor(item.signalType)
                }}
              >
                {getStrengthLabel(item.signalStrength)}
              </span>
            </div>

            {/* Values comparison */}
            <div className="grid grid-cols-2 gap-8 mb-6">
              <div>
                <div className="text-xs font-mono text-[#8A94A6] mb-1">NORMAL</div>
                <div className="text-3xl font-light text-[#F3F4F6]">
                  {item.normalValue}{item.unit === '%' ? '%' : ''}
                </div>
              </div>
              <div>
                <div className="text-xs font-mono text-[#8A94A6] mb-1">CURRENT</div>
                <div 
                  className="text-3xl font-light"
                  style={{ color: getSignalColor(item.signalType) }}
                >
                  {item.currentValue}{item.unit === '%' ? '%' : ''}
                </div>
              </div>
            </div>

            {/* Change percentage */}
            <div className="mb-6">
              <span 
                className="text-2xl font-mono"
                style={{ color: getSignalColor(item.signalType) }}
              >
                {item.changePercent > 0 ? '+' : ''}{item.changePercent}%
              </span>
            </div>

            {/* Visual bar comparison */}
            <div className="space-y-3 mb-6">
              <div>
                <div className="flex items-center justify-between text-xs font-mono text-[#8A94A6] mb-1">
                  <span>NORMAL</span>
                </div>
                <div className="h-2 bg-[#1a1f2e] rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-[#8A94A6] rounded-full"
                    style={{ width: `${(item.normalValue / Math.max(item.normalValue, item.currentValue)) * 100}%` }}
                  />
                </div>
              </div>
              <div>
                <div className="flex items-center justify-between text-xs font-mono text-[#8A94A6] mb-1">
                  <span>CURRENT</span>
                </div>
                <div className="h-2 bg-[#1a1f2e] rounded-full overflow-hidden">
                  <div 
                    className="h-full rounded-full"
                    style={{ 
                      width: `${(item.currentValue / Math.max(item.normalValue, item.currentValue)) * 100}%`,
                      backgroundColor: getSignalColor(item.signalType)
                    }}
                  />
                </div>
              </div>
            </div>

            {/* Description */}
            <p className="text-sm text-[#8A94A6] leading-relaxed">
              {item.description}
            </p>
          </motion.div>
        ))}
      </div>
    </section>
  );
}
