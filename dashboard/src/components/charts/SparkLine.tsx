import { type ReactElement } from 'react'
import { LineChart, Line, ResponsiveContainer } from 'recharts'

interface SparkLineProps {
  data: number[]
  color?: string
  width?: number
  height?: number
  className?: string
}

export function FridaySparkLine({ data, color = '#00f5ff', width, height = 32, className = '' }: SparkLineProps): ReactElement {
  const chartData = data.map((value, index) => ({ index, value }))

  return (
    <div className={className} style={width ? { width } : undefined}>
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={chartData} margin={{ top: 2, right: 2, bottom: 2, left: 2 }}>
          <Line
            type="monotone"
            dataKey="value"
            stroke={color}
            strokeWidth={1.5}
            dot={false}
            animationDuration={400}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
