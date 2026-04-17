import React from 'react'
import { motion } from 'framer-motion'
import clsx from 'clsx'

export default function BarMetric({ label, value, max = 100, color = 'earth', suffix = '%' }) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100))
  const colors = {
    earth: 'bg-earth-500', sky: 'bg-sky-500', amber: 'bg-amber-500', red: 'bg-red-500'
  }
  const auto = value >= 70 ? 'earth' : value >= 45 ? 'amber' : 'red'
  const barColor = colors[color === 'auto' ? auto : color] || colors.earth

  return (
    <div className="space-y-1.5">
      <div className="flex justify-between items-center">
        <span className="text-xs text-carbon-600">{label}</span>
        <span className="text-xs font-mono font-medium text-carbon-800">{value?.toFixed?.(1) ?? value}{suffix}</span>
      </div>
      <div className="h-2 bg-carbon-100 rounded-full overflow-hidden">
        <motion.div
          className={clsx('h-full rounded-full', barColor)}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
        />
      </div>
    </div>
  )
}
