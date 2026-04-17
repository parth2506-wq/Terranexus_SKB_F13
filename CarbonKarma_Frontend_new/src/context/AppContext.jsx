import React, { createContext, useContext, useState, useCallback } from 'react'

const AppContext = createContext(null)

export function AppProvider({ children }) {
  const [location, setLocation] = useState({ lat: null, lon: null, geojson: null })
  const [activeTab, setActiveTab] = useState('dashboard')
  const [dataSource, setDataSource] = useState(null) // 'live' | 'cached' | 'fallback'
  const [farmId, setFarmId] = useState('farm_001')
  const [nSteps, setNSteps] = useState(12)
  const [stepDays, setStepDays] = useState(7)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [hasRun, setHasRun] = useState(false)

  // Cache all panel data
  const [panelData, setPanelData] = useState({
    satellite: null, fusion: null, awd: null, methane: null,
    verification: null, credits: null, analytics: null, llm: null
  })

  const updatePanelData = useCallback((panel, data) => {
    setPanelData(prev => ({ ...prev, [panel]: data }))
  }, [])

  const resetAll = useCallback(() => {
    setPanelData({ satellite: null, fusion: null, awd: null, methane: null, verification: null, credits: null, analytics: null, llm: null })
    setHasRun(false)
    setDataSource(null)
  }, [])

  return (
    <AppContext.Provider value={{
      location, setLocation,
      activeTab, setActiveTab,
      dataSource, setDataSource,
      farmId, setFarmId,
      nSteps, setNSteps,
      stepDays, setStepDays,
      isAnalyzing, setIsAnalyzing,
      hasRun, setHasRun,
      panelData, updatePanelData, setPanelData,
      resetAll
    }}>
      {children}
    </AppContext.Provider>
  )
}

export const useApp = () => {
  const ctx = useContext(AppContext)
  if (!ctx) throw new Error('useApp must be used within AppProvider')
  return ctx
}
