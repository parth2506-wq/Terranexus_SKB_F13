import React from 'react'
import { motion } from 'framer-motion'
import { useTranslation } from 'react-i18next'
import { useApp } from '../../context/AppContext'
import StatusBadge from '../ui/StatusBadge'
import BarMetric from '../charts/BarMetric'
import { ShieldCheck, CheckCircle, XCircle, Copy } from 'lucide-react'
import clsx from 'clsx'

const LEVEL_CONFIG = {
  GOLD:   { bg: 'from-amber-50 to-yellow-50', border: 'border-amber-300', badge: 'text-amber-800 bg-amber-100', emoji: '🥇' },
  SILVER: { bg: 'from-carbon-50 to-slate-50', border: 'border-carbon-300', badge: 'text-carbon-700 bg-carbon-100', emoji: '🥈' },
  BRONZE: { bg: 'from-orange-50 to-amber-50', border: 'border-orange-300', badge: 'text-orange-700 bg-orange-100', emoji: '🥉' },
  FAILED: { bg: 'from-red-50 to-rose-50',    border: 'border-red-200',    badge: 'text-red-700 bg-red-100',    emoji: '❌' },
}

export default function VerificationPanel() {
  const { t } = useTranslation()
  const { panelData } = useApp()
  const data = panelData.verification
  if (!data) return null

  const v = data.verification || {}
  const level = v.level || 'FAILED'
  const cfg = LEVEL_CONFIG[level] || LEVEL_CONFIG.FAILED
  const integrity = v.data_integrity || {}
  const checks = v.checks || []
  const llm = data.llm_explanation || {}
  const awd = data.awd_summary || {}
  const ch4 = data.methane_summary || {}

  const copyFingerprint = () => {
    if (v.fingerprint) navigator.clipboard.writeText(v.fingerprint)
  }

  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="space-y-5">
      <div className="flex items-center gap-2">
        <ShieldCheck className="w-5 h-5 text-earth-600" />
        <h2 className="section-title mb-0">{t('verification.title')}</h2>
      </div>

      {/* Level hero card */}
      <div className={clsx('glass-card p-5 bg-gradient-to-br border-2', cfg.bg, cfg.border)}>
        <div className="flex items-start gap-4">
          <div className="text-5xl leading-none">{cfg.emoji}</div>
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-2">
              <span className={clsx('px-3 py-1 rounded-lg text-sm font-display', cfg.badge)}>{level} Verification</span>
              <StatusBadge type={v.status} label={v.status === 'verified' ? 'Verified' : 'Not Verified'} />
            </div>
            <p className="text-xs text-carbon-600 leading-relaxed">{v.explanation}</p>
            <div className="grid grid-cols-3 gap-3 mt-3">
              <div className="text-center bg-white/70 rounded-xl p-2">
                <p className="text-xs text-carbon-400">{t('verification.confidence')}</p>
                <p className="text-xl font-display text-carbon-900">{((v.confidence || 0) * 100).toFixed(0)}%</p>
              </div>
              <div className="text-center bg-white/70 rounded-xl p-2">
                <p className="text-xs text-carbon-400">Checks Passed</p>
                <p className="text-xl font-display text-carbon-900">{integrity.checks_passed}/{integrity.checks_total}</p>
              </div>
              <div className="text-center bg-white/70 rounded-xl p-2">
                <p className="text-xs text-carbon-400">Avg Score</p>
                <p className="text-xl font-display text-carbon-900">{((integrity.average_score || 0) * 100).toFixed(0)}%</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Check details */}
      <div className="glass-card p-4">
        <p className="text-sm font-medium text-carbon-700 mb-4">{t('verification.dataIntegrity')} — Check Results</p>
        <div className="space-y-3">
          {checks.map((check, i) => (
            <motion.div key={i} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.06 }}
              className="flex items-start gap-3 p-3 rounded-xl bg-carbon-50 hover:bg-carbon-100 transition-colors">
              {check.passed
                ? <CheckCircle className="w-4 h-4 text-earth-500 shrink-0 mt-0.5" />
                : <XCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
              }
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-xs font-medium text-carbon-700 capitalize">{check.name?.replace(/_/g, ' ')}</p>
                  <span className="text-xs font-mono text-carbon-500 shrink-0">{((check.score || 0) * 100).toFixed(0)}%</span>
                </div>
                <p className="text-[11px] text-carbon-400 mt-0.5 truncate">{check.detail}</p>
                <div className="mt-1.5 h-1 bg-carbon-200 rounded-full overflow-hidden">
                  <div className={`h-full rounded-full ${check.passed ? 'bg-earth-500' : 'bg-red-400'}`} style={{ width: `${(check.score || 0) * 100}%` }} />
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>

      {/* AWD + methane summary */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="glass-card p-4">
          <p className="text-sm font-medium text-carbon-700 mb-3">AWD Evidence</p>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between"><span className="text-carbon-500">Status</span><StatusBadge type={awd.awd_status} /></div>
            <div className="flex justify-between"><span className="text-carbon-500">Cycles</span><strong className="text-carbon-800">{awd.cycles}</strong></div>
            <div className="flex justify-between"><span className="text-carbon-500">Confidence</span><strong className="text-carbon-800">{((awd.confidence || 0) * 100).toFixed(1)}%</strong></div>
          </div>
        </div>
        <div className="glass-card p-4">
          <p className="text-sm font-medium text-carbon-700 mb-3">Methane Evidence</p>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between"><span className="text-carbon-500">Mean Flux</span><strong className="text-carbon-800">{ch4.mean_daily_flux?.toFixed(1)} mg/m²/d</strong></div>
            <div className="flex justify-between"><span className="text-carbon-500">Reduction</span><strong className="text-earth-700">{ch4.total_reduction_pct?.toFixed(1)}%</strong></div>
            <div className="flex justify-between"><span className="text-carbon-500">Season Total</span><strong className="text-carbon-800">{ch4.season_total_kg_ha?.toFixed(1)} kg/ha</strong></div>
          </div>
        </div>
      </div>

      {/* LLM explanation */}
      {llm.explanation && (
        <div className="glass-card p-4 border-l-4 border-earth-400">
          <p className="text-xs font-medium text-carbon-500 uppercase tracking-wider mb-2">AI Explanation</p>
          <p className="text-sm text-carbon-700 leading-relaxed" dangerouslySetInnerHTML={{ __html: llm.explanation.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') }} />
          <p className="text-[10px] text-carbon-400 mt-2">Source: {llm.source}</p>
        </div>
      )}

      {/* Fingerprint */}
      {v.fingerprint && (
        <div className="glass-card p-3 flex items-center justify-between gap-3">
          <div className="flex-1 min-w-0">
            <p className="text-xs text-carbon-400 mb-0.5">{t('verification.fingerprint')}</p>
            <p className="text-xs font-mono text-carbon-600 truncate">{v.fingerprint}</p>
          </div>
          <button onClick={copyFingerprint} className="btn-ghost py-1 px-2 text-xs flex items-center gap-1 shrink-0">
            <Copy className="w-3.5 h-3.5" /> Copy
          </button>
        </div>
      )}
    </motion.div>
  )
}
