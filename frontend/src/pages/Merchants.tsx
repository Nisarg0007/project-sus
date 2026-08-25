import { useState, useMemo, useCallback, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useSearchParams } from 'react-router-dom';
import { merchants, merchantDirectory, merchantProfiles, generateActivityData } from '../data/mockData';
import { useInvestigation } from '../context/InvestigationContext';
import { MerchantsHeader } from '../components/merchants/MerchantsHeader';
import { MerchantDirectory } from '../components/merchants/MerchantDirectory';
import { MerchantProfileHero } from '../components/merchants/MerchantProfileHero';
import { BehavioralFingerprint } from '../components/merchants/BehavioralFingerprint';
import { BehaviorChange } from '../components/merchants/BehaviorChange';
import { MerchantActivity } from '../components/merchants/MerchantActivity';
import { AnomalyHistory } from '../components/merchants/AnomalyHistory';
import { RiskPosture } from '../components/merchants/RiskPosture';

export default function Merchants() {
  const [searchParams, setSearchParams] = useSearchParams();
  const { setMerchant } = useInvestigation();
  const urlMerchant = searchParams.get('merchant');
  const [selectedId, setSelectedId] = useState<string>(urlMerchant ?? 'merchant_001');

  // Sync from URL params
  useEffect(() => {
    if (urlMerchant && merchants.find(m => m.id === urlMerchant)) {
      setSelectedId(urlMerchant);
      setMerchant(urlMerchant);
    }
  }, [urlMerchant, setMerchant]);

  const selectedMerchant = useMemo(() =>
    merchants.find(m => m.id === selectedId) ?? merchants[0],
    [selectedId]
  );

  const selectedProfile = useMemo(() =>
    merchantProfiles[selectedId] ?? merchantProfiles['merchant_001'],
    [selectedId]
  );

  const activityData = useMemo(() => generateActivityData(), []);

  const handleSelect = useCallback((id: string) => {
    setSelectedId(id);
    setMerchant(id);
    setSearchParams({ merchant: id }, { replace: true });
  }, [setMerchant, setSearchParams]);

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        e.preventDefault();
        const currentIdx = merchants.findIndex(m => m.id === selectedId);
        if (e.key === 'ArrowDown') {
          const next = currentIdx < merchants.length - 1 ? currentIdx + 1 : 0;
          setSelectedId(merchants[next].id);
        } else {
          const prev = currentIdx > 0 ? currentIdx - 1 : merchants.length - 1;
          setSelectedId(merchants[prev].id);
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectedId]);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5 }}
    >
      {/* Header */}
      <MerchantsHeader />

      {/* Main content area */}
      <div className="px-[var(--content-px)] max-w-[var(--content-max)] mx-auto pb-24">
        <div className="flex gap-8">
          {/* Left: Merchant Directory */}
          <div className="w-[240px] flex-shrink-0 hidden lg:block">
            <div className="sticky top-24">
              <MerchantDirectory
                merchants={merchantDirectory}
                selectedId={selectedId}
                onSelect={handleSelect}
              />
            </div>
          </div>

          {/* Mobile directory */}
          <div className="lg:hidden w-full mb-6">
            <MerchantDirectory
              merchants={merchantDirectory}
              selectedId={selectedId}
              onSelect={handleSelect}
            />
          </div>

          {/* Right: Profile content */}
          <div className="flex-1 min-w-0">
            <motion.div
              key={selectedId}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.35 }}
            >
              {/* Profile Hero */}
              <div className="mb-10">
                <MerchantProfileHero merchant={selectedMerchant} profile={selectedProfile} />
              </div>

              {/* Divider */}
              <div className="h-px bg-[#1a1f2e] mb-10" />

              {/* Behavioral Fingerprint */}
              <div className="mb-12">
                <BehavioralFingerprint dimensions={selectedProfile.behavioralDimensions} />
              </div>

              {/* What Changed */}
              <div className="mb-12">
                <BehaviorChange dimensions={selectedProfile.behavioralDimensions} />
              </div>

              {/* Divider */}
              <div className="h-px bg-[#1a1f2e] mb-10" />

              {/* Activity Evolution */}
              <div className="mb-12">
                <MerchantActivity
                  data={activityData}
                  merchantId={selectedId}
                />
              </div>

              {/* Anomaly History */}
              <div className="mb-12">
                <AnomalyHistory entries={selectedProfile.anomalyHistory} merchantId={selectedId} />
              </div>

              {/* Risk Posture */}
              <div className="mb-8">
                <RiskPosture profile={selectedProfile} />
              </div>
            </motion.div>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
