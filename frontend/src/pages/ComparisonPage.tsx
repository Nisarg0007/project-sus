/**
 * Investigation Comparison Page
 *
 * Compares two persisted investigations side by side.
 * URL state: base_id, compare_id
 * Data flow: URL params → dataSource.compareInvestigations() → UI
 */

import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowLeft, ArrowRight, Search, AlertTriangle, Minus, Plus } from 'lucide-react';
import { dataSource } from '../data/dataSource';
import type { BackendComparisonResponse } from '../api/investigations';

// ---------------------------------------------------------------------------
// Visual config
// ---------------------------------------------------------------------------

const changeColor = (val: number) => {
  if (val > 0) return '#34D399';
  if (val < 0) return '#FF5C5C';
  return '#8A94A6';
};

const changeIcon = (val: number) => {
  if (val > 0) return <Plus className="w-3 h-3" />;
  if (val < 0) return <Minus className="w-3 h-3" />;
  return null;
};

const formatPct = (pct: number | null) => {
  if (pct === null) return '—';
  const sign = pct > 0 ? '+' : '';
  return `${sign}${pct.toFixed(1)}%`;
};

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function ComparisonPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const baseId = searchParams.get('base_id') ?? '';
  const compareId = searchParams.get('compare_id') ?? '';

  const [data, setData] = useState<BackendComparisonResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const validParams = baseId && compareId && baseId !== compareId;

  useEffect(() => {
    if (!validParams) {
      setLoading(false);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);
    setData(null);

    dataSource.compareInvestigations(baseId, compareId).then((result) => {
      if (cancelled) return;
      if (result === null) {
        setError('One or both investigations could not be found.');
      } else {
        setData(result);
      }
      setLoading(false);
    });

    return () => { cancelled = true; };
  }, [baseId, compareId, validParams]);

  // --- Invalid params state ---
  if (!validParams) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="px-[var(--content-px)] max-w-[var(--content-max)] mx-auto pt-8 pb-24"
      >      <BackButton onClick={() => navigate('/investigations')} />
      <div className="mt-16 flex flex-col items-center gap-4 text-center">
          <div className="w-12 h-12 rounded-full bg-[#1E293B]/60 flex items-center justify-center">
            <Search className="w-5 h-5 text-[#8A94A6]" />
          </div>
          <h2 className="text-lg font-medium text-[#F3F4F6]">Invalid comparison</h2>
          <p className="text-sm text-[#8A94A6] max-w-md">
            Select two different investigation IDs from the history to compare their results.
          </p>
          <button
            onClick={() => navigate('/investigations')}
            className="mt-2 px-4 py-2 text-xs font-mono tracking-wider text-[#38BDF8] bg-[#38BDF8]/8 hover:bg-[#38BDF8]/15 transition-colors"
          >
            VIEW INVESTIGATION HISTORY
          </button>
        </div>
      </motion.div>
    );
  }

  // --- Loading state ---
  if (loading) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="px-[var(--content-px)] max-w-[var(--content-max)] mx-auto pt-8 pb-24"
      >
        <BackButton onClick={() => navigate('/investigations')} />
        <div className="mt-12 flex flex-col items-center gap-4">
          <div className="w-5 h-5 border-2 border-[#38BDF8]/30 border-t-[#38BDF8] rounded-full animate-spin" />
          <span className="text-xs font-mono text-[#8A94A6]">Comparing investigations...</span>
        </div>
      </motion.div>
    );
  }

  // --- Error state ---
  if (error || !data) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="px-[var(--content-px)] max-w-[var(--content-max)] mx-auto pt-8 pb-24"
      >
        <BackButton onClick={() => navigate('/investigations')} />
        <div className="mt-16 flex flex-col items-center gap-4 text-center">
          <div className="w-12 h-12 rounded-full bg-[#1E293B]/60 flex items-center justify-center">
            <AlertTriangle className="w-5 h-5 text-[#FBBF24]" />
          </div>
          <h2 className="text-lg font-medium text-[#F3F4F6]">Comparison failed</h2>
          <p className="text-sm text-[#8A94A6] max-w-md">
            {error ?? 'Could not load comparison data.'}
            {dataSource.getMode() === 'mock' && (
              <span className="block mt-2 text-xs text-[#8A94A6]/60">
                Comparison is only available in API mode.
              </span>
            )}
          </p>
          <button
            onClick={() => navigate('/investigations')}
            className="mt-2 px-4 py-2 text-xs font-mono tracking-wider text-[#38BDF8] bg-[#38BDF8]/8 hover:bg-[#38BDF8]/15 rounded-sm transition-colors"
          >
            GO TO INVESTIGATIONS
          </button>
        </div>
      </motion.div>
    );
  }

  // --- Comparison view ---
  const inc = data.incidents;
  const totalChanges = inc.changed.length;
  const hasIncidentChanges = inc.only_in_base.length + inc.only_in_compare.length + totalChanges > 0;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.4 }}
      className="px-[var(--content-px)] max-w-[var(--content-max)] mx-auto pt-8 pb-24"
    >
      {/* Back navigation */}
      <BackButton onClick={() => navigate('/investigations')} />

      {/* Header */}
      <div className="mt-8 mb-2">
        <span className="text-[10px] font-mono tracking-[0.2em] uppercase text-[#8A94A6]">
          INVESTIGATION COMPARISON
        </span>
        <h1 className="text-2xl font-medium text-[#F3F4F6] tracking-tight mt-2 mb-1">
          Comparison Results
        </h1>
        <div className="flex items-center gap-3 text-[11px] font-mono mt-3">
          <span className="text-[#38BDF8]">{data.base.investigation_id}</span>
          <ArrowRight className="w-3.5 h-3.5 text-[#8A94A6]" />
          <span className="text-[#34D399]">{data.compare.investigation_id}</span>
        </div>
      </div>

      <div className="h-px bg-[#1a1f2e]/60 my-6" />

      {/* Summary comparison */}
      <section className="mb-10">
        <SectionLabel text="SUMMARY CHANGES" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {Object.values(data.summary).map((m) => (
            <MetricRow key={m.label} metric={m} />
          ))}
        </div>
      </section>

      {/* Incident comparison */}
      <section>
        <SectionLabel text="INCIDENT CHANGES" />

        {!hasIncidentChanges && (
          <div className="bg-[#0D111A] border border-[#1a1f2e]/60 rounded-sm p-8 text-center">
            <p className="text-sm text-[#8A94A6]/60 font-mono">
              No incident differences detected.
            </p>
            <p className="text-[10px] text-[#8A94A6]/40 font-mono mt-2">
              Both investigations produced the same incident set.
            </p>
          </div>
        )}

        {/* New incidents */}
        {inc.only_in_compare.length > 0 && (
          <div className="mb-4">
            <h4 className="text-[10px] font-mono tracking-wider text-[#34D399] mb-2">
              NEW INCIDENTS ({inc.only_in_compare.length})
            </h4>
            <div className="space-y-1">
              {inc.only_in_compare.map((id) => (
                <div key={id} className="flex items-center gap-3 px-4 py-2 bg-[#34D399]/5 border border-[#34D399]/20 text-[11px] font-mono">
                  <Plus className="w-3 h-3 text-[#34D399]" />
                  <span className="text-[#34D399]">{id}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Removed incidents */}
        {inc.only_in_base.length > 0 && (
          <div className="mb-4">
            <h4 className="text-[10px] font-mono tracking-wider text-[#FF5C5C] mb-2">
              REMOVED INCIDENTS ({inc.only_in_base.length})
            </h4>
            <div className="space-y-1">
              {inc.only_in_base.map((id) => (
                <div key={id} className="flex items-center gap-3 px-4 py-2 bg-[#FF5C5C]/5 border border-[#FF5C5C]/20 text-[11px] font-mono">
                  <Minus className="w-3 h-3 text-[#FF5C5C]" />
                  <span className="text-[#FF5C5C]">{id}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Changed incidents */}
        {inc.changed.length > 0 && (
          <div className="mb-4">
            <h4 className="text-[10px] font-mono tracking-wider text-[#FBBF24] mb-2">
              CHANGED INCIDENTS ({inc.changed.length})
            </h4>
            <div className="space-y-2">
              {inc.changed.map((ch) => (
                <IncidentChangeRow key={ch.incident_id} change={ch} />
              ))}
            </div>
          </div>
        )}

        {/* Unchanged count */}
        {inc.unchanged_count > 0 && (
          <p className="text-[10px] font-mono text-[#8A94A6]/50 mt-3">
            {inc.unchanged_count} incident{inc.unchanged_count !== 1 ? 's' : ''} unchanged
          </p>
        )}
      </section>
    </motion.div>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function BackButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="flex items-center gap-2 text-[11px] font-mono text-[#8A94A6] hover:text-[#38BDF8] transition-colors duration-200"
    >
      <ArrowLeft className="w-3.5 h-3.5" />
      INVESTIGATIONS
    </button>
  );
}

function SectionLabel({ text }: { text: string }) {
  return (
    <h3 className="text-[10px] font-mono tracking-[0.2em] uppercase text-[#8A94A6] mb-3">
      {text}
    </h3>
  );
}

function MetricRow({ metric }: { metric: BackendComparisonResponse['summary']['total_results'] }) {
  const color = changeColor(metric.absolute_change);
  const isRate = metric.label === 'Spike Rate';
  const fmt = (v: number) => isRate ? `${(v * 100).toFixed(1)}%` : v.toLocaleString();

  return (
    <div className="bg-[#0D111A] border border-[#1a1f2e]/60 rounded-sm px-4 py-3">
      <div className="text-[9px] font-mono text-[#8A94A6] tracking-wider mb-2">
        {metric.label.toUpperCase()}
      </div>
      <div className="flex items-baseline gap-3">
        <span className="text-sm font-mono text-[#F3F4F6]">{fmt(metric.base_value)}</span>
        <ArrowRight className="w-3 h-3 text-[#8A94A6]" />
        <span className="text-sm font-mono" style={{ color }}>{fmt(metric.compare_value)}</span>
      </div>
      <div className="flex items-center gap-1.5 mt-1.5">
        {changeIcon(metric.absolute_change)}
        <span className="text-[10px] font-mono" style={{ color }}>
          {isRate
            ? `${metric.absolute_change > 0 ? '+' : ''}${(metric.absolute_change * 100).toFixed(1)}pp`
            : `${metric.absolute_change > 0 ? '+' : ''}${metric.absolute_change}`}
        </span>
        <span className="text-[9px] font-mono text-[#8A94A6]/50">
          ({formatPct(metric.percentage_change)})
        </span>
      </div>
    </div>
  );
}

function IncidentChangeRow({ change }: { change: BackendComparisonResponse['incidents']['changed'][number] }) {
  const fields: { label: string; changed: boolean; old: string | null; new_: string | null }[] = [
    { label: 'Severity', changed: change.severity_changed, old: change.old_severity, new_: change.new_severity },
    { label: 'Classification', changed: change.classification_changed, old: change.old_classification, new_: change.new_classification },
    { label: 'Fraud Prob', changed: change.fraud_probability_changed, old: change.old_fraud_probability !== null ? `${(change.old_fraud_probability * 100).toFixed(1)}%` : null, new_: change.new_fraud_probability !== null ? `${(change.new_fraud_probability * 100).toFixed(1)}%` : null },
    { label: 'Confidence', changed: change.confidence_changed, old: change.old_confidence !== null ? `${(change.old_confidence * 100).toFixed(1)}%` : null, new_: change.new_confidence !== null ? `${(change.new_confidence * 100).toFixed(1)}%` : null },
    { label: 'Anomaly Score', changed: change.anomaly_score_changed, old: change.old_anomaly_score?.toFixed(2) ?? null, new_: change.new_anomaly_score?.toFixed(2) ?? null },
    { label: 'Predicted Cause', changed: change.predicted_cause_changed, old: change.old_predicted_cause, new_: change.new_predicted_cause },
  ].filter((f) => f.changed);

  return (
    <div className="bg-[#0D111A] border border-[#1a1f2e]/60 rounded-sm overflow-hidden">
      <div className="flex items-center gap-4 px-4 py-2.5 border-b border-[#1a1f2e]/40">
        <span className="text-[10px] font-mono text-[#38BDF8] tracking-wider">{change.incident_id}</span>
        <span className="text-[10px] font-mono text-[#8A94A6]">{change.merchant_id}</span>
      </div>
      <div className="px-4 py-2 space-y-1">
        {fields.map((f) => (
          <div key={f.label} className="flex items-center gap-3 text-[10px] font-mono">
            <span className="text-[#8A94A6] w-28 shrink-0">{f.label}</span>
            <span className="text-[#FF5C5C] line-through opacity-60">{f.old ?? '—'}</span>
            <ArrowRight className="w-2.5 h-2.5 text-[#8A94A6]" />
            <span className="text-[#34D399]">{f.new_ ?? '—'}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
