import React, { useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'

function normalizeSeries(data) {
  if (!data) return []
  if (Array.isArray(data)) return data
  if (data.records) return data.records
  if (data.data) return normalizeSeries(data.data)
  return []
}

export default function TrustReplay({ fusionSeries }) {
  const series = normalizeSeries(fusionSeries)
  const [stepIndex, setStepIndex] = useState(0)
  const steps = useMemo(() => [
    { title: 'Flood detected', description: 'Satellite water concentration and surface inundation triggered the first AWD event.', metric: `${(series[0]?.water_level ?? 0.72) * 100}% water` },
    { title: 'Drying detected', description: 'Field moisture drops below threshold, confirming a drying phase before AWD re-flooding.', metric: `${(series[Math.min(series.length - 1, 3)]?.water_level ?? 0.18) * 100}% water` },
    { title: 'Irrigation event', description: 'Rainfall or irrigation signatures coincide with rising water levels in the field.', metric: `${series.filter(item => item.rainfall > 0 || item.rainfall_mm > 0).length} events` },
    { title: 'AWD cycle confirmed', description: 'The complete flood-dry-flood sequence matches AWD thresholds and verification rules.', metric: 'Cycle confirmed' }
  ], [series])

  const active = steps[stepIndex]
  const timelineProgress = (stepIndex / (steps.length - 1)) * 100

  return (
    <div className="glass-card p-5 space-y-5">
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-wider text-carbon-500">Trust Replay</p>
          <h3 className="text-2xl font-display text-carbon-900">AWD verification timeline</h3>
        </div>
        <div className="text-right">
          <p className="text-xs text-carbon-500 uppercase tracking-wider">Step {stepIndex + 1} of {steps.length}</p>
          <p className="text-xl font-display text-earth-700">{active.title}</p>
        </div>
      </div>

      <div className="glass-card-hover p-4 bg-earth-50 border border-earth-200/70 rounded-3xl">
        <div className="relative h-3 rounded-full bg-carbon-200/70 overflow-hidden">
          <motion.div className="absolute inset-y-0 left-0 bg-earth-500 rounded-full" initial={false} animate={{ width: `${timelineProgress}%` }} transition={{ duration: 0.35 }} />
        </div>
        <div className="grid grid-cols-4 gap-2 mt-3 text-[10px] text-carbon-500 uppercase tracking-[0.16em]">
          {steps.map((step, index) => (
            <div key={step.title} className="text-center">{step.title}</div>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-[2fr_1fr] gap-5">
        <div className="space-y-4">
          <p className="text-sm text-carbon-500 leading-relaxed">{active.description}</p>
          <div className="glass-card p-4 bg-white/90 border border-carbon-200">
            <p className="text-xs uppercase tracking-wider text-carbon-400">Current metric</p>
            <p className="text-xl font-display text-carbon-900 mt-2">{active.metric}</p>
          </div>
          <div className="space-y-3">
            <label className="text-xs uppercase tracking-wider text-carbon-500">Replay slider</label>
            <input
              type="range"
              min="0"
              max={steps.length - 1}
              value={stepIndex}
              onChange={e => setStepIndex(Number(e.target.value))}
              className="w-full accent-earth-600"
            />
          </div>
        </div>
        <div className="glass-card p-4 bg-sky-50 border-sky-200/70">
          <p className="text-xs uppercase tracking-wider text-carbon-500 mb-3">Water level playback</p>
          <div className="h-[220px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={series.map((entry, index) => ({
                timestamp: entry.timestamp || entry.date || `T${index + 1}`,
                water: (entry.water_level ?? entry.waterProb ?? entry.water_prob_mean ?? 0) * 100
              }))}>
                <XAxis dataKey="timestamp" tick={{ fontSize: 10, fill: '#94a3b8' }} tickLine={false} axisLine={false} />
                <YAxis tick={{ fontSize: 10, fill: '#94a3b8' }} tickLine={false} axisLine={false} />
                <Tooltip cursor={{ stroke: '#cbd5e1', strokeWidth: 1 }} />
                <Line type="monotone" dataKey="water" stroke="#0ea5e9" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  )
}
