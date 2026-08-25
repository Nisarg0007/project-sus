import { motion } from 'framer-motion';
import { AlertTriangle, Shield } from 'lucide-react';

export default function Incidents() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="max-w-7xl mx-auto"
    >
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-lg bg-sus-red/20 flex items-center justify-center">
            <AlertTriangle className="w-5 h-5 text-sus-red" />
          </div>
          <div>
            <h1 className="text-2xl font-bold">Incidents</h1>
            <p className="text-sus-text-dim text-sm font-mono">
              FRAUD INCIDENT MANAGEMENT
            </p>
          </div>
        </div>
        <p className="text-sus-text-dim max-w-2xl">
          Track and manage fraud incidents detected by SUS.
          Review evidence, assign investigation status, and track resolution.
        </p>
      </div>

      {/* Coming Soon Card */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.2 }}
        className="bg-sus-surface border border-sus-border rounded-2xl p-12 text-center"
      >
        <div className="w-16 h-16 rounded-full bg-sus-red/10 flex items-center justify-center mx-auto mb-6">
          <Shield className="w-8 h-8 text-sus-red" />
        </div>
        <h3 className="text-xl font-semibold mb-2">Coming in Next Milestone</h3>
        <p className="text-sus-text-dim max-w-md mx-auto">
          Full incident management workflow with status tracking,
          evidence review, and resolution workflows.
        </p>
        <div className="mt-6 flex items-center justify-center gap-4 text-xs font-mono text-sus-text-dim">
          <span className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4" />
            Incident Tracking
          </span>
          <span>•</span>
          <span>Evidence Review</span>
          <span>•</span>
          <span>Resolution Workflows</span>
        </div>
      </motion.div>
    </motion.div>
  );
}
