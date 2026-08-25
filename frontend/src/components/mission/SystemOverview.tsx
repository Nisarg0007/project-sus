import { motion } from 'framer-motion';
import { DashboardMetrics } from '../../types';

interface SystemOverviewProps {
  metrics: DashboardMetrics;
}

export function SystemOverview({ metrics }: SystemOverviewProps) {
  const items = [
    { value: metrics.monitoredWindows, label: 'windows analyzed' },
    { value: metrics.spikesDetected, label: 'anomalies detected' },
    { value: metrics.fraudIncidents, label: 'fraud incidents' },
    { value: metrics.needsReview, label: 'require review' },
  ];

  return (
    <section className="relative py-16 px-8 max-w-[1600px] mx-auto">
      <div className="flex items-center gap-4 mb-12">
        <span className="text-xs font-mono text-[#8A94A6] tracking-widest">
          SYSTEM OVERVIEW
        </span>
        <div className="h-px flex-1 bg-[#1a1f2e]" />
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-8">
        {items.map((item, index) => (
          <motion.div
            key={item.label}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: index * 0.1 }}
            className="text-center"
          >
            <div className="text-4xl lg:text-5xl font-light text-[#F3F4F6] mb-2">
              {item.value}
            </div>
            <div className="text-xs font-mono text-[#8A94A6] tracking-wider">
              {item.label}
            </div>
          </motion.div>
        ))}
      </div>
    </section>
  );
}
