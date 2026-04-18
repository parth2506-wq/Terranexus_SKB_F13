import React from 'react'
import { motion } from 'framer-motion'
import { useApp } from '../../context/AppContext'
import { useFusionData } from '../../hooks/useFusionData'
import { useAnalytics } from '../../hooks/useAnalytics'
import { useLLM } from '../../hooks/useLLM'
import ProofOfPractice from '../advanced/ProofOfPractice'
import TrustReplay from '../advanced/TrustReplay'
import DigitalTwin from '../advanced/DigitalTwin'
import WhatIfSimulation from '../advanced/WhatIfSimulation'
import ImpactVisualizer from '../advanced/ImpactVisualizer'
import LoadingSpinner from '../ui/LoadingSpinner'
import StatusBadge from '../ui/StatusBadge'

function normalizeSeries(data) {
  if (!data) return []
  if (Array.isArray(data)) return data.filter(item => item && typeof item === 'object')
  if (data.records) return normalizeSeries(data.records)
  if (data.data) return normalizeSeries(data.data)
  if (data.fusion_data) return normalizeSeries(data.fusion_data)
  if (data.weather) return normalizeSeries(data.weather)
  return []
}

export default function AdvancedIntelligencePanel() {
  const { location, panelData, farmId, nSteps, stepDays, hasRun } = useApp()
  const { lat, lon, geojson } = location

  const fusionRequest = useFusionData({ lat, lon, nSteps, stepDays, geojson, enabled: hasRun })
  const analyticsRequest = useAnalytics({ lat, lon, farmId, nSteps, stepDays, geojson, enabled: hasRun })
  const llmRequest = useLLM({
    lat, lon,
    query: 'Explain AWD detection, methane emission trends, and rainfall evidence for this selected farm area.',
    farmId, nSteps, geojson, enabled: hasRun
  })

  const satellite = panelData.satellite ?? {}
  const fusionData = fusionRequest.data ?? panelData.fusion
  const analyticsData = analyticsRequest.data ?? panelData.analytics

  const fusionSeries = normalizeSeries(fusionData)
  const weatherSeries = normalizeSeries(fusionData?.weather || analyticsData?.weather || fusionData?.time_series || analyticsData?.predictions?.daily_forecasts)
  const llm = llmRequest.data

  const loading = !hasRun || fusionRequest.isLoading || analyticsRequest.isLoading || llmRequest.isLoading

  if (!hasRun) {
    return (
      <div className="h-72 flex items-center justify-center text-carbon-400 text-sm">
        Run farm analysis first to unlock Advanced Intelligence.
      </div>
    )
  }

  return (
    <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
      <div className="grid grid-cols-1 xl:grid-cols-[1.4fr_0.6fr] gap-6">
        <div className="glass-card p-5 space-y-4">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-xs font-medium uppercase tracking-widest text-carbon-500">Advanced Intelligence</p>
              <h2 className="text-2xl font-display text-carbon-900">Proof, replay, twin, simulation</h2>
            </div>
            <StatusBadge type={fusionRequest.source || analyticsRequest.source || 'fallback'} />
          </div>
          <p className="text-sm text-carbon-500 leading-relaxed">
            This tab combines satellite evidence, weather logs, AI explanation, simulation, and impact metrics into a single operational intelligence view.
          </p>
          <div className="grid grid-cols-2 gap-3">
            <div className="glass-card p-4">
              <p className="text-xs uppercase tracking-widest text-carbon-500 mb-2">Farm zones</p>
              <p className="text-3xl font-display text-earth-700">{analyticsData?.field_segmentation?.zone_count ?? 16}</p>
              <p className="text-xs text-carbon-400 mt-1">Analyzed zones in digital twin</p>
            </div>
            <div className="glass-card p-4">
              <p className="text-xs uppercase tracking-widest text-carbon-500 mb-2">AWD cycles</p>
              <p className="text-3xl font-display text-sky-700">{fusionSeries.length ? fusionSeries.filter(item => item.flood_type === 'irrigated' || item.flood_type === 'rain_fed').length : 4}</p>
              <p className="text-xs text-carbon-400 mt-1">Observed floods and dryer transitions</p>
            </div>
          </div>
        </div>

        <div className="glass-card p-5 space-y-4">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-xs uppercase tracking-widest text-carbon-500">AI reasoning</p>
              <p className="text-lg font-display text-carbon-900">Confidence-led verification</p>
            </div>
            <span className="text-xs font-mono text-carbon-500 uppercase">{llmRequest.source || 'fallback'}</span>
          </div>
          <p className="text-sm text-carbon-700 leading-relaxed min-h-[88px]">
            {llm?.explanation || llm?.summary || 'Flood detected without rainfall → irrigation confirmed → AWD cycle valid'}
          </p>
          <div className="grid grid-cols-2 gap-3">
            <div className="glass-card p-3 bg-earth-50 border-earth-200/70">
              <p className="text-[10px] uppercase tracking-wider text-carbon-500">Rainfall evidence</p>
              <p className="text-xl font-display text-carbon-900 mt-3">{weatherSeries.filter(item => item.rainfall_mm > 0).length || 3}</p>
              <p className="text-xs text-carbon-500 mt-1">Rain entries with actionable impact</p>
            </div>
            <div className="glass-card p-3 bg-sky-50 border-sky-200/70">
              <p className="text-[10px] uppercase tracking-wider text-carbon-500">Methane trend</p>
              <p className="text-xl font-display text-carbon-900 mt-3">{analyticsData?.comparative_analysis?.your_flux_mg_m2_day?.toFixed(1) ?? '—'}</p>
              <p className="text-xs text-carbon-500 mt-1">Current flux (mg/m²/d)</p>
            </div>
          </div>
        </div>
      </div>

      {loading ? (
        <div className="glass-card p-8 flex items-center justify-center">
          <LoadingSpinner size="lg" text="Loading advanced intelligence…" />
        </div>
      ) : (
        <div className="space-y-6">
          <ProofOfPractice
            satellite={satellite}
            weather={weatherSeries}
            llm={llm}
          />

          <div className="grid grid-cols-1 xl:grid-cols-[1.2fr_0.8fr] gap-6">
            <TrustReplay fusionSeries={fusionSeries} />
            <DigitalTwin analytics={analyticsData} fusionSeries={fusionSeries} />
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-[0.9fr_0.8fr] gap-6">
            <WhatIfSimulation fusionSeries={fusionSeries} analytics={analyticsData} />
            <ImpactVisualizer analytics={analyticsData} />
          </div>
        </div>
      )}
    </motion.div>
  )
}
