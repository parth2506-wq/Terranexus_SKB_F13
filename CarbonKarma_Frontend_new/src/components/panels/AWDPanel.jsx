import React from 'react'
import { motion } from 'framer-motion'
import { useTranslation } from 'react-i18next'
import { useApp } from '../../context/AppContext'
import TimeSeriesChart from '../charts/TimeSeriesChart'
import StatusBadge from '../ui/StatusBadge'
import GaugeChart from '../charts/GaugeChart'
import { Droplets, Waves, CloudRain } from 'lucide-react'

export default function AWDPanel() {
  const { t } = useTranslation()
  const { panelData } = useApp()
  const data = panelData.awd
  if (!data) return (
    <div className="flex items-center justify-center h-48 text-carbon-400 text-sm">No AWD data available.</div>
  )

  const seq = data.flood_dry_sequence || []
  const perStep = data.per_step_status || []
  const tsData = seq.map(r => ({
    timestamp: r.timestamp,
    water_level: +(r.water_level * 100).toFixed(1),
    state_value: r.state === 'flooded' ? 100 : r.state === 'dry' ? 0 : 50
  }))

  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="space-y-5">
      <div className="flex items-center gap-2">
        <Droplets className="w-5 h-5 text-sky-600" />
        <h2 className="section-title mb-0">{t('awd.title')}</h2>
      </div>

      {/* Status hero */}
      <div className="glass-card p-5 bg-gradient-to-br from-sky-50 to-earth-50/40 border border-sky-200/60">
        <div className="flex items-center gap-6">
          <GaugeChart value={(data.confidence || 0) * 100} max={100} color="auto" size={140} label={t('awd.confidence')} sublabel="%" />
          <div className="flex-1 space-y-3">
            <div>
              <p className="text-xs text-carbon-500 uppercase tracking-wider mb-1.5">{t('awd.status')}</p>
              <StatusBadge type={data.awd_status} />
            </div>
            <div className="grid grid-cols-3 gap-2">
              {[
                [t('awd.cycles'), data.cycles || 0, 'text-carbon-900'],
                [t('awd.irrigationEvents'), data.irrigation_events?.length || 0, 'text-earth-700'],
                [t('awd.rainEvents'), data.rain_events?.length || 0, 'text-sky-700'],
              ].map(([label, val, cls]) => (
                <div key={label} className="text-center bg-white/70 rounded-xl p-2">
                  <p className="text-[10px] text-carbon-400">{label}</p>
                  <p className={`text-2xl font-display ${cls}`}>{val}</p>
                </div>
              ))}
            </div>
            <div className="text-xs text-carbon-500">
              <span>{t('awd.lstmSignal')}: </span>
              <div className="inline-flex items-center gap-2 ml-1">
                <div className="w-24 h-1.5 bg-carbon-100 rounded-full overflow-hidden">
                  <div className="h-full bg-sky-500 rounded-full transition-all" style={{ width: `${(data.lstm_signal || 0) * 100}%` }} />
                </div>
                <span className="font-mono">{((data.lstm_signal || 0) * 100).toFixed(1)}%</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Cycle timeline chart */}
      <div className="glass-card p-4">
        <p className="text-sm font-medium text-carbon-700 mb-4">Flood–Dry Cycle Timeline</p>
        <TimeSeriesChart data={tsData} height={180} series={[
          { key: 'water_level', name: 'Water Level %', color: '#36aaf5' },
          { key: 'state_value', name: 'State (100=flood)', color: '#5c9934', dashed: true },
        ]} />
        {/* Colour-coded blocks */}
        <div className="flex gap-0.5 mt-3 overflow-x-auto rounded-xl overflow-hidden">
          {perStep.map((s, i) => (
            <div key={i} title={`${s.timestamp} — ${s.state}`}
              className={`flex-1 min-w-[24px] py-3 transition-all cursor-default group relative ${
                s.state === 'flooded' ? 'bg-sky-400 hover:bg-sky-500' :
                s.state === 'dry'     ? 'bg-amber-300 hover:bg-amber-400' :
                                        'bg-carbon-200 hover:bg-carbon-300'}`}>
              <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 bg-carbon-900 text-white text-[9px] px-1.5 py-0.5 rounded whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity z-10 pointer-events-none">
                {s.timestamp?.slice(5)} · {s.state}
              </div>
            </div>
          ))}
        </div>
        <div className="flex gap-4 mt-2 text-xs text-carbon-500">
          <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-sky-400 inline-block" /> Flooded</span>
          <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-amber-300 inline-block" /> Dry</span>
          <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-carbon-200 inline-block" /> Transition</span>
        </div>
      </div>

      {/* Events grids */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="glass-card p-4">
          <p className="text-sm font-medium text-carbon-700 mb-3 flex items-center gap-2">
            <Waves className="w-4 h-4 text-earth-600" /> {t('awd.irrigationEvents')}
          </p>
          {!(data.irrigation_events?.length)
            ? <p className="text-xs text-carbon-400 text-center py-4">No irrigation events detected</p>
            : data.irrigation_events.map((ev, i) => (
              <div key={i} className="flex items-center justify-between text-xs border-b border-carbon-100 py-2 last:border-0">
                <span className="font-mono text-carbon-500">{ev.timestamp}</span>
                <span className="text-earth-700">{(ev.water_level * 100).toFixed(1)}%</span>
                <span className="text-sky-600">{ev.rainfall_mm?.toFixed(1)} mm</span>
              </div>
            ))
          }
        </div>
        <div className="glass-card p-4">
          <p className="text-sm font-medium text-carbon-700 mb-3 flex items-center gap-2">
            <CloudRain className="w-4 h-4 text-sky-600" /> {t('awd.rainEvents')}
          </p>
          {!(data.rain_events?.length)
            ? <p className="text-xs text-carbon-400 text-center py-4">No rain-driven events detected</p>
            : data.rain_events.map((ev, i) => (
              <div key={i} className="flex items-center justify-between text-xs border-b border-carbon-100 py-2 last:border-0">
                <span className="font-mono text-carbon-500">{ev.timestamp}</span>
                <span className="text-sky-700">{(ev.water_level * 100).toFixed(1)}%</span>
                <span className="text-sky-600 font-medium">{ev.rainfall_mm?.toFixed(1)} mm</span>
              </div>
            ))
          }
        </div>
      </div>

      {/* Detection params */}
      <div className="glass-card p-4">
        <p className="text-xs font-medium text-carbon-500 uppercase tracking-wider mb-3">Detection Parameters</p>
        <div className="grid grid-cols-3 gap-3 text-center">
          {Object.entries(data.detection_params || { flood_threshold: 0.55, dry_threshold: 0.25, min_cycle_days: 5 })
            .map(([k, v]) => (
              <div key={k} className="bg-carbon-50 rounded-xl p-3">
                <p className="text-[10px] text-carbon-400 capitalize mb-1">{k.replace(/_/g, ' ')}</p>
                <p className="text-sm font-mono font-medium text-carbon-800">{v}</p>
              </div>
            ))}
        </div>
      </div>
    </motion.div>
  )
}
