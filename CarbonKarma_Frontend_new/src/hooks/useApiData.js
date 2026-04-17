import { useState, useCallback } from 'react'
import { useApp } from '../context/AppContext'

export function useApiData() {
  const { setDataSource } = useApp()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const fetchData = useCallback(async (apiFn, onSuccess, key) => {
    setLoading(true)
    setError(null)
    try {
      const result = await apiFn()
      if (result?.source) setDataSource(result.source)
      if (result?.data) onSuccess(result.data, result.source)
      return result
    } catch (err) {
      setError(err.message)
      console.error(`[useApiData] Error fetching ${key}:`, err)
    } finally {
      setLoading(false)
    }
  }, [setDataSource])

  return { loading, error, fetchData }
}
