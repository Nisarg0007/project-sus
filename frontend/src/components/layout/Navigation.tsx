import { NavLink, useLocation } from 'react-router-dom';
import { Crosshair, Activity, AlertTriangle, Building2 } from 'lucide-react';
import type { ReactNode } from 'react';

interface NavItemConfig {
  id: string;
  label: string;
  path: string;
  icon: ReactNode;
}

const navItems: NavItemConfig[] = [
  { id: 'mission-control', label: 'MISSION', path: '/', icon: <Crosshair className="w-3.5 h-3.5" /> },
  { id: 'activity', label: 'ACTIVITY', path: '/activity', icon: <Activity className="w-3.5 h-3.5" /> },
  { id: 'incidents', label: 'INCIDENTS', path: '/incidents', icon: <AlertTriangle className="w-3.5 h-3.5" /> },
  { id: 'merchants', label: 'MERCHANTS', path: '/merchants', icon: <Building2 className="w-3.5 h-3.5" /> },
];

export function Navigation() {
  const location = useLocation();

  return (
    <nav className="fixed top-0 left-0 right-0 h-16 bg-[#080B12]/80 backdrop-blur-xl border-b border-[#1a1f2e] z-50">
      <div className="max-w-[1600px] mx-auto px-8 h-full flex items-center justify-between">
        {/* Logo */}
        <div className="flex items-center gap-3">
          <div className="flex items-center">
            <span className="text-xl font-bold tracking-tight">
              SUS
            </span>
            <span className="ml-3 text-xs font-mono text-[#8A94A6] tracking-widest hidden sm:block">
              SPIKE UNDERSTANDING SYSTEM
            </span>
          </div>
        </div>

        {/* Navigation Links */}
        <div className="flex items-center gap-1">
          {navItems.map((item) => {
            const isActive = location.pathname === item.path;

            return (
              <NavLink
                key={item.id}
                to={item.path}
                className={`flex items-center gap-2 px-4 py-2 text-sm font-medium tracking-wide transition-all duration-200 ${
                  isActive
                    ? 'text-[#F3F4F6]'
                    : 'text-[#8A94A6] hover:text-[#F3F4F6]'
                }`}
              >
                <span className={isActive ? 'text-[#38BDF8]' : ''}>
                  {item.icon}
                </span>
                <span className="hidden md:inline">{item.label}</span>
              </NavLink>
            );
          })}
        </div>

        {/* System Status */}
        <div className="flex items-center gap-2 text-xs font-mono">
          <div className="w-1.5 h-1.5 rounded-full bg-[#34D399] animate-pulse" />
          <span className="text-[#8A94A6]">SYSTEM OPERATIONAL</span>
        </div>
      </div>
    </nav>
  );
}
