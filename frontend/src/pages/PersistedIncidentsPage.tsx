import { useState, useEffect, useCallback, useMemo } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  Search, Filter, ChevronLeft, ChevronRight, ArrowUpDown,
  ArrowUp, ArrowDown, X, AlertTriangle, Clock, User,
} from 'lucide-react';
import { dataSource } from '../data/dataSource';
import type { IncidentListItem } from '../services/incidentService';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const PAGE_SIZE = 20;

const WORKFLOW_STATUSES = [
  { value: '', label: 'All statuses' },
  { value: 'open', label: 'Open' },
  { value: 'investigating', label: 'Investigating' },
  { value: 'resolved', label: 'Resolved' },
  { value: 'false_positive', label: 'False Positive' },
];

const CLASSIFICATIONS = [
  { value: '', label: 'All classifications' },
  { value: 'fraud_spike', label: 'Fraud Spike' },
  { value: 'organic_spike', label: 'Organic Spike' },
  { value: 'review_required', label: 'Review Required' },
];

const SEVERITIES = [
  { value: '', label: 'All severities' },
  { value: 'critical', label: 'Critical' },
  { value: 'high', label: 'High' },
  { value: 'medium', label: 'Medium' },
  { value: 'low', label: 'Low' },
];

const SORT_OPTIONS = [
  { value: 'created_at', label: 'Created' },
  { value: 'updated_at', label: 'Updated' },
  { value: 'severity', label: 'Severity' },
  { value: 'fraud_probability', label: 'Fraud Probability' },
  { value: 'confidence', label: 'Confidence' },
];

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

const workflowColors: Record<string, string> = {
  open: '#8A94A6',
  investigating: '#38BDF8',
  resolved: '#34D399',
  false_positive: '#A78BFA',
};

// ---------------------------------------------------------------------------
// URL state helpers
// ---------------------------------------------------------------------------

function readUrlState(sp: URLSearchParams) {
  return {
    search: sp.get('search') ?? '',
    workflowStatus: sp.get('workflow_status') ?? '',
    classification: sp.get('classification') ?? '',
    severity: sp.get('severity') ?? '',
    assignedAnalyst: sp.get('assigned_analyst') ?? '',
    investigationId: sp.get('investigation_id') ?? '',
    createdFrom: sp.get('created_from') ?? '',
    createdTo: sp.get('created_to') ?? '',
    sortBy: sp.get('sort_by') ?? 'created_at',
    sortOrder: sp.get('sort_order') ?? 'desc',
    page: Math.max(1, parseInt(sp.get('page') ?? '1', 10) || 1),
  };
}

function writeUrlState(
  setSearchParams: (params: URLSearchParams | Record<string, string>, opts?: { replace?: boolean }) => void,
  state: ReturnType<typeof readUrlState>,
) {
  const p = new URLSearchParams();
  if (state.search) p.set('search', state.search);
  if (state.workflowStatus) p.set('workflow_status', state.workflowStatus);
  if (state.classification) p.set('classification', state.classification);
  if (state.severity) p.set('severity', state.severity);
  if (state.assignedAnalyst) p.set('assigned_analyst', state.assignedAnalyst);
  if (state.investigationId) p.set('investigation_id', state.investigationId);
  if (state.createdFrom) p.set('created_from', state.createdFrom);
  if (state.createdTo) p.set('created_to', state.createdTo);
  if (state.sortBy && state.sortBy !== 'created_at') p.set('sort_by', state.sortBy);
  if (state.sortOrder && state.sortOrder !== 'desc') p.set('sort_order', state.sortOrder);
  if (state.page > 1) p.set('page', String(state.page));
  setSearchParams(p, { replace: true });
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function PersistedIncidentsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const urlState = useMemo(() => readUrlState(searchParams), [searchParams]);

  // Filter form state (local until APPLY)
  const [formSearch, setFormSearch] = useState(urlState.search);
  const [formWorkflow, setFormWorkflow] = useState(urlState.workflowStatus);
  const [formClassification, setFormClassification] = useState(urlState.classification);
  const [formSeverity, setFormSeverity] = useState(urlState.severity);
  const [formAnalyst, setFormAnalyst] = useState(urlState.assignedAnalyst);
  const [formInvestigationId, setFormInvestigationId] = useState(urlState.investigationId);
  const [formDateFrom, setFormDateFrom] = useState(urlState.createdFrom);
  const [formDateTo, setFormDateTo] = useState(urlState.createdTo);

  // Data state
  const [incidents, setIncidents] = useState<IncidentListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const offset = (urlState.page - 1) * PAGE_SIZE;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const loadIncidents = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await dataSource.getPersistedIncidents({
        search: urlState.search || undefined,
        workflowStatus: urlState.workflowStatus || undefined,
        classification: urlState.classification || undefined,
        severity: urlState.severity || undefined,
        assignedAnalyst: urlState.assignedAnalyst || undefined,
        investigationId: urlState.investigationId || undefined,
        createdFrom: urlState.createdFrom || undefined,
        createdTo: urlState.createdTo || undefined,
        sortBy: urlState.sortBy || undefined,
        sortOrder: urlState.sortOrder || undefined,
        limit: PAGE_SIZE,
        offset,
      });
      if (result) {
        setIncidents(result.incidents);
        setTotal(result.total);
      } else {
        setIncidents([]);
        setTotal(0);
      }
    } catch {
      setError('Failed to load incidents');
    } finally {
      setLoading(false);
    }
  }, [urlState, offset]);

  useEffect(() => {
    loadIncidents();
  }, [loadIncidents]);

  // Sync form from URL on mount / URL change
  useEffect(() => {
    setFormSearch(urlState.search);
    setFormWorkflow(urlState.workflowStatus);
    setFormClassification(urlState.classification);
    setFormSeverity(urlState.severity);
    setFormAnalyst(urlState.assignedAnalyst);
    setFormInvestigationId(urlState.investigationId);
    setFormDateFrom(urlState.createdFrom);
    setFormDateTo(urlState.createdTo);
  }, [urlState.search, urlState.workflowStatus, urlState.classification, urlState.severity, urlState.assignedAnalyst, urlState.investigationId, urlState.createdFrom, urlState.createdTo]);

  const applyFilters = () => {
    writeUrlState(setSearchParams, {
      ...urlState,
      search: formSearch,
      workflowStatus: formWorkflow,
      classification: formClassification,
      severity: formSeverity,
      assignedAnalyst: formAnalyst,
      investigationId: formInvestigationId,
      createdFrom: formDateFrom,
      createdTo: formDateTo,
      page: 1,
    });
  };

  const clearFilters = () => {
    setFormSearch('');
    setFormWorkflow('');
    setFormClassification('');
    setFormSeverity('');
    setFormAnalyst('');
    setFormInvestigationId('');
    setFormDateFrom('');
    setFormDateTo('');
    writeUrlState(setSearchParams, {
      ...urlState,
      search: '',
      workflowStatus: '',
      classification: '',
      severity: '',
      assignedAnalyst: '',
      investigationId: '',
      createdFrom: '',
      createdTo: '',
      page: 1,
    });
  };

  const toggleSort = (field: string) => {
    const newOrder = urlState.sortBy === field && urlState.sortOrder === 'asc' ? 'desc' : 'asc';
    writeUrlState(setSearchParams, { ...urlState, sortBy: field, sortOrder: newOrder, page: 1 });
  };

  const goToPage = (page: number) => {
    writeUrlState(setSearchParams, { ...urlState, page: Math.max(1, Math.min(page, totalPages)) });
  };

  const hasActiveFilters = !!(
    urlState.search || urlState.workflowStatus || urlState.classification ||
    urlState.severity || urlState.assignedAnalyst || urlState.investigationId ||
    urlState.createdFrom || urlState.createdTo
  );

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
      className="px-[var(--content-px)] max-w-[var(--content-max)] mx-auto py-6 pb-24"
    >
      {/* Header */}
      <div className="flex items-baseline gap-3 mb-6">
        <h1 className="text-[11px] font-mono tracking-[0.2em] uppercase text-[#8A94A6]">
          Incidents
        </h1>
        {hasActiveFilters && (
          <span className="text-[10px] font-mono text-[#38BDF8]/50">
            Filters active
          </span>
        )}
        {total > 0 && (
          <span className="text-[10px] font-mono text-[#8A94A6]/50 ml-auto">
            {total} total
          </span>
        )}
      </div>

      {/* Filter bar */}
      <div className="border border-[#1E293B] bg-[#0B0F18]/80 p-4 mb-6">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3 h-3 text-[#8A94A6]/40" />
            <input
              type="text"
              value={formSearch}
              onChange={e => setFormSearch(e.target.value)}
              placeholder="Search ID or merchant..."
              className="w-full bg-[#0D111A] border border-[#1E293B] text-[#F3F4F6] text-[10px] font-mono pl-7 pr-2 py-1.5 placeholder:text-[#8A94A6]/30 focus:border-[#38BDF8]/50 focus:outline-none"
            />
          </div>

          {/* Workflow Status */}
          <select
            value={formWorkflow}
            onChange={e => setFormWorkflow(e.target.value)}
            className="bg-[#0D111A] border border-[#1E293B] text-[#F3F4F6] text-[10px] font-mono px-2 py-1.5 focus:border-[#38BDF8]/50 focus:outline-none"
          >
            {WORKFLOW_STATUSES.map(o => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>

          {/* Classification */}
          <select
            value={formClassification}
            onChange={e => setFormClassification(e.target.value)}
            className="bg-[#0D111A] border border-[#1E293B] text-[#F3F4F6] text-[10px] font-mono px-2 py-1.5 focus:border-[#38BDF8]/50 focus:outline-none"
          >
            {CLASSIFICATIONS.map(o => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>

          {/* Severity */}
          <select
            value={formSeverity}
            onChange={e => setFormSeverity(e.target.value)}
            className="bg-[#0D111A] border border-[#1E293B] text-[#F3F4F6] text-[10px] font-mono px-2 py-1.5 focus:border-[#38BDF8]/50 focus:outline-none"
          >
            {SEVERITIES.map(o => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
          {/* Assigned Analyst */}
          <input
            type="text"
            value={formAnalyst}
            onChange={e => setFormAnalyst(e.target.value)}
            placeholder="Analyst..."
            className="bg-[#0D111A] border border-[#1E293B] text-[#F3F4F6] text-[10px] font-mono px-2 py-1.5 placeholder:text-[#8A94A6]/30 focus:border-[#38BDF8]/50 focus:outline-none"
          />

          {/* Investigation ID */}
          <input
            type="text"
            value={formInvestigationId}
            onChange={e => setFormInvestigationId(e.target.value)}
            placeholder="Investigation ID..."
            className="bg-[#0D111A] border border-[#1E293B] text-[#F3F4F6] text-[10px] font-mono px-2 py-1.5 placeholder:text-[#8A94A6]/30 focus:border-[#38BDF8]/50 focus:outline-none"
          />

          {/* Date From */}
          <input
            type="datetime-local"
            value={formDateFrom}
            onChange={e => setFormDateFrom(e.target.value)}
            className="bg-[#0D111A] border border-[#1E293B] text-[#F3F4F6] text-[10px] font-mono px-2 py-1.5 focus:border-[#38BDF8]/50 focus:outline-none"
          />

          {/* Date To */}
          <input
            type="datetime-local"
            value={formDateTo}
            onChange={e => setFormDateTo(e.target.value)}
            className="bg-[#0D111A] border border-[#1E293B] text-[#F3F4F6] text-[10px] font-mono px-2 py-1.5 focus:border-[#38BDF8]/50 focus:outline-none"
          />
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2">
          <button
            onClick={applyFilters}
            className="px-3 py-1.5 text-[10px] font-mono tracking-wider uppercase bg-[#0F1623] border border-[#1E293B] text-[#38BDF8] hover:border-[#38BDF8]/30 transition-all"
          >
            <Filter className="w-3 h-3 inline mr-1.5" />
            Apply Filters
          </button>
          {hasActiveFilters && (
            <button
              onClick={clearFilters}
              className="px-3 py-1.5 text-[10px] font-mono tracking-wider uppercase text-[#8A94A6] hover:text-[#F3F4F6] transition-colors"
            >
              <X className="w-3 h-3 inline mr-1" />
              Clear
            </button>
          )}

          {/* Sort controls */}
          <div className="ml-auto flex items-center gap-2">
            <span className="text-[9px] font-mono text-[#8A94A6]/40">Sort:</span>
            {SORT_OPTIONS.map(opt => {
              const active = urlState.sortBy === opt.value;
              return (
                <button
                  key={opt.value}
                  onClick={() => toggleSort(opt.value)}
                  className={`flex items-center gap-1 px-2 py-1 text-[9px] font-mono transition-colors ${
                    active ? 'text-[#38BDF8]' : 'text-[#8A94A6]/50 hover:text-[#8A94A6]'
                  }`}
                >
                  {opt.label}
                  {active && (
                    urlState.sortOrder === 'asc'
                      ? <ArrowUp className="w-2.5 h-2.5" />
                      : <ArrowDown className="w-2.5 h-2.5" />
                  )}
                  {!active && <ArrowUpDown className="w-2.5 h-2.5 opacity-30" />}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="border border-[#FF5C5C]/30 bg-[#FF5C5C]/5 p-4 mb-6 flex items-center gap-3">
          <AlertTriangle className="w-4 h-4 text-[#FF5C5C]" />
          <span className="text-xs font-mono text-[#FF5C5C]">{error}</span>
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="flex items-center gap-3 py-16">
          <div className="w-4 h-4 border-2 border-[#38BDF8]/30 border-t-[#38BDF8] rounded-full animate-spin" />
          <span className="text-xs font-mono text-[#8A94A6]">Loading incidents...</span>
        </div>
      )}

      {/* Empty state */}
      {!loading && incidents.length === 0 && (
        <div className="text-center py-16">
          <p className="text-sm font-mono text-[#8A94A6]/60">
            {hasActiveFilters ? 'No incidents match the current filters.' : 'No incidents yet. Run an investigation to generate incidents for review.'}
          </p>
          {hasActiveFilters && (
            <button
              onClick={clearFilters}
              className="mt-3 text-[10px] font-mono text-[#38BDF8] hover:underline"
            >
              Clear filters
            </button>
          )}
        </div>
      )}

      {/* Incident list */}
      {!loading && incidents.length > 0 && (
        <>
          <div className="border border-[#1E293B] divide-y divide-[#1E293B]/60">
            {incidents.map(inc => {
              const sevColor = severityColors[inc.severity] ?? '#8A94A6';
              const classColor = classificationColors[inc.classification] ?? '#8A94A6';
              const wfColor = workflowColors[inc.workflowStatus] ?? '#8A94A6';
              return (
                <motion.button
                  key={inc.incidentId}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  onClick={() => navigate(`/incidents/${inc.incidentId}`)}
                  className="w-full text-left p-4 bg-[#0B0F18]/60 hover:bg-[#0D111A] transition-colors"
                >
                  <div className="flex items-center gap-4 mb-1.5">
                    <span className="text-[10px] font-mono text-[#38BDF8] tracking-wider">
                      {inc.incidentId}
                    </span>
                    <span
                      className="px-1.5 py-0.5 text-[9px] font-mono tracking-wider uppercase"
                      style={{ color: sevColor, backgroundColor: `${sevColor}15`, border: `1px solid ${sevColor}30` }}
                    >
                      {inc.severity}
                    </span>
                    <span
                      className="px-1.5 py-0.5 text-[9px] font-mono tracking-wider uppercase"
                      style={{ color: classColor, backgroundColor: `${classColor}15`, border: `1px solid ${classColor}30` }}
                    >
                      {inc.classification.replace('_', ' ')}
                    </span>
                    <span
                      className="px-1.5 py-0.5 text-[9px] font-mono tracking-wider uppercase"
                      style={{ color: wfColor, backgroundColor: `${wfColor}15`, border: `1px solid ${wfColor}30` }}
                    >
                      {inc.workflowStatus}
                    </span>
                    <span className="text-[10px] font-mono text-[#8A94A6]/60 ml-auto">
                      {inc.merchantId}
                    </span>
                  </div>
                  <div className="flex items-center gap-4 text-[9px] font-mono text-[#8A94A6]/60">
                    <span className="flex items-center gap-1">
                      <Clock className="w-2.5 h-2.5" />
                      {new Date(inc.createdAt).toLocaleDateString()}
                    </span>
                    <span>{(inc.fraudProbability * 100).toFixed(1)}% fraud</span>
                    <span>{(inc.confidence * 100).toFixed(1)}% conf</span>
                    {inc.assignedAnalyst && (
                      <span className="flex items-center gap-1 text-[#38BDF8]/70">
                        <User className="w-2.5 h-2.5" />
                        {inc.assignedAnalyst}
                      </span>
                    )}
                    {inc.resolution && (
                      <span className="text-[#A78BFA]/70">{inc.resolution}</span>
                    )}
                  </div>
                  {inc.anomalySummary && (
                    <p className="text-[9px] font-mono text-[#8A94A6]/40 mt-1 line-clamp-1">
                      {inc.anomalySummary}
                    </p>
                  )}
                </motion.button>
              );
            })}
          </div>

          {/* Pagination */}
          <div className="flex items-center justify-between mt-4">
            <span className="text-[10px] font-mono text-[#8A94A6]/50">
              Showing {offset + 1}–{Math.min(offset + PAGE_SIZE, total)} of {total}
            </span>
            <div className="flex items-center gap-2">
              <button
                onClick={() => goToPage(urlState.page - 1)}
                disabled={urlState.page <= 1}
                className="p-1.5 text-[#8A94A6] hover:text-[#38BDF8] disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span className="text-[10px] font-mono text-[#8A94A6]">
                Page {urlState.page} of {totalPages}
              </span>
              <button
                onClick={() => goToPage(urlState.page + 1)}
                disabled={urlState.page >= totalPages}
                className="p-1.5 text-[#8A94A6] hover:text-[#38BDF8] disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </>
      )}
    </motion.div>
  );
}
