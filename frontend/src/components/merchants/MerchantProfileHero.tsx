import { motion } from 'framer-motion';
import { MerchantProfile, Merchant } from '../../types';

interface MerchantProfileHeroProps {
  merchant: Merchant;
  profile: MerchantProfile;
}

const riskColors: Record<string, string> = {
  normal: '#34D399',
  watch: '#FBBF24',
  high_attention: '#FF5C5C',
};

export function MerchantProfileHero({ merchant, profile }: MerchantProfileHeroProps) {
  const color = riskColors[profile.riskPosture];

  return (
    <motion.div
      key={profile.merchantId}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
    >
      {/* Merchant identity */}
      <div className="mb-8">
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.1 }}
          className="flex items-center gap-3 mb-3"
        >
          <span className="text-xs font-mono text-[#8A94A6] tracking-wider">BEHAVIORAL PROFILE</span>
          <div className="h-px flex-1 bg-[#1a1f2e]" />
          <span className="text-[10px] font-mono tracking-wider px-2 py-0.5 rounded-sm"
            style={{ color, backgroundColor: `${color}12` }}>
            {profile.riskLabel}
          </span>
        </motion.div>

        <motion.h2
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.15 }}
          className="text-3xl sm:text-4xl font-light text-[#F3F4F6] tracking-tight mb-3"
        >
          {merchant.name}
        </motion.h2>

        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.4, delay: 0.25 }}
          className="text-sm text-[#8A94A6] leading-relaxed max-w-2xl"
        >
          {profile.summary}
        </motion.p>
      </div>

      {/* Stats row */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.3 }}
        className="flex flex-wrap gap-6 lg:gap-10"
      >
        <StatItem label="DAILY VOLUME" value={merchant.dailyVolume.toLocaleString()} color="#8A94A6" />
        <StatItem label="WINDOWS" value={String(profile.totalWindows)} color="#8A94A6" />
        <StatItem label="SPIKES" value={String(profile.spikeCount)} color="#38BDF8" />
        <StatItem label="FRAUD" value={String(profile.fraudCount)} color="#FF5C5C" />
        <StatItem label="ORGANIC" value={String(profile.organicCount)} color="#34D399" />
        <StatItem label="REVIEW" value={String(profile.reviewCount)} color="#FBBF24" />
      </motion.div>
    </motion.div>
  );
}

function StatItem({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className="text-right">
      <div className="text-lg font-mono font-medium" style={{ color }}>{value}</div>
      <div className="text-[9px] font-mono text-[#8A94A6] tracking-[0.12em] mt-0.5">{label}</div>
    </div>
  );
}
