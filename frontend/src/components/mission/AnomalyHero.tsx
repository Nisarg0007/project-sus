import { motion } from 'framer-motion';
import { InvestigationAnomaly } from '../../types';
import { investigationAnomalies } from '../../data/mockData';

interface AnomalyHeroProps {
  anomaly: InvestigationAnomaly;
  onSelectAnomaly: (anomaly: InvestigationAnomaly) => void;
}

export function AnomalyHero({ anomaly, onSelectAnomaly }: AnomalyHeroProps) {
  const severityColors = {
    critical: '#FF5C5C',
    high: '#FBBF24',
    medium: '#38BDF8',
    low: '#34D399',
  };

  return (
    <section className="relative py-12 lg:py-16 px-[var(--content-px)] max-w-[var(--content-max)] mx-auto">
      {/* Background accent */}
      <div 
        className="absolute top-0 left-0 w-full h-full opacity-5"
        style={{
          background: `radial-gradient(ellipse at 30% 20%, ${severityColors[anomaly.severity]} 0%, transparent 50%)`,
        }}
      />

      <div className="relative grid grid-cols-1 lg:grid-cols-12 gap-12 items-start">
        {/* Left: Investigation Label + Main Narrative */}
        <div className="lg:col-span-7">
          {/* Investigation label */}
          <motion.div 
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="flex items-center gap-4 mb-8"
          >
            <span className="text-[11px] font-mono text-[#8A94A6]/60 tracking-[0.12em]">
              MISSION / LIVE INVESTIGATION
            </span>
            <div className="h-px flex-1 bg-[#1a1f2e]" />
          </motion.div>

          {/* Anomaly number */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.1 }}
          >
            <span className="text-sm font-mono text-[#8A94A6] tracking-widest">
              ANOMALY {anomaly.anomalyNumber}
            </span>
          </motion.div>

          {/* Main narrative */}
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="text-4xl lg:text-5xl font-light mt-6 mb-8 leading-tight"
          >
            <span className="text-[#F3F4F6]">
              {anomaly.merchantName} experienced
            </span>
            <br />
            <span className="text-[#F3F4F6]">
              an unusual{' '}
              <span className="font-medium" style={{ color: severityColors[anomaly.severity] }}>
                transaction surge.
              </span>
            </span>
          </motion.h1>

          {/* Volume multiple */}
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.7, delay: 0.3 }}
            className="flex items-end gap-6 mb-8"
          >
            <span 
              className="text-7xl lg:text-8xl font-light tracking-tight"
              style={{ color: severityColors[anomaly.severity] }}
            >
              {anomaly.volumeMultiple.toFixed(1)}×
            </span>
            <div className="pb-3">
              <span className="text-sm font-mono text-[#8A94A6] tracking-wider block">
                ABOVE HISTORICAL BASELINE
              </span>
              <span className="text-sm font-mono text-[#8A94A6]">
                {anomaly.dateFormatted}
              </span>
            </div>
          </motion.div>

          {/* Summary text */}
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.5, delay: 0.5 }}
            className="text-[#8A94A6] text-base leading-relaxed max-w-xl"
          >
            {anomaly.anomalySummary}
          </motion.p>
        </div>

        {/* Right: Classification */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6, delay: 0.4 }}
          className="lg:col-span-5"
        >
          <div className="border border-[#1a1f2e] rounded-sm p-8 bg-[#0D111A]/50">
            <span className="text-[11px] font-mono text-[#8A94A6]/60 tracking-[0.12em] block mb-6">
              CLASSIFICATION
            </span>
            
            {/* Status */}
            <div className="mb-8">
              <span 
                className="text-2xl font-medium tracking-wide"
                style={{ color: severityColors[anomaly.severity] }}
              >
                {anomaly.status === 'fraud_spike' ? 'FRAUD SPIKE' : 
                 anomaly.status === 'organic_spike' ? 'ORGANIC SPIKE' : 'REVIEW REQUIRED'}
              </span>
            </div>

            {/* Fraud Probability - dominant visual */}
            <div className="mb-8">
              <div className="flex items-baseline gap-2">
                <span 
                  className="text-6xl font-light"
                  style={{ color: severityColors[anomaly.severity] }}
                >
                  {(anomaly.fraudProbability * 100).toFixed(1)}
                </span>
                <span 
                  className="text-2xl"
                  style={{ color: severityColors[anomaly.severity] }}
                >
                  %
                </span>
              </div>
              <span className="text-xs font-mono text-[#8A94A6] tracking-wider">
                FRAUD LIKELIHOOD
              </span>
            </div>

            {/* Confidence */}
            <div className="flex items-center gap-3 pt-6 border-t border-[#1a1f2e]">
              <div className={`w-2 h-2 rounded-full ${
                anomaly.confidenceBand === 'high_confidence' ? 'bg-[#34D399]' :
                anomaly.confidenceBand === 'ambiguous' ? 'bg-[#FBBF24]' : 'bg-[#FF5C5C]'
              }`} />
              <span className="text-xs font-mono text-[#8A94A6] tracking-wider">
                {anomaly.confidenceBand === 'high_confidence' ? 'HIGH CONFIDENCE' :
                 anomaly.confidenceBand === 'ambiguous' ? 'AMBIGUOUS' : 'LOW CONFIDENCE'}
              </span>
              <span className="text-sm text-[#F3F4F6] ml-auto">
                {(anomaly.confidence * 100).toFixed(1)}%
              </span>
            </div>
          </div>

          {/* Anomaly selector */}
          <div className="mt-6">
            <span className="text-[11px] font-mono text-[#8A94A6]/60 tracking-[0.12em] block mb-3">
              SELECT ANOMALY
            </span>
            <div className="flex gap-2">
              {['024', '018', '015'].map((num, idx) => (
                <button
                  key={num}
                  onClick={() => onSelectAnomaly(investigationAnomalies[idx])}
                  className={`px-4 py-2 text-xs font-mono rounded-sm transition-all ${
                    anomaly.anomalyNumber === num
                      ? 'bg-[#1a1f2e] text-[#F3F4F6]'
                      : 'text-[#8A94A6] hover:text-[#F3F4F6] hover:bg-[#0D111A]'
                  }`}
                >
                  #{num}
                </button>
              ))}
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
