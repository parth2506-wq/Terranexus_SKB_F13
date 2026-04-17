import React from 'react'
import clsx from 'clsx'

const configs = {
  live:        { bg: 'bg-earth-100', text: 'text-earth-700', dot: 'bg-earth-500', label: '● Live' },
  cached:      { bg: 'bg-sky-100',   text: 'text-sky-700',   dot: 'bg-sky-500',   label: '◉ Cached' },
  fallback:    { bg: 'bg-amber-100', text: 'text-amber-700', dot: 'bg-amber-500', label: '◎ Demo' },
  gold:        { bg: 'bg-amber-100', text: 'text-amber-800', dot: 'bg-amber-500', label: '★ Gold' },
  silver:      { bg: 'bg-carbon-100',text: 'text-carbon-700',dot: 'bg-carbon-400',label: '◆ Silver' },
  bronze:      { bg: 'bg-orange-100',text: 'text-orange-700',dot: 'bg-orange-500',label: '◇ Bronze' },
  failed:      { bg: 'bg-red-100',   text: 'text-red-700',   dot: 'bg-red-500',   label: '✕ Failed' },
  active_awd:  { bg: 'bg-earth-100', text: 'text-earth-700', dot: 'bg-earth-500', label: '✓ Active AWD' },
  conventional:{ bg: 'bg-sky-100',   text: 'text-sky-700',   dot: 'bg-sky-400',   label: '~ Conventional' },
  uncertain:   { bg: 'bg-amber-100', text: 'text-amber-700', dot: 'bg-amber-400', label: '? Uncertain' },
  high:        { bg: 'bg-red-100',   text: 'text-red-700',   dot: 'bg-red-500',   label: 'High' },
  medium:      { bg: 'bg-amber-100', text: 'text-amber-700', dot: 'bg-amber-400', label: 'Medium' },
  low:         { bg: 'bg-earth-100', text: 'text-earth-700', dot: 'bg-earth-500', label: 'Low' },
}

export default function StatusBadge({ type, label, className = '' }) {
  const cfg = configs[type?.toLowerCase?.()] || configs.fallback
  return (
    <span className={clsx('inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium font-mono', cfg.bg, cfg.text, className)}>
      <span className={clsx('w-1.5 h-1.5 rounded-full', cfg.dot)} />
      {label || cfg.label}
    </span>
  )
}
