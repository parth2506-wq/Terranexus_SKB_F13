import React, { useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import clsx from 'clsx'

function normalizeZones(data) {
  if (!data) return []
  if (Array.isArray(data)) return data
  if (data.zones) return data.zones
  if (data.field_segmentation?.zones) return data.field_segmentation.zones
  return []
}

function getZoneStyle(zone) {
  const water = Math.max(0, Math.min(1, zone.water_level ?? zone.water ?? 0))
  const methane = Math.max(0, Math.min(1, (zone.methane_level ?? zone.methane ?? 0) / 500))
  return {
    background: `linear-gradient(135deg, rgba(${Math.round(40 + water * 180)}, ${Math.round(140 - water * 90)}, ${Math.round(255 - water * 110)}, 0.95), rgba(${Math.round(240 - methane * 90)}, ${Math.round(220 - methane * 80)}, ${Math.round(100 + methane * 40)}, 0.95))`
  }
}

export default function DigitalTwin({ analytics, fusionSeries }) {
  const zones = normalizeZones(analytics)
  const [timeIndex, setTimeIndex] = useState(1)
  const stages = ['Past', 'Present', 'Future']

  const displayZones = useMemo(() => {
    if (!zones.length) {
      return Array.from({ length: 16 }, (_, i) => ({ zone_id: i + 1, water_level: 0.45 + (i % 4) * 0.05, methane_level: 220 + (i % 4) * 16, ndvi: 0.35 + (i % 4) * 0.06 }))
    }

    const modifier = timeIndex === 0 ? -0.08 : timeIndex === 2 ? 0.1 : 0
    return zones.slice(0, 16).map(zone => ({
      ...zone,
      water_level: Math.max(0, Math.min(1, (zone.water_level ?? 0.45) + modifier)),
      methane_level: Math.max(0, (zone.methane_level ?? 260) - modifier * 80),
      ndvi: Math.max(0, Math.min(1, (zone.ndvi ?? 0.4) + modifier * 0.08))
    }))
  }, [zones, timeIndex])

  return (
    <div className="glass-card p-5 space-y-5">
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-wider text-carbon-500">Digital Twin</p>
          <h3 className="text-2xl font-display text-carbon-900">Simulated farm zones</h3>
        </div>
        <div className="text-right">
          <p className="text-xs uppercase tracking-wider text-carbon-500">Timeline</p>
          <p className="text-lg font-display text-sky-700">{stages[timeIndex]}</p>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-2">
        {displayZones.map(zone => (
          <motion.div key={zone.zone_id}
            layout
            className="aspect-square rounded-3xl border border-carbon-100 shadow-sm"
            style={getZoneStyle(zone)}
            title={`Zone ${zone.zone_id}: Water ${(zone.water_level * 100).toFixed(0)}%, CH₄ ${Math.round(zone.methane_level)} mg/m²/d`}
          >
            <div className="flex h-full flex-col justify-between p-3 text-[10px] font-mono text-white drop-shadow-sm">
              <span>#{zone.zone_id}</span>
              <span>{zone.ndvi?.toFixed(2)}</span>
            </div>
          </motion.div>
        ))}
      </div>

      <div className="glass-card p-4 bg-white/90 border border-carbon-200">
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-wider text-carbon-500">Zone dynamics</p>
            <p className="text-sm text-carbon-700">Water, methane and vegetation trends for each farm quadrant.</p>
          </div>
          <div className="text-right">
            <p className="text-xs text-carbon-400">Zones</p>
            <p className="text-lg font-display text-earth-700">{displayZones.length}</p>
          </div>
        </div>
        <div className="mt-4">
          <input
            type="range"
            min="0"
            max={stages.length - 1}
            value={timeIndex}
            onChange={e => setTimeIndex(Number(e.target.value))}
            className="w-full accent-sky-600"
          />
          <div className="flex items-center justify-between text-[11px] text-carbon-400 mt-2">
            {stages.map(stage => <span key={stage}>{stage}</span>)}
          </div>
        </div>
      </div>
    </div>
  )
}
