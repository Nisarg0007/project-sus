import { motion } from 'framer-motion';

interface IncidentsHeaderProps {
  totalIncidents: number;
  criticalCount: number;
  highCount: number;
  reviewCount: number;
}

export function IncidentsHeader({ totalIncidents, criticalCount, reviewCount }: IncidentsHeaderProps) {
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
          INCIDENT INTELLIGENCE
        </span>
        <div className="h-px flex-1 bg-[#1a1f2e]" />
      </motion.div>

      {/* Main composition: metrics embedded with headline */}
      <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-8">
        {/* Left: headline + description */}
        <div className="max-w-xl">
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.1 }}
            className="text-3xl sm:text-4xl lg:text-5xl font-light leading-[1.15] tracking-tight mb-4"
          >
            <span className="text-[#F3F4F6]">Every anomaly leaves </span>
            <span className="text-[#F3F4F6] font-normal">evidence</span>
            <span className="text-[#F3F4F6]">.</span>
          </motion.h1>

          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.6, delay: 0.3 }}
            className="text-[#8A94A6] text-sm sm:text-base leading-relaxed"
          >
            Prioritized investigations generated from transaction behavior,
            anomaly detection, and cause classification.
          </motion.p>
        </div>

        {/* Right: embedded metrics */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.4 }}
          className="flex items-end gap-8 lg:gap-10 flex-shrink-0"
        >
          <div className="text-right">
            <div className="text-4xl lg:text-5xl font-light text-[#FF5C5C] tracking-tight">
              {criticalCount}
            </div>
            <div className="text-[10px] font-mono text-[#8A94A6] tracking-[0.15em] mt-1">
              CRITICAL INCIDENTS
            </div>
          </div>
          <div className="w-px h-12 bg-[#1a1f2e] self-center" />
          <div className="text-right">
            <div className="text-4xl lg:text-5xl font-light text-[#FBBF24] tracking-tight">
              {reviewCount}
            </div>
            <div className="text-[10px] font-mono text-[#8A94A6] tracking-[0.15em] mt-1">
              NEED REVIEW
            </div>
          </div>
          <div className="w-px h-12 bg-[#1a1f2e] self-center" />
          <div className="text-right">
            <div className="text-4xl lg:text-5xl font-light text-[#F3F4F6] tracking-tight">
              {totalIncidents}
            </div>
            <div className="text-[10px] font-mono text-[#8A94A6] tracking-[0.15em] mt-1">
              TOTAL INCIDENTS
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
