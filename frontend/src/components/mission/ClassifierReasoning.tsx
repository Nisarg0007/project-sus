import { motion } from 'framer-motion';
import { ModelContribution } from '../../types';

interface ClassifierReasoningProps {
  contributions: ModelContribution[];
  fraudProbability: number;
}

export function ClassifierReasoning({ contributions, fraudProbability }: ClassifierReasoningProps) {
  // Split contributions by direction
  const fraudContributions = contributions
    .filter(c => c.direction === 'fraud')
    .sort((a, b) => b.contribution - a.contribution);
  
  const organicContributions = contributions
    .filter(c => c.direction === 'organic')
    .sort((a, b) => b.contribution - a.contribution);

  const maxContribution = Math.max(...contributions.map(c => Math.abs(c.contribution)));

  return (
    <section className="relative py-16 px-8 max-w-[1600px] mx-auto">
      <div className="flex items-center gap-4 mb-12">
        <span className="text-xs font-mono text-[#8A94A6] tracking-widest">
          CLASSIFIER REASONING
        </span>
        <div className="h-px flex-1 bg-[#1a1f2e]" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-12">
        {/* Left: Feature contributions */}
        <div className="space-y-12">
          {/* Fraud evidence */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5 }}
          >
            <h4 className="text-sm font-mono text-[#FF5C5C] tracking-widest mb-6">
              FRAUD EVIDENCE
            </h4>
            <div className="space-y-4">
              {fraudContributions.map((item, index) => (
                <div key={item.feature}>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-[#F3F4F6]">{item.label}</span>
                    <span className="text-xs font-mono text-[#8A94A6]">
                      {(item.contribution * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div className="h-1.5 bg-[#1a1f2e] rounded-full overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${(item.contribution / maxContribution) * 100}%` }}
                      transition={{ duration: 0.6, delay: index * 0.1 }}
                      className="h-full bg-[#FF5C5C] rounded-full"
                    />
                  </div>
                </div>
              ))}
            </div>
          </motion.div>

          {/* Organic evidence */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
          >
            <h4 className="text-sm font-mono text-[#34D399] tracking-widest mb-6">
              ORGANIC EVIDENCE
            </h4>
            <div className="space-y-4">
              {organicContributions.map((item, index) => (
                <div key={item.feature}>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-[#F3F4F6]">{item.label}</span>
                    <span className="text-xs font-mono text-[#8A94A6]">
                      {(item.contribution * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div className="h-1.5 bg-[#1a1f2e] rounded-full overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${(item.contribution / maxContribution) * 100}%` }}
                      transition={{ duration: 0.6, delay: 0.3 + index * 0.1 }}
                      className="h-full bg-[#34D399] rounded-full"
                    />
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        </div>

        {/* Right: Evidence scale */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.6, delay: 0.3 }}
          className="flex items-center justify-center"
        >
          <div className="w-full max-w-md">
            {/* Scale visualization */}
            <div className="relative mb-12">
              {/* Labels */}
              <div className="flex justify-between mb-4">
                <span className="text-xs font-mono text-[#34D399]">← ORGANIC</span>
                <span className="text-xs font-mono text-[#FF5C5C]">FRAUD →</span>
              </div>

              {/* Scale track */}
              <div className="relative h-1 bg-[#1a1f2e] rounded-full">
                {/* Center mark */}
                <div className="absolute left-1/2 -translate-x-1/2 -top-1 w-0.5 h-3 bg-[#8A94A6]" />
                
                {/* Indicator */}
                <motion.div
                  initial={{ left: '50%' }}
                  animate={{ left: `${fraudProbability * 100}%` }}
                  transition={{ duration: 0.8, ease: 'easeOut' }}
                  className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2"
                >
                  <div className="w-4 h-4 rounded-full bg-[#FF5C5C] border-2 border-[#080B12] shadow-lg" />
                </motion.div>
              </div>

              {/* Value */}
              <div className="text-center mt-8">
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5, delay: 0.5 }}
                >
                  <span className="text-5xl font-light text-[#FF5C5C]">
                    {(fraudProbability * 100).toFixed(1)}%
                  </span>
                  <div className="text-xs font-mono text-[#8A94A6] mt-2 tracking-widest">
                    FRAUD LIKELIHOOD
                  </div>
                </motion.div>
              </div>
            </div>

            {/* Model note */}
            <div className="border-t border-[#1a1f2e] pt-6 mt-8">
              <p className="text-xs text-[#8A94A6] leading-relaxed">
                Model signals derived from LogisticRegression coefficients.
                Contributions represent the relative influence of each behavioral feature
                on the classification decision.
              </p>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
