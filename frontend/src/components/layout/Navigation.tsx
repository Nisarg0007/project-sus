import { NavLink, useLocation } from 'react-router-dom';
import { Crosshair, Activity, AlertTriangle, Building2, Search, History } from 'lucide-react';
import type { ReactNode } from 'react';
import { useInvestigation } from '../../context/InvestigationContext';
import { merchants } from '../../data/mockData';

interface NavItemConfig {
  id: string;
  label: string;
  path: string;
  icon: ReactNode;
}

const navItems: NavItemConfig[] = [
  { id: 'mission-control', label: 'Mission', path: '/', icon: <Crosshair className="w-3.5 h-3.5" /> },
  { id: 'activity', label: 'Activity', path: '/activity', icon: <Activity className="w-3.5 h-3.5" /> },
  { id: 'incidents', label: 'Incidents', path: '/incidents', icon: <AlertTriangle className="w-3.5 h-3.5" /> },
  { id: 'merchants', label: 'Merchants', path: '/merchants', icon: <Building2 className="w-3.5 h-3.5" /> },
  { id: 'investigations', label: 'History', path: '/investigations', icon: <History className="w-3.5 h-3.5" /> },
];

function ContextIndicator({ path }: { path: string }) {
  const location = useLocation();
  const { selectedMerchantId, selectedIncidentId } = useInvestigation();
  const isActive = location.pathname === path;
  if (!isActive) return null;

  let text = '';
  if (path === '/merchants' && selectedMerchantId) {
    const m = merchants.find(m => m.id === selectedMerchantId);
    text = m ? m.name : selectedMerchantId;
  } else if (path === '/incidents' && selectedIncidentId) {
    text = selectedIncidentId.replace('INC-', '').substring(0, 18);
  } else if (path === '/activity') {
    text = 'Live feed';
  } else if (path === '/') {
    text = 'Overview';
  } else if (path === '/investigations') {
    text = 'All runs';
  }

  if (!text) return null;
  return (
    <span className="text-[9px] font-mono text-[#38BDF8]/50 tracking-wider block -mt-0.5">
      {text}
    </span>
  );
}

export function Navigation() {
  const location = useLocation();

  return (
    <nav className="fixed top-0 left-0 right-0 h-16 bg-[#080B12]/90 backdrop-blur-xl border-b border-[#1a1f2e]/60 z-50">
      <div className="max-w-[var(--content-max)] mx-auto px-[var(--content-px)] h-full flex items-center justify-between gap-8">
        {/* Logo */}
        <div className="flex items-center gap-3 flex-shrink-0">
          <span className="text-lg font-bold tracking-tight text-[#F3F4F6]">
            SUS
          </span>
          <span className="text-[10px] font-mono text-[#8A94A6]/60 tracking-[0.15em] hidden lg:block">
            SPIKE UNDERSTANDING SYSTEM
          </span>
        </div>

        {/* Navigation Links */}
        <div className="flex items-center">
          {navItems.map((item) => {
            const isActive = location.pathname === item.path;

            return (
              <NavLink
                key={item.id}
                to={item.path}
                className="relative px-3 lg:px-4 py-5 text-[13px] font-medium tracking-wide transition-colors duration-200"
              >
                <span className="flex items-center gap-2">
                  <span className={`transition-colors duration-200 ${isActive ? 'text-[#38BDF8]' : 'text-[#8A94A6]/60'}`}>
                    {item.icon}
                  </span>
                  <span className={`hidden md:inline transition-colors duration-200 ${isActive ? 'text-[#F3F4F6]' : 'text-[#8A94A6] hover:text-[#F3F4F6]/80'}`}>
                    {item.label}
                  </span>
                </span>
                {/* Active indicator - subtle bottom line */}
                {isActive && (
                  <span className="absolute bottom-0 left-3 right-3 h-[2px] bg-[#38BDF8] rounded-full" />
                )}
                <ContextIndicator path={item.path} />
              </NavLink>
            );
          })}
        </div>

        {/* Right: Search control + Status */}
        <div className="flex items-center gap-3 flex-shrink-0">
          {/* Search control */}
          <button
            onClick={() => window.dispatchEvent(new KeyboardEvent('keydown', { key: 'k', ctrlKey: true }))}
            className="flex items-center gap-2.5 pl-3 pr-2 py-1.5 text-[12px] text-[#8A94A6]/70 bg-[#0D111A]/80 border border-[#1a1f2e]/60 rounded-md hover:border-[#2a3040] hover:text-[#8A94A6] hover:bg-[#0D111A] transition-all duration-200 group min-w-[180px] lg:min-w-[220px]"
          >
            <Search className="w-3.5 h-3.5 text-[#8A94A6]/50 group-hover:text-[#8A94A6] transition-colors flex-shrink-0" />
            <span className="flex-1 text-left text-[11px] font-mono tracking-wide hidden sm:inline">
              Search SUS...
            </span>
            <kbd className="hidden sm:inline text-[9px] font-mono text-[#8A94A6]/40 px-1.5 py-0.5 bg-[#111827]/80 border border-[#1a1f2e]/40 rounded">
              <span className="hidden lg:inline">⌘</span>K
            </kbd>
          </button>

          {/* Status indicator */}
          <div className="flex items-center gap-1.5">
            <div className="w-1.5 h-1.5 rounded-full bg-[#34D399] animate-pulse" />
            <span className="text-[10px] font-mono text-[#8A94A6]/50 hidden xl:inline">OPERATIONAL</span>
          </div>
        </div>
      </div>
    </nav>
  );
}
