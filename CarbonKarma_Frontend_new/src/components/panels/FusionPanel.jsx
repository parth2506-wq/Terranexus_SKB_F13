import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useTranslation } from 'react-i18next'
import { useApp } from '../../context/AppContext'
import TimeSeriesChart from '../charts/TimeSeriesChart'
import StatusBadge from '../ui/StatusBadge'
import MetricCard from '../ui/MetricCard'
import { Layers, X, Droplets, Activity, Thermometer, Wind, CloudRain, Map } from 'lucide-react'

function PixelCard({ data, onClose }) {
  const { t } = useTranslation()
  if (!data) return null
  const fields = [
    { label: t('fusion.waterLevel'), value: (data.water_level * 100)?.toFixed(1), unit: '%', color: 'sky' },
    { label: t('fusion.ndvi'), value: data.ndvi?.toFixed(4), color: 'earth' },
    { label: t('fusion.temperature'), value: data.temperature?.toFixed(1), unit: '°C', color: 'red' },
    { label: t('fusion.rainfall'), value: data.rainfall?.toFixed(1), unit: 'mm', color: 'sky' },
    { label: t('fusion.soilMoisture'), value: (data.soil_moisture * 100)?.toFixed(1), unit: '%', color: 'amber' },
    { label: 'CNN Water Score', value: (data.cnn_water_score * 100)?.toFixed(1), unit: '%', color: 'sky' },
  ]
  return (
    <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0 }}
      className="glass-card p-4 border-l-4 border-earth-500">
      <div className="flex items-start justify-between mb-3">
        <div>
          <p className="text-sm font-medium text-carbon-800">{t('fusion.pixelInsight')}</p>
          <p className="text-xs font-mono text-carbon-400">{data.timestamp}</p>
        </div>
        <div className="flex items-center gap-2">
          <StatusBadge type={data.flood_type} label={data.flood_type?.replace('_', ' ')} />
          <button onClick={onClose} className="text-carbon-400 hover:text-carbon-700"><X className="w-4 h-4" /></button>
        </div>
      </div>
      <div className="grid grid-cols-3 gap-2">
        {fields.map(({ label, value, unit, color }) => (
          <div key={label} className={`bg-${color}-50 rounded-xl p-2.5 text-center`}>
            <p className="text-[9px] text-carbon-500 uppercase tracking-wider mb-0.5">{label}</p>
            <p className={`text-sm font-display text-${color}-700`}>{value ?? '—'}<span className="text-xs ml-0.5 font-mono">{unit}</span></p>
          </div>
        ))}
      </div>
      <div className="mt-3 pt-3 border-t border-carbon-100 flex items-center justify-between text-xs">
        <span className="text-carbon-500">AWD: <strong className="text-carbon-800">{data.awd_status || '—'}</strong></span>
        <span className="text-carbon-500">Stage: <strong className="text-carbon-800">{data.phenology_stage || '—'}</strong></span>
        <span className="text-carbon-500">Cloud: <strong className="text-carbon-800">{((data.cloud_fraction || 0) * 100).toFixed(0)}%</strong></span>
      </div>
    </motion.div>
  )
}

export default function FusionPanel() {
  const { t } = useTranslation()
  const { panelData } = useApp()
  const [selectedStep, setSelectedStep] = useState(null)
  const data = panelData.fusion
  if (!data) return null

  const fd = data.fusion_data || []
  const latest = fd[fd.length - 1] || {}

  const tsData = fd.map(r => ({
    timestamp: r.timestamp,
    water_level: r.water_level,
    ndvi: r.ndvi,
    soil_moisture: r.soil_moisture,
    temperature: r.temperature,
    rainfall: r.rainfall,
  }))

  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="space-y-5">
      <div className="flex items-center gap-2">
        <Layers className="w-5 h-5 text-earth-600" />
        <h2 className="section-title mb-0">{t('fusion.title')}</h2>
      </div>

      {/* Latest step summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <MetricCard label={t('fusion.waterLevel')} value={(latest.water_level * 100)?.toFixed(1)} unit="%" icon={Droplets} color="sky" />
        <MetricCard label={t('fusion.ndvi')} value={latest.ndvi?.toFixed(4)} icon={Activity} color="earth" />
        <MetricCard label={t('fusion.temperature')} value={latest.temperature?.toFixed(1)} unit="°C" icon={Thermometer} color="red" />
        <MetricCard label={t('fusion.soilMoisture')} value={(latest.soil_moisture * 100)?.toFixed(1)} unit="%" icon={Wind} color="amber" />
      </div>

      {/* Pixel picker hint */}
      <div className="glass-card p-3 flex items-center gap-2 text-xs text-carbon-500 border-dashed">
        <Map className="w-4 h-4 text-earth-500 shrink-0" />
        <span>Click any observation step below to inspect pixel-level data. Use the map panel for spatial pixel inspection.</span>
      </div>

      {/* Step selector timeline */}
      <div className="glass-card p-4">
        <p className="text-xs font-medium text-carbon-500 uppercase tracking-wider mb-3">Observation Steps</p>
        <div className="flex gap-2 overflow-x-auto pb-2">
          {fd.map((r, i) => (
            <button key={i} onClick={() => setSelectedStep(selectedStep === i ? null : i)}
              className={`shrink-0 text-center rounded-xl px-3 py-2 transition-all border ${selectedStep === i ? 'bg-earth-600 text-white border-earth-600' : 'bg-white border-carbon-200 hover:border-earth-300 text-carbon-700'}`}>
              <p className="text-[10px] font-mono">{r.timestamp?.slice(5)}</p>
              <p className="text-xs font-medium">{(r.water_level * 100).toFixed(0)}%</p>
              <div className={`w-full h-1 rounded-full mt-1 ${r.flood_type === 'irrigated' ? 'bg-sky-400' : r.flood_type === 'rain_fed' ? 'bg-earth-400' : r.flood_type === 'surface_water' ? 'bg-sky-200' : 'bg-carbon-200'}`} />
            </button>
          ))}
        </div>
        <AnimatePresence>
          {selectedStep !== null && (
            <motion.div className="mt-3" initial={{ height: 0 }} animate={{ height: 'auto' }} exit={{ height: 0 }}>
              <PixelCard data={fd[selectedStep]} onClose={() => setSelectedStep(null)} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Multi-series chart */}
      <div className="glass-card p-4">
        <p className="text-sm font-medium text-carbon-700 mb-4">All Layers — Time Series</p>
        <TimeSeriesChart data={tsData} height={220} series={[
          { key: 'water_level', name: 'Water', color: '#36aaf5' },
          { key: 'ndvi', name: 'NDVI', color: '#5c9934' },
          { key: 'soil_moisture', name: 'Soil Moisture', color: '#f59e0b' },
        ]} />
      </div>

      <div className="glass-card p-4">
        <p className="text-sm font-medium text-carbon-700 mb-4">Temperature & Rainfall</p>
        <TimeSeriesChart data={tsData} height={180} series={[
          { key: 'temperature', name: 'Temp °C', color: '#ef4444' },
          { key: 'rainfall', name: 'Rainfall mm', color: '#7cc8fb' },
        ]} />
      </div>
    </motion.div>
  )
}
