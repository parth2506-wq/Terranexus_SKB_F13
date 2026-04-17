import React from 'react'
import { motion } from 'framer-motion'
import clsx from 'clsx'

export default function MetricCard({ label, value, unit, icon: Icon, trend, color = 'earth', className = '', onClick }) {
  const colors = {
    earth:  'from-earth-50 to-earth-100/50 border-earth-200/60',
    sky:    'from-sky-50 to-sky-100/50 border-sky-200/60',
    amber:  'from-amber-50 to-amber-100/50 border-amber-200/60',
    red:    'from-red-50 to-red-100/50 border-red-200/60',
    purple: 'from-purple-50 to-purple-100/50 border-purple-200/60',
  }
  const iconColors = { earth: 'text-earth-600', sky: 'text-sky-600', amber: 'text-amber-600', red: 'text-red-600', purple: 'text-purple-600' }

  return (
    <motion.div
      whileHover={onClick ? { y: -2, boxShadow: '0 8px 24px rgba(0,0,0,0.10)' } : {}}
      onClick={onClick}
      className={clsx(
        'glass-card bg-gradient-to-br border p-4 rounded-2xl',
        colors[color],
        onClick && 'cursor-pointer',
        className
      )}
    >
      <div className="flex items-start justify-between mb-2">
        <p className="text-xs font-medium text-carbon-500 uppercase tracking-wider">{label}</p>
        {Icon && <Icon className={clsx('w-4 h-4', iconColors[color])} />}
      </div>
      <div className="flex items-end gap-1.5">
        <span className="text-2xl font-display text-carbon-900">{value ?? '—'}</span>
        {unit && <span className="text-xs text-carbon-400 mb-1 font-mono">{unit}</span>}
      </div>
      {trend !== undefined && (
        <p className={clsx('text-xs mt-1 font-medium', trend >= 0 ? 'text-earth-600' : 'text-red-500')}>
          {trend >= 0 ? '↑' : '↓'} {Math.abs(trend).toFixed(1)}%
        </p>
      )}
    </motion.div>
  )
}
