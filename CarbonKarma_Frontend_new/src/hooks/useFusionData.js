import { useEffect, useState } from 'react'
import { fetchFusionData } from '../services/api'

export function useFusionData({ lat, lon, nSteps, stepDays, geojson, enabled = true }) {
  const [fusion, setFusion] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)
  const [source, setSource] = useState(null)

  useEffect(() => {
    if (!enabled || !lat || !lon) return
    let active = true
    setIsLoading(true)
    setError(null)

    fetchFusionData(lat, lon, nSteps, stepDays, true, geojson)
      .then(result => {
        if (!active) return
        setFusion(result.data)
        setSource(result.source)
        setIsLoading(false)
      })
      .catch(err => {
        if (!active) return
        setError(err.message)
        setIsLoading(false)
      })

    return () => { active = false }
  }, [lat, lon, nSteps, stepDays, geojson, enabled])

  return { data: fusion, isLoading, error, source }
}
