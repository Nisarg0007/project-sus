import { motion } from 'framer-motion';
import { InvestigationAnomaly } from '../../types';

interface InvestigationFlowProps {
  anomaly: InvestigationAnomaly;
}

export function InvestigationFlow({ anomaly }: InvestigationFlowProps) {
  const stages = [
    {
      number: '01',
      title: 'DETECTED',
      description: 'The transaction volume exceeded the expected historical range.',
      metrics: [
        { label: 'Volume', value: `${anomaly.volumeMultiple.toFixed(1)}× baseline` },
        { label: 'Z-score', value: anomaly.zScore.toFixed(2) },
      ],
    },
    {
      number: '02',
      title: 'INVESTIGATED',
      description: 'SUS compared the anomaly against the merchant\'s historical behavior patterns.',
      metrics: [
        { label: 'Features analyzed', value: '38' },
        { label: 'Behavioral signals', value: `${anomaly.behavioralEvidence.length}` },
      ],
    },
    {
      number: '03',
      title: 'EVIDENCE',
      description: 'Multiple behavioral signals changed simultaneously, creating a distinctive pattern.',
      metrics: [
        { label: 'Strong signals', value: `${anomaly.behavioralEvidence.filter(e => e.signalStrength === 'strong').length}` },
        { label: 'Moderate signals', value: `${anomaly.behavioralEvidence.filter(e => e.signalStrength === 'moderate').length}` },
      ],
    },
    {
      number: '04',
      title: 'CLASSIFIED',
      description: anomaly.classificationSummary,
      metrics: [
        { label: 'Confidence', value: `${(anomaly.confidence * 100).toFixed(1)}%` },
        { label: 'Classification', value: anomaly.status.replace('_', ' ').toUpperCase() },
      ],
    },
  ];

  return (
    <section className="relative py-12 lg:py-16 px-[var(--content-px)] max-w-[var(--content-max)] mx-auto">
      <div className="flex items-center gap-4 mb-12">
        <span className="text-[11px] font-mono text-[#8A94A6]/60 tracking-[0.12em]">
          INVESTIGATION TIMELINE
        </span>
        <div className="h-px flex-1 bg-[#1a1f2e]" />
      </div>

      <div className="relative">
        {/* Vertical line */}
        <div className="absolute left-[19px] top-0 bottom-0 w-px bg-[#1a1f2e]" />

        <div className="space-y-12">
          {stages.map((stage, index) => (
            <motion.div
              key={stage.number}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.5, delay: index * 0.15 }}
              className="relative flex gap-8"
            >
              {/* Node */}
              <div className="relative z-10 flex-shrink-0">
                <div className="w-10 h-10 rounded-full border border-[#1a1f2e] bg-[#080B12] flex items-center justify-center">
                  <span className="text-xs font-mono text-[#8A94A6]">
                    {stage.number}
                  </span>
                </div>
              </div>

              {/* Content */}
              <div className="flex-1 pb-8">
                <div className="flex items-start justify-between gap-8">
                  <div className="flex-1">
                    <h4 className="text-sm font-mono text-[#8A94A6] tracking-widest mb-2">
                      {stage.title}
                    </h4>
                    <p className="text-[#F3F4F6] text-base leading-relaxed max-w-lg">
                      {stage.description}
                    </p>
                  </div>

                  {/* Metrics */}
                  <div className="flex gap-6">
                    {stage.metrics.map((metric) => (
                      <div key={metric.label} className="text-right">
                        <div className="text-xs font-mono text-[#8A94A6] mb-1">
                          {metric.label}
                        </div>
                        <div className="text-sm text-[#F3F4F6] font-mono">
                          {metric.value}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
