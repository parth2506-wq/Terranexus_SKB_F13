import React, { useEffect, useRef, useState, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { useApp } from '../../context/AppContext'
import clsx from 'clsx'
import { Layers, Droplets, Activity, Thermometer, CloudRain, X, Info } from 'lucide-react'

let L = null
let drawLoaded = false

function loadLeaflet() {
  if (typeof window === 'undefined') return null
  if (!L) L = window.L
  return L
}

// Color ramps for heatmap layers
function getColor(value, band) {
  const v = Math.max(0, Math.min(1, value))
  if (band === 'water_prob') {
    const r = Math.round(0 + v * 0)
    const g = Math.round(100 + v * 155)
    const b = Math.round(200 + v * 55)
    return `rgba(${r},${g},${b},${0.3 + v * 0.5})`
  }
  if (band === 'ndvi') {
    const r = Math.round(200 - v * 150)
    const g = Math.round(100 + v * 155)
    const b = Math.round(50 - v * 30)
    return `rgba(${r},${g},${b},${0.25 + v * 0.5})`
  }
  if (band === 'lst_norm') {
    const r = Math.round(50 + v * 205)
    const g = Math.round(100 - v * 60)
    const b = Math.round(200 - v * 180)
    return `rgba(${r},${g},${b},${0.3 + v * 0.45})`
  }
  const r = Math.round(100 + v * 100)
  const g = Math.round(150 + v * 80)
  const b = Math.round(220 - v * 100)
  return `rgba(${r},${g},${b},${0.25 + v * 0.45})`
}

function renderHeatmapToCanvas(data, band) {
  if (!data?.length) return null
  const lats = data.map(p => p.lat)
  const lons = data.map(p => p.lon)
  const minLat = Math.min(...lats), maxLat = Math.max(...lats)
  const minLon = Math.min(...lons), maxLon = Math.max(...lons)
  const size = Math.round(Math.sqrt(data.length)) || 8
  const canvas = document.createElement('canvas')
  canvas.width = size * 6
  canvas.height = size * 6
  const ctx = canvas.getContext('2d')
  data.forEach(({ lat, lon, value }) => {
    const col = Math.round((lon - minLon) / (maxLon - minLon || 1) * (size - 1))
    const row = Math.round((maxLat - lat) / (maxLat - minLat || 1) * (size - 1))
    ctx.fillStyle = getColor(value, band)
    ctx.fillRect(col * 6, row * 6, 6, 6)
  })
  const sw = L.latLng(minLat, minLon)
  const ne = L.latLng(maxLat, maxLon)
  return { canvas, bounds: L.latLngBounds(sw, ne) }
}

const LAYER_CONFIG = [
  { id: 'water_prob', label: 'Water',  icon: Droplets,    color: 'text-sky-600' },
  { id: 'ndvi',       label: 'NDVI',   icon: Activity,    color: 'text-earth-600' },
  { id: 'lst_norm',   label: 'Temp',   icon: Thermometer, color: 'text-red-500' },
  { id: 'soil_moisture', label: 'Soil', icon: CloudRain,  color: 'text-amber-600' },
]

export default function FarmMap({ heatmaps, onMapClick, onFarmDrawn, activePanel }) {
  const { t } = useTranslation()
  const { location } = useApp()
  const mapRef = useRef(null)
  const mapInstanceRef = useRef(null)
  const layersRef = useRef({})
  const drawLayerRef = useRef(null)
  const farmLayerRef = useRef(null)
  const markerRef = useRef(null)
  const [activeLayers, setActiveLayers] = useState(['water_prob'])
  const [opacities, setOpacities] = useState({ water_prob: 0.7, ndvi: 0.7, lst_norm: 0.7, soil_moisture: 0.7 })
  const [pixelInfo, setPixelInfo] = useState(null)
  const [mapReady, setMapReady] = useState(false)

  // Init map
  useEffect(() => {
    if (mapInstanceRef.current || !mapRef.current) return
    L = window.L
    if (!L) return

    const map = L.map(mapRef.current, {
      center: [20.5937, 78.9629],
      zoom: 5,
      zoomControl: false,
    })

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap',
      maxZoom: 19,
    }).addTo(map)

    L.control.zoom({ position: 'topright' }).addTo(map)

    // Draw controls
    const drawnItems = new L.FeatureGroup()
    map.addLayer(drawnItems)
    drawLayerRef.current = drawnItems

    if (L.Control && L.Control.Draw) {
      const drawControl = new L.Control.Draw({
        position: 'topright',
        draw: {
          polygon: { shapeOptions: { color: '#467a27', fillColor: '#5c9934', fillOpacity: 0.2 } },
          rectangle: { shapeOptions: { color: '#467a27', fillColor: '#5c9934', fillOpacity: 0.2 } },
          circle: false, circlemarker: false, marker: false, polyline: false,
        },
        edit: { featureGroup: drawnItems }
      })
      map.addControl(drawControl)

      map.on(L.Draw.Event.CREATED, (e) => {
        drawnItems.clearLayers()
        drawnItems.addLayer(e.layer)
        const geojson = e.layer.toGeoJSON()
        const center = e.layer.getBounds().getCenter()
        onFarmDrawn?.({ lat: center.lat, lon: center.lng, geojson })
      })
    }

    // Click handler
    map.on('click', (e) => {
      const { lat, lng } = e.latlng
      onMapClick?.({ lat, lon: lng })
      if (markerRef.current) markerRef.current.remove()
      markerRef.current = L.circleMarker([lat, lng], {
        radius: 6, color: '#467a27', fillColor: '#5c9934', fillOpacity: 0.8, weight: 2
      }).addTo(map)
    })

    mapInstanceRef.current = map
    setMapReady(true)
    return () => { map.remove(); mapInstanceRef.current = null }
  }, [])

  // Update map center when location changes
  useEffect(() => {
    if (!mapInstanceRef.current || !location.lat) return
    mapInstanceRef.current.setView([location.lat, location.lon], 13)
    if (farmLayerRef.current) { farmLayerRef.current.remove(); farmLayerRef.current = null }
    if (markerRef.current) { markerRef.current.remove(); markerRef.current = null }
    markerRef.current = L.circleMarker([location.lat, location.lon], {
      radius: 8, color: '#467a27', fillColor: '#5c9934', fillOpacity: 0.9, weight: 2
    }).bindPopup(`<b>${location.lat.toFixed(4)}°N, ${location.lon.toFixed(4)}°E</b>`).addTo(mapInstanceRef.current)
  }, [location.lat, location.lon])

  // Render heatmap layers
  useEffect(() => {
    if (!mapInstanceRef.current || !heatmaps) return
    // Clear existing image overlays
    Object.values(layersRef.current).forEach(l => { if (l) mapInstanceRef.current.removeLayer(l) })
    layersRef.current = {}

    activeLayers.forEach(band => {
      const hm = heatmaps[band]
      if (!hm?.data?.length) return
      const result = renderHeatmapToCanvas(hm.data, band)
      if (!result) return
      const url = result.canvas.toDataURL()
      const overlay = L.imageOverlay(url, result.bounds, { opacity: opacities[band], interactive: false })
      overlay.addTo(mapInstanceRef.current)
      layersRef.current[band] = overlay
    })
  }, [heatmaps, activeLayers, opacities])

  const toggleLayer = useCallback((id) => {
    setActiveLayers(prev => prev.includes(id) ? prev.filter(l => l !== id) : [...prev, id])
  }, [])

  const setOpacity = useCallback((id, val) => {
    setOpacities(prev => ({ ...prev, [id]: parseFloat(val) }))
    if (layersRef.current[id]) layersRef.current[id].setOpacity(parseFloat(val))
  }, [])

  return (
    <div className="relative w-full h-full rounded-2xl overflow-hidden shadow-card">
      <div ref={mapRef} className="w-full h-full" />

      {/* Layer controls */}
      {heatmaps && (
        <div className="absolute top-4 left-4 z-[400] glass-card p-3 space-y-2 min-w-[160px]">
          <p className="text-xs font-medium text-carbon-600 flex items-center gap-1.5">
            <Layers className="w-3.5 h-3.5" /> Layers
          </p>
          {LAYER_CONFIG.map(({ id, label, icon: Icon, color }) => (
            <div key={id} className="space-y-1">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={activeLayers.includes(id)}
                  onChange={() => toggleLayer(id)}
                  className="accent-earth-600 w-3.5 h-3.5"
                />
                <Icon className={`w-3.5 h-3.5 ${color}`} />
                <span className="text-xs text-carbon-700">{label}</span>
              </label>
              {activeLayers.includes(id) && (
                <div className="flex items-center gap-2 pl-5">
                  <input
                    type="range" min="0.1" max="1" step="0.1"
                    value={opacities[id]}
                    onChange={e => setOpacity(id, e.target.value)}
                    className="w-16 h-1 accent-earth-600"
                  />
                  <span className="text-[10px] text-carbon-400 font-mono">{(opacities[id] * 100).toFixed(0)}%</span>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* No data message */}
      {!heatmaps && !location.lat && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="glass-card px-5 py-4 text-center max-w-xs">
            <div className="w-10 h-10 bg-earth-100 rounded-xl flex items-center justify-center mx-auto mb-3">
              <Info className="w-5 h-5 text-earth-600" />
            </div>
            <p className="text-sm font-medium text-carbon-700">Draw or click your farm</p>
            <p className="text-xs text-carbon-400 mt-1">Use the draw tools (top-right) or click a location on the map to begin analysis</p>
          </div>
        </div>
      )}
    </div>
  )
}
