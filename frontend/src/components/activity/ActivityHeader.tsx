import { motion } from 'framer-motion';
import { ChevronDown } from 'lucide-react';
import { TimeRange } from '../../types';
import { merchants } from '../../data/mockData';

interface ActivityHeaderProps {
  selectedMerchant: string;
  onMerchantChange: (merchantId: string) => void;
  timeRange: TimeRange;
  onTimeRangeChange: (range: TimeRange) => void;
}

const timeRanges: Array<{ value: TimeRange; label: string }> = [
  { value: '7d', label: 'LAST 7 DAYS' },
  { value: '14d', label: 'LAST 14 DAYS' },
  { value: '30d', label: 'LAST 30 DAYS' },
  { value: '45d', label: 'LAST 45 DAYS' },
];

export function ActivityHeader({
  selectedMerchant,
  onMerchantChange,
  timeRange,
  onTimeRangeChange,
}: ActivityHeaderProps) {
  const selectedMerchantLabel = selectedMerchant === 'all'
    ? 'ALL MERCHANTS'
    : merchants.find(m => m.id === selectedMerchant)?.name.toUpperCase() ?? selectedMerchant;

  const selectedTimeRangeLabel = timeRanges.find(r => r.value === timeRange)?.label ?? 'LAST 45 DAYS';

  return (
    <section className="py-12 lg:py-16 px-[var(--content-px)] max-w-[var(--content-max)] mx-auto">
      {/* Top label */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="flex items-center gap-4 mb-8"
      >
        <span className="text-[11px] font-mono text-[#8A94A6]/60 tracking-[0.15em]">
          ACTIVITY INTELLIGENCE
        </span>
        <div className="h-px flex-1 bg-[#1a1f2e]" />
      </motion.div>

      {/* Headline + Controls row */}
      <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-8">
        {/* Left: Headline + description */}
        <div className="max-w-2xl">
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.1 }}
            className="text-3xl sm:text-4xl lg:text-5xl font-light leading-[1.15] tracking-tight mb-3"
          >
            <span className="text-[#F3F4F6]">Every spike tells </span>
            <span className="text-[#F3F4F6] font-normal">a different story</span>
            <span className="text-[#F3F4F6]">.</span>
          </motion.h1>

          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.6, delay: 0.3 }}
            className="text-[#8A94A6] text-[15px] leading-relaxed"
          >
            Explore transaction behavior across merchants and identify where activity
            diverges from normal patterns.
          </motion.p>
        </div>

        {/* Right: Controls */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.4 }}
          className="flex items-center gap-3 flex-shrink-0"
        >
          {/* Merchant selector */}
          <div className="relative group">
            <select
              value={selectedMerchant}
              onChange={(e) => onMerchantChange(e.target.value)}
              className="appearance-none px-3 py-1.5 pr-8 text-xs font-mono tracking-wider text-[#8A94A6]
                         bg-[#0D111A] border border-[#1a1f2e] rounded-sm cursor-pointer
                         hover:border-[#2a3040] hover:text-[#F3F4F6] transition-colors duration-200
                         focus:outline-none focus:border-[#38BDF8]/30"
            >
              <option value="all">ALL MERCHANTS</option>
              {merchants.map(m => (
                <option key={m.id} value={m.id}>{m.name.toUpperCase()}</option>
              ))}
            </select>
            <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-3 h-3 text-[#8A94A6] pointer-events-none" />
          </div>

          {/* Time range selector */}
          <div className="relative">
            <select
              value={timeRange}
              onChange={(e) => onTimeRangeChange(e.target.value as TimeRange)}
              className="appearance-none px-3 py-1.5 pr-8 text-xs font-mono tracking-wider text-[#8A94A6]
                         bg-[#0D111A] border border-[#1a1f2e] rounded-sm cursor-pointer
                         hover:border-[#2a3040] hover:text-[#F3F4F6] transition-colors duration-200
                         focus:outline-none focus:border-[#38BDF8]/30"
            >
              {timeRanges.map(r => (
                <option key={r.value} value={r.value}>{r.label}</option>
              ))}
            </select>
            <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-3 h-3 text-[#8A94A6] pointer-events-none" />
          </div>

          {/* Current selection label (hidden on mobile, shown for context) */}
          <span className="hidden xl:block text-[10px] font-mono text-[#8A94A6]/60 tracking-wider max-w-[200px] truncate">
            {selectedMerchantLabel} · {selectedTimeRangeLabel}
          </span>
        </motion.div>
      </div>
    </section>
  );
}
