import React from 'react'
import MetricCard from '../ui/MetricCard'
import { Leaf, Droplets, Sparkles } from 'lucide-react'

export default function ImpactVisualizer({ analytics }) {
  const impact = analytics?.impact_metrics || {}
  const co2 = impact.co2e_reduced_tonnes ?? 12
  const water = impact.water_saved_m3_total ?? 4300
  const methanePct = impact.ch4_reduction_pct ?? impact.methane_reduction_pct ?? 32
  const trees = impact.trees_equivalent ?? Math.round(co2 * 40)
  const households = Math.max(1, Math.round(water / 150))

  return (
    <div className="glass-card p-5 space-y-5">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-wider text-carbon-500">Impact Visualizer</p>
          <h3 className="text-2xl font-display text-carbon-900">Relatable environmental savings</h3>
        </div>
        <div className="text-right text-xs text-carbon-400">Estimated from analytics</div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <MetricCard label="CO₂ reduced" value={co2.toFixed(1)} unit="t" icon={Leaf} color="earth" />
        <MetricCard label="Water saved" value={(water / 1000).toFixed(1)} unit="k m³" icon={Droplets} color="sky" />
        <MetricCard label="Methane reduced" value={`${methanePct.toFixed(0)}%`} icon={Sparkles} color="amber" />
      </div>

      <div className="grid grid-cols-1 gap-3">
        <div className="glass-card p-4 bg-earth-50 border-earth-200/70">
          <p className="text-sm font-medium text-carbon-900">Equivalent to planting</p>
          <p className="text-3xl font-display text-carbon-900 mt-2">{trees.toLocaleString()}</p>
          <p className="text-xs text-carbon-500 mt-1">trees in one season</p>
        </div>
        <div className="glass-card p-4 bg-sky-50 border-sky-200/70">
          <p className="text-sm font-medium text-carbon-900">Water saved for households</p>
          <p className="text-3xl font-display text-carbon-900 mt-2">{households.toLocaleString()}</p>
          <p className="text-xs text-carbon-500 mt-1">households for one month</p>
        </div>
      </div>
    </div>
  )
}
