import { motion } from 'framer-motion';
import { ArrowRight, AlertTriangle, CheckCircle, HelpCircle } from 'lucide-react';
import { InvestigationAnomaly } from '../../types';

interface FindingsSectionProps {
  onSelectAnomaly: (anomaly: InvestigationAnomaly) => void;
}

// The three canonical findings from the SUS pipeline
const findings: Array<{
  anomalyIndex: number;
  badge: string;
  badgeColor: string;
  borderColor: string;
  accentColor: string;
  icon: React.ReactNode;
  metrics: Array<{ label: string; value: string; color: string }>;
}> = [
  {
    anomalyIndex: 0,
    badge: 'CRITICAL',
    badgeColor: '#FF5C5C',
    borderColor: 'rgba(255, 92, 92, 0.2)',
    accentColor: '#FF5C5C',
    icon: <AlertTriangle className="w-3.5 h-3.5" />,
    metrics: [
      { label: 'Fraud probability', value: '96.1%', color: '#FF5C5C' },
      { label: 'Failed payment rate', value: '+157%', color: '#FF5C5C' },
      { label: 'IP diversity', value: '-29%', color: '#FF5C5C' },
    ],
  },
  {
    anomalyIndex: 1,
    badge: 'ORGANIC',
    badgeColor: '#34D399',
    borderColor: 'rgba(52, 211, 153, 0.2)',
    accentColor: '#34D399',
    icon: <CheckCircle className="w-3.5 h-3.5" />,
    metrics: [
      { label: 'Fraud probability', value: '12.0%', color: '#34D399' },
      { label: 'New customer activity', value: '+45%', color: '#34D399' },
      { label: 'SKU diversity', value: '+17%', color: '#34D399' },
    ],
  },
  {
    anomalyIndex: 2,
    badge: 'INVESTIGATE',
    badgeColor: '#FBBF24',
    borderColor: 'rgba(251, 191, 36, 0.2)',
    accentColor: '#FBBF24',
    icon: <HelpCircle className="w-3.5 h-3.5" />,
    metrics: [
      { label: 'Fraud probability', value: '58.0%', color: '#FBBF24' },
      { label: 'Retry behavior', value: '+33%', color: '#FBBF24' },
      { label: 'IP diversity', value: '-8%', color: '#8A94A6' },
    ],
  },
];

// Lazy import to avoid circular deps
import { investigationAnomalies } from '../../data/mockData';

export function FindingsSection({ onSelectAnomaly }: FindingsSectionProps) {
  return (
    <section className="py-16 px-8 max-w-[1600px] mx-auto">
      {/* Section header */}
      <div className="flex items-center gap-4 mb-12">
        <span className="text-xs font-mono text-[#8A94A6] tracking-[0.2em]">
          WHAT SUS FOUND
        </span>
        <div className="h-px flex-1 bg-[#1a1f2e]" />
      </div>

      {/* Three finding cards */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {findings.map((finding, index) => {
          const anomaly = investigationAnomalies[finding.anomalyIndex];

          return (
            <motion.div
              key={anomaly.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.1 + index * 0.12 }}
              whileHover={{ y: -4, transition: { duration: 0.2 } }}
              className="relative bg-[#0D111A] rounded-sm overflow-hidden cursor-pointer group"
              style={{ border: `1px solid ${finding.borderColor}` }}
              onClick={() => onSelectAnomaly(anomaly)}
            >
              {/* Top accent line */}
              <div
                className="h-px w-full"
                style={{ backgroundColor: finding.accentColor, opacity: 0.6 }}
              />

              <div className="p-8">
                {/* Badge */}
                <div className="flex items-center gap-2 mb-6">
                  <span
                    className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-sm text-[11px] font-mono font-medium tracking-wider"
                    style={{
                      color: finding.badgeColor,
                      backgroundColor: `${finding.badgeColor}12`,
                    }}
                  >
                    {finding.icon}
                    {finding.badge}
                  </span>
                </div>

                {/* Merchant */}
                <div className="mb-4">
                  <span className="text-sm font-mono text-[#8A94A6] tracking-wider">
                    {anomaly.merchantName}
                  </span>
                </div>

                {/* Summary */}
                <p className="text-sm text-[#8A94A6] leading-relaxed mb-8">
                  {anomaly.anomalySummary}
                </p>

                {/* Metrics */}
                <div className="space-y-4 mb-8">
                  {finding.metrics.map((metric) => (
                    <div key={metric.label} className="flex items-center justify-between">
                      <span className="text-xs text-[#8A94A6]">{metric.label}</span>
                      <span
                        className="text-sm font-mono font-medium"
                        style={{ color: metric.color }}
                      >
                        {metric.value}
                      </span>
                    </div>
                  ))}
                </div>

                {/* CTA */}
                <div
                  className="flex items-center gap-2 text-xs font-mono tracking-wider group-hover:gap-3 transition-all duration-200"
                  style={{ color: finding.accentColor }}
                >
                  <span>INVESTIGATE</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </div>
              </div>
            </motion.div>
          );
        })}
      </div>
    </section>
  );
}
