import { type ReactElement } from 'react'
import {
  BarChart as RechartsBarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Cell,
} from 'recharts'

interface DataPoint {
  label: string
  value: number
  color?: string
}

interface BarChartProps {
  data: DataPoint[]
  dataKey?: string
  color?: string
  height?: number
  showGrid?: boolean
  showAxis?: boolean
  barSize?: number
  className?: string
}

const NEON_COLORS = [
  '#00f5ff', '#b400ff', '#00ff88', '#ffe600', '#ff003c', '#ff6b00', '#ff2d95',
]

export function FridayBarChart({
  data,
  dataKey = 'value',
  color,
  height = 200,
  showGrid = false,
  showAxis = true,
  barSize = 16,
  className = '',
}: BarChartProps): ReactElement {
  return (
    <div className={className}>
      <ResponsiveContainer width="100%" height={height}>
        <RechartsBarChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
          {showGrid && (
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="rgba(0,245,255,0.05)"
              vertical={false}
            />
          )}
          {showAxis && (
            <>
              <XAxis
                dataKey="label"
                axisLine={false}
                tickLine={false}
                tick={{ fill: '#686890', fontSize: 10 }}
              />
              <YAxis
                axisLine={false}
                tickLine={false}
                tick={{ fill: '#686890', fontSize: 10 }}
              />
            </>
          )}
          <Tooltip
            contentStyle={{
              background: '#0d0d1a',
              border: '1px solid rgba(0,245,255,0.15)',
              borderRadius: '8px',
              color: '#ddddee',
              fontSize: '12px',
              fontFamily: "'JetBrains Mono', monospace",
            }}
            cursor={{ fill: 'rgba(0,245,255,0.05)' }}
          />
          <Bar
            dataKey={dataKey}
            barSize={barSize}
            radius={[4, 4, 0, 0]}
            animationDuration={600}
          >
            {data.map((entry, index) => (
              <Cell
                key={entry.label}
                fill={entry.color ?? color ?? NEON_COLORS[index % NEON_COLORS.length]!}
              />
            ))}
          </Bar>
        </RechartsBarChart>
      </ResponsiveContainer>
    </div>
  )
}
