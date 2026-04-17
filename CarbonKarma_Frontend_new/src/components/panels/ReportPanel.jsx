import React, { useState } from 'react'
import { motion } from 'framer-motion'
import { useTranslation } from 'react-i18next'
import { useApp } from '../../context/AppContext'
import { generateReport } from '../../services/api'
import { FileDown, FileText, CheckCircle, ExternalLink, Clock } from 'lucide-react'

export default function ReportPanel() {
  const { t } = useTranslation()
  const { location, farmId, panelData } = useApp()
  const [generating, setGenerating] = useState(false)
  const [reportData, setReportData] = useState(null)
  const [error, setError] = useState('')

  const handleGenerate = async () => {
    if (!location.lat) return
    setGenerating(true)
    setError('')
    try {
      const r = await generateReport(location.lat, location.lon, farmId, 12, location.geojson)
      if (r.data?.status === 'success') {
        setReportData(r.data)
      } else {
        setError(r.error || 'Report generation failed')
      }
    } catch (e) {
      setError(e.message)
    }
    setGenerating(false)
  }

  const verification = panelData.verification?.verification || {}
  const credits = panelData.credits || {}
  const farmScore = panelData.analytics?.farm_score || {}
  const rep = reportData?.report || {}

  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="space-y-5">
      <div className="flex items-center gap-2">
        <FileDown className="w-5 h-5 text-earth-600" />
        <h2 className="section-title mb-0">{t('report.title')}</h2>
      </div>

      {/* Summary cards */}
      {(verification.level || credits.credits_earned) && (
        <div className="grid grid-cols-3 gap-3">
          <div className="glass-card p-4 text-center">
            <p className="text-xs text-carbon-400">Verification Level</p>
            <p className="text-xl font-display text-earth-700">{verification.level || '—'}</p>
          </div>
          <div className="glass-card p-4 text-center">
            <p className="text-xs text-carbon-400">Credits Earned</p>
            <p className="text-xl font-display text-carbon-900">{(credits.credits_earned || 0).toFixed(4)}</p>
            <p className="text-[10px] font-mono text-carbon-400">tCO₂e</p>
          </div>
          <div className="glass-card p-4 text-center">
            <p className="text-xs text-carbon-400">Farm Score</p>
            <p className="text-xl font-display text-carbon-900">{farmScore.overall_score?.toFixed(0) || '—'}</p>
            <p className="text-[10px] font-mono text-carbon-400">{farmScore.grade ? `Grade ${farmScore.grade}` : ''}</p>
          </div>
        </div>
      )}

      {/* Generate button */}
      <div className="glass-card p-6 text-center">
        <div className="w-16 h-16 bg-earth-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
          <FileText className="w-8 h-8 text-earth-600" />
        </div>
        <h3 className="font-display text-lg text-carbon-800 mb-2">Full MRV Report</h3>
        <p className="text-sm text-carbon-500 mb-5 max-w-sm mx-auto">
          Generates a comprehensive PDF/text report including satellite data, AWD analysis, methane estimates, verification results, and carbon credits.
        </p>
        <motion.button
          whileTap={{ scale: 0.97 }}
          onClick={handleGenerate}
          disabled={generating || !location.lat}
          className="btn-primary px-8 py-3 text-base inline-flex items-center gap-2"
        >
          {generating
            ? <><div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" /> Generating...</>
            : <><FileDown className="w-5 h-5" /> {t('report.generate')}</>
          }
        </motion.button>
        {error && <p className="text-sm text-red-500 mt-3">{error}</p>}
      </div>

      {/* Report result */}
      {reportData && (
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="space-y-3">
          <div className="glass-card p-4 border-l-4 border-earth-500">
            <div className="flex items-center gap-2 mb-3">
              <CheckCircle className="w-5 h-5 text-earth-500" />
              <p className="font-medium text-carbon-800">Report Generated Successfully</p>
            </div>
            <div className="space-y-2 text-sm">
              {[
                ['Report ID', rep.report_id?.slice(0, 16) + '…'],
                ['Format', rep.format?.toUpperCase()],
                ['Summary', rep.summary],
                ['Generated', rep.generated_at ? new Date(rep.generated_at).toLocaleString() : ''],
                ['File', rep.file_name],
              ].map(([label, value]) => (
                <div key={label} className="flex gap-2">
                  <span className="text-carbon-400 w-24 shrink-0">{label}</span>
                  <span className="text-carbon-700 font-mono text-xs truncate">{value}</span>
                </div>
              ))}
            </div>
          </div>

          {rep.file_name && (
            <a
              href={(import.meta.env.VITE_API_URL ? import.meta.env.VITE_API_URL.replace(/\/$/, '') : 'http://127.0.0.1:5000') + `/report/download?path=${encodeURIComponent(rep.file_name)}`}
              target="_blank" rel="noopener noreferrer"
              className="btn-primary w-full flex items-center justify-center gap-2 py-3"
            >
              <ExternalLink className="w-4 h-4" /> {t('report.download')} ({rep.format?.toUpperCase()})
            </a>
          )}

          {/* Embedded verification data */}
          {reportData.verification && (
            <div className="glass-card p-4 bg-carbon-50">
              <p className="text-xs font-medium text-carbon-500 uppercase tracking-wider mb-2">Verification Summary</p>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div><span className="text-carbon-400">Level: </span><strong>{reportData.verification.level}</strong></div>
                <div><span className="text-carbon-400">Confidence: </span><strong>{((reportData.verification.confidence || 0) * 100).toFixed(0)}%</strong></div>
                <div><span className="text-carbon-400">Credits: </span><strong>{(reportData.credits_earned || 0).toFixed(4)} tCO₂e</strong></div>
                <div><span className="text-carbon-400">Score: </span><strong>{reportData.farm_score?.overall_score?.toFixed(1)}/100</strong></div>
              </div>
            </div>
          )}
        </motion.div>
      )}

      {/* Report list hint */}
      <div className="glass-card p-3 flex items-center gap-2 text-xs text-carbon-500">
        <Clock className="w-4 h-4 text-carbon-400 shrink-0" />
        <span>Reports are stored server-side. Use <code className="bg-carbon-100 px-1 py-0.5 rounded font-mono text-[10px]">GET /api/report/list?farm_id={farmId}</code> to list all reports for this farm.</span>
      </div>
    </motion.div>
  )
}
