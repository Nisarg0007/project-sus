import { useState, useMemo, useCallback, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useSearchParams } from 'react-router-dom';
import { IncidentSeverityFilter, FullIncident } from '../types';
import { fullIncidents } from '../data/mockData';
import { useInvestigation } from '../context/InvestigationContext';
import { IncidentsHeader } from '../components/incidents/IncidentsHeader';
import { PriorityStrip } from '../components/incidents/PriorityStrip';
import { IncidentQueue } from '../components/incidents/IncidentQueue';
import { IncidentInvestigation } from '../components/incidents/IncidentInvestigation';

export default function Incidents() {
  const [searchParams, setSearchParams] = useSearchParams();
  const { setIncident } = useInvestigation();
  const urlIncident = searchParams.get('incident');
  const [selectedId, setSelectedId] = useState<string | null>(urlIncident ?? fullIncidents[0]?.id ?? null);
  const [filter, setFilter] = useState<IncidentSeverityFilter>('all');

  // Sync from URL params
  useEffect(() => {
    if (urlIncident && fullIncidents.find(i => i.id === urlIncident)) {
      setSelectedId(urlIncident);
      setIncident(urlIncident);
    }
  }, [urlIncident, setIncident]);

  const selectedIncident = useMemo(() => {
    return fullIncidents.find(i => i.id === selectedId) ?? null;
  }, [selectedId]);

  const criticalCount = useMemo(() => fullIncidents.filter(i => i.severity === 'critical').length, []);
  const highCount = useMemo(() => fullIncidents.filter(i => i.severity === 'high').length, []);
  const reviewCount = useMemo(() => fullIncidents.filter(i => i.predictedCause === 'review_required').length, []);

  const handleSelect = useCallback((incident: FullIncident) => {
    const next = selectedId === incident.id ? null : incident.id;
    setSelectedId(next);
    setIncident(next);
    if (next) {
      setSearchParams({ incident: next }, { replace: true });
    } else {
      setSearchParams({}, { replace: true });
    }
  }, [selectedId, setIncident, setSearchParams]);

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        e.preventDefault();
        const currentIdx = fullIncidents.findIndex(i => i.id === selectedId);
        if (e.key === 'ArrowDown') {
          const next = currentIdx < fullIncidents.length - 1 ? currentIdx + 1 : 0;
          setSelectedId(fullIncidents[next].id);
        } else {
          const prev = currentIdx > 0 ? currentIdx - 1 : fullIncidents.length - 1;
          setSelectedId(fullIncidents[prev].id);
        }
      }
      if (e.key === 'Escape') {
        setSelectedId(null);
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
      <IncidentsHeader
        totalIncidents={fullIncidents.length}
        criticalCount={criticalCount}
        highCount={highCount}
        reviewCount={reviewCount}
      />

      {/* Priority Strip */}
      <PriorityStrip
        incidents={fullIncidents}
        selectedId={selectedId}
        onSelect={handleSelect}
      />

      {/* Divider */}
      <div className="max-w-[1600px] mx-auto px-8 mb-6">
        <div className="h-px bg-[#1a1f2e]" />
      </div>

      {/* Main workspace: Queue + Investigation */}
      <div className="px-8 max-w-[1600px] mx-auto pb-24">
        <div className="flex gap-8">
          {/* Left: Queue */}
          <div className="w-[320px] flex-shrink-0 hidden lg:block">
            <div className="sticky top-24">
              <IncidentQueue
                incidents={fullIncidents}
                selectedId={selectedId}
                onSelect={handleSelect}
                filter={filter}
                onFilterChange={setFilter}
              />
            </div>
          </div>

          {/* Mobile queue (shown below lg) */}
          <div className="lg:hidden w-full mb-6">
            <IncidentQueue
              incidents={fullIncidents}
              selectedId={selectedId}
              onSelect={handleSelect}
              filter={filter}
              onFilterChange={setFilter}
            />
          </div>

          {/* Center/Right: Investigation */}
          <div className="flex-1 min-w-0">
            <IncidentInvestigation incident={selectedIncident} />
          </div>
        </div>
      </div>
    </motion.div>
  );
}
