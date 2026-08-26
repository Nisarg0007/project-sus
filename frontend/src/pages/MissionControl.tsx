import { useState, useMemo } from 'react';
import { motion } from 'framer-motion';
import { investigationAnomalies, getMerchant001Timeline } from '../data/mockData';
import { InvestigationAnomaly, ActivityDataPoint } from '../types';
import { useInvestigation } from '../context/InvestigationContext';
import { ProductHero } from '../components/mission/ProductHero';
import { ActivityVisualization } from '../components/mission/ActivityVisualization';
import { FindingsSection } from '../components/mission/FindingsSection';
import { InvestigationFlow } from '../components/mission/InvestigationFlow';
import { EvidenceBlocks } from '../components/mission/EvidenceBlocks';
import { ClassifierReasoning } from '../components/mission/ClassifierReasoning';
import { FinalVerdict } from '../components/mission/FinalVerdict';

export default function MissionControl() {
  const [selectedAnomaly, setSelectedAnomaly] = useState<InvestigationAnomaly>(
    investigationAnomalies[0]
  );
  const { isLoading, error, result, executeInvestigation } = useInvestigation();

  const timelineData = useMemo(() => getMerchant001Timeline(), []);

  const handleAnomalyClick = (point: ActivityDataPoint) => {
    if (point.anomalyId) {
      const anomaly = investigationAnomalies.find(a =>
        a.id.includes(point.date || '')
      );
      if (anomaly) {
        setSelectedAnomaly(anomaly);
      }
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5 }}
    >
      {/* Product Hero — tagline + key metrics */}
      <ProductHero />

      {/* Activity Visualization */}
      <div className="px-[var(--content-px)] max-w-[var(--content-max)] mx-auto py-4">
        <ActivityVisualization
          data={timelineData}
          selectedAnomalyId={selectedAnomaly.id}
          onAnomalyClick={handleAnomalyClick}
        />
      </div>

      {/* What SUS Found — 3 outcome cards */}
      <FindingsSection onSelectAnomaly={setSelectedAnomaly} />

      {/* Divider */}
      <div className="max-w-[var(--content-max)] mx-auto px-[var(--content-px)]">
        <div className="h-px bg-[#1a1f2e]/60" />
      </div>

      {/* Investigation Deep Dive — visible when an anomaly is selected */}
      <motion.div
        key={selectedAnomaly.id}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.4 }}
      >
        <InvestigationFlow anomaly={selectedAnomaly} />
        <EvidenceBlocks evidence={selectedAnomaly.behavioralEvidence} />
        <ClassifierReasoning
          contributions={selectedAnomaly.modelContributions}
          fraudProbability={selectedAnomaly.fraudProbability}
        />
        <FinalVerdict anomaly={selectedAnomaly} />
      </motion.div>

      {/* Footer spacer */}
      <div className="h-24" />

      {/* API Integration Trigger — minimal, unobtrusive */}
      <div className="px-[var(--content-px)] max-w-[var(--content-max)] mx-auto pb-8">
        <div className="border-t border-[#1a1f2e]/60 pt-6">
          <div className="flex items-center gap-4">
            <button
              onClick={() => executeInvestigation()}
              disabled={isLoading}
              className="px-4 py-2 text-xs font-mono tracking-wider uppercase bg-[#0F1623] border border-[#1E293B] text-[#8A94A6] hover:text-[#38BDF8] hover:border-[#38BDF8]/30 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? 'Running Investigation...' : 'Run Investigation'}
            </button>
            {result && (
              <span className="text-xs font-mono text-[#34D399]">
                {result.totalResults} windows analyzed — {result.fullIncidents.length} incidents found
              </span>
            )}
            {error && (
              <span className="text-xs font-mono text-[#FF5C5C]">
                {error}
              </span>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
}
