import { motion } from 'framer-motion';
import { AlertTriangle, ExternalLink } from 'lucide-react';
import { FullIncident } from '../../types';
import { useNavigation } from '../../hooks/useNavigation';

interface PriorityStripProps {
  incidents: FullIncident[];
  selectedId: string | null;
  onSelect: (incident: FullIncident) => void;
}

export function PriorityStrip({ incidents, selectedId, onSelect }: PriorityStripProps) {
  const { navigateToMerchantFromActivity } = useNavigation();
  // Show top critical/high incidents
  const priorityIncidents = incidents
    .filter(i => i.severity === 'critical' || i.severity === 'high')
    .slice(0, 3);

  return (
    <section className="px-[var(--content-px)] max-w-[var(--content-max)] mx-auto mb-8">
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.5 }}
      >
        {/* Strip header */}
        <div className="flex items-center gap-3 mb-4">
          <AlertTriangle className="w-3.5 h-3.5 text-[#FF5C5C]" />
          <span className="text-[10px] font-mono text-[#FF5C5C] tracking-[0.15em]">
            CRITICAL NOW
          </span>
        </div>

        {/* Strip items */}
        <div className="flex gap-3 overflow-x-auto pb-2 -mx-2 px-2">
          {priorityIncidents.map((incident, idx) => {
            const isSelected = selectedId === incident.id;
            return (
              <motion.button
                key={incident.id}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.3, delay: 0.6 + idx * 0.08 }}
                onClick={() => onSelect(incident)}
                className={`flex-shrink-0 w-[280px] text-left p-4 rounded-sm border transition-all duration-200 ${
                  isSelected
                    ? 'bg-[#FF5C5C]/8 border-[#FF5C5C]/30'
                    : 'bg-[#0D111A] border-[#1a1f2e] hover:border-[#2a3040]'
                }`}
              >
                <div className="flex items-center gap-2 mb-2">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      navigateToMerchantFromActivity(incident.merchantId);
                    }}
                    className="flex items-center gap-1 text-[10px] font-mono text-[#FF5C5C] tracking-wider hover:text-[#F3F4F6] transition-colors"
                  >
                    {incident.merchantName}
                    <ExternalLink className="w-2.5 h-2.5 opacity-50" />
                  </button>
                </div>
                <p className="text-sm text-[#F3F4F6] leading-snug mb-3 line-clamp-2">
                  {incident.headline}
                </p>
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-mono text-[#8A94A6] tracking-wider">
                    FRAUD PROBABILITY
                  </span>
                  <span className="text-sm font-mono text-[#FF5C5C]">
                    {(incident.fraudProbability * 100).toFixed(1)}%
                  </span>
                </div>
              </motion.button>
            );
          })}
        </div>
      </motion.div>
    </section>
  );
}
