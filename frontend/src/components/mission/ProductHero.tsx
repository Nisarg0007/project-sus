import { motion } from 'framer-motion';

const metricItems = [
  { key: 'monitoredWindows' as const, value: 360, label: 'MONITORED', sublabel: 'WINDOWS', color: '#38BDF8' },
  { key: 'spikesDetected' as const, value: 73, label: 'SPIKES', sublabel: 'DETECTED', color: '#38BDF8' },
  { key: 'fraudIncidents' as const, value: 31, label: 'FRAUD', sublabel: 'INCIDENTS', color: '#FF5C5C' },
  { key: 'needsReview' as const, value: 3, label: 'NEED', sublabel: 'REVIEW', color: '#FBBF24' },
];

export function ProductHero() {
  return (
    <section className="relative py-20 px-8 max-w-[1600px] mx-auto overflow-hidden">
      {/* Subtle radial background glow */}
      <div
        className="absolute inset-0 opacity-[0.04] pointer-events-none"
        style={{
          background: 'radial-gradient(ellipse 80% 60% at 25% 30%, #38BDF8 0%, transparent 70%)',
        }}
      />
      <div
        className="absolute inset-0 opacity-[0.02] pointer-events-none"
        style={{
          background: 'radial-gradient(ellipse 60% 50% at 75% 60%, #FF5C5C 0%, transparent 70%)',
        }}
      />

      <div className="relative">
        {/* Top label */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="flex items-center gap-4 mb-10"
        >
          <span className="text-xs font-mono text-[#8A94A6] tracking-[0.2em]">
            SPIKE UNDERSTANDING SYSTEM
          </span>
          <div className="h-px flex-1 bg-[#1a1f2e]" />
        </motion.div>

        {/* Main headline */}
        <div className="mb-8">
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.1 }}
            className="text-4xl sm:text-5xl lg:text-6xl font-light leading-[1.15] tracking-tight max-w-3xl"
          >
            <span className="text-[#F3F4F6]">Understand the spike.</span>
            <br />
            <span className="text-[#F3F4F6]">Before it becomes an </span>
            <span className="text-[#FF5C5C] font-normal">incident</span>
            <span className="text-[#F3F4F6]">.</span>
          </motion.h1>
        </div>

        {/* Description */}
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.6, delay: 0.3 }}
          className="text-[#8A94A6] text-base sm:text-lg leading-relaxed max-w-2xl mb-16"
        >
          SUS detects transaction anomalies across your merchant portfolio, classifies their cause,
          and surfaces the evidence you need to act — before fraud becomes a loss.
        </motion.p>

        {/* Metrics composition */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.4 }}
          className="grid grid-cols-2 lg:grid-cols-4 gap-px bg-[#1a1f2e] rounded-sm overflow-hidden max-w-5xl"
        >
          {metricItems.map((item, index) => (
            <motion.div
              key={item.key}
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.5 + index * 0.1 }}
              className="bg-[#0D111A] px-8 py-10 relative group"
            >
              {/* Top accent line */}
              <div
                className="absolute top-0 left-0 right-0 h-px opacity-40"
                style={{ backgroundColor: item.color }}
              />

              {/* Value */}
              <div
                className="text-5xl lg:text-6xl font-light tracking-tight mb-3"
                style={{ color: item.color }}
              >
                {item.value}
              </div>

              {/* Label */}
              <div className="font-mono text-xs tracking-[0.15em] text-[#8A94A6]">
                <span className="block">{item.label}</span>
                <span className="block mt-0.5">{item.sublabel}</span>
              </div>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
