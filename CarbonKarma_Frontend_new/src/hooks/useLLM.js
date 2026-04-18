import { useEffect, useState } from 'react'
import { fetchLLMInsights } from '../services/api'

export function useLLM({ lat, lon, query, farmId, nSteps, geojson, enabled = true }) {
  const [insights, setInsights] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)
  const [source, setSource] = useState(null)

  useEffect(() => {
    if (!enabled || !lat || !lon || !query) return
    let active = true
    setIsLoading(true)
    setError(null)

    fetchLLMInsights(lat, lon, query, farmId, nSteps, geojson)
      .then(result => {
        if (!active) return
        setInsights(result.data)
        setSource(result.source)
        setIsLoading(false)
      })
      .catch(err => {
        if (!active) return
        setError(err.message)
        setIsLoading(false)
      })

    return () => { active = false }
  }, [lat, lon, query, farmId, nSteps, geojson, enabled])

  return { data: insights, isLoading, error, source }
}
