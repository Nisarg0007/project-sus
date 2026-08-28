/**
 * Investigation Detail Page
 *
 * Displays a persisted investigation's full results: header, summary,
 * configuration, processing note, and all associated incidents.
 *
 * Data flow: URL param → dataSource.getInvestigationById() → mapper → UI
 */

import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowLeft, FileText } from 'lucide-react';
import { dataSource } from '../data/dataSource';
import type { InvestigationHistoryDetail } from '../api/mappers/investigationHistoryMapper';
import type { FullIncident } from '../types';

// ---------------------------------------------------------------------------
// Severity / classification visual config
// ---------------------------------------------------------------------------

const severityColors: Record<string, string> = {
  critical: '#FF5C5C',
  high: '#F97316',
  medium: '#FBBF24',
  low: '#8A94A6',
};

const classificationColors: Record<string, string> = {
  fraud_spike: '#FF5C5C',
  organic_spike: '#34D399',
  review_required: '#FBBF24',
  baseline: '#8A94A6',
};

const classificationLabels: Record<string, string> = {
  fraud_spike: 'FRAUD',
  organic_spike: 'ORGANIC',
  review_required: 'REVIEW',
  baseline: 'BASELINE',
};

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function InvestigationDetailPage() {
  const { investigationId } = useParams<{ investigationId: string }>();
  const navigate = useNavigate();
  const [detail, setDetail] = useState<InvestigationHistoryDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    if (!investigationId) return;

    let cancelled = false;
    setLoading(true);
    setNotFound(false);
    setDetail(null);

    dataSource.getInvestigationById(investigationId).then((result) => {
      if (cancelled) return;
      if (result === null) {
        setNotFound(true);
      } else {
        setDetail(result);
      }
      setLoading(false);
    });

    return () => { cancelled = true; };
  }, [investigationId]);

  // --- Loading state ---
  if (loading) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.3 }}
        className="px-[var(--content-px)] max-w-[var(--content-max)] mx-auto pt-8 pb-24"
      >
        <BackButton onClick={() => navigate('/')} />
        <div className="mt-12 flex flex-col items-center gap-4">
          <div className="w-5 h-5 border-2 border-[#38BDF8]/30 border-t-[#38BDF8] rounded-full animate-spin" />
          <span className="text-xs font-mono text-[#8A94A6]">Loading investigation...</span>
        </div>
      </motion.div>
    );
  }

  // --- Not found state ---
  if (notFound || !detail) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.3 }}
        className="px-[var(--content-px)] max-w-[var(--content-max)] mx-auto pt-8 pb-24"
      >
        <BackButton onClick={() => navigate('/')} />
        <div className="mt-16 flex flex-col items-center gap-4 text-center">
          <div className="w-12 h-12 rounded-full bg-[#1E293B]/60 flex items-center justify-center">
            <FileText className="w-5 h-5 text-[#8A94A6]" />
          </div>
          <h2 className="text-lg font-medium text-[#F3F4F6]">Investigation not found</h2>
          <p className="text-sm text-[#8A94A6] max-w-md">
            The investigation <span className="font-mono text-[#38BDF8]">{investigationId}</span> could not be found.
            {dataSource.getMode() === 'mock' && (
              <span className="block mt-2 text-xs text-[#8A94A6]/60">
                Persisted investigations are only available in API mode.
              </span>
            )}
          </p>
          <button
            onClick={() => navigate('/')}
            className="mt-4 px-4 py-2 text-xs font-mono tracking-wider text-[#38BDF8] bg-[#38BDF8]/8 hover:bg-[#38BDF8]/15 rounded-sm transition-colors"
          >
            RETURN TO MISSION CONTROL
          </button>
        </div>
      </motion.div>
    );
  }

  // --- Detail view ---
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.4 }}
      className="px-[var(--content-px)] max-w-[var(--content-max)] mx-auto pt-8 pb-24"
    >
      {/* Back navigation */}
      <BackButton onClick={() => navigate('/')} />

      {/* Investigation header */}
      <div className="mt-8 mb-8">
        <div className="flex items-center gap-3 mb-2">
          <span className="text-[10px] font-mono tracking-[0.2em] uppercase text-[#8A94A6]">
            INVESTIGATION
          </span>
          <span className="px-2 py-0.5 text-[10px] font-mono tracking-wider uppercase bg-[#38BDF8]/10 text-[#38BDF8] rounded-sm">
            {detail.status}
          </span>
        </div>
        <h1 className="text-2xl font-mono font-medium text-[#F3F4F6] tracking-tight mb-1">
          {detail.investigationId}
        </h1>
        <p className="text-sm text-[#8A94A6]">
          {detail.createdAtFormatted}
        </p>
      </div>

      {/* Divider */}
      <div className="h-px bg-[#1a1f2e]/60 mb-8" />

      {/* Summary grid */}
      <section className="mb-10">
        <SectionLabel text="SUMMARY" />
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
          <StatCard label="Total Windows" value={detail.summary.totalWindows} />
          <StatCard label="Spikes Detected" value={detail.summary.spikesDetected} color="#38BDF8" />
          <StatCard label="Fraud Incidents" value={detail.summary.fraudIncidents} color="#FF5C5C" />
          <StatCard label="Organic Incidents" value={detail.summary.organicIncidents} color="#34D399" />
          <StatCard label="Review Required" value={detail.summary.reviewRequired} color="#FBBF24" />
          <StatCard label="Baseline Windows" value={detail.summary.baselineWindows} />
          <StatCard label="Spike Rate" value={`${(detail.summary.spikeRate * 100).toFixed(1)}%`} color="#38BDF8" />
        </div>
      </section>

      {/* Configuration */}
      <section className="mb-10">
        <SectionLabel text="CONFIGURATION" />
        <div className="bg-[#0D111A] border border-[#1a1f2e]/60 rounded-sm p-5">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-3">
            <ConfigRow label="Z Threshold" value={detail.zThreshold.toFixed(2)} />
            <ConfigRow label="Min History Days" value={String(detail.minHistoryDays)} />
            {detail.merchantFilter && (
              <ConfigRow label="Merchant Filter" value={detail.merchantFilter} />
            )}
            {detail.modelPath && (
              <ConfigRow label="Model Path" value={detail.modelPath} />
            )}
            <ConfigRow label="Transactions" value={detail.transactionsPath} mono />
            <ConfigRow label="Window Labels" value={detail.windowLabelsPath} mono />
          </div>
        </div>
      </section>

      {/* Divider */}
      <div className="h-px bg-[#1a1f2e]/60 mb-8" />

      {/* Incidents */}
      <section>
        <div className="flex items-baseline gap-3 mb-4">
          <SectionLabel text="INCIDENTS" />
          <span className="text-[10px] font-mono text-[#8A94A6]/60">
            {detail.incidents.length} total
          </span>
        </div>

        {detail.incidents.length === 0 ? (
          <div className="bg-[#0D111A] border border-[#1a1f2e]/60 rounded-sm p-8 text-center">
            <p className="text-sm text-[#8A94A6]/60 font-mono">
              No incidents generated by this investigation.
            </p>
            <p className="text-[10px] text-[#8A94A6]/40 font-mono mt-2">
              All merchant-day windows were classified as baseline.
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {detail.incidents.map((inc) => (
              <IncidentCard key={inc.id} incident={inc} />
            ))}
          </div>
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
      MISSION CONTROL
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

function StatCard({
  label,
  value,
  color = '#F3F4F6',
}: {
  label: string;
  value: number | string;
  color?: string;
}) {
  return (
    <div className="bg-[#0D111A] border border-[#1a1f2e]/60 rounded-sm px-4 py-3">
      <div className="text-[10px] font-mono text-[#8A94A6] tracking-wider mb-1">
        {label.toUpperCase()}
      </div>
      <div className="text-lg font-mono font-medium" style={{ color }}>
        {typeof value === 'number' ? value.toLocaleString() : value}
      </div>
    </div>
  );
}

function ConfigRow({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div className="flex items-baseline justify-between gap-4">
      <span className="text-[10px] font-mono text-[#8A94A6] tracking-wider shrink-0">
        {label.toUpperCase()}
      </span>
      <span className={`text-xs text-[#F3F4F6] text-right truncate ${mono ? 'font-mono text-[10px] text-[#8A94A6]' : ''}`}>
        {value}
      </span>
    </div>
  );
}

function IncidentCard({ incident }: { incident: FullIncident }) {
  const sevColor = severityColors[incident.severity] ?? '#8A94A6';
  const clsColor = classificationColors[incident.predictedCause] ?? '#8A94A6';
  const clsLabel = classificationLabels[incident.predictedCause] ?? incident.predictedCause;

  return (
    <motion.div
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className="bg-[#0D111A] border border-[#1a1f2e]/60 rounded-sm overflow-hidden hover:border-[#2a3040] transition-colors duration-200"
    >
      {/* Incident header */}
      <div className="flex items-center gap-4 px-5 py-3 border-b border-[#1a1f2e]/40">
        <span className="text-[10px] font-mono text-[#38BDF8] tracking-wider">
          {incident.id}
        </span>
        <span className="text-[10px] font-mono text-[#8A94A6]">
          {incident.merchantId}
        </span>
        <span className="text-[10px] font-mono text-[#8A94A6]">
          {incident.date}
        </span>
        <div className="ml-auto flex items-center gap-3">
          <span
            className="text-[10px] font-mono tracking-wider px-1.5 py-0.5 rounded-sm"
            style={{ color: sevColor, backgroundColor: `${sevColor}15` }}
          >
            {incident.severity.toUpperCase()}
          </span>
          <span
            className="text-[10px] font-mono tracking-wider px-1.5 py-0.5 rounded-sm"
            style={{ color: clsColor, backgroundColor: `${clsColor}15` }}
          >
            {clsLabel}
          </span>
        </div>
      </div>

      {/* Incident body */}
      <div className="px-5 py-4">
        {/* Key metrics row */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-4">
          <MetricItem label="Fraud Probability" value={`${(incident.fraudProbability * 100).toFixed(1)}%`} color={clsColor} />
          <MetricItem label="Confidence" value={`${(incident.confidence * 100).toFixed(1)}%`} />
          <MetricItem label="Anomaly Score" value={incident.anomalyScore.toFixed(2)} />
          {incident.predictedCause && (
            <MetricItem label="Predicted Cause" value={incident.predictedCause.replace('_', ' ')} />
          )}
        </div>

        {/* Summary */}
        {(incident.headline || incident.summary) && (
          <div className="mb-4">
            <div className="text-[10px] font-mono text-[#8A94A6] tracking-wider mb-1">
              SUMMARY
            </div>
            <p className="text-sm text-[#F3F4F6] leading-relaxed">
              {incident.headline || incident.summary}
            </p>
          </div>
        )}

        {/* Top signals */}
        {incident.topSignals.length > 0 && (
          <div className="mb-4">
            <div className="text-[10px] font-mono text-[#8A94A6] tracking-wider mb-2">
              TOP SIGNALS
            </div>
            <div className="flex flex-wrap gap-2">
              {incident.topSignals.map((signal, i) => (
                <span
                  key={i}
                  className="text-[10px] font-mono text-[#8A94A6] bg-[#1E293B]/40 border border-[#1a1f2e]/40 px-2 py-1 rounded-sm"
                >
                  {signal}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Recommended action */}
        {incident.recommendedAction && (
          <div className="bg-[#080B12] border border-[#1a1f2e]/40 rounded-sm px-4 py-3">
            <div className="text-[10px] font-mono text-[#8A94A6] tracking-wider mb-1">
              RECOMMENDED ACTION
            </div>
            <p className="text-xs text-[#F3F4F6]">
              {incident.recommendedAction}
            </p>
          </div>
        )}
      </div>
    </motion.div>
  );
}

function MetricItem({
  label,
  value,
  color = '#F3F4F6',
}: {
  label: string;
  value: string;
  color?: string;
}) {
  return (
    <div>
      <div className="text-[9px] font-mono text-[#8A94A6] tracking-wider mb-0.5">
        {label.toUpperCase()}
      </div>
      <div className="text-sm font-mono font-medium" style={{ color }}>
        {value}
      </div>
    </div>
  );
}
