import { motion } from 'framer-motion';
import { Building2, Users } from 'lucide-react';

export default function Merchants() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="max-w-7xl mx-auto"
    >
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-lg bg-sus-green/20 flex items-center justify-center">
            <Building2 className="w-5 h-5 text-sus-green" />
          </div>
          <div>
            <h1 className="text-2xl font-bold">Merchants</h1>
            <p className="text-sus-text-dim text-sm font-mono">
              MERCHANT PORTFOLIO MANAGEMENT
            </p>
          </div>
        </div>
        <p className="text-sus-text-dim max-w-2xl">
          Monitor merchant activity, risk levels, and transaction patterns.
          View individual merchant profiles and historical performance.
        </p>
      </div>

      {/* Coming Soon Card */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.2 }}
        className="bg-sus-surface border border-sus-border rounded-2xl p-12 text-center"
      >
        <div className="w-16 h-16 rounded-full bg-sus-green/10 flex items-center justify-center mx-auto mb-6">
          <Users className="w-8 h-8 text-sus-green" />
        </div>
        <h3 className="text-xl font-semibold mb-2">Coming in Next Milestone</h3>
        <p className="text-sus-text-dim max-w-md mx-auto">
          Merchant portfolio management with individual profiles,
          risk assessments, and transaction history analysis.
        </p>
        <div className="mt-6 flex items-center justify-center gap-4 text-xs font-mono text-sus-text-dim">
          <span className="flex items-center gap-2">
            <Building2 className="w-4 h-4" />
            Merchant Profiles
          </span>
          <span>•</span>
          <span>Risk Assessment</span>
          <span>•</span>
          <span>Transaction History</span>
        </div>
      </motion.div>
    </motion.div>
  );
}
