import { useMemo, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ActivityDataPoint } from '../../types';

interface MerchantActivityProps {
  data: ActivityDataPoint[];
  merchantId: string;
  onAnomalyClick?: (point: ActivityDataPoint) => void;
}

const STATUS_COLORS: Record<string, string> = {
  normal: '#38BDF8',
  fraud: '#FF5C5C',
  organic: '#34D399',
  review: '#FBBF24',
};

export function MerchantActivity({ data, merchantId, onAnomalyClick }: MerchantActivityProps) {
  const [hoveredPoint, setHoveredPoint] = useState<ActivityDataPoint | null>(null);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });

  const merchantData = useMemo(() =>
    data.filter(d => d.merchant === merchantId),
    [data, merchantId]
  );

  const chartWidth = 1200;
  const chartHeight = 300;
  const padding = { top: 25, right: 25, bottom: 40, left: 65 };
  const innerWidth = chartWidth - padding.left - padding.right;
  const innerHeight = chartHeight - padding.top - padding.bottom;

  const { xScale, yScale, maxVal } = useMemo(() => {
    const values = merchantData.flatMap(d => [d.actual, d.baseline]);
    const maxVal = Math.max(...values) * 1.12;
    const xScale = (date: string) => {
      const idx = merchantData.findIndex(d => d.date === date);
      return padding.left + (idx / Math.max(merchantData.length - 1, 1)) * innerWidth;
    };
    const yScale = (value: number) => padding.top + innerHeight - (value / maxVal) * innerHeight;
    return { xScale, yScale, maxVal };
  }, [merchantData, innerWidth, innerHeight, padding]);

  const actualPath = useMemo(() =>
    merchantData.map((d, i) => `${i === 0 ? 'M' : 'L'} ${xScale(d.date)} ${yScale(d.actual)}`).join(' '),
    [merchantData, xScale, yScale]
  );

  const baselinePath = useMemo(() =>
    merchantData.map((d, i) => `${i === 0 ? 'M' : 'L'} ${xScale(d.date)} ${yScale(d.baseline)}`).join(' '),
    [merchantData, xScale, yScale]
  );

  const actualArea = useMemo(() => {
    if (merchantData.length === 0) return '';
    const bottom = yScale(0);
    const pts = merchantData.map(d => `${xScale(d.date)},${yScale(d.actual)}`);
    return `M ${xScale(merchantData[0].date)},${bottom} L ${pts.join(' L ')} L ${xScale(merchantData[merchantData.length - 1].date)},${bottom} Z`;
  }, [merchantData, xScale, yScale]);

  const yTicks = useMemo(() => {
    const ticks: number[] = [];
    const step = Math.ceil(maxVal / 5 / 100) * 100;
    for (let v = 0; v <= maxVal; v += step) ticks.push(v);
    return ticks;
  }, [maxVal]);

  const xLabels = useMemo(() =>
    merchantData
      .filter((_, i) => i % 7 === 0 || i === merchantData.length - 1)
      .map(d => ({
        date: d.date,
        label: new Date(d.date + 'T00:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      })),
    [merchantData]
  );

  const anomalyPoints = useMemo(() =>
    merchantData.filter(d => d.type && d.type !== 'normal'),
    [merchantData]
  );

  const handleMouseMove = useCallback((e: React.MouseEvent<SVGGElement>, point: ActivityDataPoint) => {
    const svg = e.currentTarget.closest('svg');
    if (!svg) return;
    const rect = svg.getBoundingClientRect();
    setTooltipPos({ x: e.clientX - rect.left, y: e.clientY - rect.top });
    setHoveredPoint(point);
  }, []);

  return (
    <div>
      <div className="flex items-center gap-4 mb-4">
        <span className="text-[11px] font-mono text-[#8A94A6]/60 tracking-[0.12em]">
          ACTIVITY EVOLUTION
        </span>
        <div className="h-px flex-1 bg-[#1a1f2e]" />
        <span className="text-[10px] font-mono text-[#8A94A6]/60 tracking-wider">
          45-DAY WINDOW
        </span>
      </div>

      <div className="bg-[#0D111A] border border-[#1a1f2e] rounded-sm p-4 relative overflow-hidden">
        <svg
          viewBox={`0 0 ${chartWidth} ${chartHeight}`}
          className="w-full h-auto"
          onMouseLeave={() => setHoveredPoint(null)}
        >
          <defs>
            <linearGradient id={`mactGrad-${merchantId}`} x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#38BDF8" stopOpacity={0.15} />
              <stop offset="100%" stopColor="#38BDF8" stopOpacity={0} />
            </linearGradient>
          </defs>

          {/* Y grid */}
          {yTicks.map(v => (
            <g key={v}>
              <line x1={padding.left} y1={yScale(v)} x2={chartWidth - padding.right} y2={yScale(v)}
                stroke="#1a1f2e" strokeWidth={1} />
              <text x={padding.left - 10} y={yScale(v)} textAnchor="end"
                fill="#8A94A6" fontSize={10} fontFamily="monospace">
                {v >= 1000 ? `${(v / 1000).toFixed(1)}k` : v}
              </text>
            </g>
          ))}

          {/* X labels */}
          {xLabels.map(({ date, label }) => (
            <text key={date} x={xScale(date)} y={chartHeight - 12}
              textAnchor="middle" fill="#8A94A6" fontSize={10} fontFamily="monospace">
              {label}
            </text>
          ))}

          {/* Baseline */}
          <path d={baselinePath} fill="none" stroke="#8A94A6" strokeWidth={1} strokeDasharray="4 4" opacity={0.4} />

          {/* Actual area + line */}
          <path d={actualArea} fill={`url(#mactGrad-${merchantId})`} />
          <path d={actualPath} fill="none" stroke="#38BDF8" strokeWidth={2} />

          {/* Anomaly markers */}
          {anomalyPoints.map(d => {
            const x = xScale(d.date);
            const y = yScale(d.actual);
            const color = STATUS_COLORS[d.type ?? 'normal'];
            return (
              <g key={`a-${d.date}`}
                onMouseMove={(e) => handleMouseMove(e, d)}
                onClick={() => onAnomalyClick?.(d)}
                className="cursor-pointer"
              >
                <circle cx={x} cy={y} r={10} fill={color} opacity={0.08} />
                <circle cx={x} cy={y} r={5} fill={color} stroke="#0D111A" strokeWidth={2} />
              </g>
            );
          })}

          {/* Hover crosshair */}
          {hoveredPoint && (
            <line
              x1={xScale(hoveredPoint.date)} y1={padding.top}
              x2={xScale(hoveredPoint.date)} y2={chartHeight - padding.bottom}
              stroke="#8A94A6" strokeWidth={1} strokeDasharray="3 3" opacity={0.4}
            />
          )}
        </svg>

        {/* Tooltip */}
        <AnimatePresence>
          {hoveredPoint && (
            <motion.div
              initial={{ opacity: 0, scale: 0.96 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.96 }}
              transition={{ duration: 0.12 }}
              className="absolute pointer-events-none z-20 bg-[#111827] border border-[#2a3040] rounded-sm p-3 min-w-[180px]"
              style={{ left: Math.min(tooltipPos.x + 16, chartWidth * 0.7), top: Math.max(tooltipPos.y - 80, 10) }}
            >
              <div className="font-mono text-[10px] text-[#8A94A6] tracking-wider mb-2">
                {new Date(hoveredPoint.date + 'T00:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
              </div>
              {hoveredPoint.type && hoveredPoint.type !== 'normal' && (
                <div className="flex items-center gap-2 mb-2">
                  <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: STATUS_COLORS[hoveredPoint.type] }} />
                  <span className="text-[10px] font-mono font-medium tracking-wider"
                    style={{ color: STATUS_COLORS[hoveredPoint.type] }}>
                    {hoveredPoint.type === 'fraud' ? 'FRAUD SPIKE' : hoveredPoint.type === 'organic' ? 'ORGANIC SURGE' : 'REVIEW'}
                  </span>
                </div>
              )}
              <div className="space-y-1">
                <div className="flex justify-between text-xs">
                  <span className="text-[#8A94A6]">Transactions</span>
                  <span className="text-[#F3F4F6] font-mono">{hoveredPoint.actual.toLocaleString()}</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-[#8A94A6]">Baseline</span>
                  <span className="text-[#8A94A6] font-mono">{hoveredPoint.baseline.toLocaleString()}</span>
                </div>
                {hoveredPoint.type !== 'normal' && (
                  <div className="pt-1 mt-1 border-t border-[#1a1f2e] flex justify-between text-xs">
                    <span className="text-[#8A94A6]">Anomaly</span>
                    <span className="font-mono font-medium"
                      style={{ color: STATUS_COLORS[hoveredPoint.type ?? 'normal'] }}>
                      +{((hoveredPoint.actual / hoveredPoint.baseline - 1) * 100).toFixed(0)}%
                    </span>
                  </div>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
