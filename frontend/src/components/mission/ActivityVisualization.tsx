import { useMemo, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ActivityDataPoint } from '../../types';

interface ActivityVisualizationProps {
  data: ActivityDataPoint[];
  selectedAnomalyId?: string;
  onAnomalyClick?: (point: ActivityDataPoint) => void;
}

export function ActivityVisualization({ 
  data, 
  selectedAnomalyId,
  onAnomalyClick 
}: ActivityVisualizationProps) {
  const [hoveredPoint, setHoveredPoint] = useState<ActivityDataPoint | null>(null);
  const [tooltipPosition, setTooltipPosition] = useState({ x: 0, y: 0 });

  // Calculate chart dimensions
  const chartWidth = 1200;
  const chartHeight = 320;
  const padding = { top: 20, right: 20, bottom: 40, left: 60 };
  const innerWidth = chartWidth - padding.left - padding.right;
  const innerHeight = chartHeight - padding.top - padding.bottom;

  // Process data for the selected merchant
  const merchantData = useMemo(() => {
    return data.filter(d => d.merchant === 'merchant_001');
  }, [data]);

  // Calculate scales
  const { xScale, yScale, maxVal } = useMemo(() => {
    const dates = merchantData.map(d => d.date);
    const values = merchantData.flatMap(d => [d.actual, d.baseline]);
    const maxVal = Math.max(...values) * 1.1;
    
    const xScale = (date: string) => {
      const idx = dates.indexOf(date);
      return padding.left + (idx / (dates.length - 1)) * innerWidth;
    };
    
    const yScale = (value: number) => {
      return padding.top + innerHeight - (value / maxVal) * innerHeight;
    };
    
    return { xScale, yScale, maxVal };
  }, [merchantData, innerWidth, innerHeight, padding]);

  // Generate path for actual values
  const actualPath = useMemo(() => {
    if (merchantData.length === 0) return '';
    return merchantData.map((d, i) => {
      const x = xScale(d.date);
      const y = yScale(d.actual);
      return `${i === 0 ? 'M' : 'L'} ${x} ${y}`;
    }).join(' ');
  }, [merchantData, xScale, yScale]);

  // Generate path for baseline
  const baselinePath = useMemo(() => {
    if (merchantData.length === 0) return '';
    return merchantData.map((d, idx) => {
      const x = xScale(d.date);
      const y = yScale(d.baseline);
      return `${idx === 0 ? 'M' : 'L'} ${x} ${y}`;
    }).join(' ');
  }, [merchantData, xScale, yScale]);

  // Area fill for actual
  const actualArea = useMemo(() => {
    if (merchantData.length === 0) return '';
    const bottom = yScale(0);
    const points = merchantData.map((d) => {
      const x = xScale(d.date);
      const y = yScale(d.actual);
      return `${x},${y}`;
    });
    return `M ${padding.left},${bottom} L ${points.join(' L ')} L ${xScale(merchantData[merchantData.length - 1].date)},${bottom} Z`;
  }, [merchantData, xScale, yScale, padding]);

  // Y-axis ticks
  const yTicks = useMemo(() => {
    const ticks = [];
    const step = Math.ceil(maxVal / 5 / 100) * 100;
    for (let i = 0; i <= maxVal; i += step) {
      ticks.push(i);
    }
    return ticks;
  }, [maxVal]);

  // X-axis labels (every 7 days)
  const xLabels = useMemo(() => {
    return merchantData
      .filter((_, i) => i % 7 === 0 || i === merchantData.length - 1)
      .map(d => ({
        date: d.date,
        label: new Date(d.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      }));
  }, [merchantData]);

  // Anomaly points
  const anomalyPoints = useMemo(() => {
    return merchantData.filter(d => d.type && d.type !== 'normal');
  }, [merchantData]);

  const getAnomalyColor = (type: string | undefined) => {
    switch (type) {
      case 'fraud': return '#FF5C5C';
      case 'organic': return '#34D399';
      case 'review': return '#FBBF24';
      default: return '#38BDF8';
    }
  };

  const handleMouseMove = (e: React.MouseEvent<SVGGElement>, point: ActivityDataPoint) => {
    const svg = e.currentTarget.closest('svg');
    if (svg) {
      const rect = svg.getBoundingClientRect();
      setTooltipPosition({
        x: e.clientX - rect.left,
        y: e.clientY - rect.top,
      });
      setHoveredPoint(point);
    }
  };

  return (
    <div className="relative">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-lg font-medium">TRANSACTION ACTIVITY</h3>
          <p className="text-sm text-[#8A94A6] font-mono mt-1">
            MERCHANT_001 • 45-DAY WINDOW
          </p>
        </div>
        <div className="flex items-center gap-6 text-xs font-mono">
          <span className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[#34D399]" />
            ORGANIC
          </span>
          <span className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[#FF5C5C]" />
            FRAUD
          </span>
          <span className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[#FBBF24]" />
            REVIEW
          </span>
        </div>
      </div>

      <div className="bg-[#0D111A] border border-[#1a1f2e] rounded-sm p-6 relative overflow-hidden">
        <svg 
          viewBox={`0 0 ${chartWidth} ${chartHeight}`}
          className="w-full h-auto"
          onMouseLeave={() => setHoveredPoint(null)}
        >
          <defs>
            <linearGradient id="actualGradient" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#38BDF8" stopOpacity={0.15} />
              <stop offset="100%" stopColor="#38BDF8" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="baselineGradient" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#8A94A6" stopOpacity={0.05} />
              <stop offset="100%" stopColor="#8A94A6" stopOpacity={0} />
            </linearGradient>
          </defs>

          {/* Grid lines */}
          {yTicks.map((tick) => (
            <g key={tick}>
              <line
                x1={padding.left}
                y1={yScale(tick)}
                x2={chartWidth - padding.right}
                y2={yScale(tick)}
                stroke="#1a1f2e"
                strokeWidth={1}
              />
              <text
                x={padding.left - 10}
                y={yScale(tick)}
                textAnchor="end"
                fill="#8A94A6"
                fontSize={10}
                fontFamily="monospace"
              >
                {tick}
              </text>
            </g>
          ))}

          {/* X-axis labels */}
          {xLabels.map(({ date, label }) => (
            <text
              key={date}
              x={xScale(date)}
              y={chartHeight - 10}
              textAnchor="middle"
              fill="#8A94A6"
              fontSize={10}
              fontFamily="monospace"
            >
              {label}
            </text>
          ))}

          {/* Baseline area */}
          <path
            d={baselinePath.replace('M', `M ${padding.left},${yScale(0)} L`)}
            fill="url(#baselineGradient)"
          />

          {/* Baseline line */}
          <path
            d={baselinePath}
            fill="none"
            stroke="#8A94A6"
            strokeWidth={1}
            strokeDasharray="4 4"
            opacity={0.5}
          />

          {/* Actual area */}
          <path
            d={actualArea}
            fill="url(#actualGradient)"
          />

          {/* Actual line */}
          <path
            d={actualPath}
            fill="none"
            stroke="#38BDF8"
            strokeWidth={2}
          />

          {/* Anomaly points */}
          {anomalyPoints.map((point) => {
            const x = xScale(point.date);
            const y = yScale(point.actual);
            const isSelected = point.anomalyId === selectedAnomalyId;
            const color = getAnomalyColor(point.type);

            return (
              <g 
                key={point.date}
                onMouseMove={(e) => handleMouseMove(e, point)}
                onClick={() => onAnomalyClick?.(point)}
                className="cursor-pointer"
              >
                {/* Pulse effect for selected */}
                {isSelected && (
                  <>
                    <circle
                      cx={x}
                      cy={y}
                      r={20}
                      fill={color}
                      opacity={0.1}
                    >
                      <animate
                        attributeName="r"
                        from="12"
                        to="24"
                        dur="1.5s"
                        repeatCount="indefinite"
                      />
                      <animate
                        attributeName="opacity"
                        from="0.2"
                        to="0"
                        dur="1.5s"
                        repeatCount="indefinite"
                      />
                    </circle>
                    <circle
                      cx={x}
                      cy={y}
                      r={12}
                      fill="none"
                      stroke={color}
                      strokeWidth={2}
                      opacity={0.5}
                    />
                  </>
                )}
                
                {/* Point */}
                <circle
                  cx={x}
                  cy={y}
                  r={isSelected ? 6 : 4}
                  fill={color}
                  stroke="#080B12"
                  strokeWidth={2}
                />
              </g>
            );
          })}

          {/* Selected anomaly marker */}
          {merchantData.find(d => d.isSelected) && (
            <g>
              <line
                x1={xScale(merchantData.find(d => d.isSelected)!.date)}
                y1={padding.top}
                x2={xScale(merchantData.find(d => d.isSelected)!.date)}
                y2={chartHeight - padding.bottom}
                stroke="#FF5C5C"
                strokeWidth={1}
                strokeDasharray="4 4"
                opacity={0.5}
              />
              <text
                x={xScale(merchantData.find(d => d.isSelected)!.date)}
                y={padding.top - 5}
                textAnchor="middle"
                fill="#FF5C5C"
                fontSize={10}
                fontFamily="monospace"
              >
                ANOMALY 024
              </text>
            </g>
          )}
        </svg>

        {/* Tooltip */}
        <AnimatePresence>
          {hoveredPoint && (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="absolute pointer-events-none z-10 bg-[#1a1f2e] border border-[#2a3040] rounded-sm p-3 text-sm"
              style={{
                left: Math.min(tooltipPosition.x + 16, chartWidth - 200),
                top: tooltipPosition.y - 60,
              }}
            >
              <div className="font-mono text-xs text-[#8A94A6] mb-1">
                {new Date(hoveredPoint.date).toLocaleDateString('en-US', { 
                  month: 'short', 
                  day: 'numeric',
                  year: 'numeric'
                })}
              </div>
              <div className="flex items-center gap-2 mb-1">
                <span className="w-2 h-2 rounded-full" style={{ backgroundColor: getAnomalyColor(hoveredPoint.type) }} />
                <span className="font-medium" style={{ color: getAnomalyColor(hoveredPoint.type) }}>
                  {hoveredPoint.type === 'fraud' ? 'FRAUD' : 
                   hoveredPoint.type === 'organic' ? 'ORGANIC' :
                   hoveredPoint.type === 'review' ? 'REVIEW' : 'NORMAL'}
                </span>
              </div>
              <div className="text-[#F3F4F6]">
                {hoveredPoint.actual.toLocaleString()} transactions
              </div>
              <div className="text-[#8A94A6] text-xs">
                Baseline: {hoveredPoint.baseline.toLocaleString()}
              </div>
              {hoveredPoint.type !== 'normal' && (
                <div className="text-xs font-mono mt-1" style={{ color: getAnomalyColor(hoveredPoint.type) }}>
                  {((hoveredPoint.actual / hoveredPoint.baseline - 1) * 100).toFixed(0)}% above baseline
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
