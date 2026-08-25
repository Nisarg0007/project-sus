import { motion } from 'framer-motion';

export function MerchantsHeader() {
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
          MERCHANT INTELLIGENCE
        </span>
        <div className="h-px flex-1 bg-[#1a1f2e]" />
      </motion.div>

      {/* Headline + metrics composition */}
      <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-8">
        <div className="max-w-xl">
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.1 }}
            className="text-3xl sm:text-4xl lg:text-5xl font-light leading-[1.15] tracking-tight mb-3"
          >
            <span className="text-[#F3F4F6]">Normal is different </span>
            <span className="text-[#F3F4F6] font-normal">for everyone</span>
            <span className="text-[#F3F4F6]">.</span>
          </motion.h1>

          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.6, delay: 0.3 }}
            className="text-[#8A94A6] text-sm sm:text-base leading-relaxed"
          >
            SUS builds a behavioral baseline for every merchant,
            then identifies the moments when that behavior changes.
          </motion.p>
        </div>

        {/* Inline metrics */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.4 }}
          className="flex items-end gap-8 lg:gap-10 flex-shrink-0"
        >
          <div className="text-right">
            <div className="text-4xl lg:text-5xl font-light text-[#38BDF8] tracking-tight">8</div>
            <div className="text-[10px] font-mono text-[#8A94A6] tracking-[0.15em] mt-1">MERCHANTS MONITORED</div>
          </div>
          <div className="w-px h-12 bg-[#1a1f2e] self-center" />
          <div className="text-right">
            <div className="text-4xl lg:text-5xl font-light text-[#38BDF8] tracking-tight">360</div>
            <div className="text-[10px] font-mono text-[#8A94A6] tracking-[0.15em] mt-1">BEHAVIORAL WINDOWS</div>
          </div>
          <div className="w-px h-12 bg-[#1a1f2e] self-center" />
          <div className="text-right">
            <div className="text-4xl lg:text-5xl font-light text-[#F3F4F6] tracking-tight">73</div>
            <div className="text-[10px] font-mono text-[#8A94A6] tracking-[0.15em] mt-1">SPIKES OBSERVED</div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
