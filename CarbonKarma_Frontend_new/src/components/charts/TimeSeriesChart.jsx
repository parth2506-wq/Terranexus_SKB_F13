import React from 'react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend, ReferenceLine
} from 'recharts'
import { format, parseISO } from 'date-fns'

const COLORS = { water: '#36aaf5', ndvi: '#5c9934', methane: '#f59e0b', rainfall: '#7cc8fb', temperature: '#ef4444' }

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="glass-card p-3 shadow-card-hover text-xs space-y-1 min-w-[160px]">
      <p className="font-medium text-carbon-700 mb-1.5">{label}</p>
      {payload.map(({ name, value, color }) => (
        <div key={name} className="flex items-center justify-between gap-3">
          <span className="flex items-center gap-1.5" style={{ color }}>
            <span className="w-2 h-2 rounded-full" style={{ background: color }} />
            {name}
          </span>
          <span className="font-mono text-carbon-800">{typeof value === 'number' ? value.toFixed(3) : value}</span>
        </div>
      ))}
    </div>
  )
}

export default function TimeSeriesChart({ data = [], series = [], height = 220, title, showGrid = true }) {
  const formatted = data.map(d => ({
    ...d,
    date: d.timestamp ? (() => {
      try { return format(parseISO(d.timestamp), 'MMM d') } catch { return d.timestamp }
    })() : d.date
  }))

  return (
    <div>
      {title && <p className="text-xs font-medium text-carbon-500 uppercase tracking-wider mb-3">{title}</p>}
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={formatted} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
          {showGrid && <CartesianGrid strokeDasharray="3 3" stroke="#e9ecef" vertical={false} />}
          <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#adb5bd', fontFamily: 'JetBrains Mono' }} tickLine={false} axisLine={false} />
          <YAxis tick={{ fontSize: 10, fill: '#adb5bd', fontFamily: 'JetBrains Mono' }} tickLine={false} axisLine={false} />
          <Tooltip content={<CustomTooltip />} cursor={{ stroke: '#ced4da', strokeWidth: 1, strokeDasharray: '4 4' }} />
          <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 11, fontFamily: 'DM Sans' }} />
          {series.map(({ key, name, color, dashed }) => (
            <Line
              key={key} type="monotone" dataKey={key} name={name}
              stroke={color || COLORS[key] || '#5c9934'}
              strokeWidth={2} dot={false} activeDot={{ r: 4 }}
              strokeDasharray={dashed ? '5 3' : undefined}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
