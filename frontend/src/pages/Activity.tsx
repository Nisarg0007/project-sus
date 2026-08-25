import { useState, useMemo, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useSearchParams } from 'react-router-dom';
import { ActivityEvent as ActivityEventType, TimeRange } from '../types';
import { generateActivityData, activityEvents } from '../data/mockData';
import { ActivityHeader } from '../components/activity/ActivityHeader';
import { ActivityTimeline } from '../components/activity/ActivityTimeline';
import { ActivityFeed } from '../components/activity/ActivityFeed';
import { ActivityDetail } from '../components/activity/ActivityDetail';

export default function Activity() {
  const [searchParams] = useSearchParams();
  const urlMerchant = searchParams.get('merchant');
  const urlEvent = searchParams.get('event');

  const [selectedMerchant, setSelectedMerchant] = useState(urlMerchant ?? 'all');
  const [timeRange, setTimeRange] = useState<TimeRange>('45d');
  const [selectedEvent, setSelectedEvent] = useState<ActivityEventType | null>(null);

  // Sync from URL params
  useEffect(() => {
    if (urlMerchant) setSelectedMerchant(urlMerchant);
    if (urlEvent) {
      const match = activityEvents.find(e => e.id === urlEvent);
      if (match) setSelectedEvent(match);
    }
  }, [urlMerchant, urlEvent]);

  const timelineData = useMemo(() => generateActivityData(), []);

  // Filter events by time range
  const filteredEvents = useMemo(() => {
    const now = new Date('2025-07-25');
    const daysBack = { '7d': 7, '14d': 14, '30d': 30, '45d': 45 }[timeRange];
    const cutoff = new Date(now);
    cutoff.setDate(cutoff.getDate() - daysBack);
    const cutoffStr = cutoff.toISOString().split('T')[0];

    return activityEvents.filter(e => {
      const inTimeRange = e.date >= cutoffStr;
      const inMerchant = selectedMerchant === 'all' || e.merchantId === selectedMerchant;
      return inTimeRange && inMerchant;
    });
  }, [timeRange, selectedMerchant]);

  const handleSelectEvent = (event: ActivityEventType) => {
    setSelectedEvent(prev => prev?.id === event.id ? null : event);
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5 }}
    >
      {/* Header */}
      <ActivityHeader
        selectedMerchant={selectedMerchant}
        onMerchantChange={setSelectedMerchant}
        timeRange={timeRange}
        onTimeRangeChange={setTimeRange}
      />

      {/* Timeline */}
      <section className="px-8 max-w-[1600px] mx-auto mb-12">
        <ActivityTimeline
          data={timelineData}
          selectedMerchant={selectedMerchant}
          onPointClick={(point) => {
            // Try to match a timeline point to an event
            if (point.merchant) {
              const match = activityEvents.find(
                e => e.merchantId === point.merchant && e.date === point.date
              );
              if (match) {
                setSelectedEvent(match);
              }
            }
          }}
        />

        {/* Legend */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
          className="flex items-center gap-6 mt-4 px-2"
        >
          <span className="flex items-center gap-2 text-[10px] font-mono text-[#8A94A6] tracking-wider">
            <span className="w-1.5 h-1.5 rounded-full bg-[#38BDF8]" />
            BASELINE
          </span>
          <span className="flex items-center gap-2 text-[10px] font-mono text-[#FF5C5C] tracking-wider">
            <span className="w-1.5 h-1.5 rounded-full bg-[#FF5C5C]" />
            FRAUD
          </span>
          <span className="flex items-center gap-2 text-[10px] font-mono text-[#34D399] tracking-wider">
            <span className="w-1.5 h-1.5 rounded-full bg-[#34D399]" />
            ORGANIC
          </span>
          <span className="flex items-center gap-2 text-[10px] font-mono text-[#FBBF24] tracking-wider">
            <span className="w-1.5 h-1.5 rounded-full bg-[#FBBF24]" />
            REVIEW
          </span>
        </motion.div>
      </section>

      {/* Divider */}
      <div className="max-w-[1600px] mx-auto px-8 mb-8">
        <div className="h-px bg-[#1a1f2e]" />
      </div>

      {/* Feed + Detail */}
      <div className="px-8 max-w-[1600px] mx-auto pb-24">
        <div className="flex gap-8">
          {/* Feed */}
          <div className="flex-1 min-w-0">
            <ActivityFeed
              events={filteredEvents}
              selectedEventId={selectedEvent?.id ?? null}
              onSelectEvent={handleSelectEvent}
            />
          </div>

          {/* Detail panel — inline on desktop */}
          <div className="hidden lg:block w-[380px] flex-shrink-0">
            {selectedEvent ? (
              <motion.div
                key={selectedEvent.id}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.3 }}
                className="sticky top-24"
              >
                <InlineDetail event={selectedEvent} />
              </motion.div>
            ) : (
              <div className="sticky top-24 bg-[#0D111A] border border-[#1a1f2e] rounded-sm p-8 text-center">
                <p className="text-sm text-[#8A94A6]/60 font-mono">
                  Select an event to inspect
                </p>
                <p className="text-[10px] text-[#8A94A6]/40 font-mono mt-2">
                  Click any item in the feed above
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Mobile detail drawer */}
      <ActivityDetail
        event={selectedEvent}
        onClose={() => setSelectedEvent(null)}
      />
    </motion.div>
  );
}

// Inline detail panel for desktop
import { AlertTriangle, CheckCircle, HelpCircle, ArrowRight } from 'lucide-react';
import { useNavigation } from '../hooks/useNavigation';

const statusDisplay: Record<string, { color: string; label: string; icon: React.ReactNode }> = {
  fraud_spike: { color: '#FF5C5C', label: 'FRAUD SPIKE', icon: <AlertTriangle className="w-4 h-4" /> },
  organic_spike: { color: '#34D399', label: 'ORGANIC SURGE', icon: <CheckCircle className="w-4 h-4" /> },
  review_required: { color: '#FBBF24', label: 'REVIEW REQUIRED', icon: <HelpCircle className="w-4 h-4" /> },
};

function InlineDetail({ event }: { event: ActivityEventType }) {
  const status = statusDisplay[event.status];
  const { navigateToIncidentFromActivity } = useNavigation();

  return (
    <div className="bg-[#0D111A] border border-[#1a1f2e] rounded-sm overflow-hidden">
      {/* Header */}
      <div className="px-5 py-3 border-b border-[#1a1f2e] flex items-center justify-between">
        <span className="text-[10px] font-mono text-[#8A94A6] tracking-[0.2em]">
          EVENT DETAIL
        </span>
        <span
          className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-sm text-[10px] font-mono font-medium tracking-wider"
          style={{ color: status.color, backgroundColor: `${status.color}12` }}
        >
          {status.icon}
          {status.label}
        </span>
      </div>

      <div className="p-5">
        {/* Overview */}
        <div className="mb-5">
          <div className="text-[10px] font-mono text-[#8A94A6] tracking-[0.15em] mb-3">OVERVIEW</div>
          <div className="space-y-2">
            <Row label="Merchant" value={event.merchantName} />
            <Row label="Date" value={`${event.date} · ${event.time}`} />
            <Row label="Volume" value={`${event.transactionCount.toLocaleString()} txns`} valueColor="#F3F4F6" />
            <Row label="Baseline" value={`${event.baselineVolume.toLocaleString()} txns`} />
            <Row label="Multiple" value={`${event.volumeMultiple.toFixed(1)}×`} valueColor={status.color} />
            <Row label="Z-Score" value={event.zScore.toFixed(2)} />
          </div>
        </div>

        {/* Classification */}
        <div className="mb-5">
          <div className="text-[10px] font-mono text-[#8A94A6] tracking-[0.15em] mb-3">CLASSIFICATION</div>
          <div className="bg-[#080B12] border border-[#1a1f2e] rounded-sm p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] font-mono text-[#8A94A6] tracking-wider">FRAUD PROB</span>
              <span className="text-base font-mono font-medium" style={{ color: status.color }}>
                {(event.fraudProbability * 100).toFixed(1)}%
              </span>
            </div>
            <div className="h-1 bg-[#1a1f2e] rounded-full overflow-hidden mb-3">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${event.fraudProbability * 100}%` }}
                transition={{ duration: 0.8 }}
                className="h-full rounded-full"
                style={{ backgroundColor: status.color }}
              />
            </div>
            <div className="flex items-center justify-between pt-2 border-t border-[#1a1f2e]">
              <span className="text-[10px] font-mono text-[#8A94A6] tracking-wider">CONFIDENCE</span>
              <span className="text-xs font-mono text-[#F3F4F6]">{(event.confidence * 100).toFixed(1)}%</span>
            </div>
          </div>
        </div>

        {/* Evidence signals */}
        <div className="mb-5">
          <div className="text-[10px] font-mono text-[#8A94A6] tracking-[0.15em] mb-3">EVIDENCE</div>
          <div className="space-y-2">
            {event.evidenceSignals.map(signal => (
              <div key={signal.feature} className="bg-[#080B12] border border-[#1a1f2e] rounded-sm p-3">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[10px] font-mono text-[#8A94A6] tracking-wider">
                    {signal.label.toUpperCase()}
                  </span>
                  <span
                    className="text-xs font-mono font-medium"
                    style={{
                      color: signal.signalType === 'fraud' ? '#FF5C5C'
                        : signal.signalType === 'organic' ? '#34D399' : '#8A94A6',
                    }}
                  >
                    {signal.changePercent > 0 ? '+' : ''}{signal.changePercent}%
                  </span>
                </div>
                <div className="flex items-baseline gap-2">
                  <span className="text-sm font-mono text-[#F3F4F6]">
                    {signal.currentValue}{signal.unit === '%' ? '%' : ''}
                  </span>
                  <span className="text-[10px] text-[#8A94A6]">
                    from {signal.normalValue}{signal.unit === '%' ? '%' : ''}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* CTA */}
        <button
          onClick={() => {
            if (event.incidentId) {
              navigateToIncidentFromActivity(event.incidentId, event.merchantId);
            }
          }}
          className="w-full flex items-center justify-center gap-2 py-2.5 text-[10px] font-mono tracking-wider text-[#38BDF8] bg-[#38BDF8]/8 hover:bg-[#38BDF8]/15 rounded-sm transition-colors"
        >
          <span>{event.incidentId ? 'VIEW FULL INCIDENT' : 'NO ASSOCIATED INCIDENT'}</span>
          {event.incidentId && <ArrowRight className="w-3 h-3" />}
        </button>
      </div>
    </div>
  );
}

function Row({ label, value, valueColor = '#8A94A6' }: { label: string; value: string; valueColor?: string }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-xs text-[#8A94A6]">{label}</span>
      <span className="text-xs font-mono" style={{ color: valueColor }}>{value}</span>
    </div>
  );
}
