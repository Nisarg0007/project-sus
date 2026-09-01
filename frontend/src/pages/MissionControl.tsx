import { useState, useMemo, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { investigationAnomalies, getMerchant001Timeline } from '../data/mockData';
import { InvestigationAnomaly, ActivityDataPoint } from '../types';
import { useInvestigation } from '../context/InvestigationContext';
import { dataSource } from '../data/dataSource';
import type { InvestigationHistoryItem } from '../api/mappers/investigationHistoryMapper';
import { ProductHero } from '../components/mission/ProductHero';
import { ActivityVisualization } from '../components/mission/ActivityVisualization';
import { FindingsSection } from '../components/mission/FindingsSection';
import { InvestigationFlow } from '../components/mission/InvestigationFlow';
import { EvidenceBlocks } from '../components/mission/EvidenceBlocks';
import { ClassifierReasoning } from '../components/mission/ClassifierReasoning';
import { FinalVerdict } from '../components/mission/FinalVerdict';
import { RunInvestigationPanel } from '../components/mission/RunInvestigationPanel';

export default function MissionControl() {
  const navigate = useNavigate();
  const [selectedAnomaly, setSelectedAnomaly] = useState<InvestigationAnomaly>(
    investigationAnomalies[0]
  );
  const { result } = useInvestigation();
  const [historyItems, setHistoryItems] = useState<InvestigationHistoryItem[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  const timelineData = useMemo(() => getMerchant001Timeline(), []);

  // Load investigation history on mount
  const loadHistory = useCallback(async () => {
    setHistoryLoading(true);
    try {
      const history = await dataSource.getInvestigationHistory(5, 0);
      setHistoryItems(history.items);
    } catch {
      // Silently fail — history is supplementary
    } finally {
      setHistoryLoading(false);
    }
  }, []);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  // Reload history after a new investigation completes
  useEffect(() => {
    if (result) {
      loadHistory();
    }
  }, [result, loadHistory]);

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

      {/* Run Investigation Panel — upload or default dataset */}
      <div className="px-[var(--content-px)] max-w-[var(--content-max)] mx-auto pb-8">
        <div className="border-t border-[#1a1f2e]/60 pt-6">
          <RunInvestigationPanel />
        </div>
      </div>

      {/* Investigation History — persisted runs */}
      {historyItems.length > 0 && (
        <div className="px-[var(--content-px)] max-w-[var(--content-max)] mx-auto pb-12">
          <div className="border-t border-[#1a1f2e]/60 pt-8">
            <div className="flex items-baseline gap-3 mb-4">
              <h3 className="text-[11px] font-mono tracking-[0.2em] uppercase text-[#8A94A6]">
                Recent Investigations
              </h3>
              {historyLoading && (
                <span className="text-[10px] font-mono text-[#38BDF8]/50">loading...</span>
              )}
              <button
                onClick={() => navigate('/investigations')}
                className="ml-auto text-[10px] font-mono text-[#8A94A6] hover:text-[#38BDF8] transition-colors"
              >
                VIEW ALL →
              </button>
            </div>
            <div className="space-y-2">
              {historyItems.map((item) => (
                <motion.div
                  key={item.investigationId}
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3 }}
                  onClick={() => navigate(`/investigations/${item.investigationId}`)}
                  className="flex items-center gap-6 py-3 px-4 border border-[#1E293B]/60 bg-[#0B0F18]/60 hover:border-[#38BDF8]/20 hover:bg-[#0D111A]/80 cursor-pointer transition-all duration-200"
                >
                  <span className="text-[10px] font-mono text-[#38BDF8] tracking-wider shrink-0">
                    {item.investigationId}
                  </span>
                  <span className="text-[10px] font-mono text-[#8A94A6] shrink-0">
                    {item.createdAtFormatted}
                  </span>
                  <div className="flex items-center gap-4 text-[10px] font-mono">
                    <span className="text-[#8A94A6]">
                      {item.totalResults} windows
                    </span>
                    <span className="text-[#FF5C5C]">
                      {item.fraudIncidents} fraud
                    </span>
                    <span className="text-[#34D399]">
                      {item.organicIncidents} organic
                    </span>
                    <span className="text-[#FBBF24]">
                      {item.reviewRequired} review
                    </span>
                  </div>
                  <span className="text-[10px] font-mono text-[#8A94A6] ml-auto">
                    {item.status}
                  </span>
                </motion.div>
              ))}
            </div>
          </div>
        </div>
      )}
    </motion.div>
  );
}
