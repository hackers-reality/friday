import { type ReactElement } from 'react'
import {
  AreaChart as RechartsAreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts'

interface DataPoint {
  label: string
  value: number
  [key: string]: string | number
}

interface AreaChartProps {
  data: DataPoint[]
  dataKey?: string
  color?: string
  height?: number
  showGrid?: boolean
  showAxis?: boolean
  gradient?: boolean
  className?: string
}

export function FridayAreaChart({
  data,
  dataKey = 'value',
  color = '#00f5ff',
  height = 200,
  showGrid = false,
  showAxis = true,
  gradient = true,
  className = '',
}: AreaChartProps): ReactElement {
  const gradientId = `area-gradient-${color.replace('#', '')}`

  return (
    <div className={className}>
      <ResponsiveContainer width="100%" height={height}>
        <RechartsAreaChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
          {gradient && (
            <defs>
              <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={color} stopOpacity={0.3} />
                <stop offset="95%" stopColor={color} stopOpacity={0} />
              </linearGradient>
            </defs>
          )}
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
            labelStyle={{ color: '#686890' }}
          />
          <Area
            type="monotone"
            dataKey={dataKey}
            stroke={color}
            strokeWidth={2}
            fill={gradient ? `url(#${gradientId})` : 'transparent'}
            animationDuration={800}
          />
        </RechartsAreaChart>
      </ResponsiveContainer>
    </div>
  )
}
