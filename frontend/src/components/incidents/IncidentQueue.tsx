import { useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { FullIncident, IncidentSeverityFilter } from '../../types';
import { IncidentQueueItem } from './IncidentQueueItem';

interface IncidentQueueProps {
  incidents: FullIncident[];
  selectedId: string | null;
  onSelect: (incident: FullIncident) => void;
  filter: IncidentSeverityFilter;
  onFilterChange: (filter: IncidentSeverityFilter) => void;
}

const filters: Array<{ value: IncidentSeverityFilter; label: string; color: string }> = [
  { value: 'all', label: 'ALL', color: '#8A94A6' },
  { value: 'critical', label: 'CRITICAL', color: '#FF5C5C' },
  { value: 'high', label: 'HIGH', color: '#FBBF24' },
  { value: 'review', label: 'REVIEW', color: '#38BDF8' },
];

export function IncidentQueue({ incidents, selectedId, onSelect, filter, onFilterChange }: IncidentQueueProps) {
  const counts = useMemo(() => ({
    all: incidents.length,
    critical: incidents.filter(i => i.severity === 'critical').length,
    high: incidents.filter(i => i.severity === 'high').length,
    review: incidents.filter(i => i.predictedCause === 'review_required').length,
  }), [incidents]);

  const filtered = useMemo(() => {
    switch (filter) {
      case 'critical': return incidents.filter(i => i.severity === 'critical');
      case 'high': return incidents.filter(i => i.severity === 'high');
      case 'review': return incidents.filter(i => i.predictedCause === 'review_required');
      default: return incidents;
    }
  }, [incidents, filter]);

  return (
    <div className="flex flex-col h-full">
      {/* Filters */}
      <div className="flex items-center gap-1 mb-4">
        {filters.map(f => {
          const isActive = filter === f.value;
          return (
            <button
              key={f.value}
              onClick={() => onFilterChange(f.value)}
              className="relative px-3 py-1.5 text-[10px] font-mono tracking-wider transition-colors duration-200 rounded-sm"
              style={{ color: isActive ? f.color : '#8A94A6' }}
            >
              <span className="relative z-10">
                {f.label} <span className="opacity-50">{counts[f.value]}</span>
              </span>
              {isActive && (
                <motion.div
                  layoutId="incidentFilterBg"
                  className="absolute inset-0 rounded-sm"
                  style={{ backgroundColor: `${f.color}10` }}
                  transition={{ type: 'spring', stiffness: 500, damping: 35 }}
                />
              )}
            </button>
          );
        })}
      </div>

      {/* Queue header */}
      <div className="flex items-center gap-4 mb-3">
        <span className="text-[10px] font-mono text-[#8A94A6] tracking-[0.2em]">
          INCIDENT QUEUE
        </span>
        <div className="h-px flex-1 bg-[#1a1f2e]" />
        <span className="text-[10px] font-mono text-[#8A94A6]/60 tracking-wider">
          {filtered.length}
        </span>
      </div>

      {/* Queue list */}
      <div className="flex-1 overflow-y-auto space-y-px">
        <AnimatePresence mode="popLayout">
          {filtered.map((incident, index) => (
            <IncidentQueueItem
              key={incident.id}
              incident={incident}
              isSelected={selectedId === incident.id}
              onClick={() => onSelect(incident)}
              index={index}
            />
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}
