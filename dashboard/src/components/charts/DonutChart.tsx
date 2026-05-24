import { type ReactElement } from 'react'
import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts'

interface DataPoint {
  label: string
  value: number
  color?: string
}

interface DonutChartProps {
  data: DataPoint[]
  size?: number
  className?: string
}

const NEON_COLORS = ['#00f5ff', '#b400ff', '#00ff88', '#ffe600', '#ff003c', '#ff6b00', '#ff2d95']

export function FridayDonutChart({ data, size = 160, className = '' }: DonutChartProps): ReactElement {
  const total = data.reduce((sum, d) => sum + d.value, 0)

  return (
    <div className={className}>
      <ResponsiveContainer width="100%" height={size}>
        <PieChart>
          <Pie
            data={data}
            dataKey="value"
            cx="50%"
            cy="50%"
            innerRadius={size * 0.3}
            outerRadius={size * 0.42}
            paddingAngle={2}
            animationDuration={600}
          >
            {data.map((entry, i) => (
              <Cell key={entry.label} fill={entry.color ?? NEON_COLORS[i % NEON_COLORS.length]} />
            ))}
          </Pie>
        </PieChart>
      </ResponsiveContainer>
      {/* Center total */}
      <div className="text-center -mt-4">
        <span className="text-xl font-display text-neon-cyan">{total}</span>
      </div>
      {/* Legend */}
      <div className="flex flex-wrap justify-center gap-3 mt-3">
        {data.map((d, i) => (
          <div key={d.label} className="flex items-center gap-1.5 text-xs">
            <span className="w-2 h-2 rounded-full" style={{ backgroundColor: d.color ?? NEON_COLORS[i % NEON_COLORS.length] }} />
            <span className="text-text-dim">{d.label}</span>
            <span className="text-text-muted font-mono">{d.value}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
