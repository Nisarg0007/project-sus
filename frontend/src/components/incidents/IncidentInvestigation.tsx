import { motion, AnimatePresence } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { FullIncident, BehavioralEvidence } from '../../types';
import { IncidentTimeline } from './IncidentTimeline';
import { RecommendedAction } from './RecommendedAction';
import { AlertTriangle, CheckCircle, HelpCircle, ExternalLink, ArrowRight } from 'lucide-react';
import { useNavigation } from '../../hooks/useNavigation';

interface IncidentInvestigationProps {
  incident: FullIncident | null;
}

const causeConfig: Record<string, { color: string; label: string; icon: React.ReactNode }> = {
  fraud_spike: { color: '#FF5C5C', label: 'FRAUD', icon: <AlertTriangle className="w-4 h-4" /> },
  organic_spike: { color: '#34D399', label: 'ORGANIC', icon: <CheckCircle className="w-4 h-4" /> },
  review_required: { color: '#FBBF24', label: 'REVIEW REQUIRED', icon: <HelpCircle className="w-4 h-4" /> },
};

const confidenceLabels: Record<string, string> = {
  high_confidence: 'High confidence',
  ambiguous: 'Ambiguous — needs review',
  low_confidence: 'Low confidence',
};

export function IncidentInvestigation({ incident }: IncidentInvestigationProps) {
  if (!incident) {
    return (
      <div className="flex items-center justify-center h-full min-h-[400px]">
        <div className="text-center">
          <p className="text-sm text-[#8A94A6]/60 font-mono">Select an incident to investigate</p>
          <p className="text-[10px] text-[#8A94A6]/40 font-mono mt-2">
            Click any item in the queue or priority strip
          </p>
        </div>
      </div>
    );
  }

  const cause = causeConfig[incident.predictedCause];
  const sortedContributions = [...incident.modelContributions].sort((a, b) => b.contribution - a.contribution);
  const maxContribution = Math.max(...sortedContributions.map(c => c.contribution));

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={incident.id}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -10 }}
        transition={{ duration: 0.3 }}
      >
        {/* Incident ID + Severity + Detail Link */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <span className="text-[10px] font-mono text-[#8A94A6]/60 tracking-wider">
              {incident.id}
            </span>
            <span
              className="text-[10px] font-mono tracking-wider px-2 py-0.5 rounded-sm"
              style={{ color: cause.color, backgroundColor: `${cause.color}12` }}
            >
              {incident.severity.toUpperCase()}
            </span>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-[10px] font-mono text-[#8A94A6] tracking-wider">
              {incident.dateFormatted}
            </span>
            <NavigateToDetailButton incidentId={incident.id} />
          </div>
        </div>

        {/* Merchant + Headline */}
        <div className="mb-8">
          <MerchantLink merchantId={incident.merchantId} merchantName={incident.merchantName} />
          <h2 className="text-xl sm:text-2xl font-light text-[#F3F4F6] leading-snug">
            &ldquo;{incident.headline}&rdquo;
          </h2>
        </div>

        {/* === A. WHAT CHANGED === */}
        <div className="mb-8">
          <div className="text-[10px] font-mono text-[#8A94A6] tracking-[0.15em] mb-3">
            WHAT CHANGED
          </div>
          <div className="h-px bg-[#1a1f2e] mb-4" />

          {/* Volume comparison */}
          <div className="bg-[#0D111A] border border-[#1a1f2e] rounded-sm p-4 mb-3">
            <div className="flex items-center justify-between mb-3">
              <span className="text-[10px] font-mono text-[#8A94A6] tracking-wider">TRANSACTION VOLUME</span>
              <span className="text-lg font-mono font-medium" style={{ color: cause.color }}>
                {incident.volumeMultiple.toFixed(1)}× baseline
              </span>
            </div>
            {/* Comparison bars */}
            <div className="space-y-2">
              <div>
                <div className="flex items-center justify-between text-[9px] font-mono text-[#8A94A6] mb-1">
                  <span>NORMAL</span>
                  <span>{incident.baselineVolume.toLocaleString()} txns</span>
                </div>
                <div className="h-1.5 bg-[#1a1f2e] rounded-full overflow-hidden">
                  <div className="h-full bg-[#8A94A6]/50 rounded-full" style={{ width: '42%' }} />
                </div>
              </div>
              <div>
                <div className="flex items-center justify-between text-[9px] font-mono mb-1" style={{ color: cause.color }}>
                  <span>CURRENT</span>
                  <span>{incident.transactionCount.toLocaleString()} txns</span>
                </div>
                <div className="h-1.5 bg-[#1a1f2e] rounded-full overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${Math.min(incident.volumeMultiple / 3 * 100, 100)}%` }}
                    transition={{ duration: 0.8, delay: 0.2 }}
                    className="h-full rounded-full"
                    style={{ backgroundColor: cause.color, opacity: 0.7 }}
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Evidence signals */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {incident.behavioralEvidence.map((signal, idx) => (
              <EvidenceSignal key={signal.feature} signal={signal} index={idx} accentColor={cause.color} />
            ))}
          </div>
        </div>

        {/* === B. WHY SUS FLAGGED THIS === */}
        <div className="mb-8">
          <div className="text-[10px] font-mono text-[#8A94A6] tracking-[0.15em] mb-3">
            WHY SUS FLAGGED THIS
          </div>
          <div className="h-px bg-[#1a1f2e] mb-4" />

          <div className="space-y-3">
            {sortedContributions.slice(0, 3).map((contrib, idx) => (
              <motion.div
                key={contrib.feature}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.3, delay: 0.2 + idx * 0.08 }}
                className="bg-[#0D111A] border border-[#1a1f2e] rounded-sm p-4"
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="text-[9px] font-mono text-[#8A94A6]/60 tracking-wider">
                      {idx === 0 ? 'PRIMARY' : idx === 1 ? 'SECONDARY' : 'TERTIARY'}
                    </span>
                    <span className="text-xs text-[#F3F4F6] font-medium">
                      {contrib.label}
                    </span>
                  </div>
                  <span
                    className="text-xs font-mono font-medium"
                    style={{ color: contrib.direction === 'fraud' ? '#FF5C5C' : '#34D399' }}
                  >
                    {(contrib.contribution * 100).toFixed(0)}%
                  </span>
                </div>
                {/* Contribution bar */}
                <div className="h-1 bg-[#1a1f2e] rounded-full overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${(contrib.contribution / maxContribution) * 100}%` }}
                    transition={{ duration: 0.6, delay: 0.3 + idx * 0.1 }}
                    className="h-full rounded-full"
                    style={{ backgroundColor: contrib.direction === 'fraud' ? '#FF5C5C' : '#34D399' }}
                  />
                </div>
              </motion.div>
            ))}
          </div>
        </div>

        {/* === C. CAUSE CLASSIFICATION === */}
        <div className="mb-8">
          <div className="text-[10px] font-mono text-[#8A94A6] tracking-[0.15em] mb-3">
            CAUSE CLASSIFICATION
          </div>
          <div className="h-px bg-[#1a1f2e] mb-4" />

          <div className="bg-[#0D111A] border border-[#1a1f2e] rounded-sm p-5">
            <div className="flex items-start justify-between mb-4">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span style={{ color: cause.color }}>{cause.icon}</span>
                  <span className="text-lg font-medium tracking-wide" style={{ color: cause.color }}>
                    {cause.label}
                  </span>
                </div>
                <p className="text-xs text-[#8A94A6] mt-2 leading-relaxed max-w-md">
                  {incident.classificationSummary}
                </p>
              </div>
              <div className="text-right flex-shrink-0 ml-6">
                <motion.div
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ duration: 0.5, delay: 0.3 }}
                >
                  <span className="text-3xl font-light" style={{ color: cause.color }}>
                    {(incident.fraudProbability * 100).toFixed(1)}
                  </span>
                  <span className="text-lg" style={{ color: cause.color }}>%</span>
                </motion.div>
                <div className="text-[10px] font-mono text-[#8A94A6] tracking-wider mt-1">
                  FRAUD PROBABILITY
                </div>
              </div>
            </div>

            {/* Confidence bar */}
            <div className="pt-3 border-t border-[#1a1f2e]">
              <div className="flex items-center justify-between mb-2">
                <span className="text-[10px] font-mono text-[#8A94A6] tracking-wider">CONFIDENCE</span>
                <span className="text-xs font-mono text-[#F3F4F6]">
                  {(incident.confidence * 100).toFixed(1)}% — {confidenceLabels[incident.confidenceBand]}
                </span>
              </div>
              <div className="h-1 bg-[#1a1f2e] rounded-full overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${incident.confidence * 100}%` }}
                  transition={{ duration: 0.8, delay: 0.4 }}
                  className="h-full rounded-full"
                  style={{ backgroundColor: cause.color, opacity: 0.6 }}
                />
              </div>
            </div>
          </div>
        </div>

        {/* === INCIDENT TIMELINE === */}
        <div className="mb-8">
          <div className="text-[10px] font-mono text-[#8A94A6] tracking-[0.15em] mb-3">
            INCIDENT TIMELINE
          </div>
          <div className="h-px bg-[#1a1f2e] mb-4" />

          <div className="bg-[#0D111A] border border-[#1a1f2e] rounded-sm p-5">
            <IncidentTimeline steps={incident.timeline} />
          </div>
        </div>

        {/* === RECOMMENDED ACTION === */}
        <RecommendedAction
          actionType={incident.actionType}
          recommendedAction={incident.recommendedAction}
        />
      </motion.div>
    </AnimatePresence>
  );
}

// Evidence signal sub-component
function EvidenceSignal({ signal, index }: { signal: BehavioralEvidence; index: number; accentColor: string }) {
  const signalColor = signal.signalType === 'fraud' ? '#FF5C5C'
    : signal.signalType === 'organic' ? '#34D399'
    : '#8A94A6';

  return (
    <motion.div
      initial={{ opacity: 0, y: 5 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: 0.15 + index * 0.06 }}
      className="bg-[#0D111A] border border-[#1a1f2e] rounded-sm p-4"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <span className="text-[10px] font-mono text-[#8A94A6] tracking-wider">
          {signal.label.toUpperCase()}
        </span>
        <span
          className="text-xs font-mono font-medium"
          style={{ color: signalColor }}
        >
          {signal.changePercent > 0 ? '+' : ''}{signal.changePercent}%
        </span>
      </div>

      {/* Values comparison */}
      <div className="flex items-baseline gap-3 mb-3">
        <span className="text-lg font-mono text-[#F3F4F6]">
          {signal.currentValue}{signal.unit === '%' ? '%' : ''}
        </span>
        <span className="text-[10px] text-[#8A94A6]">
          from {signal.normalValue}{signal.unit === '%' ? '%' : ''}
        </span>
      </div>

      {/* Comparison bar */}
      <div className="space-y-1.5 mb-3">
        <div className="h-1 bg-[#1a1f2e] rounded-full overflow-hidden">
          <div
            className="h-full bg-[#8A94A6]/40 rounded-full"
            style={{ width: `${(signal.normalValue / Math.max(signal.normalValue, signal.currentValue)) * 100}%` }}
          />
        </div>
        <div className="h-1 bg-[#1a1f2e] rounded-full overflow-hidden">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${(signal.currentValue / Math.max(signal.normalValue, signal.currentValue)) * 100}%` }}
            transition={{ duration: 0.6, delay: 0.2 + index * 0.08 }}
            className="h-full rounded-full"
            style={{ backgroundColor: signalColor, opacity: 0.7 }}
          />
        </div>
      </div>

      {/* Description */}
      <p className="text-[11px] text-[#8A94A6] leading-relaxed">
        {signal.description}
      </p>
    </motion.div>
  );
}

function MerchantLink({ merchantId, merchantName }: { merchantId: string; merchantName: string }) {
  const { navigateToMerchantFromActivity } = useNavigation();
  return (
    <button
      onClick={() => navigateToMerchantFromActivity(merchantId)}
      className="flex items-center gap-1.5 text-xs font-mono text-[#8A94A6] tracking-wider hover:text-[#38BDF8] transition-colors mb-2"
    >
      {merchantName}
      <ExternalLink className="w-3 h-3 opacity-50" />
    </button>
  );
}

function NavigateToDetailButton({ incidentId }: { incidentId: string }) {
  const navigate = useNavigate();
  return (
    <button
      onClick={() => navigate(`/incidents/${incidentId}`)}
      className="flex items-center gap-1.5 px-2.5 py-1 text-[9px] font-mono tracking-wider uppercase text-[#38BDF8] border border-[#38BDF8]/20 hover:border-[#38BDF8]/50 hover:bg-[#38BDF8]/5 transition-all duration-200"
    >
      Full Detail
      <ArrowRight className="w-2.5 h-2.5" />
    </button>
  );
}
