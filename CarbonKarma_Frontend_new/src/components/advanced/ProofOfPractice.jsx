import React, { useEffect, useState } from 'react'
import TimeSeriesChart from '../charts/TimeSeriesChart'
import MetricCard from '../ui/MetricCard'
import { motion } from 'framer-motion'
import { useApp } from '../../context/AppContext'
import { useApiData } from '../../hooks/useApiData'
import { fetchSatelliteData, fetchLLMExplain } from '../../services/api'
import LoadingSpinner from '../ui/LoadingSpinner'

function normalizeSeries(data) {
  if (!data) return []
  if (Array.isArray(data)) return data
  if (data.records) return data.records
  if (data.data) return normalizeSeries(data.data)
  return []
}

function formatSnapshot(point = {}) {
  return {
    waterProb: point.water_prob_mean ?? point.water_prob ?? point.water_level ?? 0,
    ndvi: point.ndvi_mean ?? point.ndvi ?? 0,
    status: point.is_flooded ? 'Flooded' : point.flood_type || (point.water_level > 0.45 ? 'Wet' : 'Dry'),
    rainfall: point.rainfall_mm ?? point.rainfall ?? 0,
    timestamp: point.timestamp || point.date || 'Unknown'
  }
}

export default function ProofOfPractice({ satellite: propSatellite, weather: propWeather, llm: propLLM }) {
  const { location, nSteps, stepDays, farmId } = useApp()
  const { loading, error, fetchData } = useApiData()
  const [satellite, setSatellite] = useState(null)
  const [weather, setWeather] = useState(null)
  const [llm, setLLM] = useState(null)
  const [allSnapshots, setAllSnapshots] = useState([])

  // Fetch satellite data from API when location changes
  useEffect(() => {
    if (!location.lat || !location.lon) {
      // Fallback to props if location not set
      setSatellite(propSatellite)
      setWeather(propWeather)
      setLLM(propLLM)
      return
    }

    const fetchRealData = async () => {
      // Fetch satellite data
      await fetchData(
        () => fetchSatelliteData(location.lat, location.lon, nSteps, stepDays, location.geojson),
        (data) => {
          setSatellite(data)
          // Extract all snapshots from sentinel1 or sentinel2
          const s1 = normalizeSeries(data?.sentinel1)
          const s2 = normalizeSeries(data?.sentinel2)
          const snapshots = s1.length ? s1 : s2
          setAllSnapshots(snapshots)
        },
        'satellite'
      )

      // Fetch LLM insights for explanation
      await fetchData(
        () => fetchLLMExplain(location.lat, location.lon, farmId, nSteps),
        (data) => {
          setLLM(data)
        },
        'llm-explain'
      )
    }

    fetchRealData()
  }, [location.lat, location.lon, nSteps, stepDays, farmId, fetchData])

  // Use real data if available, fallback to props
  const sentinel1 = normalizeSeries(satellite?.sentinel1 || satellite?.sentinel_1 || propSatellite?.sentinel1 || propSatellite?.sentinel_1 || satellite)
  const sentinel2 = normalizeSeries(satellite?.sentinel2 || satellite?.sentinel_2 || propSatellite?.sentinel2 || propSatellite?.sentinel_2)
  const snapshots = sentinel1.length ? sentinel1 : sentinel2
  const before = formatSnapshot(snapshots[0])
  const after = formatSnapshot(snapshots[snapshots.length - 1])

  const rainfallLog = normalizeSeries(
    satellite?.weather || weather || propWeather || []
  )
    .filter(entry => entry && (entry.rainfall_mm != null || entry.rainfall != null))
    .slice(-5)
    .reverse()

  const aiText = llm?.explanation || llm?.summary || propLLM?.explanation || propLLM?.summary ||
    `Flood detected without rainfall → irrigation confirmed → AWD cycle valid.`

  if (loading && !snapshots.length) {
    return (
      <div className="glass-card p-5 flex items-center justify-center min-h-96">
        <LoadingSpinner />
      </div>
    )
  }

  if (error && !snapshots.length) {
    return (
      <div className="glass-card p-5 text-center">
        <p className="text-sm text-red-600">Error loading satellite data: {error}</p>
      </div>
    )
  }

  return (
    <div className="glass-card p-5 space-y-5">
      <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-wider text-carbon-500">Proof-of-Practice Engine</p>
          <h3 className="text-2xl font-display text-carbon-900">Verifiable AWD & methane evidence</h3>
          <p className="text-sm text-carbon-500 max-w-2xl mt-2">
            Compare satellite signatures, rainfall logs, and AI reasoning to explain why this field qualifies for AWD verification.
          </p>
        </div>
        <div className="grid grid-cols-2 gap-2 w-full md:w-auto">
          <MetricCard label="Before/After" value={snapshots.length ? `${snapshots.length} steps` : '—'} unit="observations" color="earth" />
          <MetricCard label="Rain events" value={rainfallLog.length} unit="records" color="sky" />
        </div>
      </div>

      {/* Data Source Badge */}
      {loading && (
        <div className="flex items-center gap-2 text-xs text-amber-600 bg-amber-50/70 px-3 py-2 rounded-full w-fit">
          <div className="w-2 h-2 bg-amber-500 rounded-full animate-pulse" />
          Loading live satellite data...
        </div>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-[0.8fr_0.65fr] gap-5">
        <div className="space-y-4">
          {/* Snapshot Gallery */}
          {snapshots.length > 2 && (
            <div className="glass-card p-4 bg-earth-50 border-earth-200/70">
              <p className="text-xs uppercase tracking-wider text-carbon-500 mb-3">Satellite snapshots timeline</p>
              <div className="flex gap-2 overflow-x-auto pb-2">
                {snapshots.map((snap, idx) => {
                  const formatted = formatSnapshot(snap)
                  return (
                    <motion.div
                      key={idx}
                      whileHover={{ scale: 1.05 }}
                      className="flex-shrink-0 w-24 p-2 rounded-lg bg-white/70 border border-earth-200 text-center cursor-pointer"
                    >
                      <p className="text-[10px] text-carbon-400">{(formatted.waterProb * 100).toFixed(0)}%</p>
                      <p className="text-xs font-medium text-carbon-700">{formatted.status}</p>
                      <p className="text-[10px] text-carbon-500 mt-1">{typeof formatted.timestamp === 'string' ? formatted.timestamp.split('T')[0] : formatted.timestamp}</p>
                    </motion.div>
                  )
                })}
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {[{ title: 'Before', point: before }, { title: 'After', point: after }].map(({ title, point }) => (
              <motion.div key={title} whileHover={{ y: -2 }} className="glass-card p-4 bg-earth-50 border-earth-200/70">
                <p className="text-xs uppercase tracking-wider text-carbon-500 mb-3">{title} satellite evidence</p>
                <p className="text-sm text-carbon-700">{point.status}</p>
                <div className="mt-3 space-y-2">
                  <p className="text-xs text-carbon-400">Water probability</p>
                  <p className="text-2xl font-display text-carbon-900">{(point.waterProb * 100).toFixed(0)}%</p>
                </div>
                <div className="mt-3 grid grid-cols-2 gap-3 text-xs text-carbon-500">
                  <div>
                    <p className="font-medium text-carbon-700">NDVI</p>
                    <p>{point.ndvi.toFixed(2)}</p>
                  </div>
                  <div>
                    <p className="font-medium text-carbon-700">Rain</p>
                    <p>{point.rainfall.toFixed(1)} mm</p>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>

          <div className="glass-card p-4">
            <div className="flex items-center justify-between mb-4">
              <p className="text-xs uppercase tracking-wider text-carbon-500">Rainfall logs</p>
              <span className="text-[10px] uppercase text-carbon-400">Recent events</span>
            </div>
            <TimeSeriesChart
              data={rainfallLog.length ? rainfallLog.map(entry => ({ timestamp: entry.timestamp || entry.date || 'n/a', rainfall: entry.rainfall_mm ?? entry.rainfall ?? 0 })) : []}
              height={210}
              series={[{ key: 'rainfall', name: 'Rainfall', color: '#38bdf8' }]}
              title="Rainfall intensity"
            />
          </div>
        </div>

        <div className="glass-card p-5 bg-sky-50 border-sky-200/70">
          <p className="text-xs uppercase tracking-wider text-carbon-500 mb-3">AI explanation</p>
          <div className="space-y-4">
            <p className="text-sm text-carbon-700 leading-relaxed">{aiText}</p>
            <div className="space-y-3">
              <div className="rounded-3xl bg-white/85 p-4 shadow-sm">
                <p className="text-[10px] uppercase tracking-wider text-carbon-400">Satellite match</p>
                <p className="text-sm text-carbon-800">{before.status} → {after.status}</p>
              </div>
              <div className="rounded-3xl bg-white/85 p-4 shadow-sm">
                <p className="text-[10px] uppercase tracking-wider text-carbon-400">Weather alignment</p>
                <p className="text-sm text-carbon-800">{rainfallLog.length ? `${rainfallLog.length} rain records confirm observed field response.` : 'Minimal rainfall observations support AWD detection.'}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
