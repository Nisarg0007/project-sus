/**
 * Investigation Analytics Page
 *
 * Displays aggregate analytics across persisted investigations:
 * overview stats, activity over time, incident trends, status distribution,
 * top merchants, and recent activity.
 *
 * Data flow: URL params → dataSource.getInvestigationAnalytics(filters) → UI
 */

import { useState, useEffect, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, PieChart, Pie, Cell,
} from 'recharts';
import { ArrowLeft, TrendingUp, AlertTriangle, Search, X } from 'lucide-react';
import { dataSource } from '../data/dataSource';
import type { BackendAnalyticsResponse, BackendActivityDay } from '../api/investigations';

// ---------------------------------------------------------------------------
// Color palette
// ---------------------------------------------------------------------------

const COLORS = {
  cyan: '#38BDF8',
  red: '#FF5C5C',
  green: '#34D399',
  amber: '#FBBF24',
  muted: '#8A94A6',
  surface: '#0D111A',
  border: '#1a1f2e',
};

const PIE_COLORS = [COLORS.cyan, COLORS.red, COLORS.green, COLORS.amber, COLORS.muted];

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function InvestigationAnalyticsPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  // --- URL state ---
  const urlFrom = searchParams.get('created_from') ?? '';
  const urlTo = searchParams.get('created_to') ?? '';

  // --- Local edit state ---
  const [editFrom, setEditFrom] = useState(urlFrom);
  const [editTo, setEditTo] = useState(urlTo);

  // --- Data state ---
  const [analytics, setAnalytics] = useState<BackendAnalyticsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const dateError = editFrom && editTo && editFrom > editTo
    ? 'From date must be before To date'
    : null;

  const hasActiveFilters = urlFrom !== '' || urlTo !== '';

  // --- Sync edit state from URL ---
  useEffect(() => {
    setEditFrom(urlFrom);
    setEditTo(urlTo);
  }, [urlFrom, urlTo]);

  // --- Load analytics ---
  const loadAnalytics = useCallback(async (from: string, to: string) => {
    setLoading(true);
    setError(null);
    try {
      const filters: Record<string, string> = {};
      if (from) filters.created_from = from;
      if (to) filters.created_to = to;
      const result = await dataSource.getInvestigationAnalytics(
        Object.keys(filters).length > 0 ? filters as { created_from?: string; created_to?: string } : undefined,
      );
      setAnalytics(result);
    } catch {
      setError('Failed to load analytics data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadAnalytics(urlFrom, urlTo);
  }, [loadAnalytics, urlFrom, urlTo]);

  // --- Filter actions ---
  const handleApply = () => {
    const params = new URLSearchParams();
    if (editFrom) params.set('created_from', editFrom);
    if (editTo) params.set('created_to', editTo);
    setSearchParams(params, { replace: true });
  };

  const handleClear = () => {
    setEditFrom('');
    setEditTo('');
    setSearchParams(new URLSearchParams(), { replace: true });
  };

  // --- Derived data ---
  const o = analytics?.overview;
  const overview = o ? [
    { label: 'INVESTIGATIONS', value: o.total_investigations, color: COLORS.cyan },
    { label: 'RESULTS ANALYZED', value: o.total_results.toLocaleString(), color: COLORS.muted },
    { label: 'SPIKES DETECTED', value: o.total_spikes_detected.toLocaleString(), color: COLORS.cyan },
    { label: 'FRAUD INCIDENTS', value: o.total_fraud_incidents.toLocaleString(), color: COLORS.red },
    { label: 'AVG SPIKE RATE', value: `${(o.average_spike_rate * 100).toFixed(1)}%`, color: COLORS.cyan },
    { label: 'AVG FRAUD / RUN', value: o.average_fraud_per_investigation.toFixed(1), color: COLORS.red },
  ] : [];

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.4 }}
      className="px-[var(--content-px)] max-w-[var(--content-max)] mx-auto pt-8 pb-24"
    >
      {/* Back navigation */}
      <button
        onClick={() => navigate('/')}
        className="flex items-center gap-2 text-[11px] font-mono text-[#8A94A6] hover:text-[#38BDF8] transition-colors duration-200"
      >
        <ArrowLeft className="w-3.5 h-3.5" />
        INVESTIGATE
      </button>

      {/* Page header */}
      <div className="mt-8 mb-2">
        <div className="flex items-center gap-3 mb-2">
          <span className="text-[10px] font-mono tracking-[0.2em] uppercase text-[#8A94A6]">
            INVESTIGATION ANALYTICS
          </span>
          {analytics && (
            <span className="text-[10px] font-mono text-[#38BDF8]/60">
              {analytics.overview.total_investigations} investigations analyzed
            </span>
          )}
        </div>
        <h1 className="text-2xl font-medium text-[#F3F4F6] tracking-tight mb-1">
          Analytics Dashboard
        </h1>
        <p className="text-sm text-[#8A94A6]">
          Aggregate insights across all persisted investigation runs.
        </p>
      </div>

      {/* Divider */}
      <div className="h-px bg-[#1a1f2e]/60 my-6" />

      {/* Date range filter */}
      <div className="mb-8">
        <div className="flex items-end gap-3 flex-wrap">
          <div>
            <label className="block text-[9px] font-mono text-[#8A94A6] tracking-wider mb-1">FROM</label>
            <input
              type="datetime-local"
              value={editFrom}
              onChange={(e) => setEditFrom(e.target.value)}
              className="px-3 py-1.5 text-[11px] font-mono text-[#F3F4F6] bg-[#0B0F18] border border-[#1a1f2e]/60 focus:border-[#38BDF8]/40 focus:outline-none transition-colors [color-scheme:dark]"
            />
          </div>
          <div>
            <label className="block text-[9px] font-mono text-[#8A94A6] tracking-wider mb-1">TO</label>
            <input
              type="datetime-local"
              value={editTo}
              onChange={(e) => setEditTo(e.target.value)}
              className="px-3 py-1.5 text-[11px] font-mono text-[#F3F4F6] bg-[#0B0F18] border border-[#1a1f2e]/60 focus:border-[#38BDF8]/40 focus:outline-none transition-colors [color-scheme:dark]"
            />
          </div>
          {dateError && (
            <span className="text-[10px] font-mono text-[#FF5C5C] ml-2">{dateError}</span>
          )}
          <button
            onClick={handleApply}
            disabled={!!dateError}
            className="px-4 py-1.5 text-[11px] font-mono tracking-wider text-[#38BDF8] bg-[#38BDF8]/8 hover:bg-[#38BDF8]/15 border border-[#38BDF8]/20 disabled:opacity-40 disabled:cursor-not-allowed transition-all duration-200"
          >
            APPLY
          </button>
          {hasActiveFilters && (
            <button
              onClick={handleClear}
              className="flex items-center gap-1.5 px-3 py-1.5 text-[11px] font-mono text-[#8A94A6] hover:text-[#F3F4F6] transition-colors"
            >
              <X className="w-3 h-3" />
              CLEAR
            </button>
          )}
        </div>
      </div>

      {/* Loading state */}
      {loading && (
        <div className="flex flex-col items-center gap-4 py-20">
          <div className="w-5 h-5 border-2 border-[#38BDF8]/30 border-t-[#38BDF8] rounded-full animate-spin" />
          <span className="text-xs font-mono text-[#8A94A6]">Loading analytics...</span>
        </div>
      )}

      {/* Error state */}
      {error && !loading && (
        <div className="flex flex-col items-center gap-4 py-20">
          <div className="w-12 h-12 rounded-full bg-[#FF5C5C]/10 flex items-center justify-center">
            <AlertTriangle className="w-5 h-5 text-[#FF5C5C]" />
          </div>
          <h2 className="text-lg font-medium text-[#F3F4F6]">Unable to load analytics</h2>
          <p className="text-sm text-[#8A94A6]">{error}</p>
        </div>
      )}

      {/* Content */}
      {!loading && !error && analytics && (
        <>
          {/* Overview cards */}
          <section className="mb-10">
            <SectionLabel text="OVERVIEW" />
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
              {overview.map((item) => (
                <StatCard key={item.label} label={item.label} value={item.value} color={item.color} />
              ))}
            </div>
          </section>

          {/* Activity over time + Incident trends side by side */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-10">
            <section>
              <SectionLabel text="INVESTIGATION ACTIVITY" />
              <ActivityChart data={analytics.activity_over_time} />
            </section>
            <section>
              <SectionLabel text="INCIDENT TRENDS" />
              <IncidentTrendsChart data={analytics.activity_over_time} />
            </section>
          </div>

          {/* Status + Top Merchants side by side */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-10">
            <section>
              <SectionLabel text="STATUS DISTRIBUTION" />
              <StatusDistribution data={analytics.status_distribution} />
            </section>
            <section>
              <SectionLabel text="TOP MERCHANTS" />
              <TopMerchants data={analytics.top_merchants} />
            </section>
          </div>

          {/* Recent Activity */}
          <section className="mb-10">
            <SectionLabel text="RECENT ACTIVITY" />
            <RecentActivityList data={analytics.recent_activity} onNavigate={navigate} />
          </section>
        </>
      )}

      {/* Empty state */}
      {!loading && !error && analytics && analytics.overview.total_investigations === 0 && (
        <div className="flex flex-col items-center gap-4 py-12 mb-8 border border-[#1a1f2e]/60 bg-[#0D111A]/40">
          <Search className="w-8 h-8 text-[#8A94A6]/30" />
          <p className="text-sm text-[#8A94A6]">No investigation data available yet.</p>
          <p className="text-[10px] font-mono text-[#8A94A6]/50">Run investigations to see aggregate analytics here.</p>
          <button
            onClick={() => navigate('/')}
            className="px-4 py-2 text-xs font-mono tracking-wider text-[#38BDF8] bg-[#38BDF8]/8 hover:bg-[#38BDF8]/15 transition-colors"
          >
            GO TO INVESTIGATE
          </button>
        </div>
      )}
    </motion.div>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function SectionLabel({ text }: { text: string }) {
  return (
    <h3 className="text-[10px] font-mono tracking-[0.2em] uppercase text-[#8A94A6] mb-3">
      {text}
    </h3>
  );
}

function StatCard({ label, value, color = '#F3F4F6' }: { label: string; value: string | number; color?: string }) {
  return (
    <div className="bg-[#0D111A] border border-[#1a1f2e]/60 rounded-sm px-4 py-3">
      <div className="text-[10px] font-mono text-[#8A94A6] tracking-wider mb-1">{label}</div>
      <div className="text-lg font-mono font-medium" style={{ color }}>
        {typeof value === 'number' ? value.toLocaleString() : value}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Activity over time chart (BarChart)
// ---------------------------------------------------------------------------

function ActivityChart({ data }: { data: BackendActivityDay[] }) {
  if (data.length === 0) {
    return <EmptyChart message="No activity data available." />;
  }

  return (
    <div className="bg-[#0D111A] border border-[#1a1f2e]/60 rounded-sm p-4">
      <ResponsiveContainer width="100%" height={280}>
        <BarChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1a1f2e" />
          <XAxis
            dataKey="date"
            stroke="#8A94A6"
            fontSize={9}
            tickLine={false}
            tickFormatter={(v) => { const d = new Date(v); return `${d.getMonth() + 1}/${d.getDate()}`; }}
          />
          <YAxis stroke="#8A94A6" fontSize={9} tickLine={false} />
          <Tooltip
            contentStyle={{ background: '#0D111A', border: '1px solid #1a1f2e', borderRadius: 2, fontSize: 11, fontFamily: 'monospace' }}
            labelStyle={{ color: '#8A94A6' }}
          />
          <Bar dataKey="investigations" fill={COLORS.cyan} radius={[2, 2, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Incident trends chart (multi-line)
// ---------------------------------------------------------------------------

function IncidentTrendsChart({ data }: { data: BackendActivityDay[] }) {
  if (data.length === 0) {
    return <EmptyChart message="No incident trend data available." />;
  }

  return (
    <div className="bg-[#0D111A] border border-[#1a1f2e]/60 rounded-sm p-4">
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1a1f2e" />
          <XAxis
            dataKey="date"
            stroke="#8A94A6"
            fontSize={9}
            tickLine={false}
            tickFormatter={(v) => { const d = new Date(v); return `${d.getMonth() + 1}/${d.getDate()}`; }}
          />
          <YAxis stroke="#8A94A6" fontSize={9} tickLine={false} />
          <Tooltip
            contentStyle={{ background: '#0D111A', border: '1px solid #1a1f2e', borderRadius: 2, fontSize: 11, fontFamily: 'monospace' }}
            labelStyle={{ color: '#8A94A6' }}
          />
          <Line type="monotone" dataKey="fraud_incidents" stroke={COLORS.red} strokeWidth={2} dot={{ r: 3, fill: COLORS.red }} name="Fraud" />
          <Line type="monotone" dataKey="organic_incidents" stroke={COLORS.green} strokeWidth={2} dot={{ r: 3, fill: COLORS.green }} name="Organic" />
          <Line type="monotone" dataKey="review_required" stroke={COLORS.amber} strokeWidth={2} dot={{ r: 3, fill: COLORS.amber }} name="Review" />
        </LineChart>
      </ResponsiveContainer>
      {/* Legend */}
      <div className="flex items-center gap-4 mt-2 justify-center">
        {[
          { color: COLORS.red, label: 'Fraud' },
          { color: COLORS.green, label: 'Organic' },
          { color: COLORS.amber, label: 'Review' },
        ].map((l) => (
          <div key={l.label} className="flex items-center gap-1.5">
            <div className="w-2 h-2 rounded-full" style={{ background: l.color }} />
            <span className="text-[9px] font-mono text-[#8A94A6]">{l.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Status distribution (PieChart)
// ---------------------------------------------------------------------------

function StatusDistribution({ data }: { data: { status: string; count: number }[] }) {
  if (data.length === 0) {
    return (
      <div className="bg-[#0D111A] border border-[#1a1f2e]/60 rounded-sm p-8 flex flex-col items-center gap-2">
        <Search className="w-5 h-5 text-[#8A94A6]/30" />
        <span className="text-xs font-mono text-[#8A94A6]/60">No status data available.</span>
      </div>
    );
  }

  return (
    <div className="bg-[#0D111A] border border-[#1a1f2e]/60 rounded-sm p-4">
      <div className="flex items-center gap-6">
        <ResponsiveContainer width="50%" height={200}>
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius={50}
              outerRadius={80}
              dataKey="count"
              nameKey="status"
              paddingAngle={2}
            >
              {data.map((_, i) => (
                <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{ background: '#0D111A', border: '1px solid #1a1f2e', borderRadius: 2, fontSize: 11, fontFamily: 'monospace' }}
            />
          </PieChart>
        </ResponsiveContainer>
        <div className="flex flex-col gap-2">
          {data.map((item, i) => (
            <div key={item.status} className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full" style={{ background: PIE_COLORS[i % PIE_COLORS.length] }} />
              <span className="text-[10px] font-mono text-[#8A94A6] uppercase">{item.status}</span>
              <span className="text-[11px] font-mono text-[#F3F4F6] ml-auto">{item.count}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Top merchants
// ---------------------------------------------------------------------------

function TopMerchants({ data }: { data: { merchant_filter: string; investigation_count: number; total_spikes_detected: number; total_fraud_incidents: number }[] }) {
  if (data.length === 0) {
    return (
      <div className="bg-[#0D111A] border border-[#1a1f2e]/60 rounded-sm p-8 flex flex-col items-center gap-2">
        <Search className="w-5 h-5 text-[#8A94A6]/30" />
        <span className="text-xs font-mono text-[#8A94A6]/60">No merchant-specific investigations yet.</span>
      </div>
    );
  }

  return (
    <div className="bg-[#0D111A] border border-[#1a1f2e]/60 rounded-sm overflow-hidden">
      {/* Header */}
      <div className="grid grid-cols-4 gap-4 px-5 py-2 border-b border-[#1a1f2e]/40">
        <span className="text-[9px] font-mono text-[#8A94A6] tracking-wider">MERCHANT</span>
        <span className="text-[9px] font-mono text-[#8A94A6] tracking-wider text-right">RUNS</span>
        <span className="text-[9px] font-mono text-[#8A94A6] tracking-wider text-right">SPIKES</span>
        <span className="text-[9px] font-mono text-[#8A94A6] tracking-wider text-right">FRAUD</span>
      </div>
      {data.map((m) => (
        <div
          key={m.merchant_filter}
          className="grid grid-cols-4 gap-4 px-5 py-2.5 border-b border-[#1a1f2e]/20 hover:bg-[#111827]/40 transition-colors"
        >
          <span className="text-[11px] font-mono text-[#38BDF8] truncate">{m.merchant_filter}</span>
          <span className="text-[11px] font-mono text-[#F3F4F6] text-right">{m.investigation_count}</span>
          <span className="text-[11px] font-mono text-[#38BDF8] text-right">{m.total_spikes_detected}</span>
          <span className="text-[11px] font-mono text-[#FF5C5C] text-right">{m.total_fraud_incidents}</span>
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Recent activity
// ---------------------------------------------------------------------------

function RecentActivityList({
  data,
  onNavigate,
}: {
  data: { investigation_id: string; created_at: string; status: string; total_results: number; spikes_detected: number; fraud_incidents: number }[];
  onNavigate: (path: string) => void;
}) {
  if (data.length === 0) {
    return (
      <div className="bg-[#0D111A] border border-[#1a1f2e]/60 rounded-sm p-8 flex flex-col items-center gap-2">
        <Search className="w-5 h-5 text-[#8A94A6]/30" />
        <span className="text-xs font-mono text-[#8A94A6]/60">No recent investigations.</span>
      </div>
    );
  }

  function formatShort(iso: string): string {
    try {
      const d = new Date(iso);
      return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    } catch {
      return iso;
    }
  }

  return (
    <div className="space-y-2">
      {data.map((item) => (
        <motion.div
          key={item.investigation_id}
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2 }}
          onClick={() => onNavigate(`/investigations/${item.investigation_id}`)}
          className="flex items-center gap-6 py-3 px-4 border border-[#1E293B]/60 bg-[#0B0F18]/60 hover:border-[#38BDF8]/20 hover:bg-[#0D111A]/80 cursor-pointer transition-all duration-200"
        >
          <span className="text-[11px] font-mono text-[#38BDF8] tracking-wider shrink-0 w-[160px] truncate">
            {item.investigation_id}
          </span>
          <span className="text-[10px] font-mono text-[#8A94A6] shrink-0">
            {formatShort(item.created_at)}
          </span>
          <div className="flex items-center gap-4 text-[10px] font-mono ml-auto">
            <span className="text-[#8A94A6]">{item.total_results} windows</span>
            {item.spikes_detected > 0 && (
              <span className="text-[#38BDF8]">{item.spikes_detected} spikes</span>
            )}
            <span className="text-[#FF5C5C]">{item.fraud_incidents} fraud</span>
          </div>
          <span className="text-[9px] font-mono text-[#8A94A6] uppercase tracking-wider px-2 py-0.5 bg-[#38BDF8]/8 text-[#38BDF8]/80 shrink-0">
            {item.status}
          </span>
        </motion.div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Empty chart helper
// ---------------------------------------------------------------------------

function EmptyChart({ message }: { message: string }) {
  return (
    <div className="bg-[#0D111A] border border-[#1a1f2e]/60 rounded-sm p-8 flex flex-col items-center justify-center h-[280px]">
      <TrendingUp className="w-5 h-5 text-[#8A94A6]/20 mb-2" />
      <span className="text-xs font-mono text-[#8A94A6]/50">{message}</span>
    </div>
  );
}
