/**
 * Investigate Page
 *
 * Primary workspace for fraud/risk analysts.
 * Flow: Choose data → Configure → Run → See results → Act on incidents.
 */

import { useMemo, useEffect, useCallback, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { investigationAnomalies, getMerchant001Timeline } from '../data/mockData';
import { useInvestigation } from '../context/InvestigationContext';
import { dataSource } from '../data/dataSource';
import type { InvestigationHistoryItem } from '../api/mappers/investigationHistoryMapper';
import { RunInvestigationPanel } from '../components/mission/RunInvestigationPanel';
import { ActivityVisualization } from '../components/mission/ActivityVisualization';
import { ProductHero } from '../components/mission/ProductHero';
import { AlertTriangle, TrendingUp, Eye, ChevronRight, Clock } from 'lucide-react';

export default function MissionControl() {
  const navigate = useNavigate();
  const { result } = useInvestigation();
  const [historyItems, setHistoryItems] = useState<InvestigationHistoryItem[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  const timelineData = useMemo(() => getMerchant001Timeline(), []);

  const loadHistory = useCallback(async () => {
    setHistoryLoading(true);
    try {
      const history = await dataSource.getInvestigationHistory(3, 0);
      setHistoryItems(history.items);
    } catch {
      // Silently fail — history is supplementary
    } finally {
      setHistoryLoading(false);
    }
  }, []);

  useEffect(() => { loadHistory(); }, [loadHistory]);
  useEffect(() => { if (result) loadHistory(); }, [result, loadHistory]);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5 }}
    >
      {/* Hero */}
      <ProductHero />

      {/* Activity Visualization — compact */}
      <div className="px-[var(--content-px)] max-w-[var(--content-max)] mx-auto py-4">
        <ActivityVisualization
          data={timelineData}
          selectedAnomalyId={investigationAnomalies[0]?.id ?? ''}
          onAnomalyClick={() => {}}
        />
      </div>

      {/* Divider */}
      <div className="max-w-[var(--content-max)] mx-auto px-[var(--content-px)]">
        <div className="h-px bg-[#1a1f2e]/60" />
      </div>

      {/* Main content: Two columns */}
      <div className="px-[var(--content-px)] max-w-[var(--content-max)] mx-auto py-6">
        <div className="flex gap-8">
          {/* Left: Investigation Panel */}
          <div className="flex-1 min-w-0">
            <div className="mb-3">
              <h2 className="text-[11px] font-mono tracking-[0.2em] uppercase text-[#8A94A6]">
                New Investigation
              </h2>
              <p className="text-[10px] font-mono text-[#8A94A6]/50 mt-1">
                Upload transaction data or use the default dataset to identify unusual activity.
              </p>
            </div>
            <RunInvestigationPanel />
          </div>

          {/* Right: Results + Recent */}
          <div className="w-[360px] flex-shrink-0 hidden lg:block">
            {/* Results summary (when investigation completes) */}
            <AnimatePresence>
              {result && (
                <motion.div
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -8 }}
                  transition={{ duration: 0.3 }}
                  className="mb-6"
                >
                  <ResultsSummary result={result} onViewIncidents={() => navigate('/incidents')} />
                </motion.div>
              )}
            </AnimatePresence>

            {/* Recent Investigations */}
            <div>
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-[10px] font-mono tracking-[0.15em] uppercase text-[#8A94A6]">
                  Recent Investigations
                </h3>
                {historyItems.length > 0 && (
                  <button
                    onClick={() => navigate('/investigations')}
                    className="text-[9px] font-mono text-[#8A94A6]/50 hover:text-[#38BDF8] transition-colors flex items-center gap-1"
                  >
                    VIEW ALL <ChevronRight className="w-2.5 h-2.5" />
                  </button>
                )}
              </div>

              {historyLoading && (
                <div className="py-4 text-center">
                  <div className="w-4 h-4 border-2 border-[#38BDF8]/20 border-t-[#38BDF8] rounded-full animate-spin mx-auto" />
                </div>
              )}

              {!historyLoading && historyItems.length === 0 && (
                <div className="py-6 text-center border border-[#1a1f2e]/40">
                  <p className="text-[10px] font-mono text-[#8A94A6]/40">
                    No investigations yet. Run your first analysis above.
                  </p>
                </div>
              )}

              {!historyLoading && historyItems.length > 0 && (
                <div className="space-y-1.5">
                  {historyItems.map((item) => (
                    <motion.div
                      key={item.investigationId}
                      initial={{ opacity: 0, y: 4 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.2 }}
                      onClick={() => navigate(`/investigations/${item.investigationId}`)}
                      className="flex items-center gap-3 py-2.5 px-3 border border-[#1E293B]/60 bg-[#0B0F18]/60 hover:border-[#38BDF8]/20 hover:bg-[#0D111A]/80 cursor-pointer transition-all duration-200"
                    >
                      <div className="flex-1 min-w-0">
                        <p className="text-[10px] font-mono text-[#38BDF8] tracking-wider truncate">
                          {item.investigationId}
                        </p>
                        <div className="flex items-center gap-2 mt-0.5">
                          <span className="text-[9px] font-mono text-[#8A94A6]/50 flex items-center gap-1">
                            <Clock className="w-2.5 h-2.5" />
                            {item.createdAtFormatted}
                          </span>
                        </div>
                      </div>
                      <div className="flex items-center gap-2.5 text-[9px] font-mono shrink-0">
                        {item.fraudIncidents > 0 && (
                          <span className="text-[#FF5C5C]">{item.fraudIncidents} fraud</span>
                        )}
                        {item.organicIncidents > 0 && (
                          <span className="text-[#34D399]">{item.organicIncidents} organic</span>
                        )}
                        {item.reviewRequired > 0 && (
                          <span className="text-[#FBBF24]">{item.reviewRequired} review</span>
                        )}
                      </div>
                    </motion.div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Footer spacer */}
      <div className="h-16" />
    </motion.div>
  );
}

// ---------------------------------------------------------------------------
// Results Summary — shown after investigation completes
// ---------------------------------------------------------------------------

function ResultsSummary({
  result,
  onViewIncidents,
}: {
  result: { totalResults: number; fullIncidents: unknown[]; summary: { fraudIncidents: number; organicIncidents: number; reviewRequired: number; spikesDetected: number } };
  onViewIncidents: () => void;
}) {
  const s = result.summary;
  const hasIncidents = result.fullIncidents.length > 0;

  return (
    <div className="border border-[#1E293B]/60 bg-[#0B0F18]/80 p-4">
      <div className="flex items-center gap-2 mb-3">
        <div className="w-5 h-5 rounded-full bg-[#34D399]/10 flex items-center justify-center">
          <TrendingUp className="w-3 h-3 text-[#34D399]" />
        </div>
        <h3 className="text-[10px] font-mono tracking-[0.15em] uppercase text-[#8A94A6]">
          Investigation Complete
        </h3>
      </div>

      <div className="mb-3">
        <p className="text-lg font-mono font-medium text-[#F3F4F6]">
          {result.totalResults.toLocaleString()} windows analyzed
        </p>
      </div>

      <div className="grid grid-cols-3 gap-2 mb-4">
        <MetricPill
          label="Fraud"
          value={s.fraudIncidents}
          color="#FF5C5C"
          icon={<AlertTriangle className="w-3 h-3" />}
        />
        <MetricPill
          label="Organic"
          value={s.organicIncidents}
          color="#34D399"
          icon={<TrendingUp className="w-3 h-3" />}
        />
        <MetricPill
          label="Review"
          value={s.reviewRequired}
          color="#FBBF24"
          icon={<Eye className="w-3 h-3" />}
        />
      </div>

      {hasIncidents && (
        <button
          onClick={onViewIncidents}
          className="w-full flex items-center justify-center gap-2 py-2 text-[10px] font-mono tracking-wider text-[#38BDF8] bg-[#38BDF8]/8 hover:bg-[#38BDF8]/15 border border-[#38BDF8]/20 transition-all duration-200"
        >
          VIEW INCIDENTS
          <ChevronRight className="w-3 h-3" />
        </button>
      )}
    </div>
  );
}

function MetricPill({
  label,
  value,
  color,
  icon,
}: {
  label: string;
  value: number;
  color: string;
  icon: React.ReactNode;
}) {
  return (
    <div className="p-2 border border-[#1a1f2e]/40" style={{ borderColor: `${color}20` }}>
      <div className="flex items-center gap-1.5 mb-1">
        <span style={{ color }}>{icon}</span>
        <span className="text-[9px] font-mono text-[#8A94A6] tracking-wider">{label.toUpperCase()}</span>
      </div>
      <p className="text-base font-mono font-medium" style={{ color }}>
        {value}
      </p>
    </div>
  );
}
