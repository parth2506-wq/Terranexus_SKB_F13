import React, { useMemo, useState } from 'react'
import MetricCard from '../ui/MetricCard'
import { motion } from 'framer-motion'

function normalizeSeries(data) {
  if (!data) return []
  if (Array.isArray(data)) return data
  if (data.records) return data.records
  if (data.data) return normalizeSeries(data.data)
  return []
}

export default function WhatIfSimulation({ fusionSeries, analytics }) {
  const [delayDays, setDelayDays] = useState(2)
  const [awdEnabled, setAwdEnabled] = useState(true)
  const series = normalizeSeries(fusionSeries)
  const methaneBase = analytics?.comparative_analysis?.your_flux_mg_m2_day ?? series[series.length - 1]?.methane ?? 280
  const waterBase = analytics?.impact_metrics?.water_saved_m3_total ?? 5200

  const output = useMemo(() => {
    const awdModifier = awdEnabled ? -0.09 : 0.12
    const delayModifier = delayDays * -0.032
    const methanePct = Math.max(-60, Math.min(45, awdModifier * 100 + delayModifier * 100))
    const waterPct = Math.max(-48, Math.min(22, delayModifier * 100 + (awdEnabled ? -0.16 : 0.08)))
    const methaneChange = ((methanePct / 100) * methaneBase).toFixed(1)
    const waterChange = ((waterPct / 100) * waterBase).toFixed(0)
    const compliance = awdEnabled ? 'Improved AWD compliance' : 'Reduced AWD compliance'
    const verdict = awdEnabled
      ? 'Strong AWD outcome expected with delayed irrigation support.'
      : 'AWD disabled; methane may rise and compliance declines.'

    return { methanePct, waterPct, methaneChange, waterChange, compliance, verdict }
  }, [awdEnabled, delayDays, methaneBase, waterBase])

  return (
    <div className="glass-card p-5 space-y-5">
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-wider text-carbon-500">What-if simulation</p>
          <h3 className="text-2xl font-display text-carbon-900">Test irrigation decisions</h3>
        </div>
        <div className="text-right">
          <p className="text-xs uppercase text-carbon-400">AWD strategy</p>
          <p className="text-lg font-display text-earth-700">{awdEnabled ? 'Enabled' : 'Disabled'}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4">
        <div className="glass-card p-4 bg-white/90 border border-carbon-200">
          <div className="flex items-center justify-between gap-4">
            <label className="text-xs uppercase tracking-wider text-carbon-500">Delay irrigation</label>
            <span className="text-sm font-display text-earth-700">{delayDays} days</span>
          </div>
          <input
            type="range"
            min="0"
            max="7"
            value={delayDays}
            onChange={e => setDelayDays(Number(e.target.value))}
            className="w-full accent-earth-600 mt-3"
          />
        </div>

        <div className="glass-card p-4 bg-sky-50 border-sky-200/70 flex items-center justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-wider text-carbon-500">AWD toggle</p>
            <p className="text-lg font-display text-carbon-900">{awdEnabled ? 'Active AWD' : 'Conventional'}</p>
          </div>
          <button
            type="button"
            onClick={() => setAwdEnabled(prev => !prev)}
            className={`px-4 py-2 rounded-xl font-medium transition ${awdEnabled ? 'bg-earth-600 text-white' : 'bg-white text-carbon-700 border border-carbon-200'}`}
          >
            {awdEnabled ? 'Disable' : 'Enable'}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <MetricCard label="Methane Δ" value={`${output.methanePct.toFixed(1)}%`} unit="change" color={output.methanePct < 0 ? 'earth' : 'red'} />
        <MetricCard label="Water Δ" value={`${output.waterPct.toFixed(1)}%`} unit="change" color={output.waterPct < 0 ? 'sky' : 'amber'} />
        <MetricCard label="Compliance" value={output.compliance} unit="" color={awdEnabled ? 'earth' : 'amber'} />
      </div>

      <div className="glass-card p-4 bg-white/90 border border-carbon-200 text-sm text-carbon-600">
        <p className="font-medium text-carbon-900">Projected impact</p>
        <p className="mt-2 leading-relaxed">{output.verdict} Estimated methane shift: {output.methaneChange} mg/m²/d, water usage shift: {output.waterChange} m³.</p>
      </div>
    </div>
  )
}
