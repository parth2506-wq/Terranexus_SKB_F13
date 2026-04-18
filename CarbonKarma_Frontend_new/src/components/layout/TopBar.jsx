import React from 'react'
import { useTranslation } from 'react-i18next'
import { useApp } from '../../context/AppContext'
import StatusBadge from '../ui/StatusBadge'
import { RefreshCw, Settings } from 'lucide-react'
import clsx from 'clsx'

export default function TopBar() {
  const { t } = useTranslation()
  const { activeTab, dataSource, isAnalyzing, location } = useApp()

  const tabLabels = {
    dashboard: t('nav.dashboard'), satellite: t('nav.satellite'),
    fusion: t('nav.fusion'), awd: t('nav.awd'), methane: t('nav.methane'),
    verification: t('nav.verification'), credits: t('nav.credits'),
    analytics: t('nav.analytics'), ai: t('nav.ai'), advanced: 'Advanced Intelligence', report: t('nav.report')
  }

  return (
    <header className="h-14 bg-white/80 backdrop-blur-md border-b border-carbon-200/60 flex items-center px-5 gap-4 shrink-0 z-10">
      {/* Title */}
      <div className="flex-1">
        <h1 className="font-display text-lg text-carbon-900 leading-none">
          {tabLabels[activeTab] || t('app.title')}
        </h1>
        {location.lat && (
          <p className="text-xs text-carbon-400 font-mono mt-0.5">
            {location.lat.toFixed(4)}°N, {location.lon.toFixed(4)}°E
          </p>
        )}
      </div>

      {/* Status */}
      <div className="flex items-center gap-3">
        {isAnalyzing && (
          <div className="flex items-center gap-2 text-xs text-carbon-500">
            <RefreshCw className="w-3.5 h-3.5 animate-spin text-earth-600" />
            <span>Analyzing...</span>
          </div>
        )}
        {dataSource && <StatusBadge type={dataSource} />}
        <div className="w-px h-5 bg-carbon-200" />
        <div className="text-xs text-carbon-400 font-mono">
          {new Date().toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}
        </div>
      </div>
    </header>
  )
}
