import React, { useState } from 'react'
import { motion } from 'framer-motion'
import { useTranslation } from 'react-i18next'
import { useApp } from '../../context/AppContext'
import TimeSeriesChart from '../charts/TimeSeriesChart'
import GaugeChart from '../charts/GaugeChart'
import BarMetric from '../charts/BarMetric'
import MetricCard from '../ui/MetricCard'
import { BarChart3, AlertTriangle, User, FileText, Droplets, Leaf, Car } from 'lucide-react'
import clsx from 'clsx'

// Safe "trees" icon using SVG inline (lucide-react v0.383 doesn't have Trees)
const TreeIcon = ({ className }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 22V13" /><path d="M9 7l3-4 3 4H9z" /><path d="M7 12l5-7 5 7H7z" /><path d="M5 17l7-10 7 10H5z" />
  </svg>
)

const GRADE_COLORS = { A: 'text-earth-600', B: 'text-sky-600', C: 'text-amber-600', D: 'text-orange-600', F: 'text-red-600' }

export default function AnalyticsPanel() {
  const { t } = useTranslation()
  const { panelData } = useApp()
  const [trendWindow, setTrendWindow] = useState('30d')
  const data = panelData.analytics

  if (!data) return (
    <div className="flex items-center justify-center h-48 text-carbon-400 text-sm">No analytics data. Run analysis first.</div>
  )

  const fs    = data.farm_score || {}
  const comp  = data.comparative_analysis || {}
  const trends = data.historical_trends || {}
  const alerts = Array.isArray(data.alerts?.alerts) ? data.alerts.alerts : []
  const preds  = data.predictions || {}
  const seg    = data.field_segmentation || {}
  const impact = data.impact_metrics || {}
  const profile = data.farm_profile || {}
  const audit  = data.audit_trail || {}
  const windows = trends.windows || {}
  const tw = windows[trendWindow] || {}
  const forecasts = Array.isArray(preds.daily_forecasts) ? preds.daily_forecasts : []

  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
      <div className="flex items-center gap-2">
        <BarChart3 className="w-5 h-5 text-sky-600" />
        <h2 className="section-title mb-0">{t('analytics.title')}</h2>
      </div>

      {/* ── 1. Farm Score ───────────────────────────────────────────────── */}
      <div className="glass-card p-5">
        <p className="section-title text-base">{t('analytics.farmScore')}</p>
        <div className="flex items-center gap-6">
          <div className="text-center shrink-0">
            <p className={clsx('text-6xl font-display', GRADE_COLORS[fs.grade] || 'text-carbon-600')}>
              {fs.grade || '—'}
            </p>
            <p className="text-sm font-mono text-carbon-400">{fs.overall_score != null ? Number(fs.overall_score).toFixed(1) : '—'}/100</p>
          </div>
          <div className="flex-1 space-y-3">
            <BarMetric label={t('analytics.waterEfficiency')} value={fs.water_efficiency ?? 0} color="auto" />
            <BarMetric label={t('analytics.methaneControl')} value={fs.methane_control ?? 0} color="auto" />
            <BarMetric label={t('analytics.awdCompliance')} value={fs.awd_compliance ?? 0} color="auto" />
          </div>
        </div>
      </div>

      {/* ── 2. Comparative Analysis ─────────────────────────────────────── */}
      <div className="glass-card p-5">
        <p className="section-title text-base">{t('analytics.comparative')}</p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
          <MetricCard label="Your Flux" value={comp.your_flux_mg_m2_day != null ? Number(comp.your_flux_mg_m2_day).toFixed(1) : undefined} unit="mg/m²/d" color="amber" />
          <MetricCard label="Regional Avg" value={comp.regional_mean_mg_m2_day != null ? Number(comp.regional_mean_mg_m2_day).toFixed(1) : undefined} unit="mg/m²/d" color="sky" />
          <MetricCard label="Percentile" value={comp.percentile != null ? Number(comp.percentile).toFixed(1) : undefined} unit="%" color="earth" />
          <MetricCard label="vs Regional" value={comp.pct_vs_regional != null ? Number(comp.pct_vs_regional).toFixed(1) : undefined} unit="%" color={(comp.pct_vs_regional ?? 0) < 0 ? 'earth' : 'red'} />
        </div>
        <div className="bg-earth-50 rounded-xl p-3 text-sm">
          <span className="font-medium text-carbon-700">Performance: </span>
          <span className="text-earth-700">{(comp.performance || 'average').replace(/_/g, ' ')}</span>
          <span className="text-carbon-500 ml-2">— Region: {comp.region_label || 'South Asia'}</span>
        </div>
      </div>

      {/* ── 3. Historical Trends ────────────────────────────────────────── */}
      <div className="glass-card p-5">
        <div className="flex items-center justify-between mb-4">
          <p className="section-title text-base mb-0">{t('analytics.trends')}</p>
          <div className="flex gap-1 bg-carbon-100 rounded-lg p-1">
            {['7d', '30d', '90d'].map(w => (
              <button key={w} onClick={() => setTrendWindow(w)}
                className={clsx('px-3 py-1 rounded-md text-xs font-medium transition-all',
                  trendWindow === w ? 'bg-white text-carbon-800 shadow-sm' : 'text-carbon-500 hover:text-carbon-800')}>
                {w === '7d' ? t('analytics.days7') : w === '30d' ? t('analytics.days30') : t('analytics.days90')}
              </button>
            ))}
          </div>
        </div>
        <div className="grid grid-cols-3 gap-3">
          {[
            ['Water Level', (Number(tw.water_level ?? 0) * 100).toFixed(1), '%', 'bg-sky-50 text-sky-700'],
            ['NDVI', Number(tw.ndvi ?? 0).toFixed(3), '', 'bg-earth-50 text-earth-700'],
            ['Methane', Number(tw.methane ?? 0).toFixed(1), 'mg/m²/d', 'bg-amber-50 text-amber-700'],
          ].map(([label, value, unit, cls]) => (
            <div key={label} className={`${cls} rounded-xl p-3 text-center`}>
              <p className="text-[10px] text-carbon-400 uppercase tracking-wider">{label}</p>
              <p className="text-xl font-display">{value}</p>
              <p className="text-[10px] font-mono text-carbon-400">{unit}</p>
            </div>
          ))}
        </div>
        <p className="text-xs text-carbon-400 mt-2 text-center">
          {trendWindow} average · {trends.total_records ?? 0} records
        </p>
      </div>

      {/* ── 4. Alerts ───────────────────────────────────────────────────── */}
      {alerts.length > 0 && (
        <div className="glass-card p-4">
          <p className="section-title text-base flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-600" /> {t('analytics.alerts')}
          </p>
          <div className="space-y-2">
            {alerts.map((alert, i) => (
              <motion.div key={i}
                initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.06 }}
                className={clsx('p-3 rounded-xl border-l-4 flex items-start gap-3',
                  alert.severity === 'HIGH'   ? 'bg-red-50 border-red-400' :
                  alert.severity === 'MEDIUM' ? 'bg-amber-50 border-amber-400' :
                                                'bg-sky-50 border-sky-400')}>
                <AlertTriangle className={`w-4 h-4 shrink-0 mt-0.5 ${
                  alert.severity === 'HIGH' ? 'text-red-500' :
                  alert.severity === 'MEDIUM' ? 'text-amber-500' : 'text-sky-500'}`} />
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium text-carbon-700">
                    {(alert.type || '').replace(/_/g, ' ')}
                  </p>
                  <p className="text-xs text-carbon-500 mt-0.5">{alert.message}</p>
                  <p className="text-[10px] font-mono text-carbon-400 mt-1">{alert.timestamp}</p>
                </div>
                <span className={clsx('ml-auto text-[10px] font-medium px-2 py-0.5 rounded-full shrink-0',
                  alert.severity === 'HIGH' ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700')}>
                  {alert.severity}
                </span>
              </motion.div>
            ))}
          </div>
        </div>
      )}

      {/* ── 5. 7-Day Predictions ────────────────────────────────────────── */}
      <div className="glass-card p-4">
        <p className="section-title text-base">{t('analytics.predictions')}</p>
        {preds.irrigation_advice && (
          <div className="bg-earth-50 border border-earth-200 rounded-xl p-3 text-xs text-earth-700 mb-3 leading-relaxed">
            💧 <strong>Irrigation Advice:</strong> {preds.irrigation_advice}
          </div>
        )}
        {forecasts.length > 0 ? (
          <>
            <TimeSeriesChart
              data={forecasts.map(f => ({
                timestamp: f.date,
                methane: f.methane_mg_m2_day ?? 0,
                water: (f.water_level ?? 0) * 100,
                rainfall: f.rainfall_mm ?? 0,
              }))}
              height={180}
              series={[
                { key: 'methane', name: 'Predicted CH₄', color: '#f59e0b' },
                { key: 'water',   name: 'Water Level %', color: '#36aaf5', dashed: true },
              ]}
            />
            <div className="grid grid-cols-4 md:grid-cols-7 gap-1.5 mt-3">
              {forecasts.map((f, i) => (
                <div key={i} className="text-center bg-carbon-50 rounded-xl p-2">
                  <p className="text-[9px] font-mono text-carbon-400">{(f.date || '').slice(5)}</p>
                  <p className="text-xs font-medium text-amber-700">
                    {(f.methane_mg_m2_day ?? 0).toFixed(0)}
                  </p>
                  <p className="text-[9px] text-sky-500">{(f.rainfall_mm ?? 0).toFixed(1)}mm</p>
                </div>
              ))}
            </div>
          </>
        ) : (
          <p className="text-xs text-carbon-400 text-center py-4">No forecast data available</p>
        )}
      </div>

      {/* ── 6. Field Segmentation ───────────────────────────────────────── */}
      <div className="glass-card p-4">
        <p className="section-title text-base">{t('analytics.segmentation')}</p>
        {(seg.zones || []).length > 0 ? (
          <>
            <div className="grid grid-cols-4 md:grid-cols-8 gap-1">
              {seg.zones.slice(0, 16).map((zone, i) => {
                const intensity = Math.min(1, (zone.methane_level ?? 200) / 500)
                const r = Math.round(50 + intensity * 200)
                const g = Math.round(180 - intensity * 130)
                const b = Math.round(50 - intensity * 30)
                return (
                  <div key={i}
                    title={`Zone ${zone.zone_id}: ${(zone.methane_level ?? 0).toFixed(0)} mg/m²/d`}
                    className="aspect-square rounded-lg cursor-help transition-transform hover:scale-110"
                    style={{ background: `rgb(${r},${g},${b})` }} />
                )
              })}
            </div>
            <div className="flex items-center justify-between mt-2 text-xs text-carbon-400">
              <span>Low CH₄</span>
              <div className="flex-1 mx-2 h-1.5 rounded-full"
                style={{ background: 'linear-gradient(to right, #32b232, #f59e0b, #ef4444)' }} />
              <span>High CH₄</span>
            </div>
            <p className="text-xs text-carbon-400 text-center mt-1">
              {seg.zone_count ?? seg.zones?.length ?? 0} zones analyzed
            </p>
          </>
        ) : (
          <p className="text-xs text-carbon-400 text-center py-4">No segmentation data</p>
        )}
      </div>

      {/* ── 7. Impact Metrics ───────────────────────────────────────────── */}
      <div className="glass-card p-4">
        <p className="section-title text-base">{t('analytics.impact')}</p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <MetricCard label="CO₂e Reduced" value={impact.co2e_reduced_tonnes?.toFixed(2)} unit="t" icon={Leaf} color="earth" />
          <MetricCard label="Water Saved" value={impact.water_saved_m3_total ? (impact.water_saved_m3_total / 1000).toFixed(1) : '0'} unit="k m³" icon={Droplets} color="sky" />
          <div className="glass-card bg-gradient-to-br from-earth-50 to-earth-100/50 border border-earth-200/60 p-4 rounded-2xl">
            <div className="flex items-start justify-between mb-2">
              <p className="text-xs font-medium text-carbon-500 uppercase tracking-wider">Trees Equiv.</p>
              <TreeIcon className="w-4 h-4 text-earth-600" />
            </div>
            <div className="flex items-end gap-1.5">
              <span className="text-2xl font-display text-carbon-900">
                {impact.trees_equivalent?.toLocaleString() ?? '—'}
              </span>
            </div>
          </div>
          <MetricCard label="Car km Saved" value={impact.car_km_equivalent ? (impact.car_km_equivalent / 1000).toFixed(0) : '0'} unit="k km" icon={Car} color="amber" />
        </div>
      </div>

      {/* ── 8. Farm Profile ─────────────────────────────────────────────── */}
      <div className="glass-card p-4">
        <p className="section-title text-base flex items-center gap-2">
          <User className="w-4 h-4" /> {t('analytics.profile')}
        </p>
        <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
          {[
            ['Farmer',     profile.farmer_name],
            ['Location',   profile.farm_location],
            ['Area',       profile.farm_area_ha ? `${profile.farm_area_ha} ha` : '—'],
            ['Crop',       profile.crop_type],
            ['Season',     profile.season],
            ['Irrigation', profile.irrigation_source],
            ['Soil Type',  profile.soil_type],
            ['Program',    profile.program],
          ].map(([label, value]) => (
            <div key={label} className="flex flex-col py-1 border-b border-carbon-50">
              <span className="text-[10px] text-carbon-400 uppercase tracking-wider">{label}</span>
              <span className="text-carbon-800">{value || '—'}</span>
            </div>
          ))}
        </div>
      </div>

      {/* ── 9. Audit Trail ──────────────────────────────────────────────── */}
      <div className="glass-card p-4">
        <p className="section-title text-base flex items-center gap-2">
          <FileText className="w-4 h-4" /> {t('analytics.audit')}
        </p>
        <div className="space-y-2 max-h-52 overflow-y-auto">
          {!(audit.events?.length)
            ? <p className="text-xs text-carbon-400 text-center py-3">No audit events yet</p>
            : audit.events.map((ev, i) => (
              <div key={i} className="flex items-start gap-3 text-xs border-b border-carbon-100 py-2 last:border-0">
                <div className="w-2 h-2 rounded-full bg-earth-400 mt-1 shrink-0" />
                <div className="flex-1 min-w-0">
                  <span className="font-medium text-carbon-700">
                    {(ev.event_type || '').replace(/_/g, ' ')}
                  </span>
                  <span className="text-carbon-400 ml-2">{ev.description}</span>
                </div>
                <span className="font-mono text-carbon-400 shrink-0 text-[10px]">
                  {ev.created_at
                    ? new Date(ev.created_at * 1000).toLocaleTimeString()
                    : ''}
                </span>
              </div>
            ))
          }
        </div>
      </div>
    </motion.div>
  )
}
