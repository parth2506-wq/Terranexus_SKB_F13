import React from 'react'
import { motion } from 'framer-motion'
import { useTranslation } from 'react-i18next'
import { useApp } from '../../context/AppContext'
import TimeSeriesChart from '../charts/TimeSeriesChart'
import StatusBadge from '../ui/StatusBadge'
import MetricCard from '../ui/MetricCard'
import BarMetric from '../charts/BarMetric'
import { Flame, TrendingDown } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts'
import { format, parseISO } from 'date-fns'

export default function MethanePanel() {
  const { t } = useTranslation()
  const { panelData } = useApp()
  const data = panelData.methane
  if (!data) return null

  const m = data.methane || {}
  const latest = m.latest || {}
  const agg = m.aggregate || {}
  const perStep = m.per_step || []

  const barData = perStep.map(r => ({
    date: (() => { try { return format(parseISO(r.timestamp), 'MMM d') } catch { return r.timestamp } })(),
    methane: r.methane,
    reduction: r.reduction_percent,
    fill: r.category === 'high' ? '#ef4444' : r.category === 'medium' ? '#f59e0b' : '#5c9934'
  }))

  const reductionPct = agg.total_reduction_pct || 0
  const catDist = agg.category_distribution || {}

  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="space-y-5">
      <div className="flex items-center gap-2">
        <Flame className="w-5 h-5 text-amber-600" />
        <h2 className="section-title mb-0">{t('methane.title')}</h2>
      </div>

      {/* Hero metrics */}
      <div className="glass-card p-5 bg-gradient-to-br from-amber-50 to-red-50/30 border border-amber-200/60">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center">
            <p className="text-xs text-carbon-500 mb-1">{t('methane.flux')}</p>
            <p className="text-3xl font-display text-carbon-900">{latest.methane?.toFixed(1)}</p>
            <p className="text-xs font-mono text-carbon-400">{t('methane.unit')}</p>
            <StatusBadge type={latest.category} className="mt-1.5" />
          </div>
          <div className="text-center">
            <p className="text-xs text-carbon-500 mb-1">{t('methane.reduction')}</p>
            <p className="text-3xl font-display text-earth-700">{reductionPct?.toFixed(1)}%</p>
            <p className="text-xs font-mono text-carbon-400">vs CF baseline</p>
          </div>
          <div className="text-center">
            <p className="text-xs text-carbon-500 mb-1">{t('methane.seasonal')}</p>
            <p className="text-3xl font-display text-carbon-900">{agg.season_total_kg_ha?.toFixed(1)}</p>
            <p className="text-xs font-mono text-carbon-400">{t('methane.kgHa')}</p>
          </div>
          <div className="text-center">
            <p className="text-xs text-carbon-500 mb-1">{t('methane.baseline')}</p>
            <p className="text-3xl font-display text-red-400">{agg.baseline_kg_ha?.toFixed(1)}</p>
            <p className="text-xs font-mono text-carbon-400">{t('methane.kgHa')}</p>
          </div>
        </div>
        <div className="mt-4 pt-4 border-t border-amber-200/40">
          <BarMetric label="CH₄ Reduction vs Conventional Flooding" value={reductionPct} max={80} color="auto" />
        </div>
      </div>

      {/* Bar chart per step */}
      <div className="glass-card p-4">
        <p className="text-sm font-medium text-carbon-700 mb-4">CH₄ Flux Per Observation Step</p>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={barData} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e9ecef" vertical={false} />
            <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#adb5bd', fontFamily: 'JetBrains Mono' }} tickLine={false} axisLine={false} />
            <YAxis tick={{ fontSize: 10, fill: '#adb5bd' }} tickLine={false} axisLine={false} />
            <Tooltip formatter={v => [`${v.toFixed(1)} mg/m²/day`, 'CH₄ Flux']} labelStyle={{ fontFamily: 'DM Sans', fontSize: 12 }} />
            <ReferenceLine y={400} stroke="#ef4444" strokeDasharray="4 4" label={{ value: 'CF Baseline', position: 'right', fontSize: 10, fill: '#ef4444' }} />
            <Bar dataKey="methane" radius={[4, 4, 0, 0]} fill="#f59e0b">
              {barData.map((entry, i) => (
                <rect key={i} fill={entry.fill} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Reduction time series */}
      <div className="glass-card p-4">
        <p className="text-sm font-medium text-carbon-700 mb-4">Reduction % Over Time</p>
        <TimeSeriesChart
          data={perStep.map(r => ({ timestamp: r.timestamp, reduction: r.reduction_percent, methane: r.methane }))}
          height={180}
          series={[
            { key: 'reduction', name: 'Reduction %', color: '#5c9934' },
          ]}
        />
      </div>

      {/* Category distribution */}
      <div className="glass-card p-4">
        <p className="text-sm font-medium text-carbon-700 mb-3">Emission Category Distribution</p>
        <div className="grid grid-cols-3 gap-3">
          {[['low', catDist.low, '#5c9934'], ['medium', catDist.medium, '#f59e0b'], ['high', catDist.high, '#ef4444']].map(([cat, count, color]) => (
            <div key={cat} className="text-center rounded-xl p-3 border" style={{ borderColor: color + '40', background: color + '10' }}>
              <p className="text-2xl font-display" style={{ color }}>{count || 0}</p>
              <p className="text-xs text-carbon-500 mt-1 capitalize">{cat} emission steps</p>
            </div>
          ))}
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <MetricCard label="Mean Daily Flux" value={agg.mean_daily_flux?.toFixed(1)} unit="mg/m²/d" color="amber" />
        <MetricCard label="Peak Flux" value={agg.max_daily_flux?.toFixed(1)} unit="mg/m²/d" color="red" />
        <MetricCard label="Season Days" value={agg.season_days} icon={TrendingDown} color="earth" />
        <MetricCard label="Observations" value={agg.n_observations} color="sky" />
      </div>
    </motion.div>
  )
}
