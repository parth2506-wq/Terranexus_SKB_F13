import React, { useCallback, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useApp } from '../context/AppContext'
import FarmMap from '../components/map/FarmMap'
import LocationControls from '../components/map/LocationControls'
import SatellitePanel from '../components/panels/SatellitePanel'
import FusionPanel from '../components/panels/FusionPanel'
import AWDPanel from '../components/panels/AWDPanel'
import MethanePanel from '../components/panels/MethanePanel'
import VerificationPanel from '../components/panels/VerificationPanel'
import CreditsPanel from '../components/panels/CreditsPanel'
import AnalyticsPanel from '../components/panels/AnalyticsPanel'
import AIPanel from '../components/panels/AIPanel'
import ReportPanel from '../components/panels/ReportPanel'
import LoadingSpinner from '../components/ui/LoadingSpinner'
import ErrorBoundary from '../components/ui/ErrorBoundary'
import {
  fetchSatelliteData, fetchFusionData, fetchAWDStatus, fetchMethane,
  fetchVerification, fetchCredits, fetchAnalytics
} from '../services/api'

const panelMap = {
  satellite:    SatellitePanel,
  fusion:       FusionPanel,
  awd:          AWDPanel,
  methane:      MethanePanel,
  verification: VerificationPanel,
  credits:      CreditsPanel,
  analytics:    AnalyticsPanel,
  ai:           AIPanel,
  report:       ReportPanel,
}

const STEPS = ['Sentinel-1','Sentinel-2','LST','Weather','Fusion','AWD','Methane','Verification','Credits','Analytics']

export default function Dashboard() {
  const {
    location, setLocation, activeTab, setActiveTab,
    isAnalyzing, setIsAnalyzing, hasRun, setHasRun,
    panelData, setPanelData, farmId,
    setNSteps, setStepDays, setDataSource
  } = useApp()

  const [localSteps, setLocalSteps]       = useState(12)
  const [localStepDays, setLocalStepDays] = useState(7)

  const handleMapClick  = useCallback(({ lat, lon }) =>
    setLocation(prev => ({ ...prev, lat, lon })), [setLocation])

  const handleFarmDrawn = useCallback(({ lat, lon, geojson }) =>
    setLocation({ lat, lon, geojson }), [setLocation])

  const runAnalysis = useCallback(async () => {
    if (!location.lat || isAnalyzing) return
    setIsAnalyzing(true)
    setNSteps(localSteps)
    setStepDays(localStepDays)

    const { lat, lon, geojson } = location
    const [satR, fusR, awdR, metR, verR, credR, anaR] = await Promise.allSettled([
      fetchSatelliteData(lat, lon, localSteps, localStepDays, geojson),
      fetchFusionData(lat, lon, localSteps, localStepDays, true, geojson),
      fetchAWDStatus(lat, lon, localSteps + 2, localStepDays, geojson),
      fetchMethane(lat, lon, localSteps, localStepDays, geojson),
      fetchVerification(lat, lon, farmId, localSteps, localStepDays, geojson),
      fetchCredits(lat, lon, farmId, 4.5, localSteps, localStepDays, geojson),
      fetchAnalytics(lat, lon, farmId, localSteps, localStepDays, 'south_asia', geojson),
    ])

    const get = r => r.status === 'fulfilled' ? r.value : null
    const sources = [satR,fusR,awdR,metR,verR,credR,anaR]
      .map(r => r.status === 'fulfilled' ? r.value?.source : null).filter(Boolean)
    setDataSource(sources.includes('live') ? 'live' : sources.includes('cached') ? 'cached' : 'fallback')

    setPanelData({
      satellite:    get(satR)?.data  ?? null,
      fusion:       get(fusR)?.data  ?? null,
      awd:          get(awdR)?.data  ?? null,
      methane:      get(metR)?.data  ?? null,
      verification: get(verR)?.data  ?? null,
      credits:      get(credR)?.data ?? null,
      analytics:    get(anaR)?.data  ?? null,
      llm:          null,
    })

    setHasRun(true)
    setIsAnalyzing(false)
    setActiveTab('satellite')
  }, [location, isAnalyzing, farmId, localSteps, localStepDays])

  const ActivePanel   = panelMap[activeTab]
  const heatmaps      = panelData.fusion?.heatmaps ?? null
  const credits       = panelData.credits
  const verification  = panelData.verification?.verification
  const farmScore     = panelData.analytics?.farm_score
  const awdData       = panelData.awd

  return (
    <div className="flex h-full overflow-hidden">
      {/* ── Left: controls + map ─────────────────────────────────────── */}
      <div className="flex flex-col w-[400px] shrink-0 border-r border-carbon-200/60 bg-white/60 backdrop-blur-sm">
        <div className="p-4 space-y-3 overflow-y-auto flex-1">
          <LocationControls onAnalyze={runAnalysis} />

          {/* Settings (pre-analysis) */}
          {!hasRun && (
            <div className="glass-card p-3 space-y-2">
              <p className="text-xs font-medium text-carbon-500 uppercase tracking-wider">
                Analysis Settings
              </p>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-xs text-carbon-400 block mb-1">Steps</label>
                  <input type="number" min={5} max={50} value={localSteps}
                    onChange={e => setLocalSteps(parseInt(e.target.value) || 12)}
                    className="input-field text-sm" />
                </div>
                <div>
                  <label className="text-xs text-carbon-400 block mb-1">Step Days</label>
                  <input type="number" min={3} max={30} value={localStepDays}
                    onChange={e => setLocalStepDays(parseInt(e.target.value) || 7)}
                    className="input-field text-sm" />
                </div>
              </div>
            </div>
          )}

          {/* Quick summary (post-analysis) */}
          {hasRun && (
            <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} className="space-y-2">
              {credits && (
                <div className="glass-card p-3 flex justify-between items-center">
                  <span className="text-xs text-carbon-500">Credits Earned</span>
                  <span className="text-sm font-display text-earth-700">
                    {(credits.credits_earned ?? 0).toFixed(4)}
                    <span className="text-xs font-mono text-carbon-400 ml-1">tCO₂e</span>
                  </span>
                </div>
              )}
              {verification && (
                <div className="glass-card p-3 flex justify-between items-center">
                  <span className="text-xs text-carbon-500">Verification</span>
                  <span className={`text-sm font-display ${
                    verification.level === 'GOLD'   ? 'text-amber-600' :
                    verification.level === 'SILVER' ? 'text-carbon-600' :
                    verification.level === 'BRONZE' ? 'text-orange-600' : 'text-red-500'
                  }`}>{verification.level ?? '—'}</span>
                </div>
              )}
              {farmScore && (
                <div className="glass-card p-3 flex justify-between items-center">
                  <span className="text-xs text-carbon-500">Farm Score</span>
                  <span className="text-sm font-display text-carbon-800">
                    {(farmScore.overall_score ?? 0).toFixed(0)}/100
                    <span className="text-xs text-carbon-400 ml-1">Grade {farmScore.grade}</span>
                  </span>
                </div>
              )}
              {awdData && (
                <div className="glass-card p-3 flex justify-between items-center">
                  <span className="text-xs text-carbon-500">AWD Status</span>
                  <span className={`text-xs font-medium px-2 py-0.5 rounded-lg ${
                    awdData.awd_status === 'active_awd'   ? 'bg-earth-100 text-earth-700' :
                    awdData.awd_status === 'conventional' ? 'bg-sky-100 text-sky-700' :
                                                            'bg-amber-100 text-amber-700'
                  }`}>
                    {(awdData.awd_status ?? '').replace('_', ' ')}
                  </span>
                </div>
              )}
            </motion.div>
          )}
        </div>

        {/* Map */}
        <div className="h-[360px] p-4 pt-0 shrink-0">
          <FarmMap
            heatmaps={heatmaps}
            onMapClick={handleMapClick}
            onFarmDrawn={handleFarmDrawn}
            activePanel={activeTab}
          />
        </div>
      </div>

      {/* ── Right: panel area ────────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto bg-gradient-to-br from-earth-50/50 via-white/30 to-sky-50/30">
        {isAnalyzing ? (
          <div className="h-full flex flex-col items-center justify-center gap-6 p-8">
            <LoadingSpinner size="lg" />
            <div className="text-center">
              <p className="font-display text-xl text-carbon-800">Analyzing Field Data</p>
              <p className="text-sm text-carbon-500 mt-1">
                Running satellite intelligence + AI pipeline…
              </p>
            </div>
            <div className="flex flex-wrap justify-center gap-2 max-w-lg">
              {STEPS.map((step, i) => (
                <motion.span key={step}
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: i * 0.12, type: 'spring' }}
                  className="bg-white/80 border border-earth-200 px-3 py-1.5 rounded-lg text-xs text-carbon-600 font-medium shadow-sm"
                >
                  {step}
                </motion.span>
              ))}
            </div>
          </div>
        ) : !hasRun ? (
          <div className="h-full flex flex-col items-center justify-center px-8 py-12">
            <motion.div
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ type: 'spring', stiffness: 160 }}
              className="w-20 h-20 bg-gradient-to-br from-earth-400 to-earth-700 rounded-3xl flex items-center justify-center mx-auto mb-6 shadow-lg"
            >
              <span className="text-4xl">🌾</span>
            </motion.div>
            <h2 className="font-display text-2xl text-carbon-800 mb-2">CarbonKarma dMRV</h2>
            <p className="text-carbon-500 max-w-sm text-sm leading-relaxed mb-8 text-center">
              Draw your farm boundary on the map, click a location, or enter coordinates —
              then click <strong>Analyze Field</strong> to run the full pipeline.
            </p>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3 max-w-lg w-full">
              {[
                ['🛰️','Sentinel-1 SAR','Water probability + backscatter'],
                ['🌿','Sentinel-2 NDVI','Vegetation health mapping'],
                ['🌡️','Land Surface Temp','Thermal anomaly detection'],
                ['🧠','CNN + LSTM AI','Water feature extraction'],
                ['🌾','AWD Detection','Cycle & irrigation analysis'],
                ['💰','Carbon Credits','IPCC AR6 credit computation'],
              ].map(([em, title, desc]) => (
                <motion.div key={title} whileHover={{ y: -2 }} className="glass-card p-4 text-center">
                  <div className="text-3xl mb-2">{em}</div>
                  <p className="text-xs font-medium text-carbon-700">{title}</p>
                  <p className="text-[10px] text-carbon-400 mt-0.5">{desc}</p>
                </motion.div>
              ))}
            </div>
          </div>
        ) : (
          <div className="p-6 max-w-4xl mx-auto">
            <AnimatePresence mode="wait">
              <motion.div
                key={activeTab}
                initial={{ opacity: 0, x: 16 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -16 }}
                transition={{ duration: 0.18 }}
              >
                {/* ErrorBoundary wraps every panel — crashes show a recoverable error card */}
                <ErrorBoundary key={activeTab}>
                  {ActivePanel ? <ActivePanel /> : (
                    <div className="flex items-center justify-center h-48 text-carbon-400">
                      Select a panel from the sidebar
                    </div>
                  )}
                </ErrorBoundary>
              </motion.div>
            </AnimatePresence>
          </div>
        )}
      </div>
    </div>
  )
}
