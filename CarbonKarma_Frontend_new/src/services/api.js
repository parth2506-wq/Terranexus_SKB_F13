import axios from 'axios'
import { generateFallbackData } from '../utils/fallbackData'

const BASE_URL = import.meta.env.VITE_API_URL || '/api'

// Response cache keyed by endpoint+params hash
const responseCache = new Map()
const MAX_CACHE_AGE_MS = 5 * 60 * 1000 // 5 minutes

const apiClient = axios.create({
  baseURL: BASE_URL,
  timeout: 45000,
  headers: { 'Content-Type': 'application/json' }
})

// Request interceptor — log
apiClient.interceptors.request.use(config => {
  config.metadata = { startTime: Date.now() }
  return config
})

// Response interceptor — log timing
apiClient.interceptors.response.use(
  response => {
    const ms = Date.now() - response.config.metadata.startTime
    console.debug(`[API] ${response.config.method?.toUpperCase()} ${response.config.url} → ${response.status} (${ms}ms)`)
    return response
  },
  error => Promise.reject(error)
)

function cacheKey(endpoint, params) {
  return `${endpoint}:${JSON.stringify(params)}`
}

function getCached(key) {
  const entry = responseCache.get(key)
  if (!entry) return null
  if (Date.now() - entry.timestamp > MAX_CACHE_AGE_MS) {
    responseCache.delete(key)
    return null
  }
  return entry.data
}

function setCache(key, data) {
  responseCache.set(key, { data, timestamp: Date.now() })
}

// Core retry wrapper
async function apiCall(endpoint, params, retries = 2) {
  const key = cacheKey(endpoint, params)

  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const response = await apiClient.post(endpoint, params)
      const data = response.data
      setCache(key, data)
      return { data, source: 'live', cached: false }
    } catch (err) {
      const isLast = attempt === retries
      if (!isLast) {
        await new Promise(r => setTimeout(r, 600 * (attempt + 1)))
        continue
      }

      // Try cache
      const cached = getCached(key)
      if (cached) {
        console.warn(`[API] ${endpoint} failed — using cached response`)
        return { data: cached, source: 'cached', cached: true }
      }

      // Fallback synthetic data
      console.warn(`[API] ${endpoint} failed — using fallback data:`, err.message)
      const fallback = generateFallbackData(endpoint, params)
      return { data: fallback, source: 'fallback', cached: false, error: err.message }
    }
  }
}

async function apiGet(endpoint, params = {}) {
  const key = cacheKey(endpoint, params)
  try {
    const queryStr = new URLSearchParams(params).toString()
    const url = queryStr ? `${endpoint}?${queryStr}` : endpoint
    const response = await apiClient.get(url)
    setCache(key, response.data)
    return { data: response.data, source: 'live', cached: false }
  } catch (err) {
    const cached = getCached(key)
    if (cached) return { data: cached, source: 'cached', cached: true }
    const fallback = generateFallbackData(endpoint, params)
    return { data: fallback, source: 'fallback', cached: false, error: err.message }
  }
}

// ── Public API functions ────────────────────────────────────────────────

export const fetchSatelliteData = (lat, lon, nSteps = 12, stepDays = 7, geojson = null) =>
  apiCall('/satellite-data', { lat, lon, n_steps: nSteps, step_days: stepDays, ...(geojson && { geojson }) })

export const fetchFusionData = (lat, lon, nSteps = 12, stepDays = 7, includeHeatmaps = true, geojson = null) =>
  apiCall('/fusion-data', { lat, lon, n_steps: nSteps, step_days: stepDays, include_heatmaps: includeHeatmaps, ...(geojson && { geojson }) })

export const fetchAWDStatus = (lat, lon, nSteps = 14, stepDays = 7, geojson = null) =>
  apiCall('/awd-status', { lat, lon, n_steps: nSteps, step_days: stepDays, ...(geojson && { geojson }) })

export const fetchMethane = (lat, lon, nSteps = 12, stepDays = 7, geojson = null) =>
  apiCall('/methane', { lat, lon, n_steps: nSteps, step_days: stepDays, ...(geojson && { geojson }) })

export const fetchVerification = (lat, lon, farmId = 'farm_001', nSteps = 14, stepDays = 7, geojson = null) =>
  apiCall('/verification', { lat, lon, farm_id: farmId, n_steps: nSteps, step_days: stepDays, ...(geojson && { geojson }) })

export const fetchCredits = (lat, lon, farmId = 'farm_001', areaHa = 4.5, nSteps = 14, stepDays = 7, geojson = null) =>
  apiCall('/credits', { lat, lon, farm_id: farmId, area_ha: areaHa, n_steps: nSteps, step_days: stepDays, ...(geojson && { geojson }) })

export const fetchWallet = (farmId = 'farm_001') =>
  apiGet('/credits/wallet', { farm_id: farmId })

export const fetchAnalytics = (lat, lon, farmId = 'farm_001', nSteps = 12, stepDays = 7, region = 'south_asia', geojson = null) =>
  apiCall('/analytics', { lat, lon, farm_id: farmId, n_steps: nSteps, step_days: stepDays, region, include_heatmaps: true, ...(geojson && { geojson }) })

export const fetchLLMInsights = (lat, lon, query, farmId = 'farm_001', nSteps = 10, geojson = null) =>
  apiCall('/llm-insights', { lat, lon, query, farm_id: farmId, n_steps: nSteps, ...(geojson && { geojson }) })

export const fetchLLMExplain = (lat, lon, farmId = 'farm_001', nSteps = 12, geojson = null) =>
  apiCall('/llm-insights/explain', { lat, lon, farm_id: farmId, n_steps: nSteps, ...(geojson && { geojson }) })

export const fetchLLMAlerts = (lat, lon, farmId = 'farm_001', nSteps = 10, geojson = null) =>
  apiCall('/llm-insights/alerts', { lat, lon, farm_id: farmId, n_steps: nSteps, ...(geojson && { geojson }) })

export const fetchLLMCertificate = (lat, lon, farmId = 'farm_001', nSteps = 12, geojson = null) =>
  apiCall('/llm-insights/certificate', { lat, lon, farm_id: farmId, n_steps: nSteps, ...(geojson && { geojson }) })

export const generateReport = (lat, lon, farmId = 'farm_001', nSteps = 12, geojson = null) =>
  apiCall('/report', { lat, lon, farm_id: farmId, n_steps: nSteps, ...(geojson && { geojson }) })

export const retireCredits = (farmId, amount, reason = 'certificate') =>
  apiCall('/credits/retire', { farm_id: farmId, amount, reason })

export { apiClient }
