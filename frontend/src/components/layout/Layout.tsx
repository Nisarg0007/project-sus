import React from 'react';
import { Navigation } from './Navigation';

interface LayoutProps {
  children: React.ReactNode;
}

export function Layout({ children }: LayoutProps) {
  return (
    <div className="min-h-screen bg-[#080B12] text-[#F3F4F6]">
      {/* Top Navigation */}
      <Navigation />

      {/* Main Content */}
      <main className="pt-20">
        {children}
      </main>
    </div>
  );
}
