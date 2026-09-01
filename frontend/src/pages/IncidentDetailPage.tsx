import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowLeft, Clock, User, Save, AlertTriangle, CheckCircle } from 'lucide-react';
import { dataSource } from '../data/dataSource';
import type { IncidentDetail } from '../services/incidentService';

// ---------------------------------------------------------------------------
// Severity color mapping
// ---------------------------------------------------------------------------

const severityColors: Record<string, string> = {
  critical: '#FF5C5C',
  high: '#FF8A3D',
  medium: '#FBBF24',
  low: '#34D399',
};

const classificationColors: Record<string, string> = {
  fraud_spike: '#FF5C5C',
  organic_spike: '#34D399',
  review_required: '#FBBF24',
  baseline: '#8A94A6',
};

const workflowStatusOptions = [
  { value: 'open', label: 'OPEN', color: '#8A94A6' },
  { value: 'investigating', label: 'INVESTIGATING', color: '#38BDF8' },
  { value: 'resolved', label: 'RESOLVED', color: '#34D399' },
  { value: 'false_positive', label: 'FALSE POSITIVE', color: '#A78BFA' },
];

const resolutionOptions = [
  { value: 'confirmed_fraud', label: 'Confirmed Fraud' },
  { value: 'false_positive', label: 'False Positive' },
  { value: 'inconclusive', label: 'Inconclusive' },
];

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export default function IncidentDetailPage() {
  const { incidentId } = useParams<{ incidentId: string }>();
  const navigate = useNavigate();

  const [incident, setIncident] = useState<IncidentDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Workflow form state
  const [workflowStatus, setWorkflowStatus] = useState('');
  const [assignedAnalyst, setAssignedAnalyst] = useState('');
  const [resolution, setResolution] = useState('');
  const [analystNotes, setAnalystNotes] = useState('');
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [hasChanges, setHasChanges] = useState(false);

  const loadIncident = useCallback(async () => {
    if (!incidentId) return;
    setLoading(true);
    setError(null);
    try {
      const detail = await dataSource.getIncidentDetail(incidentId);
      if (!detail) {
        setError('Incident not found');
      } else {
        setIncident(detail);
        setWorkflowStatus(detail.workflowStatus);
        setAssignedAnalyst(detail.assignedAnalyst ?? '');
        setResolution(detail.resolution ?? '');
        setAnalystNotes(detail.analystNotes ?? '');
      }
    } catch {
      setError('Failed to load incident');
    } finally {
      setLoading(false);
    }
  }, [incidentId]);

  useEffect(() => {
    loadIncident();
  }, [loadIncident]);

  // Track changes
  useEffect(() => {
    if (!incident) return;
    const changed =
      workflowStatus !== incident.workflowStatus ||
      (assignedAnalyst || '') !== (incident.assignedAnalyst ?? '') ||
      (resolution || '') !== (incident.resolution ?? '') ||
      (analystNotes || '') !== (incident.analystNotes ?? '');
    setHasChanges(changed);
  }, [workflowStatus, assignedAnalyst, resolution, analystNotes, incident]);

  const handleSave = async () => {
    if (!incident) return;
    setSaving(true);
    setSaveError(null);
    setSaveSuccess(false);

    const payload: Record<string, string | null> = {};
    if (workflowStatus !== incident.workflowStatus) {
      payload.workflow_status = workflowStatus;
    }
    if ((assignedAnalyst || null) !== (incident.assignedAnalyst ?? null)) {
      payload.assigned_analyst = assignedAnalyst || null;
    }
    if (resolution !== (incident.resolution ?? '')) {
      payload.resolution = resolution || null;
    }
    if ((analystNotes || '') !== (incident.analystNotes ?? '')) {
      payload.analyst_notes = analystNotes || null;
    }

    if (Object.keys(payload).length === 0) {
      setSaving(false);
      return;
    }

    try {
      const updated = await dataSource.saveIncidentUpdate(incident.incidentId, payload);
      if (updated) {
        setIncident(updated);
        setWorkflowStatus(updated.workflowStatus);
        setAssignedAnalyst(updated.assignedAnalyst ?? '');
        setResolution(updated.resolution ?? '');
        setAnalystNotes(updated.analystNotes ?? '');
        setSaveSuccess(true);
        setTimeout(() => setSaveSuccess(false), 3000);
      } else {
        setSaveError('Update failed — API mode may not be enabled');
      }
    } catch {
      setSaveError('Failed to save changes');
    } finally {
      setSaving(false);
    }
  };

  // Loading state
  if (loading) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="px-[var(--content-px)] max-w-[var(--content-max)] mx-auto py-16"
      >
        <div className="flex items-center gap-3">
          <div className="w-4 h-4 border-2 border-[#38BDF8]/30 border-t-[#38BDF8] rounded-full animate-spin" />
          <span className="text-xs font-mono text-[#8A94A6]">Loading incident...</span>
        </div>
      </motion.div>
    );
  }

  // Error state
  if (error || !incident) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="px-[var(--content-px)] max-w-[var(--content-max)] mx-auto py-16"
      >
        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-2 text-xs font-mono text-[#8A94A6] hover:text-[#38BDF8] mb-6 transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Back
        </button>
        <div className="border border-[#FF5C5C]/30 bg-[#FF5C5C]/5 p-6">
          <div className="flex items-center gap-3">
            <AlertTriangle className="w-4 h-4 text-[#FF5C5C]" />
            <span className="text-sm font-mono text-[#FF5C5C]">{error || 'Incident not found'}</span>
          </div>
        </div>
      </motion.div>
    );
  }

  const statusColor = severityColors[incident.severity] ?? '#8A94A6';
  const classColor = classificationColors[incident.classification] ?? '#8A94A6';
  const currentWorkflow = workflowStatusOptions.find(o => o.value === workflowStatus);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
      className="px-[var(--content-px)] max-w-[var(--content-max)] mx-auto py-6 pb-24"
    >
      {/* Back navigation */}
      <button
        onClick={() => navigate(-1)}
        className="flex items-center gap-2 text-xs font-mono text-[#8A94A6] hover:text-[#38BDF8] mb-6 transition-colors"
      >
        <ArrowLeft className="w-3.5 h-3.5" />
        Back
      </button>

      {/* Header */}
      <div className="flex items-start justify-between mb-8">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <span className="text-[11px] font-mono text-[#38BDF8] tracking-wider">
              {incident.incidentId}
            </span>
            <span
              className="px-2 py-0.5 text-[10px] font-mono tracking-wider uppercase"
              style={{ color: statusColor, backgroundColor: `${statusColor}15`, border: `1px solid ${statusColor}30` }}
            >
              {incident.severity}
            </span>
            <span
              className="px-2 py-0.5 text-[10px] font-mono tracking-wider uppercase"
              style={{ color: classColor, backgroundColor: `${classColor}15`, border: `1px solid ${classColor}30` }}
            >
              {incident.classification.replace('_', ' ')}
            </span>
          </div>
          <div className="flex items-center gap-4 text-[10px] font-mono text-[#8A94A6]">
            <span>Merchant: {incident.merchantId}</span>
            <span>Date: {incident.date}</span>
            {incident.predictedCause && (
              <span>Predicted cause: {incident.predictedCause.replace('_', ' ')}</span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {currentWorkflow && (
            <span
              className="px-2.5 py-1 text-[10px] font-mono tracking-wider uppercase"
              style={{
                color: currentWorkflow.color,
                backgroundColor: `${currentWorkflow.color}15`,
                border: `1px solid ${currentWorkflow.color}30`,
              }}
            >
              {currentWorkflow.label}
            </span>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left column: ML Evidence (read-only) */}
        <div className="lg:col-span-2 space-y-6">
          {/* ML Evidence Section */}
          <div className="border border-[#1E293B] bg-[#0B0F18]/80 p-5">
            <h3 className="text-[10px] font-mono tracking-[0.2em] uppercase text-[#8A94A6] mb-4">
              Model Evidence
            </h3>

            {/* Scores grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-5">
              <div>
                <div className="text-[9px] font-mono text-[#8A94A6]/60 uppercase tracking-wider mb-1">
                  Fraud Probability
                </div>
                <div className="text-lg font-mono text-[#F3F4F6]">
                  {(incident.fraudProbability * 100).toFixed(1)}%
                </div>
              </div>
              <div>
                <div className="text-[9px] font-mono text-[#8A94A6]/60 uppercase tracking-wider mb-1">
                  Confidence
                </div>
                <div className="text-lg font-mono text-[#F3F4F6]">
                  {(incident.confidence * 100).toFixed(1)}%
                </div>
              </div>
              <div>
                <div className="text-[9px] font-mono text-[#8A94A6]/60 uppercase tracking-wider mb-1">
                  Confidence Band
                </div>
                <div className="text-sm font-mono text-[#F3F4F6]">
                  {incident.confidenceBand.replace('_', ' ')}
                </div>
              </div>
              <div>
                <div className="text-[9px] font-mono text-[#8A94A6]/60 uppercase tracking-wider mb-1">
                  Anomaly Score
                </div>
                <div className="text-lg font-mono text-[#F3F4F6]">
                  {incident.anomalyScore.toFixed(2)}
                </div>
              </div>
            </div>

            {/* Decision reason */}
            {incident.decisionReason && (
              <div className="mb-4">
                <div className="text-[9px] font-mono text-[#8A94A6]/60 uppercase tracking-wider mb-1">
                  Decision Reason
                </div>
                <p className="text-xs font-mono text-[#8A94A6] leading-relaxed">
                  {incident.decisionReason}
                </p>
              </div>
            )}

            {/* Anomaly summary */}
            {incident.anomalySummary && (
              <div className="mb-4">
                <div className="text-[9px] font-mono text-[#8A94A6]/60 uppercase tracking-wider mb-1">
                  Anomaly Summary
                </div>
                <p className="text-xs font-mono text-[#8A94A6] leading-relaxed">
                  {incident.anomalySummary}
                </p>
              </div>
            )}

            {/* Top signals */}
            {incident.topSignals.length > 0 && (
              <div className="mb-4">
                <div className="text-[9px] font-mono text-[#8A94A6]/60 uppercase tracking-wider mb-2">
                  Top Signals
                </div>
                <div className="space-y-1.5">
                  {incident.topSignals.map((signal, i) => (
                    <div
                      key={i}
                      className="flex items-start gap-2 text-[10px] font-mono text-[#8A94A6]"
                    >
                      <span className="text-[#38BDF8] mt-0.5">•</span>
                      <span>{signal}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Recommended action */}
            {incident.recommendedAction && (
              <div className="border-t border-[#1E293B]/60 pt-3 mt-3">
                <div className="text-[9px] font-mono text-[#8A94A6]/60 uppercase tracking-wider mb-1">
                  Recommended Action
                </div>
                <p className="text-xs font-mono text-[#FBBF24] leading-relaxed">
                  {incident.recommendedAction}
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Right column: Analyst Workflow (editable) */}
        <div className="space-y-6">
          {/* Workflow Panel */}
          <div className="border border-[#1E293B] bg-[#0B0F18]/80 p-5">
            <h3 className="text-[10px] font-mono tracking-[0.2em] uppercase text-[#8A94A6] mb-4">
              Analyst Workflow
            </h3>

            {/* Status */}
            <div className="mb-4">
              <label className="text-[9px] font-mono text-[#8A94A6]/60 uppercase tracking-wider block mb-1.5">
                Status
              </label>
              <select
                value={workflowStatus}
                onChange={e => setWorkflowStatus(e.target.value)}
                className="w-full bg-[#0D111A] border border-[#1E293B] text-[#F3F4F6] text-xs font-mono px-3 py-2 focus:border-[#38BDF8]/50 focus:outline-none transition-colors"
              >
                {workflowStatusOptions.map(opt => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Assigned Analyst */}
            <div className="mb-4">
              <label className="text-[9px] font-mono text-[#8A94A6]/60 uppercase tracking-wider block mb-1.5">
                Assigned Analyst
              </label>
              <input
                type="text"
                value={assignedAnalyst}
                onChange={e => setAssignedAnalyst(e.target.value)}
                placeholder="e.g. analyst_001"
                className="w-full bg-[#0D111A] border border-[#1E293B] text-[#F3F4F6] text-xs font-mono px-3 py-2 placeholder:text-[#8A94A6]/30 focus:border-[#38BDF8]/50 focus:outline-none transition-colors"
              />
            </div>

            {/* Resolution (only shown for resolved/false_positive) */}
            {(workflowStatus === 'resolved' || workflowStatus === 'false_positive') && (
              <div className="mb-4">
                <label className="text-[9px] font-mono text-[#8A94A6]/60 uppercase tracking-wider block mb-1.5">
                  Resolution
                </label>
                <select
                  value={resolution}
                  onChange={e => setResolution(e.target.value)}
                  className="w-full bg-[#0D111A] border border-[#1E293B] text-[#F3F4F6] text-xs font-mono px-3 py-2 focus:border-[#38BDF8]/50 focus:outline-none transition-colors"
                >
                  <option value="">— Select —</option>
                  {resolutionOptions.map(opt => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>
            )}

            {/* Notes */}
            <div className="mb-5">
              <label className="text-[9px] font-mono text-[#8A94A6]/60 uppercase tracking-wider block mb-1.5">
                Analyst Notes
              </label>
              <textarea
                value={analystNotes}
                onChange={e => setAnalystNotes(e.target.value)}
                placeholder="Add investigation notes..."
                rows={4}
                className="w-full bg-[#0D111A] border border-[#1E293B] text-[#F3F4F6] text-xs font-mono px-3 py-2 placeholder:text-[#8A94A6]/30 focus:border-[#38BDF8]/50 focus:outline-none transition-colors resize-none"
              />
            </div>

            {/* Save button */}
            <button
              onClick={handleSave}
              disabled={!hasChanges || saving}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 text-[10px] font-mono tracking-wider uppercase bg-[#0F1623] border border-[#1E293B] text-[#8A94A6] hover:text-[#38BDF8] hover:border-[#38BDF8]/30 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {saving ? (
                <>
                  <div className="w-3 h-3 border-2 border-[#38BDF8]/30 border-t-[#38BDF8] rounded-full animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <Save className="w-3.5 h-3.5" />
                  Save Changes
                </>
              )}
            </button>

            {/* Status feedback */}
            {saveSuccess && (
              <div className="mt-3 flex items-center gap-2 text-[10px] font-mono text-[#34D399]">
                <CheckCircle className="w-3.5 h-3.5" />
                Changes saved successfully
              </div>
            )}
            {saveError && (
              <div className="mt-3 flex items-center gap-2 text-[10px] font-mono text-[#FF5C5C]">
                <AlertTriangle className="w-3.5 h-3.5" />
                {saveError}
              </div>
            )}
          </div>

          {/* Status History Timeline */}
          <div className="border border-[#1E293B] bg-[#0B0F18]/80 p-5">
            <h3 className="text-[10px] font-mono tracking-[0.2em] uppercase text-[#8A94A6] mb-4">
              Status History
            </h3>

            {incident.statusHistory.length === 0 ? (
              <div className="text-[10px] font-mono text-[#8A94A6]/50">
                No status transitions recorded.
              </div>
            ) : (
              <div className="space-y-3">
                {incident.statusHistory.map((entry, i) => {
                  const entryColor = workflowStatusOptions.find(o => o.value === entry.newStatus)?.color ?? '#8A94A6';
                  return (
                    <div key={i} className="flex items-start gap-3">
                      <div className="flex flex-col items-center mt-0.5">
                        <div
                          className="w-2 h-2 rounded-full"
                          style={{ backgroundColor: entryColor }}
                        />
                        {i < incident.statusHistory.length - 1 && (
                          <div className="w-px h-5 bg-[#1E293B]" />
                        )}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-0.5">
                          <span className="text-[10px] font-mono text-[#8A94A6]/60 uppercase">
                            {entry.oldStatus.replace('_', ' ')}
                          </span>
                          <span className="text-[10px] font-mono text-[#8A94A6]/30">→</span>
                          <span
                            className="text-[10px] font-mono uppercase"
                            style={{ color: entryColor }}
                          >
                            {entry.newStatus.replace('_', ' ')}
                          </span>
                        </div>
                        <div className="flex items-center gap-2 text-[9px] font-mono text-[#8A94A6]/40">
                          <Clock className="w-2.5 h-2.5" />
                          <span>{new Date(entry.createdAt).toLocaleString()}</span>
                          {entry.changedBy && (
                            <>
                              <User className="w-2.5 h-2.5" />
                              <span>{entry.changedBy}</span>
                            </>
                          )}
                        </div>
                        {entry.note && (
                          <p className="mt-1 text-[10px] font-mono text-[#8A94A6]/60">
                            {entry.note}
                          </p>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Metadata */}
          <div className="border border-[#1E293B] bg-[#0B0F18]/80 p-5">
            <h3 className="text-[10px] font-mono tracking-[0.2em] uppercase text-[#8A94A6] mb-3">
              Metadata
            </h3>
            <div className="space-y-2 text-[10px] font-mono">
              <div className="flex justify-between">
                <span className="text-[#8A94A6]/60">Created</span>
                <span className="text-[#8A94A6]">{new Date(incident.createdAt).toLocaleString()}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#8A94A6]/60">Last Updated</span>
                <span className="text-[#8A94A6]">{new Date(incident.updatedAt).toLocaleString()}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
