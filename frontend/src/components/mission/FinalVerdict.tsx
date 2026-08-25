import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { InvestigationAnomaly } from '../../types';

interface FinalVerdictProps {
  anomaly: InvestigationAnomaly;
}

export function FinalVerdict({ anomaly }: FinalVerdictProps) {
  const navigate = useNavigate();

  const severityColors = {
    critical: '#FF5C5C',
    high: '#FBBF24',
    medium: '#38BDF8',
    low: '#34D399',
  };

  const statusLabels = {
    fraud_spike: 'FRAUD SPIKE',
    organic_spike: 'ORGANIC SPIKE',
    review_required: 'REVIEW REQUIRED',
    baseline: 'BASELINE',
  };

  return (
    <section className="relative py-12 lg:py-16 px-[var(--content-px)] max-w-[var(--content-max)] mx-auto">
      <div className="flex items-center gap-4 mb-12">
        <span className="text-[11px] font-mono text-[#8A94A6]/60 tracking-[0.12em]">
          CONCLUSION
        </span>
        <div className="h-px flex-1 bg-[#1a1f2e]" />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="grid grid-cols-1 lg:grid-cols-12 gap-12"
      >
        {/* Left: Verdict */}
        <div className="lg:col-span-7">
          <div className="mb-8">
            <span className="text-[11px] font-mono text-[#8A94A6]/60 tracking-[0.12em] block mb-4">
              SUS CONCLUSION
            </span>
            <div className="h-px bg-[#1a1f2e] mb-8" />
          </div>

          {/* Verdict title */}
          <motion.h2
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="text-4xl lg:text-5xl font-light mb-8"
            style={{ color: severityColors[anomaly.severity] }}
          >
            {statusLabels[anomaly.status]}
          </motion.h2>

          {/* Confidence and probability */}
          <div className="flex items-center gap-8 mb-8">
            <div>
              <div className="text-xs font-mono text-[#8A94A6] mb-1">CONFIDENCE</div>
              <div className="text-lg text-[#F3F4F6]">{(anomaly.confidence * 100).toFixed(1)}%</div>
            </div>
            <div className="w-px h-12 bg-[#1a1f2e]" />
            <div>
              <div className="text-xs font-mono text-[#8A94A6] mb-1">PROBABILITY</div>
              <div className="text-lg" style={{ color: severityColors[anomaly.severity] }}>
                {(anomaly.fraudProbability * 100).toFixed(1)}%
              </div>
            </div>
          </div>

          {/* Summary */}
          <p className="text-[#8A94A6] text-base leading-relaxed max-w-2xl mb-12">
            {anomaly.classificationSummary}
          </p>

          {/* Divider */}
          <div className="h-px bg-[#1a1f2e] mb-8" />

          {/* Recommended action */}
          <div className="mb-8">
            <span className="text-[11px] font-mono text-[#8A94A6]/60 tracking-[0.12em] block mb-4">
              RECOMMENDED ACTION
            </span>
            <p className="text-[#F3F4F6] text-lg leading-relaxed max-w-2xl">
              {anomaly.recommendedAction}
            </p>
          </div>

          {/* CTA */}
          {anomaly.incidentId && (
            <motion.button
              whileHover={{ x: 4 }}
              onClick={() => navigate('/incidents')}
              className="flex items-center gap-3 text-sm font-mono tracking-wider"
              style={{ color: severityColors[anomaly.severity] }}
            >
              <span>OPEN INCIDENT</span>
              <span className="text-lg">→</span>
            </motion.button>
          )}
        </div>

        {/* Right: Quick stats */}
        <div className="lg:col-span-5">
          <div className="bg-[#0D111A] border border-[#1a1f2e] rounded-sm p-8">
            <span className="text-[11px] font-mono text-[#8A94A6]/60 tracking-[0.12em] block mb-6">
              INVESTIGATION SUMMARY
            </span>

            <div className="space-y-6">
              <div className="flex items-center justify-between py-4 border-b border-[#1a1f2e]">
                <span className="text-sm text-[#8A94A6]">Anomaly</span>
                <span className="text-sm font-mono text-[#F3F4F6]">#{anomaly.anomalyNumber}</span>
              </div>
              <div className="flex items-center justify-between py-4 border-b border-[#1a1f2e]">
                <span className="text-sm text-[#8A94A6]">Merchant</span>
                <span className="text-sm font-mono text-[#F3F4F6]">{anomaly.merchantName}</span>
              </div>
              <div className="flex items-center justify-between py-4 border-b border-[#1a1f2e]">
                <span className="text-sm text-[#8A94A6]">Date</span>
                <span className="text-sm font-mono text-[#F3F4F6]">{anomaly.dateFormatted}</span>
              </div>
              <div className="flex items-center justify-between py-4 border-b border-[#1a1f2e]">
                <span className="text-sm text-[#8A94A6]">Volume Multiple</span>
                <span className="text-sm font-mono" style={{ color: severityColors[anomaly.severity] }}>
                  {anomaly.volumeMultiple.toFixed(1)}×
                </span>
              </div>
              <div className="flex items-center justify-between py-4 border-b border-[#1a1f2e]">
                <span className="text-sm text-[#8A94A6]">Z-Score</span>
                <span className="text-sm font-mono text-[#F3F4F6]">{anomaly.zScore.toFixed(2)}</span>
              </div>
              <div className="flex items-center justify-between py-4">
                <span className="text-sm text-[#8A94A6]">Confidence Band</span>
                <div className="flex items-center gap-2">
                  <div className={`w-2 h-2 rounded-full ${
                    anomaly.confidenceBand === 'high_confidence' ? 'bg-[#34D399]' :
                    anomaly.confidenceBand === 'ambiguous' ? 'bg-[#FBBF24]' : 'bg-[#FF5C5C]'
                  }`} />
                  <span className="text-sm font-mono text-[#F3F4F6]">
                    {anomaly.confidenceBand === 'high_confidence' ? 'HIGH' :
                     anomaly.confidenceBand === 'ambiguous' ? 'AMBIGUOUS' : 'LOW'}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </motion.div>
    </section>
  );
}
