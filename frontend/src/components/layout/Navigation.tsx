import { NavLink, useLocation } from 'react-router-dom';
import { Search, AlertTriangle, History, BarChart3 } from 'lucide-react';
import type { ReactNode } from 'react';
import { useInvestigation } from '../../context/InvestigationContext';

interface NavItemConfig {
  id: string;
  label: string;
  path: string;
  icon: ReactNode;
  group: 'primary' | 'secondary';
}

const navItems: NavItemConfig[] = [
  { id: 'investigate', label: 'Investigate', path: '/', icon: <Search className="w-3.5 h-3.5" />, group: 'primary' },
  { id: 'incidents', label: 'Incidents', path: '/incidents', icon: <AlertTriangle className="w-3.5 h-3.5" />, group: 'primary' },
  { id: 'investigations', label: 'History', path: '/investigations', icon: <History className="w-3.5 h-3.5" />, group: 'secondary' },
  { id: 'analytics', label: 'Analytics', path: '/analytics', icon: <BarChart3 className="w-3.5 h-3.5" />, group: 'secondary' },
];

function ContextIndicator({ path }: { path: string }) {
  const location = useLocation();
  const { selectedIncidentId } = useInvestigation();
  const isActive = location.pathname === path;
  if (!isActive) return null;

  let text = '';
  if (path === '/') {
    text = 'Transaction analysis';
  } else if (path === '/incidents') {
    text = selectedIncidentId
      ? selectedIncidentId.replace('INC-', '').substring(0, 18)
      : 'Analyst workflow queue';
  } else if (path === '/investigations') {
    text = 'All investigation runs';
  } else if (path === '/analytics') {
    text = 'Aggregate insights';
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
  const primaryItems = navItems.filter(i => i.group === 'primary');
  const secondaryItems = navItems.filter(i => i.group === 'secondary');

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
          {/* Primary items */}
          {primaryItems.map((item) => {
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
                {isActive && (
                  <span className="absolute bottom-0 left-3 right-3 h-[2px] bg-[#38BDF8] rounded-full" />
                )}
                <ContextIndicator path={item.path} />
              </NavLink>
            );
          })}

          {/* Separator */}
          <div className="w-px h-6 bg-[#1a1f2e]/60 mx-1" />

          {/* Secondary items */}
          {secondaryItems.map((item) => {
            const isActive = location.pathname.startsWith(item.path);
            return (
              <NavLink
                key={item.id}
                to={item.path}
                className="relative px-3 lg:px-4 py-5 text-[13px] font-medium tracking-wide transition-colors duration-200"
              >
                <span className="flex items-center gap-2">
                  <span className={`transition-colors duration-200 ${isActive ? 'text-[#38BDF8]' : 'text-[#8A94A6]/40'}`}>
                    {item.icon}
                  </span>
                  <span className={`hidden md:inline transition-colors duration-200 ${isActive ? 'text-[#F3F4F6]' : 'text-[#8A94A6]/60 hover:text-[#F3F4F6]/60'}`}>
                    {item.label}
                  </span>
                </span>
                {isActive && (
                  <span className="absolute bottom-0 left-3 right-3 h-[2px] bg-[#38BDF8]/60 rounded-full" />
                )}
                <ContextIndicator path={item.path} />
              </NavLink>
            );
          })}
        </div>

        {/* Right: Search control + Status */}
        <div className="flex items-center gap-3 flex-shrink-0">
          <button
            onClick={() => window.dispatchEvent(new KeyboardEvent('keydown', { key: 'k', ctrlKey: true }))}
            className="flex items-center gap-2.5 pl-3 pr-2 py-1.5 text-[12px] text-[#8A94A6]/70 bg-[#0D111A]/80 border border-[#1a1f2e]/60 rounded-md hover:border-[#2a3040] hover:text-[#8A94A6] hover:bg-[#0D111A] transition-all duration-200 group min-w-[180px] lg:min-w-[220px]"
          >
            <Search className="w-3.5 h-3.5 text-[#8A94A6]/50 group-hover:text-[#8A94A6] transition-colors flex-shrink-0" />
            <span className="flex-1 text-left text-[11px] font-mono tracking-wide hidden sm:inline">
              Search...
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
