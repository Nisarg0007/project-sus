import { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ActivityEvent as ActivityEventType, ActivityFilter } from '../../types';
import { ActivityEventItem } from './ActivityEvent';

interface ActivityFeedProps {
  events: ActivityEventType[];
  selectedEventId: string | null;
  onSelectEvent: (event: ActivityEventType) => void;
}

const filters: Array<{ value: ActivityFilter; label: string; color: string }> = [
  { value: 'all', label: 'ALL', color: '#8A94A6' },
  { value: 'fraud', label: 'FRAUD', color: '#FF5C5C' },
  { value: 'organic', label: 'ORGANIC', color: '#34D399' },
  { value: 'review', label: 'REVIEW', color: '#FBBF24' },
];

const filterMap: Record<ActivityFilter, string | null> = {
  all: null,
  fraud: 'fraud_spike',
  organic: 'organic_spike',
  review: 'review_required',
};

export function ActivityFeed({ events, selectedEventId, onSelectEvent }: ActivityFeedProps) {
  const [activeFilter, setActiveFilter] = useState<ActivityFilter>('all');

  const filteredEvents = useMemo(() => {
    if (activeFilter === 'all') return events;
    const status = filterMap[activeFilter];
    return events.filter(e => e.status === status);
  }, [events, activeFilter]);

  const counts = useMemo(() => ({
    all: events.length,
    fraud: events.filter(e => e.status === 'fraud_spike').length,
    organic: events.filter(e => e.status === 'organic_spike').length,
    review: events.filter(e => e.status === 'review_required').length,
  }), [events]);

  return (
    <div>
      {/* Header + filters */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <span className="text-[11px] font-mono text-[#8A94A6]/60 tracking-[0.12em]">
            EVENT FEED
          </span>
          <div className="h-px w-12 bg-[#1a1f2e]" />
          <span className="text-[10px] font-mono text-[#8A94A6]/60 tracking-wider">
            {filteredEvents.length} EVENT{filteredEvents.length !== 1 ? 'S' : ''}
          </span>
        </div>

        {/* Filter controls */}
        <div className="flex items-center gap-1">
          {filters.map(f => {
            const isActive = activeFilter === f.value;
            return (
              <button
                key={f.value}
                onClick={() => setActiveFilter(f.value)}
                className="relative px-3 py-1.5 text-[10px] font-mono tracking-wider transition-colors duration-200 rounded-sm"
                style={{
                  color: isActive ? f.color : '#8A94A6',
                }}
              >
                <span className="relative z-10">
                  {f.label}
                  <span className="ml-1 opacity-50">{counts[f.value]}</span>
                </span>
                {isActive && (
                  <motion.div
                    layoutId="activityFilterBg"
                    className="absolute inset-0 rounded-sm"
                    style={{ backgroundColor: `${f.color}10` }}
                    transition={{ type: 'spring', stiffness: 500, damping: 35 }}
                  />
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Events list */}
      <div className="space-y-1">
        <AnimatePresence mode="popLayout">
          {filteredEvents.map((event, index) => (
            <ActivityEventItem
              key={event.id}
              event={event}
              isSelected={selectedEventId === event.id}
              onClick={() => onSelectEvent(event)}
              index={index}
            />
          ))}
        </AnimatePresence>

        {filteredEvents.length === 0 && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="py-12 text-center"
          >
            <p className="text-sm text-[#8A94A6]/60 font-mono">No events match this filter.</p>
          </motion.div>
        )}
      </div>
    </div>
  );
}
