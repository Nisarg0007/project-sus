import { useMemo, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ActivityDataPoint } from '../../types';

interface ActivityTimelineProps {
  data: ActivityDataPoint[];
  selectedMerchant: string;
  onPointClick?: (point: ActivityDataPoint) => void;
}

const STATUS_COLORS: Record<string, string> = {
  normal: '#38BDF8',
  fraud: '#FF5C5C',
  organic: '#34D399',
  review: '#FBBF24',
};

const STATUS_LABELS: Record<string, string> = {
  normal: 'NORMAL',
  fraud: 'FRAUD SPIKE',
  organic: 'ORGANIC SURGE',
  review: 'REVIEW REQUIRED',
};

export function ActivityTimeline({ data, selectedMerchant, onPointClick }: ActivityTimelineProps) {
  const [hoveredPoint, setHoveredPoint] = useState<ActivityDataPoint | null>(null);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });

  const chartWidth = 1400;
  const chartHeight = 380;
  const padding = { top: 30, right: 30, bottom: 50, left: 70 };
  const innerWidth = chartWidth - padding.left - padding.right;
  const innerHeight = chartHeight - padding.top - padding.bottom;

  // Aggregate data by date across all merchants (or filtered)
  const aggregatedData = useMemo(() => {
    const filtered = selectedMerchant === 'all'
      ? data
      : data.filter(d => d.merchant === selectedMerchant);

    const byDate: Record<string, { date: string; baseline: number; actual: number; types: Set<string> }> = {};
    for (const d of filtered) {
      if (!byDate[d.date]) {
        byDate[d.date] = { date: d.date, baseline: 0, actual: 0, types: new Set() };
      }
      byDate[d.date].baseline += d.baseline;
      byDate[d.date].actual += d.actual;
      if (d.type && d.type !== 'normal') {
        byDate[d.date].types.add(d.type);
      }
    }

    return Object.values(byDate)
      .sort((a, b) => a.date.localeCompare(b.date))
      .map(d => {
        // Determine dominant anomaly type for the day
        let type: ActivityDataPoint['type'] = 'normal';
        if (d.types.has('fraud')) type = 'fraud';
        else if (d.types.has('review')) type = 'review';
        else if (d.types.has('organic')) type = 'organic';
        return { ...d, type };
      });
  }, [data, selectedMerchant]);

  // Also compute per-merchant anomalies for the tooltip
  const merchantAnomalies = useMemo(() => {
    const filtered = selectedMerchant === 'all'
      ? data
      : data.filter(d => d.merchant === selectedMerchant);
    return filtered.filter(d => d.type && d.type !== 'normal');
  }, [data, selectedMerchant]);

  // Scales
  const { xScale, yScale, maxVal } = useMemo(() => {
    const dates = aggregatedData.map(d => d.date);
    const allValues = aggregatedData.flatMap(d => [d.actual, d.baseline]);
    const maxVal = Math.max(...allValues) * 1.12;

    const xScale = (date: string) => {
      const idx = dates.indexOf(date);
      return padding.left + (idx / Math.max(dates.length - 1, 1)) * innerWidth;
    };
    const yScale = (value: number) => {
      return padding.top + innerHeight - (value / maxVal) * innerHeight;
    };
    return { xScale, yScale, maxVal };
  }, [aggregatedData, innerWidth, innerHeight, padding]);

  // Paths
  const actualPath = useMemo(() => {
    return aggregatedData.map((d, i) => {
      const x = xScale(d.date);
      const y = yScale(d.actual);
      return `${i === 0 ? 'M' : 'L'} ${x} ${y}`;
    }).join(' ');
  }, [aggregatedData, xScale, yScale]);

  const baselinePath = useMemo(() => {
    return aggregatedData.map((d, i) => {
      const x = xScale(d.date);
      const y = yScale(d.baseline);
      return `${i === 0 ? 'M' : 'L'} ${x} ${y}`;
    }).join(' ');
  }, [aggregatedData, xScale, yScale]);

  const actualArea = useMemo(() => {
    if (aggregatedData.length === 0) return '';
    const bottom = yScale(0);
    const pts = aggregatedData.map(d => `${xScale(d.date)},${yScale(d.actual)}`);
    return `M ${xScale(aggregatedData[0].date)},${bottom} L ${pts.join(' L ')} L ${xScale(aggregatedData[aggregatedData.length - 1].date)},${bottom} Z`;
  }, [aggregatedData, xScale, yScale]);

  const baselineArea = useMemo(() => {
    if (aggregatedData.length === 0) return '';
    const bottom = yScale(0);
    const pts = aggregatedData.map(d => `${xScale(d.date)},${yScale(d.baseline)}`);
    return `M ${xScale(aggregatedData[0].date)},${bottom} L ${pts.join(' L ')} L ${xScale(aggregatedData[aggregatedData.length - 1].date)},${bottom} Z`;
  }, [aggregatedData, xScale, yScale]);

  // Ticks
  const yTicks = useMemo(() => {
    const ticks: number[] = [];
    const step = Math.ceil(maxVal / 6 / 500) * 500;
    for (let v = 0; v <= maxVal; v += step) ticks.push(v);
    return ticks;
  }, [maxVal]);

  const xLabels = useMemo(() => {
    return aggregatedData
      .filter((_, i) => i % 7 === 0 || i === aggregatedData.length - 1)
      .map(d => ({
        date: d.date,
        label: new Date(d.date + 'T00:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      }));
  }, [aggregatedData]);

  // Anomaly markers
  const anomalyPoints = useMemo(() => {
    return aggregatedData.filter(d => d.type && d.type !== 'normal');
  }, [aggregatedData]);

  const handleMouseMove = useCallback((e: React.MouseEvent<SVGGElement>, point: typeof aggregatedData[0]) => {
    const svg = e.currentTarget.closest('svg');
    if (!svg) return;
    const rect = svg.getBoundingClientRect();
    setTooltipPos({
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    });
    // Build a pseudo-ActivityDataPoint for the tooltip
    setHoveredPoint({
      date: point.date,
      baseline: point.baseline,
      actual: point.actual,
      type: point.type,
    });
  }, []);

  const handleClick = useCallback((point: typeof aggregatedData[0]) => {
    // Find matching data points for this date
    const match = merchantAnomalies.find(d => d.date === point.date && d.type === point.type);
    if (match) onPointClick?.(match);
  }, [merchantAnomalies, onPointClick]);

  return (
    <div className="relative">
      {/* Chart container */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.2 }}
        className="bg-[#0D111A] border border-[#1a1f2e] rounded-sm relative overflow-hidden"
      >
        <svg
          viewBox={`0 0 ${chartWidth} ${chartHeight}`}
          className="w-full h-auto"
          onMouseLeave={() => setHoveredPoint(null)}
        >
          <defs>
            <linearGradient id="actActualGrad" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#38BDF8" stopOpacity={0.18} />
              <stop offset="100%" stopColor="#38BDF8" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="actBaseGrad" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#8A94A6" stopOpacity={0.06} />
              <stop offset="100%" stopColor="#8A94A6" stopOpacity={0} />
            </linearGradient>
          </defs>

          {/* Y grid */}
          {yTicks.map(v => (
            <g key={v}>
              <line
                x1={padding.left} y1={yScale(v)}
                x2={chartWidth - padding.right} y2={yScale(v)}
                stroke="#1a1f2e" strokeWidth={1}
              />
              <text
                x={padding.left - 12} y={yScale(v)}
                textAnchor="end" fill="#8A94A6" fontSize={10} fontFamily="monospace"
              >
                {v >= 1000 ? `${(v / 1000).toFixed(1)}k` : v}
              </text>
            </g>
          ))}

          {/* X labels */}
          {xLabels.map(({ date, label }) => (
            <text
              key={date}
              x={xScale(date)} y={chartHeight - 14}
              textAnchor="middle" fill="#8A94A6" fontSize={10} fontFamily="monospace"
            >
              {label}
            </text>
          ))}

          {/* Baseline area + line */}
          <path d={baselineArea} fill="url(#actBaseGrad)" />
          <path d={baselinePath} fill="none" stroke="#8A94A6" strokeWidth={1} strokeDasharray="4 4" opacity={0.4} />

          {/* Actual area + line */}
          <path d={actualArea} fill="url(#actActualGrad)" />
          <path d={actualPath} fill="none" stroke="#38BDF8" strokeWidth={2} />

          {/* Anomaly markers */}
          {anomalyPoints.map(d => {
            const x = xScale(d.date);
            const y = yScale(d.actual);
            const color = STATUS_COLORS[d.type ?? 'normal'];
            return (
              <g
                key={`anomaly-${d.date}`}
                onMouseMove={(e) => handleMouseMove(e, d)}
                onClick={() => handleClick(d)}
                className="cursor-pointer"
              >
                {/* Outer ring */}
                <circle cx={x} cy={y} r={10} fill={color} opacity={0.08} />
                {/* Point */}
                <circle cx={x} cy={y} r={5} fill={color} stroke="#0D111A" strokeWidth={2} />
              </g>
            );
          })}

          {/* Hover crosshair */}
          {hoveredPoint && aggregatedData.find(d => d.date === hoveredPoint.date) && (
            <g>
              <line
                x1={xScale(hoveredPoint.date)} y1={padding.top}
                x2={xScale(hoveredPoint.date)} y2={chartHeight - padding.bottom}
                stroke="#8A94A6" strokeWidth={1} strokeDasharray="3 3" opacity={0.4}
              />
            </g>
          )}
        </svg>

        {/* Tooltip */}
        <AnimatePresence>
          {hoveredPoint && (
            <motion.div
              initial={{ opacity: 0, scale: 0.96 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.96 }}
              transition={{ duration: 0.15 }}
              className="absolute pointer-events-none z-20 bg-[#111827] border border-[#2a3040] rounded-sm p-4 min-w-[220px]"
              style={{
                left: Math.min(tooltipPos.x + 20, chartWidth * 0.65),
                top: Math.max(tooltipPos.y - 100, 10),
              }}
            >
              {/* Date */}
              <div className="font-mono text-[10px] text-[#8A94A6] tracking-wider mb-2">
                {new Date(hoveredPoint.date + 'T00:00:00').toLocaleDateString('en-US', {
                  month: 'short', day: 'numeric', year: 'numeric',
                })}
              </div>

              {/* Merchant (if single) */}
              {selectedMerchant !== 'all' && (
                <div className="text-xs text-[#8A94A6] font-mono mb-2">
                  {selectedMerchant.toUpperCase()}
                </div>
              )}

              {/* Classification badge */}
              {hoveredPoint.type && hoveredPoint.type !== 'normal' && (
                <div className="flex items-center gap-2 mb-3">
                  <span
                    className="w-1.5 h-1.5 rounded-full"
                    style={{ backgroundColor: STATUS_COLORS[hoveredPoint.type] }}
                  />
                  <span
                    className="text-[11px] font-mono font-medium tracking-wider"
                    style={{ color: STATUS_COLORS[hoveredPoint.type] }}
                  >
                    {STATUS_LABELS[hoveredPoint.type]}
                  </span>
                </div>
              )}

              {/* Metrics */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-mono text-[#8A94A6] tracking-wider">TRANSACTIONS</span>
                  <span className="text-sm text-[#F3F4F6] font-mono">{hoveredPoint.actual.toLocaleString()}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-mono text-[#8A94A6] tracking-wider">BASELINE</span>
                  <span className="text-sm text-[#8A94A6] font-mono">{hoveredPoint.baseline.toLocaleString()}</span>
                </div>
                {hoveredPoint.type !== 'normal' && (
                  <>
                    <div className="h-px bg-[#1a1f2e] my-1.5" />
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] font-mono text-[#8A94A6] tracking-wider">ANOMALY</span>
                      <span
                        className="text-sm font-mono font-medium"
                        style={{ color: STATUS_COLORS[hoveredPoint.type ?? 'normal'] }}
                      >
                        +{((hoveredPoint.actual / hoveredPoint.baseline - 1) * 100).toFixed(0)}%
                      </span>
                    </div>
                  </>
                )}
              </div>

              {hoveredPoint.type !== 'normal' && (
                <div className="mt-2 text-[10px] font-mono text-[#8A94A6]/60 tracking-wider">
                  CLICK TO INVESTIGATE →
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </div>
  );
}
