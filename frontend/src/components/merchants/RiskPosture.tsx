import { motion } from 'framer-motion';
import { MerchantProfile } from '../../types';

interface RiskPostureProps {
  profile: MerchantProfile;
}

const postureConfig: Record<string, { color: string; label: string; description: string; barWidth: number }> = {
  normal: {
    color: '#34D399',
    label: 'NORMAL',
    description: 'No sustained deviation from expected behavioral patterns.',
    barWidth: 15,
  },
  watch: {
    color: '#FBBF24',
    label: 'WATCH',
    description: 'Minor behavioral deviations detected. Monitoring for further changes.',
    barWidth: 45,
  },
  high_attention: {
    color: '#FF5C5C',
    label: 'HIGH ATTENTION',
    description: 'Multiple anomalies detected within the monitoring period. Active investigation recommended.',
    barWidth: 80,
  },
};

export function RiskPosture({ profile }: RiskPostureProps) {
  const config = postureConfig[profile.riskPosture];

  // Calculate stability score based on fraud count and risk
  const stabilityScore = Math.max(0, 100 - (profile.fraudCount * 30) - (profile.reviewCount * 10) - (profile.organicCount * 0));

  return (
    <div>
      <div className="flex items-center gap-4 mb-4">
        <span className="text-[10px] font-mono text-[#8A94A6] tracking-[0.2em]">CURRENT RISK POSTURE</span>
        <div className="h-px flex-1 bg-[#1a1f2e]" />
      </div>

      <div className="bg-[#0D111A] border border-[#1a1f2e] rounded-sm p-6">
        <div className="flex items-start justify-between mb-5">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: config.color }} />
              <span className="text-lg font-medium tracking-wide" style={{ color: config.color }}>
                {config.label}
              </span>
            </div>
            <p className="text-sm text-[#8A94A6] leading-relaxed max-w-md">
              {config.description}
            </p>
          </div>

          {/* Confidence ring */}
          <div className="text-right flex-shrink-0 ml-6">
            <svg width="64" height="64" viewBox="0 0 64 64">
              <circle cx="32" cy="32" r="28" fill="none" stroke="#1a1f2e" strokeWidth="3" />
              <motion.circle
                cx="32" cy="32" r="28"
                fill="none"
                stroke={config.color}
                strokeWidth="3"
                strokeDasharray={`${(stabilityScore / 100) * 175.9} 175.9`}
                strokeLinecap="round"
                transform="rotate(-90 32 32)"
                initial={{ strokeDasharray: '0 175.9' }}
                animate={{ strokeDasharray: `${(stabilityScore / 100) * 175.9} 175.9` }}
                transition={{ duration: 1, delay: 0.3 }}
              />
              <text x="32" y="36" textAnchor="middle" fill="#F3F4F6" fontSize="14" fontFamily="monospace" fontWeight="500">
                {stabilityScore}
              </text>
            </svg>
            <div className="text-[9px] font-mono text-[#8A94A6] tracking-wider mt-1">STABILITY</div>
          </div>
        </div>

        {/* Behavioral stability bar */}
        <div className="mb-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] font-mono text-[#8A94A6] tracking-wider">BEHAVIORAL STABILITY</span>
          </div>
          <div className="h-2 bg-[#1a1f2e] rounded-full overflow-hidden">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${stabilityScore}%` }}
              transition={{ duration: 0.8, delay: 0.4 }}
              className="h-full rounded-full"
              style={{ backgroundColor: config.color, opacity: 0.6 }}
            />
          </div>
        </div>

        {/* Incident summary */}
        <div className="pt-4 border-t border-[#1a1f2e] flex items-center gap-6">
          {profile.fraudCount > 0 && (
            <span className="text-[10px] font-mono text-[#FF5C5C]">
              {profile.fraudCount} FRAUD INCIDENT{profile.fraudCount > 1 ? 'S' : ''}
            </span>
          )}
          {profile.organicCount > 0 && (
            <span className="text-[10px] font-mono text-[#34D399]">
              {profile.organicCount} ORGANIC EVENT{profile.organicCount > 1 ? 'S' : ''}
            </span>
          )}
          {profile.reviewCount > 0 && (
            <span className="text-[10px] font-mono text-[#FBBF24]">
              {profile.reviewCount} REVIEW CASE{profile.reviewCount > 1 ? 'S' : ''}
            </span>
          )}
          {profile.fraudCount === 0 && profile.organicCount === 0 && profile.reviewCount === 0 && (
            <span className="text-[10px] font-mono text-[#34D399]">NO ANOMALIES DETECTED</span>
          )}
        </div>
      </div>
    </div>
  );
}
