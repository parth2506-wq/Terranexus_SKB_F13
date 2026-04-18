import { useEffect, useState } from 'react'
import { fetchAnalytics } from '../services/api'

export function useAnalytics({ lat, lon, farmId, nSteps, stepDays, geojson, enabled = true }) {
  const [analytics, setAnalytics] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)
  const [source, setSource] = useState(null)

  useEffect(() => {
    if (!enabled || !lat || !lon) return
    let active = true
    setIsLoading(true)
    setError(null)

    fetchAnalytics(lat, lon, farmId, nSteps, stepDays, 'south_asia', geojson)
      .then(result => {
        if (!active) return
        setAnalytics(result.data)
        setSource(result.source)
        setIsLoading(false)
      })
      .catch(err => {
        if (!active) return
        setError(err.message)
        setIsLoading(false)
      })

    return () => { active = false }
  }, [lat, lon, farmId, nSteps, stepDays, geojson, enabled])

  return { data: analytics, isLoading, error, source }
}
