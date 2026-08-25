import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, ArrowRight, Crosshair, Activity, AlertTriangle, Building2 } from 'lucide-react';
import { merchants, fullIncidents } from '../../data/mockData';

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  onNavigate: (path: string) => void;
}

interface CommandItem {
  id: string;
  label: string;
  category: string;
  path: string;
  icon: React.ReactNode;
  color: string;
}

export function CommandPalette({ isOpen, onClose, onNavigate }: CommandPaletteProps) {
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  // Build command items
  const allItems = useMemo<CommandItem[]>(() => {
    const items: CommandItem[] = [
      // Page navigation
      { id: 'page-mission', label: 'Mission Control', category: 'Pages', path: '/', icon: <Crosshair className="w-3.5 h-3.5" />, color: '#38BDF8' },
      { id: 'page-activity', label: 'Activity Intelligence', category: 'Pages', path: '/activity', icon: <Activity className="w-3.5 h-3.5" />, color: '#38BDF8' },
      { id: 'page-incidents', label: 'Incident Intelligence', category: 'Pages', path: '/incidents', icon: <AlertTriangle className="w-3.5 h-3.5" />, color: '#38BDF8' },
      { id: 'page-merchants', label: 'Merchant Intelligence', category: 'Pages', path: '/merchants', icon: <Building2 className="w-3.5 h-3.5" />, color: '#38BDF8' },
      // Merchants
      ...merchants.map(m => ({
        id: `merchant-${m.id}`,
        label: m.name,
        category: 'Merchants',
        path: `/merchants?merchant=${m.id}`,
        icon: <Building2 className="w-3.5 h-3.5" />,
        color: '#34D399',
      })),
      // Incidents
      ...fullIncidents.map(i => ({
        id: `incident-${i.id}`,
        label: `${i.headline} — ${i.merchantName}`,
        category: 'Incidents',
        path: `/incidents?incident=${i.id}`,
        icon: <AlertTriangle className="w-3.5 h-3.5" />,
        color: i.severity === 'critical' ? '#FF5C5C' : i.severity === 'high' ? '#FBBF24' : '#38BDF8',
      })),
    ];
    return items;
  }, []);

  // Filter items
  const filteredItems = useMemo(() => {
    if (!query.trim()) return allItems;
    const q = query.toLowerCase();
    return allItems.filter(item =>
      item.label.toLowerCase().includes(q) ||
      item.category.toLowerCase().includes(q)
    );
  }, [allItems, query]);

  // Group by category
  const groupedItems = useMemo(() => {
    const groups: Record<string, CommandItem[]> = {};
    for (const item of filteredItems) {
      if (!groups[item.category]) groups[item.category] = [];
      groups[item.category].push(item);
    }
    return groups;
  }, [filteredItems]);

  const flatFiltered = useMemo(() => filteredItems, [filteredItems]);

  // Reset on open
  useEffect(() => {
    if (isOpen) {
      setQuery('');
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  // Keyboard navigation
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex(prev => Math.min(prev + 1, flatFiltered.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex(prev => Math.max(prev - 1, 0));
    } else if (e.key === 'Enter' && flatFiltered[selectedIndex]) {
      e.preventDefault();
      onNavigate(flatFiltered[selectedIndex].path);
      onClose();
    } else if (e.key === 'Escape') {
      onClose();
    }
  }, [flatFiltered, selectedIndex, onNavigate, onClose]);

  // Scroll selected item into view
  useEffect(() => {
    if (listRef.current) {
      const selected = listRef.current.querySelector('[data-selected="true"]');
      selected?.scrollIntoView({ block: 'nearest' });
    }
  }, [selectedIndex]);

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[100]"
            onClick={onClose}
          />

          {/* Panel */}
          <motion.div
            initial={{ opacity: 0, scale: 0.96, y: -10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: -10 }}
            transition={{ duration: 0.15 }}
            className="fixed top-[15vh] left-1/2 -translate-x-1/2 w-full max-w-[560px] z-[101]"
          >
            <div className="bg-[#0D111A] border border-[#1a1f2e] rounded-sm shadow-2xl overflow-hidden">
              {/* Search input */}
              <div className="flex items-center gap-3 px-5 py-4 border-b border-[#1a1f2e]">
                <Search className="w-4 h-4 text-[#8A94A6] flex-shrink-0" />
                <input
                  ref={inputRef}
                  type="text"
                  value={query}
                  onChange={(e) => { setQuery(e.target.value); setSelectedIndex(0); }}
                  onKeyDown={handleKeyDown}
                  placeholder="Search pages, merchants, incidents..."
                  className="flex-1 bg-transparent text-sm text-[#F3F4F6] placeholder:text-[#8A94A6]/50 outline-none font-mono"
                />
                <kbd className="text-[10px] font-mono text-[#8A94A6] px-1.5 py-0.5 bg-[#111827] border border-[#1a1f2e] rounded-sm">
                  ESC
                </kbd>
              </div>

              {/* Results */}
              <div ref={listRef} className="max-h-[50vh] overflow-y-auto py-2">
                {flatFiltered.length === 0 ? (
                  <div className="px-5 py-8 text-center">
                    <p className="text-sm text-[#8A94A6]/60 font-mono">No results found</p>
                  </div>
                ) : (
                  Object.entries(groupedItems).map(([category, items]) => (
                    <div key={category}>
                      <div className="px-5 py-2">
                        <span className="text-[9px] font-mono text-[#8A94A6]/60 tracking-[0.15em]">
                          {category.toUpperCase()}
                        </span>
                      </div>
                      {items.map(item => {
                        const globalIdx = flatFiltered.indexOf(item);
                        const isSelected = globalIdx === selectedIndex;
                        return (
                          <button
                            key={item.id}
                            data-selected={isSelected}
                            onClick={() => { onNavigate(item.path); onClose(); }}
                            onMouseEnter={() => setSelectedIndex(globalIdx)}
                            className={`w-full flex items-center gap-3 px-5 py-2.5 text-left transition-colors duration-75 ${
                              isSelected ? 'bg-[#111827]' : 'hover:bg-[#111827]/50'
                            }`}
                          >
                            <span style={{ color: item.color }}>{item.icon}</span>
                            <span className="flex-1 text-sm text-[#F3F4F6] truncate">
                              {item.label}
                            </span>
                            {isSelected && (
                              <ArrowRight className="w-3 h-3 text-[#8A94A6]" />
                            )}
                          </button>
                        );
                      })}
                    </div>
                  ))
                )}
              </div>

              {/* Footer hint */}
              <div className="px-5 py-2.5 border-t border-[#1a1f2e] flex items-center gap-4">
                <span className="text-[9px] font-mono text-[#8A94A6]/50">
                  ↑↓ navigate · ↵ select · esc close
                </span>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
