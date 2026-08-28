/**
 * Investigation History Page
 *
 * Displays a paginated list of all persisted investigations.
 * Each item is clickable and navigates to the InvestigationDetailPage.
 *
 * Data flow: dataSource.getInvestigationHistory(limit, offset) → UI
 */

import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowLeft, ChevronLeft, ChevronRight, FileText, Clock } from 'lucide-react';
import { dataSource } from '../data/dataSource';
import type { InvestigationHistoryItem } from '../api/mappers/investigationHistoryMapper';

const PAGE_SIZE = 10;

// ------------------------------------------------------------------
// Main Page
// ------------------------------------------------------------------

export default function InvestigationHistoryPage() {
  const navigate = useNavigate();

  const [items, setItems] = useState<InvestigationHistoryItem[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);

  const currentPage = Math.floor(offset / PAGE_SIZE) + 1;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const showingFrom = total === 0 ? 0 : offset + 1;
  const showingTo = Math.min(offset + PAGE_SIZE, total);

  const loadPage = useCallback(async (newOffset: number) => {
    setLoading(true);
    try {
      const result = await dataSource.getInvestigationHistory(PAGE_SIZE, newOffset);
      setItems(result.items);
      setTotal(result.total);
      setOffset(result.offset);
    } catch {
      setItems([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadPage(0);
  }, [loadPage]);

  const goToPrev = () => {
    if (offset > 0) {
      loadPage(Math.max(0, offset - PAGE_SIZE));
    }
  };

  const goToNext = () => {
    if (offset + PAGE_SIZE < total) {
      loadPage(offset + PAGE_SIZE);
    }
  };

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
        MISSION CONTROL
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

      {/* Pagination info bar */}
      {total > 0 && !loading && (
        <div className="flex items-center justify-between mb-4">
          <span className="text-[11px] font-mono text-[#8A94A6]">
            Showing {showingFrom}–{showingTo} of {total}
          </span>
          <div className="flex items-center gap-1">
            <button
              onClick={goToPrev}
              disabled={offset === 0}
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
              disabled={offset + PAGE_SIZE >= total}
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

      {/* Empty state */}
      {!loading && items.length === 0 && (
        <div className="flex flex-col items-center gap-4 py-20">
          <div className="w-12 h-12 rounded-full bg-[#1E293B]/60 flex items-center justify-center">
            <FileText className="w-5 h-5 text-[#8A94A6]" />
          </div>
          <h2 className="text-lg font-medium text-[#F3F4F6]">No investigations yet</h2>
          <p className="text-sm text-[#8A94A6] max-w-md text-center">
            Run your first investigation from Mission Control to see persisted results here.
            {dataSource.getMode() === 'mock' && (
              <span className="block mt-2 text-xs text-[#8A94A6]/60">
                Investigation history is only available in API mode.
              </span>
            )}
          </p>
          <button
            onClick={() => navigate('/')}
            className="mt-2 px-4 py-2 text-xs font-mono tracking-wider text-[#38BDF8] bg-[#38BDF8]/8 hover:bg-[#38BDF8]/15 rounded-sm transition-colors"
          >
            GO TO MISSION CONTROL
          </button>
        </div>
      )}

      {/* Investigation list */}
      {!loading && items.length > 0 && (
        <div className="space-y-2">
          <AnimatePresence mode="wait">
            <motion.div
              key={offset}
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
                  onClick={() => navigate(`/investigations/${item.investigationId}`)}
                />
              ))}
            </motion.div>
          </AnimatePresence>
        </div>
      )}

      {/* Bottom pagination */}
      {!loading && total > PAGE_SIZE && (
        <div className="flex items-center justify-between mt-6 pt-4 border-t border-[#1a1f2e]/60">
          <span className="text-[11px] font-mono text-[#8A94A6]">
            Page {currentPage} of {totalPages}
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={goToPrev}
              disabled={offset === 0}
              className="px-3 py-1.5 text-[11px] font-mono text-[#8A94A6] border border-[#1a1f2e]/60 hover:border-[#2a3040] hover:text-[#F3F4F6] disabled:text-[#8A94A6]/30 disabled:border-[#1a1f2e]/30 disabled:cursor-not-allowed transition-all duration-200"
            >
              Previous
            </button>
            <button
              onClick={goToNext}
              disabled={offset + PAGE_SIZE >= total}
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
}: {
  item: InvestigationHistoryItem;
  onClick: () => void;
}) {
  const hasHighFraud = item.fraudIncidents > 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      onClick={onClick}
      className="flex items-center gap-6 py-3.5 px-5 border border-[#1E293B]/60 bg-[#0B0F18]/60 hover:border-[#38BDF8]/20 hover:bg-[#0D111A]/80 cursor-pointer transition-all duration-200"
    >
      {/* Investigation ID */}
      <span className="text-[11px] font-mono text-[#38BDF8] tracking-wider shrink-0 w-[160px] truncate">
        {item.investigationId}
      </span>

      {/* Status badge */}
      <span className="text-[9px] font-mono tracking-wider uppercase px-2 py-0.5 rounded-sm shrink-0 bg-[#38BDF8]/8 text-[#38BDF8]/80">
        {item.status}
      </span>

      {/* Timestamp */}
      <span className="text-[10px] font-mono text-[#8A94A6] shrink-0 flex items-center gap-1.5">
        <Clock className="w-3 h-3 opacity-50" />
        {item.createdAtFormatted}
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
