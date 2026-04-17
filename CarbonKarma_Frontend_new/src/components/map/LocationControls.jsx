import React, { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { motion } from 'framer-motion'
import { MapPin, Crosshair, Search, RotateCcw } from 'lucide-react'
import { useApp } from '../../context/AppContext'
import clsx from 'clsx'

export default function LocationControls({ onAnalyze }) {
  const { t } = useTranslation()
  const { location, setLocation, isAnalyzing, resetAll } = useApp()
  const [mode, setMode] = useState('click') // 'click' | 'manual'
  const [manualLat, setManualLat] = useState('')
  const [manualLon, setManualLon] = useState('')
  const [geoError, setGeoError] = useState('')
  const [detecting, setDetecting] = useState(false)

  const handleGeolocate = () => {
    if (!navigator.geolocation) { setGeoError('Geolocation not supported'); return }
    setDetecting(true); setGeoError('')
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => {
        setLocation({ lat: coords.latitude, lon: coords.longitude, geojson: null })
        setManualLat(coords.latitude.toFixed(5))
        setManualLon(coords.longitude.toFixed(5))
        setDetecting(false)
      },
      (err) => { setGeoError('Location access denied'); setDetecting(false) }
    )
  }

  const handleManualSubmit = () => {
    const lat = parseFloat(manualLat)
    const lon = parseFloat(manualLon)
    if (isNaN(lat) || isNaN(lon) || lat < -90 || lat > 90 || lon < -180 || lon > 180) {
      setGeoError('Enter valid lat (±90) and lon (±180)')
      return
    }
    setLocation({ lat, lon, geojson: null })
    setGeoError('')
  }

  const hasLocation = location.lat !== null

  return (
    <motion.div
      initial={{ y: 20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      className="glass-card p-4 space-y-3"
    >
      <div className="flex items-center gap-2 mb-1">
        <MapPin className="w-4 h-4 text-earth-600" />
        <span className="text-sm font-medium text-carbon-700">Farm Location</span>
        {hasLocation && (
          <button onClick={resetAll} className="ml-auto text-xs text-carbon-400 hover:text-red-500 flex items-center gap-1">
            <RotateCcw className="w-3 h-3" /> Reset
          </button>
        )}
      </div>

      {/* Mode tabs */}
      <div className="flex gap-1 bg-carbon-100 rounded-lg p-1">
        {['click', 'manual'].map(m => (
          <button key={m} onClick={() => setMode(m)}
            className={clsx('flex-1 py-1 rounded-md text-xs font-medium transition-all',
              mode === m ? 'bg-white text-carbon-800 shadow-sm' : 'text-carbon-500')}>
            {m === 'click' ? 'Map Click / Draw' : 'Enter Coords'}
          </button>
        ))}
      </div>

      {mode === 'manual' && (
        <div className="space-y-2">
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-xs text-carbon-500 mb-1 block">{t('map.lat')}</label>
              <input
                type="number" placeholder="13.0827" value={manualLat}
                onChange={e => setManualLat(e.target.value)} className="input-field text-sm"
              />
            </div>
            <div>
              <label className="text-xs text-carbon-500 mb-1 block">{t('map.lon')}</label>
              <input
                type="number" placeholder="80.2707" value={manualLon}
                onChange={e => setManualLon(e.target.value)} className="input-field text-sm"
              />
            </div>
          </div>
          <button onClick={handleManualSubmit} className="btn-secondary w-full text-sm py-2 flex items-center justify-center gap-2">
            <Search className="w-3.5 h-3.5" /> Set Location
          </button>
        </div>
      )}

      {/* Auto-detect */}
      <button onClick={handleGeolocate} disabled={detecting}
        className="btn-ghost w-full text-xs flex items-center justify-center gap-1.5 py-2">
        <Crosshair className={`w-3.5 h-3.5 ${detecting ? 'animate-spin' : ''}`} />
        {detecting ? t('map.searching') : t('map.detectLocation')}
      </button>

      {geoError && <p className="text-xs text-red-500 text-center">{geoError}</p>}

      {hasLocation && (
        <div className="text-xs text-carbon-500 text-center font-mono bg-earth-50 rounded-lg py-1.5">
          {location.lat.toFixed(5)}°N, {location.lon.toFixed(5)}°E
        </div>
      )}

      {/* Analyze button */}
      <motion.button
        whileTap={{ scale: 0.97 }}
        onClick={() => hasLocation && onAnalyze()}
        disabled={!hasLocation || isAnalyzing}
        className={clsx(
          'w-full py-2.5 rounded-xl font-medium text-sm transition-all duration-200 flex items-center justify-center gap-2',
          hasLocation && !isAnalyzing
            ? 'btn-primary'
            : 'bg-carbon-100 text-carbon-400 cursor-not-allowed'
        )}
      >
        {isAnalyzing ? (
          <><div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />Analyzing...</>
        ) : (
          <><Search className="w-4 h-4" />{t('map.analyze')}</>
        )}
      </motion.button>
    </motion.div>
  )
}
