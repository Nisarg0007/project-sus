import { useState, useMemo } from 'react';
import { motion } from 'framer-motion';
import { investigationAnomalies, getMerchant001Timeline } from '../data/mockData';
import { InvestigationAnomaly, ActivityDataPoint } from '../types';
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
    </motion.div>
  );
}
