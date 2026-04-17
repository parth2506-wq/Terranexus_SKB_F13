import React from 'react'
import { motion } from 'framer-motion'
import { useTranslation } from 'react-i18next'
import { useApp } from '../../context/AppContext'
import TimeSeriesChart from '../charts/TimeSeriesChart'
import MetricCard from '../ui/MetricCard'
import StatusBadge from '../ui/StatusBadge'
import { Satellite, Activity, Thermometer, CloudRain } from 'lucide-react'

export default function SatellitePanel() {
  const { t } = useTranslation()
  const { panelData } = useApp()
  const data = panelData.satellite
  if (!data) return (
    <div className="flex items-center justify-center h-48 text-carbon-400 text-sm">No satellite data available. Run analysis first.</div>
  )

  const s1 = data.sentinel1 || []
  const s2 = data.sentinel2 || []
  const lst = data.lst || []
  const wx = data.weather || []

  const latestS1 = s1[s1.length - 1] || {}
  const latestS2 = s2[s2.length - 1] || {}
  const latestLst = lst[lst.length - 1] || {}
  const latestWx = wx[wx.length - 1] || {}

  const tsData = s1.map((r, i) => ({
    timestamp: r.timestamp,
    water_prob: +(r.water_prob_mean * 100).toFixed(1),
    ndvi: +(s2[i]?.ndvi_mean || 0).toFixed(4),
    temperature: +(lst[i]?.lst_mean_celsius || 0).toFixed(1),
    rainfall: +(wx[i]?.rainfall_mm || 0).toFixed(1),
    vv: +(r.vv_mean || 0).toFixed(4),
    vh: +(r.vh_mean || 0).toFixed(4),
  }))

  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="space-y-5">
      <h2 className="section-title">{t('satellite.title')}</h2>

      {/* Top metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <MetricCard label={t('satellite.waterProbability')} value={(latestS1.water_prob_mean * 100)?.toFixed(1)} unit="%" icon={Satellite} color="sky" />
        <MetricCard label={t('satellite.ndviValue')} value={latestS2.ndvi_mean?.toFixed(4)} icon={Activity} color="earth" />
        <MetricCard label={t('satellite.tempC')} value={latestLst.lst_mean_celsius?.toFixed(1)} unit="°C" icon={Thermometer} color="red" />
        <MetricCard label={t('satellite.rainfall')} value={latestWx.rainfall_mm?.toFixed(1)} unit="mm" icon={CloudRain} color="sky" />
      </div>

      {/* Sentinel-1 SAR */}
      <div className="glass-card p-4">
        <div className="flex items-center justify-between mb-4">
          <p className="text-sm font-medium text-carbon-700">{t('satellite.sar')}</p>
          <StatusBadge type={latestS1.is_flooded ? 'active_awd' : 'uncertain'} label={latestS1.is_flooded ? 'Flooded' : 'Dry'} />
        </div>
        <TimeSeriesChart data={tsData} height={180} series={[
          { key: 'water_prob', name: 'Water Prob %', color: '#36aaf5' },
          { key: 'vv', name: 'VV (×10⁻²)', color: '#0071c4', dashed: true },
        ]} />
        <div className="grid grid-cols-3 md:grid-cols-6 gap-1.5 mt-3">
          {s1.slice(-6).map((r, i) => (
            <div key={i} className="text-center bg-sky-50 rounded-xl py-2 px-1">
              <p className="text-[9px] text-carbon-400 font-mono">{r.timestamp?.slice(5)}</p>
              <p className="text-xs font-medium text-sky-700">{(r.water_prob_mean * 100).toFixed(0)}%</p>
              <p className="text-[9px] text-carbon-400 truncate">{r.phenology_stage}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Sentinel-2 NDVI */}
      <div className="glass-card p-4">
        <p className="text-sm font-medium text-carbon-700 mb-4">{t('satellite.ndvi')} — Vegetation Index</p>
        <TimeSeriesChart data={tsData} height={160} series={[{ key: 'ndvi', name: 'NDVI', color: '#5c9934' }]} />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mt-3">
          {s2.slice(-4).map((r, i) => (
            <div key={i} className="flex flex-col bg-earth-50 rounded-xl px-3 py-2">
              <span className="text-[9px] font-mono text-carbon-400">{r.timestamp?.slice(5)}</span>
              <span className="text-sm font-medium text-earth-700">{r.ndvi_mean?.toFixed(4)}</span>
              <span className="text-[9px] text-carbon-400">±{r.ndvi_std?.toFixed(3)} | cloud {((r.cloud_fraction || 0) * 100).toFixed(0)}%</span>
            </div>
          ))}
        </div>
      </div>

      {/* Temperature + Weather side by side */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="glass-card p-4">
          <p className="text-sm font-medium text-carbon-700 mb-3">{t('satellite.temperature')} — LST (°C)</p>
          <TimeSeriesChart data={tsData} height={160} series={[{ key: 'temperature', name: 'LST °C', color: '#ef4444' }]} />
        </div>
        <div className="glass-card p-4">
          <p className="text-sm font-medium text-carbon-700 mb-3">{t('satellite.weather')} — Rainfall (mm)</p>
          <TimeSeriesChart data={tsData} height={160} series={[{ key: 'rainfall', name: 'Rainfall mm', color: '#7cc8fb' }]} />
        </div>
      </div>

      {/* Phenology timeline */}
      <div className="glass-card p-4">
        <p className="text-sm font-medium text-carbon-700 mb-3">Phenology Stages</p>
        <div className="flex gap-1.5 overflow-x-auto pb-1">
          {s1.map((r, i) => {
            const stageColor = {
              transplanting: 'bg-sky-200 text-sky-800',
              tillering:     'bg-earth-200 text-earth-800',
              heading:       'bg-earth-400 text-white',
              ripening:      'bg-amber-300 text-amber-900',
              harvest:       'bg-amber-500 text-white',
            }[r.phenology_stage] || 'bg-carbon-200 text-carbon-700'
            return (
              <div key={i} className={`shrink-0 px-2 py-1.5 rounded-lg text-center min-w-[56px] ${stageColor}`}>
                <p className="text-[9px] font-mono">{r.timestamp?.slice(5)}</p>
                <p className="text-[9px] font-medium capitalize mt-0.5">{r.phenology_stage?.replace('_', ' ')}</p>
              </div>
            )
          })}
        </div>
      </div>
    </motion.div>
  )
}
