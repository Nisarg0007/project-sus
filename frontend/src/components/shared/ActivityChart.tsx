import { useMemo } from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import { generateActivityData } from '../../data/mockData';

export function ActivityChart() {
  const data = useMemo(() => {
    const rawData = generateActivityData();

    // Aggregate by date for the main chart
    const aggregated = rawData.reduce((acc, item) => {
      if (!acc[item.date]) {
        acc[item.date] = {
          date: item.date,
          baseline: 0,
          actual: 0,
          hasAnomaly: false,
          anomalyType: null as string | null,
        };
      }
      acc[item.date].baseline += item.baseline;
      acc[item.date].actual += item.actual;

      if (item.type && item.type !== 'normal') {
        acc[item.date].hasAnomaly = true;
        acc[item.date].anomalyType = item.type;
      }

      return acc;
    }, {} as Record<string, { date: string; baseline: number; actual: number; hasAnomaly: boolean; anomalyType: string | null }>);

    return Object.values(aggregated).sort((a, b) => a.date.localeCompare(b.date));
  }, []);

  const avgBaseline = useMemo(() => {
    return data.reduce((sum, d) => sum + d.baseline, 0) / data.length;
  }, [data]);

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-sus-surface border border-sus-border rounded-lg p-3 shadow-xl">
          <p className="text-sus-text-dim text-xs font-mono mb-2">{label}</p>
          <p className="text-sus-text text-sm">
            <span className="text-sus-cyan">Actual:</span>{' '}
            {payload[0]?.value?.toLocaleString()}
          </p>
          <p className="text-sus-text text-sm">
            <span className="text-sus-text-dim">Baseline:</span>{' '}
            {payload[1]?.value?.toLocaleString()}
          </p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="bg-sus-surface border border-sus-border rounded-2xl p-6">
      <ResponsiveContainer width="100%" height={400}>
        <AreaChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="colorActual" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#06b6d4" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="colorBaseline" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#6b7280" stopOpacity={0.2} />
              <stop offset="95%" stopColor="#6b7280" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e3a5f" />
          <XAxis
            dataKey="date"
            stroke="#6b7280"
            fontSize={10}
            tickLine={false}
            tickFormatter={(value) => {
              const date = new Date(value);
              return `${date.getMonth() + 1}/${date.getDate()}`;
            }}
          />
          <YAxis stroke="#6b7280" fontSize={10} tickLine={false} />
          <Tooltip content={<CustomTooltip />} />
          <ReferenceLine
            y={avgBaseline}
            stroke="#6b7280"
            strokeDasharray="5 5"
            label={{ value: 'AVG BASELINE', position: 'right', fill: '#6b7280', fontSize: 10 }}
          />
          <Area
            type="monotone"
            dataKey="actual"
            stroke="#06b6d4"
            strokeWidth={2}
            fillOpacity={1}
            fill="url(#colorActual)"
          />
          <Area
            type="monotone"
            dataKey="baseline"
            stroke="#6b7280"
            strokeWidth={1}
            strokeDasharray="4 4"
            fillOpacity={1}
            fill="url(#colorBaseline)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
