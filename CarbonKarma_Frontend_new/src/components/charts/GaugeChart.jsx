import React from 'react'
import { RadialBarChart, RadialBar, ResponsiveContainer, PolarAngleAxis } from 'recharts'

export default function GaugeChart({ value = 0, max = 100, color = '#5c9934', size = 120, label, sublabel }) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100))
  const data = [{ value: pct, fill: color }]

  const getColor = (v) => {
    if (v >= 70) return '#5c9934'
    if (v >= 45) return '#f59e0b'
    return '#ef4444'
  }

  const finalColor = color === 'auto' ? getColor(value) : color

  return (
    <div className="flex flex-col items-center">
      <div style={{ width: size, height: size / 2 + 20 }} className="relative">
        <ResponsiveContainer width="100%" height={size}>
          <RadialBarChart
            cx="50%" cy="80%"
            innerRadius="60%" outerRadius="100%"
            barSize={10}
            data={data}
            startAngle={180} endAngle={0}
          >
            <PolarAngleAxis type="number" domain={[0, 100]} angleAxisId={0} tick={false} />
            <RadialBar background={{ fill: '#e9ecef' }} dataKey="value" fill={finalColor} cornerRadius={5} />
          </RadialBarChart>
        </ResponsiveContainer>
        <div className="absolute bottom-0 left-0 right-0 flex flex-col items-center">
          <span className="text-xl font-display text-carbon-900">{value.toFixed?.(0) ?? value}</span>
          {sublabel && <span className="text-xs text-carbon-400 font-mono">{sublabel}</span>}
        </div>
      </div>
      {label && <p className="text-xs text-carbon-500 mt-1 text-center">{label}</p>}
    </div>
  )
}
