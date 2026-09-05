/**
 * Investigation History Page
 *
 * Displays a paginated list of persisted investigations with search, filters,
 * and sorting. All state is persisted in URL query parameters for shareability.
 *
 * URL state: filters, sort_by, sort_order, page
 * Data flow: URL → state → dataSource.getInvestigationHistory(limit, offset, filters) → UI
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowLeft, AlertTriangle, ChevronLeft, ChevronRight, FileText, Clock, Search, X, ArrowUp, ArrowDown, GitCompare } from 'lucide-react';
import { dataSource } from '../data/dataSource';
import type { InvestigationHistoryItem } from '../api/mappers/investigationHistoryMapper';
import type { InvestigationHistoryFilters } from '../api/investigations';
import { formatDateTime } from '../utils/dateFormat';

const PAGE_SIZE = 10;

// ---------------------------------------------------------------------------
// Sort configuration
// ---------------------------------------------------------------------------

const SORT_OPTIONS = [
  { value: 'created_at', label: 'Date' },
  { value: 'total_results', label: 'Windows' },
  { value: 'spikes_detected', label: 'Spikes' },
  { value: 'fraud_incidents', label: 'Fraud' },
  { value: 'spike_rate', label: 'Spike Rate' },
] as const;

type SortBy = (typeof SORT_OPTIONS)[number]['value'];

function isValidSortBy(v: string | null): v is SortBy {
  return v !== null && (SORT_OPTIONS as readonly { value: string }[]).some((o) => o.value === v);
}

function isValidSortOrder(v: string | null): v is 'asc' | 'desc' {
  return v === 'asc' || v === 'desc';
}

// ---------------------------------------------------------------------------
// URL ↔ State helpers
// ---------------------------------------------------------------------------

function readFiltersFromURL(params: URLSearchParams) {
  return {
    investigationId: params.get('investigation_id') ?? '',
    status: params.get('status') ?? '',
    merchantFilter: params.get('merchant_filter') ?? '',
    createdFrom: params.get('created_from') ?? '',
    createdTo: params.get('created_to') ?? '',
  };
}

function readSortFromURL(params: URLSearchParams) {
  return {
    sortBy: isValidSortBy(params.get('sort_by')) ? params.get('sort_by') as SortBy : 'created_at',
    sortOrder: isValidSortOrder(params.get('sort_order')) ? params.get('sort_order') as 'asc' | 'desc' : 'desc',
  };
}

function readPageFromURL(params: URLSearchParams): number {
  const p = parseInt(params.get('page') ?? '1', 10);
  return isNaN(p) || p < 1 ? 1 : p;
}

function buildSearchParams(
  filters: { investigationId: string; status: string; merchantFilter: string; createdFrom: string; createdTo: string },
  sortBy: SortBy,
  sortOrder: 'asc' | 'desc',
  page: number,
): URLSearchParams {
  const p = new URLSearchParams();
  if (filters.investigationId) p.set('investigation_id', filters.investigationId);
  if (filters.status) p.set('status', filters.status);
  if (filters.merchantFilter) p.set('merchant_filter', filters.merchantFilter);
  if (filters.createdFrom) p.set('created_from', filters.createdFrom);
  if (filters.createdTo) p.set('created_to', filters.createdTo);
  if (sortBy !== 'created_at') p.set('sort_by', sortBy);
  if (sortOrder !== 'desc') p.set('sort_order', sortOrder);
  if (page > 1) p.set('page', String(page));
  return p;
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function InvestigationHistoryPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  // --- Read state from URL ---
  const urlFilters = useMemo(() => readFiltersFromURL(searchParams), [searchParams]);
  const urlSort = useMemo(() => readSortFromURL(searchParams), [searchParams]);
  const urlPage = useMemo(() => readPageFromURL(searchParams), [searchParams]);
  const hasActiveFilters = Object.values(urlFilters).some((v) => v !== '');

  // --- Local edit state for filter inputs (not yet applied) ---
  const [editFilters, setEditFilters] = useState(urlFilters);
  const [sortBy, setSortBy] = useState<SortBy>(urlSort.sortBy);
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>(urlSort.sortOrder);

  // --- Data state ---
  const [items, setItems] = useState<InvestigationHistoryItem[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [compareMode, setCompareMode] = useState(false);
  const [selectedForCompare, setSelectedForCompare] = useState<string[]>([]);

  const currentPage = urlPage;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const showingFrom = total === 0 ? 0 : offset + 1;
  const showingTo = Math.min(offset + PAGE_SIZE, total);

  const buildApiFilters = useCallback((f: typeof urlFilters): InvestigationHistoryFilters => {
    const result: InvestigationHistoryFilters = {};
    if (f.investigationId) result.investigation_id = f.investigationId;
    if (f.status) result.status = f.status;
    if (f.merchantFilter) result.merchant_filter = f.merchantFilter;
    if (f.createdFrom) result.created_from = f.createdFrom;
    if (f.createdTo) result.created_to = f.createdTo;
    return result;
  }, []);

  // --- Sync editFilters when URL changes externally ---
  useEffect(() => {
    setEditFilters(urlFilters);
  }, [urlFilters]);

  // --- Data fetching ---
  const loadPage = useCallback(
    async (page: number, filters: typeof urlFilters, sort: SortBy, order: 'asc' | 'desc') => {
      const newOffset = (page - 1) * PAGE_SIZE;
      setLoading(true);
      try {
        const apiFilters = buildApiFilters(filters);
        // Add sort params to the filters object so they flow through the data layer
        const fullFilters: InvestigationHistoryFilters = {
          ...apiFilters,
          sort_by: sort !== 'created_at' ? sort : undefined,
          sort_order: order !== 'desc' ? order : undefined,
        };
        const hasAny = Object.values(fullFilters).some((v) => v !== undefined);
        const result = await dataSource.getInvestigationHistory(
          PAGE_SIZE,
          newOffset,
          hasAny ? fullFilters : undefined,
        );
        setItems(result.items);
        setTotal(result.total);
        setOffset(result.offset);
      } catch (err) {
        setItems([]);
        setTotal(0);
        setError(err instanceof Error ? err.message : 'Failed to load investigation history');
      } finally {
        setLoading(false);
      }
    },
    [buildApiFilters],
  );

  // Fetch data whenever URL params change
  useEffect(() => {
    loadPage(urlPage, urlFilters, urlSort.sortBy, urlSort.sortOrder);
  }, [loadPage, urlPage, urlFilters, urlSort.sortBy, urlSort.sortOrder]);

  // --- URL update helpers ---
  const updateURL = useCallback(
    (f: typeof urlFilters, sort: SortBy, order: 'asc' | 'desc', page: number) => {
      const params = buildSearchParams(f, sort, order, page);
      setSearchParams(params, { replace: true });
    },
    [setSearchParams],
  );

  // --- Filter actions ---
  const handleApplyFilters = () => {
    updateURL(editFilters, sortBy, sortOrder, 1);
  };

  const handleClearFilters = () => {
    const empty = { investigationId: '', status: '', merchantFilter: '', createdFrom: '', createdTo: '' };
    setEditFilters(empty);
    updateURL(empty, sortBy, sortOrder, 1);
  };

  const handleFilterChange = (field: string, value: string) => {
    setEditFilters((prev) => ({ ...prev, [field]: value }));
  };

  // --- Sort actions ---
  const handleSortByChange = (newSortBy: SortBy) => {
    setSortBy(newSortBy);
    updateURL(editFilters, newSortBy, sortOrder, 1);
  };

  const handleSortOrderToggle = () => {
    const newOrder = sortOrder === 'desc' ? 'asc' : 'desc';
    setSortOrder(newOrder);
    updateURL(editFilters, sortBy, newOrder, 1);
  };

  // --- Pagination ---
  const goToPage = (page: number) => {
    updateURL(urlFilters, sortBy, sortOrder, page);
  };

  const goToPrev = () => {
    if (currentPage > 1) goToPage(currentPage - 1);
  };

  const goToNext = () => {
    if (currentPage < totalPages) goToPage(currentPage + 1);
  };

  // --- Date validation ---
  const dateError =
    editFilters.createdFrom &&
    editFilters.createdTo &&
    editFilters.createdFrom > editFilters.createdTo
      ? 'From date must be before To date'
      : null;

  const handleToggleCompareMode = () => {
    setCompareMode((prev) => !prev);
    setSelectedForCompare([]);
  };

  const handleSelectForCompare = (id: string) => {
    setSelectedForCompare((prev) => {
      if (prev.includes(id)) return prev.filter((x) => x !== id);
      if (prev.length >= 2) return [prev[1], id];
      return [...prev, id];
    });
  };

  const handleGoToCompare = () => {
    if (selectedForCompare.length === 2) {
      navigate(`/investigations/compare?base_id=${selectedForCompare[0]}&compare_id=${selectedForCompare[1]}`);
    }
  };

  const sortLabel = SORT_OPTIONS.find((o) => o.value === sortBy)?.label ?? 'Date';

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.4 }}
      className="px-[var(--content-px)] max-w-[var(--content-max)] mx-auto pt-8 pb-24"
    >
      {/* Back navigation */}
      <button
        onClick={() => navigate('/')}
        className="flex items-center gap-2 text-[11px] font-mono text-[#8A94A6] hover:text-[#38BDF8] transition-colors duration-200"
      >
        <ArrowLeft className="w-3.5 h-3.5" />
        INVESTIGATE
      </button>

      {/* Page header */}
      <div className="mt-8 mb-2">
        <div className="flex items-center gap-3 mb-2">
          <span className="text-[10px] font-mono tracking-[0.2em] uppercase text-[#8A94A6]">
            INVESTIGATION HISTORY
          </span>
          {total > 0 && (
            <span className="text-[10px] font-mono text-[#38BDF8]/60">
              {total} total
            </span>
          )}
        </div>
        <h1 className="text-2xl font-medium text-[#F3F4F6] tracking-tight mb-1">
          Investigation Log
        </h1>
        <p className="text-sm text-[#8A94A6]">
          Browse persisted investigation runs and review their results.
        </p>
      </div>

      {/* Divider */}
      <div className="h-px bg-[#1a1f2e]/60 my-6" />

      {/* Filter controls */}
      <div className="mb-6">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
          {/* Investigation ID search */}
          <div>
            <label className="block text-[9px] font-mono text-[#8A94A6] tracking-wider mb-1">
              INVESTIGATION ID
            </label>
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3 h-3 text-[#8A94A6]/40" />
              <input
                type="text"
                value={editFilters.investigationId}
                onChange={(e) => handleFilterChange('investigationId', e.target.value)}
                placeholder="INV-..."
                className="w-full pl-7 pr-3 py-1.5 text-[11px] font-mono text-[#F3F4F6] bg-[#0B0F18] border border-[#1a1f2e]/60 placeholder:text-[#8A94A6]/30 focus:border-[#38BDF8]/40 focus:outline-none transition-colors"
              />
            </div>
          </div>

          {/* Status filter */}
          <div>
            <label className="block text-[9px] font-mono text-[#8A94A6] tracking-wider mb-1">
              STATUS
            </label>
            <select
              value={editFilters.status}
              onChange={(e) => handleFilterChange('status', e.target.value)}
              className="w-full px-3 py-1.5 text-[11px] font-mono text-[#F3F4F6] bg-[#0B0F18] border border-[#1a1f2e]/60 focus:border-[#38BDF8]/40 focus:outline-none transition-colors appearance-none"
            >
              <option value="">All</option>
              <option value="completed">Completed</option>
            </select>
          </div>

          {/* Merchant filter */}
          <div>
            <label className="block text-[9px] font-mono text-[#8A94A6] tracking-wider mb-1">
              MERCHANT
            </label>
            <input
              type="text"
              value={editFilters.merchantFilter}
              onChange={(e) => handleFilterChange('merchantFilter', e.target.value)}
              placeholder="e.g. merchant_cloudserve"
              className="w-full px-3 py-1.5 text-[11px] font-mono text-[#F3F4F6] bg-[#0B0F18] border border-[#1a1f2e]/60 placeholder:text-[#8A94A6]/30 focus:border-[#38BDF8]/40 focus:outline-none transition-colors"
            />
          </div>

          {/* Date from */}
          <div>
            <label className="block text-[9px] font-mono text-[#8A94A6] tracking-wider mb-1">
              FROM
            </label>
            <input
              type="date"
              value={editFilters.createdFrom}
              onChange={(e) => handleFilterChange('createdFrom', e.target.value)}
              className="w-full px-3 py-1.5 text-[11px] font-mono text-[#F3F4F6] bg-[#0B0F18] border border-[#1a1f2e]/60 focus:border-[#38BDF8]/40 focus:outline-none transition-colors [color-scheme:dark]"
            />
          </div>

          {/* Date to */}
          <div>
            <label className="block text-[9px] font-mono text-[#8A94A6] tracking-wider mb-1">
              TO
            </label>
            <input
              type="date"
              value={editFilters.createdTo}
              onChange={(e) => handleFilterChange('createdTo', e.target.value)}
              className="w-full px-3 py-1.5 text-[11px] font-mono text-[#F3F4F6] bg-[#0B0F18] border border-[#1a1f2e]/60 focus:border-[#38BDF8]/40 focus:outline-none transition-colors [color-scheme:dark]"
            />
          </div>
        </div>

        {/* Date validation error */}
        {dateError && (
          <p className="text-[10px] font-mono text-[#FF5C5C] mt-1.5">
            {dateError}
          </p>
        )}

        {/* Filter actions + Sort + Compare */}
        <div className="flex items-center gap-3 mt-3 flex-wrap">
          <button
            onClick={handleApplyFilters}
            disabled={!!dateError}
            className="px-4 py-1.5 text-[11px] font-mono tracking-wider text-[#38BDF8] bg-[#38BDF8]/8 hover:bg-[#38BDF8]/15 border border-[#38BDF8]/20 disabled:opacity-40 disabled:cursor-not-allowed transition-all duration-200"
          >
            APPLY FILTERS
          </button>
          {hasActiveFilters && (
            <button
              onClick={handleClearFilters}
              className="flex items-center gap-1.5 px-3 py-1.5 text-[11px] font-mono text-[#8A94A6] hover:text-[#F3F4F6] transition-colors"
            >
              <X className="w-3 h-3" />
              CLEAR FILTERS
            </button>
          )}

          {/* Compare mode toggle */}
          <button
            onClick={handleToggleCompareMode}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-[11px] font-mono tracking-wider transition-all duration-200 border ${
              compareMode
                ? 'text-[#FBBF24] bg-[#FBBF24]/8 border-[#FBBF24]/30'
                : 'text-[#8A94A6] hover:text-[#F3F4F6] border-[#1a1f2e]/60'
            }`}
          >
            <GitCompare className="w-3 h-3" />
            {compareMode ? 'EXIT COMPARE' : 'COMPARE'}
          </button>

          {compareMode && selectedForCompare.length === 2 && (
            <button
              onClick={handleGoToCompare}
              className="px-4 py-1.5 text-[11px] font-mono tracking-wider text-[#FBBF24] bg-[#FBBF24]/8 hover:bg-[#FBBF24]/15 border border-[#FBBF24]/30 transition-all duration-200"
            >
              COMPARE ({selectedForCompare.length})
            </button>
          )}

          {compareMode && selectedForCompare.length > 0 && selectedForCompare.length < 2 && (
            <span className="text-[10px] font-mono text-[#FBBF24]/60">
              Select {2 - selectedForCompare.length} more
            </span>
          )}

          {/* Sort controls */}
          <div className="ml-auto flex items-center gap-2">
            <span className="text-[9px] font-mono text-[#8A94A6] tracking-wider hidden sm:inline">
              SORT BY
            </span>
            <div className="flex items-center">
              <select
                value={sortBy}
                onChange={(e) => handleSortByChange(e.target.value as SortBy)}
                className="px-2 py-1.5 text-[11px] font-mono text-[#F3F4F6] bg-[#0B0F18] border border-[#1a1f2e]/60 focus:border-[#38BDF8]/40 focus:outline-none transition-colors appearance-none pr-6"
              >
                {SORT_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
              <button
                onClick={handleSortOrderToggle}
                className="ml-1 p-1.5 text-[#8A94A6] hover:text-[#F3F4F6] transition-colors border border-[#1a1f2e]/60 bg-[#0B0F18]"
                title={sortOrder === 'desc' ? 'Descending (click for ascending)' : 'Ascending (click for descending)'}
              >
                {sortOrder === 'desc' ? (
                  <ArrowDown className="w-3.5 h-3.5" />
                ) : (
                  <ArrowUp className="w-3.5 h-3.5" />
                )}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Pagination info bar */}
      {total > 0 && !loading && (
        <div className="flex items-center justify-between mb-4">
          <span className="text-[11px] font-mono text-[#8A94A6]">
            Showing {showingFrom}–{showingTo} of {total}
            {sortBy !== 'created_at' && (
              <span className="text-[#38BDF8]/60 ml-2">
                · sorted by {sortLabel} {sortOrder === 'asc' ? '↑' : '↓'}
              </span>
            )}
          </span>
          <div className="flex items-center gap-1">
            <button
              onClick={goToPrev}
              disabled={currentPage <= 1}
              className="p-1.5 text-[#8A94A6] hover:text-[#F3F4F6] disabled:text-[#8A94A6]/30 disabled:cursor-not-allowed transition-colors"
              aria-label="Previous page"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="text-[11px] font-mono text-[#8A94A6] px-2">
              {currentPage}/{totalPages}
            </span>
            <button
              onClick={goToNext}
              disabled={currentPage >= totalPages}
              className="p-1.5 text-[#8A94A6] hover:text-[#F3F4F6] disabled:text-[#8A94A6]/30 disabled:cursor-not-allowed transition-colors"
              aria-label="Next page"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* Loading state */}
      {loading && (
        <div className="flex flex-col items-center gap-4 py-20">
          <div className="w-5 h-5 border-2 border-[#38BDF8]/30 border-t-[#38BDF8] rounded-full animate-spin" />
          <span className="text-xs font-mono text-[#8A94A6]">Loading investigations...</span>
        </div>
      )}

      {/* Error state */}
      {!loading && error && (
        <div className="flex flex-col items-center gap-4 py-20">
          <div className="w-12 h-12 rounded-full bg-[#FF5C5C]/10 flex items-center justify-center">
            <AlertTriangle className="w-5 h-5 text-[#FF5C5C]" />
          </div>
          <h2 className="text-lg font-medium text-[#F3F4F6]">Unable to load investigations</h2>
          <p className="text-sm text-[#8A94A6] max-w-md text-center">{error}</p>
          <button
            onClick={() => { setError(null); loadPage(urlPage, urlFilters, urlSort.sortBy, urlSort.sortOrder); }}
            className="mt-2 px-4 py-2 text-xs font-mono tracking-wider text-[#38BDF8] bg-[#38BDF8]/8 hover:bg-[#38BDF8]/15 border border-[#38BDF8]/20 transition-colors"
          >
            RETRY
          </button>
        </div>
      )}

      {/* Empty state — no data at all */}
      {!loading && items.length === 0 && !hasActiveFilters && (
        <div className="flex flex-col items-center gap-4 py-20">
          <div className="w-12 h-12 rounded-full bg-[#1E293B]/60 flex items-center justify-center">
            <FileText className="w-5 h-5 text-[#8A94A6]" />
          </div>
          <h2 className="text-lg font-medium text-[#F3F4F6]">No investigations yet</h2>
          <p className="text-sm text-[#8A94A6] max-w-md text-center">
            Run your first investigation to start detecting unusual transaction activity.
          </p>
          <button
            onClick={() => navigate('/')}
            className="mt-2 px-4 py-2 text-xs font-mono tracking-wider text-[#38BDF8] bg-[#38BDF8]/8 hover:bg-[#38BDF8]/15 transition-colors"
          >
            GO TO INVESTIGATE
          </button>
        </div>
      )}

      {/* Empty state — filters returned nothing */}
      {!loading && items.length === 0 && hasActiveFilters && (
        <div className="flex flex-col items-center gap-4 py-20">
          <div className="w-12 h-12 rounded-full bg-[#1E293B]/60 flex items-center justify-center">
            <Search className="w-5 h-5 text-[#8A94A6]" />
          </div>
          <h2 className="text-lg font-medium text-[#F3F4F6]">No matching investigations</h2>
          <p className="text-sm text-[#8A94A6] max-w-md text-center">
            No investigations match the current filters. Try adjusting your search criteria.
          </p>
          <button
            onClick={handleClearFilters}
            className="mt-2 px-4 py-2 text-xs font-mono tracking-wider text-[#38BDF8] bg-[#38BDF8]/8 hover:bg-[#38BDF8]/15 rounded-sm transition-colors"
          >
            CLEAR FILTERS
          </button>
        </div>
      )}

      {/* Investigation list */}
      {!loading && items.length > 0 && (
        <div className="space-y-2">
          <AnimatePresence mode="wait">
            <motion.div
              key={`${offset}-${sortBy}-${sortOrder}`}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="space-y-2"
            >
              {items.map((item) => (
                <InvestigationRow
                  key={item.investigationId}
                  item={item}
                  onClick={() => {
                    if (!compareMode) navigate(`/investigations/${item.investigationId}`);
                  }}
                  compareMode={compareMode}
                  selected={selectedForCompare.includes(item.investigationId)}
                  onSelect={() => handleSelectForCompare(item.investigationId)}
                />
              ))}
            </motion.div>
          </AnimatePresence>
        </div>
      )}

      {/* Bottom pagination */}
      {!loading && totalPages > 1 && (
        <div className="flex items-center justify-between mt-6 pt-4 border-t border-[#1a1f2e]/60">
          <span className="text-[11px] font-mono text-[#8A94A6]">
            Page {currentPage} of {totalPages}
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={goToPrev}
              disabled={currentPage <= 1}
              className="px-3 py-1.5 text-[11px] font-mono text-[#8A94A6] border border-[#1a1f2e]/60 hover:border-[#2a3040] hover:text-[#F3F4F6] disabled:text-[#8A94A6]/30 disabled:border-[#1a1f2e]/30 disabled:cursor-not-allowed transition-all duration-200"
            >
              Previous
            </button>
            <button
              onClick={goToNext}
              disabled={currentPage >= totalPages}
              className="px-3 py-1.5 text-[11px] font-mono text-[#8A94A6] border border-[#1a1f2e]/60 hover:border-[#2a3040] hover:text-[#F3F4F6] disabled:text-[#8A94A6]/30 disabled:border-[#1a1f2e]/30 disabled:cursor-not-allowed transition-all duration-200"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </motion.div>
  );
}

// ------------------------------------------------------------------
// Investigation row
// ------------------------------------------------------------------

function InvestigationRow({
  item,
  onClick,
  compareMode = false,
  selected = false,
  onSelect,
}: {
  item: InvestigationHistoryItem;
  onClick: () => void;
  compareMode?: boolean;
  selected?: boolean;
  onSelect?: () => void;
}) {
  const hasHighFraud = item.fraudIncidents > 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      onClick={compareMode ? onSelect : onClick}
      className={`flex items-center gap-6 py-3.5 px-5 border bg-[#0B0F18]/60 cursor-pointer transition-all duration-200 ${
        selected
          ? 'border-[#FBBF24]/40 bg-[#FBBF24]/5'
          : 'border-[#1E293B]/60 hover:border-[#38BDF8]/20 hover:bg-[#0D111A]/80'
      }`}
    >
      {/* Compare checkbox */}
      {compareMode && (
        <div
          className={`w-4 h-4 rounded-sm border shrink-0 flex items-center justify-center transition-colors ${
            selected ? 'bg-[#FBBF24] border-[#FBBF24]' : 'border-[#8A94A6]/40'
          }`}
        >
          {selected && (
            <svg className="w-2.5 h-2.5 text-[#0B0F18]" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M2 6l3 3 5-5" />
            </svg>
          )}
        </div>
      )}

      {/* Investigation info */}
      <div className="flex-1 min-w-0 shrink-0">
        <div className="flex items-center gap-2">
          <span className="text-[11px] font-mono text-[#38BDF8] tracking-wider truncate">
            {item.investigationId}
          </span>
          <span className="text-[9px] font-mono tracking-wider uppercase px-1.5 py-0.5 rounded-sm bg-[#38BDF8]/8 text-[#38BDF8]/80">
            {item.status}
          </span>
        </div>
        {item.datasetFilename && (
          <p className="text-[9px] font-mono text-[#8A94A6]/50 truncate mt-0.5">
            {item.datasetFilename}
          </p>
        )}
      </div>

      {/* Timestamp */}
      <span className="text-[10px] font-mono text-[#8A94A6] shrink-0 flex items-center gap-1.5">
        <Clock className="w-3 h-3 opacity-50" />
        {formatDateTime(item.createdAt)}
      </span>

      {/* Metrics */}
      <div className="flex items-center gap-4 text-[10px] font-mono ml-auto">
        <span className="text-[#8A94A6]">
          {item.totalResults} windows
        </span>
        {item.spikesDetected > 0 && (
          <span className="text-[#38BDF8]">
            {item.spikesDetected} spikes
          </span>
        )}
        <span style={{ color: hasHighFraud ? '#FF5C5C' : '#8A94A6' }}>
          {item.fraudIncidents} fraud
        </span>
        <span className="text-[#34D399]">
          {item.organicIncidents} organic
        </span>
        {item.reviewRequired > 0 && (
          <span className="text-[#FBBF24]">
            {item.reviewRequired} review
          </span>
        )}
      </div>
    </motion.div>
  );
}
