import { motion, AnimatePresence } from 'framer-motion';
import { ChevronRight } from 'lucide-react';
import { useInvestigation } from '../../context/InvestigationContext';

export function InvestigationPath() {
  const { investigationPath } = useInvestigation();

  if (investigationPath.length === 0) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: -5 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -5 }}
        transition={{ duration: 0.2 }}
        className="flex items-center gap-1.5 mb-4"
      >
        <span className="text-[9px] font-mono text-[#8A94A6]/40 tracking-[0.15em] mr-1">
          PATH
        </span>
        {investigationPath.map((label, idx) => (
          <span key={`${label}-${idx}`} className="flex items-center gap-1.5">
            {idx > 0 && <ChevronRight className="w-2.5 h-2.5 text-[#8A94A6]/30" />}
            <span className={`text-[10px] font-mono tracking-wider ${
              idx === investigationPath.length - 1
                ? 'text-[#38BDF8]'
                : 'text-[#8A94A6]/60'
            }`}>
              {label.toUpperCase()}
            </span>
          </span>
        ))}
      </motion.div>
    </AnimatePresence>
  );
}
