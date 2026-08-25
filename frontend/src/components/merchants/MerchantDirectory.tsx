import { motion } from 'framer-motion';
import { MerchantDirectoryItem } from '../../types';

interface MerchantDirectoryProps {
  merchants: MerchantDirectoryItem[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

export function MerchantDirectory({ merchants, selectedId, onSelect }: MerchantDirectoryProps) {
  return (
    <div>
      {/* Directory header */}
      <div className="flex items-center gap-4 mb-4">
        <span className="text-[11px] font-mono text-[#8A94A6]/60 tracking-[0.12em]">
          MERCHANT INDEX
        </span>
        <div className="h-px flex-1 bg-[#1a1f2e]" />
      </div>

      {/* Merchant list */}
      <div className="space-y-px">
        {merchants.map((merchant, idx) => {
          const isSelected = selectedId === merchant.id;
          return (
            <motion.button
              key={merchant.id}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.25, delay: idx * 0.04 }}
              onClick={() => onSelect(merchant.id)}
              className={`w-full text-left p-4 border-l-2 transition-all duration-150 ${
                isSelected
                  ? 'bg-[#111827] border-l-[#38BDF8]'
                  : 'bg-transparent border-l-transparent hover:bg-[#0D111A] hover:border-l-[#1a1f2e]'
              }`}
            >
              {/* Merchant ID */}
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs font-mono text-[#F3F4F6] tracking-wider">
                  {merchant.name}
                </span>
                {merchant.incidentCount > 0 && (
                  <span className="text-[9px] font-mono px-1.5 py-0.5 rounded-sm"
                    style={{ color: merchant.statusColor, backgroundColor: `${merchant.statusColor}10` }}>
                    {merchant.incidentCount}
                  </span>
                )}
              </div>

              {/* Status */}
              <div className="text-[10px] font-mono tracking-wider mb-1"
                style={{ color: merchant.statusColor }}>
                {merchant.statusLabel}
              </div>

              {/* Risk */}
              <div className="text-[9px] font-mono tracking-wider"
                style={{ color: merchant.riskColor }}>
                {merchant.riskLabel}
              </div>
            </motion.button>
          );
        })}
      </div>
    </div>
  );
}
