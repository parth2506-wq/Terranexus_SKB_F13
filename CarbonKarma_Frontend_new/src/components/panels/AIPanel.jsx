import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useTranslation } from 'react-i18next'
import { useApp } from '../../context/AppContext'
import {
  fetchLLMInsights, fetchLLMExplain,
  fetchLLMAlerts, fetchLLMCertificate
} from '../../services/api'
import { Bot, Send, Lightbulb, AlertTriangle, Award, ChevronDown, ChevronUp } from 'lucide-react'
import clsx from 'clsx'

function Accordion({ title, icon: Icon, children, defaultOpen = false, color = 'earth' }) {
  const [open, setOpen] = useState(defaultOpen)
  const bgMap = { earth: 'bg-earth-50', sky: 'bg-sky-50', amber: 'bg-amber-50' }
  const textMap = { earth: 'text-earth-600', sky: 'text-sky-600', amber: 'text-amber-600' }
  return (
    <div className="glass-card overflow-hidden">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center gap-3 p-4 hover:bg-carbon-50 transition-colors"
      >
        <div className={clsx('w-7 h-7 rounded-lg flex items-center justify-center', bgMap[color])}>
          <Icon className={clsx('w-4 h-4', textMap[color])} />
        </div>
        <span className="flex-1 text-sm font-medium text-carbon-700 text-left">{title}</span>
        {open
          ? <ChevronUp className="w-4 h-4 text-carbon-400" />
          : <ChevronDown className="w-4 h-4 text-carbon-400" />}
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0 }} animate={{ height: 'auto' }} exit={{ height: 0 }}
            className="overflow-hidden"
          >
            <div className="px-4 pb-4">{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

function AIResponse({ text, source, loading }) {
  if (loading) return (
    <div className="flex items-center gap-2 text-xs text-carbon-400 py-3">
      <div className="w-4 h-4 border-2 border-earth-400 border-t-transparent rounded-full animate-spin" />
      Generating response…
    </div>
  )
  if (!text) return null
  return (
    <div className="bg-earth-50 border border-earth-200 rounded-xl p-4">
      <p
        className="text-sm text-carbon-700 leading-relaxed whitespace-pre-wrap"
        dangerouslySetInnerHTML={{
          __html: String(text).replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        }}
      />
      {source && (
        <p className="text-[10px] font-mono text-carbon-400 mt-2">Source: {source}</p>
      )}
    </div>
  )
}

export default function AIPanel() {
  const { t } = useTranslation()
  const { location, farmId } = useApp()

  const [query, setQuery] = useState('')
  const [queryResult, setQueryResult] = useState(null)
  const [queryLoading, setQueryLoading] = useState(false)

  const [explainResult, setExplainResult] = useState(null)
  const [explainLoading, setExplainLoading] = useState(false)

  const [alertResult, setAlertResult] = useState(null)
  const [alertLoading, setAlertLoading] = useState(false)

  const [certResult, setCertResult] = useState(null)
  const [certLoading, setCertLoading] = useState(false)

  const noLocation = !location.lat
  const geo = location.geojson || null

  const handleQuery = async () => {
    if (!query.trim() || noLocation) return
    setQueryLoading(true)
    try {
      const r = await fetchLLMInsights(location.lat, location.lon, query, farmId, 10, geo)
      setQueryResult(r?.data ?? null)
    } catch { /* fallback handles it */ }
    setQueryLoading(false)
  }

  const handleExplain = async () => {
    if (noLocation) return
    setExplainLoading(true)
    try {
      const r = await fetchLLMExplain(location.lat, location.lon, farmId, 12, geo)
      setExplainResult(r?.data?.llm_explanation ?? null)
    } catch { /* fallback */ }
    setExplainLoading(false)
  }

  const handleAlerts = async () => {
    if (noLocation) return
    setAlertLoading(true)
    try {
      const r = await fetchLLMAlerts(location.lat, location.lon, farmId, 10, geo)
      setAlertResult(r?.data?.llm_narratives ?? null)
    } catch { /* fallback */ }
    setAlertLoading(false)
  }

  const handleCertificate = async () => {
    if (noLocation) return
    setCertLoading(true)
    try {
      const r = await fetchLLMCertificate(location.lat, location.lon, farmId, 12, geo)
      setCertResult(r?.data ?? null)
    } catch { /* fallback */ }
    setCertLoading(false)
  }

  // ── Safely extract cert text ─────────────────────────────────────────
  // Backend returns: { certificate_text: {certificate_text: string, source: string}, ... }
  // OR:              { certificate_text: string, ... }
  const extractCertText = (certData) => {
    if (!certData) return null
    const raw = certData.certificate_text
    if (!raw) return null
    if (typeof raw === 'string') return { text: raw, source: certData.source || 'template' }
    if (typeof raw === 'object' && raw.certificate_text) {
      return { text: raw.certificate_text, source: raw.source || 'template' }
    }
    return null
  }

  const certText = extractCertText(certResult)
  const queryAnswer = queryResult?.insight?.answer
    || queryResult?.insight
    || queryResult?.answer
    || null
  const querySource = queryResult?.source
    || queryResult?.insight?.source
    || 'template'

  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
      <div className="flex items-center gap-2">
        <Bot className="w-5 h-5 text-earth-600" />
        <h2 className="section-title mb-0">{t('ai.title')}</h2>
        <span className="text-xs text-carbon-400 bg-carbon-100 px-2 py-0.5 rounded-full font-mono">
          OpenRouter LLM
        </span>
      </div>

      {noLocation && (
        <div className="glass-card p-4 text-sm text-amber-700 bg-amber-50 border border-amber-200">
          ⚠️ Run an analysis first to enable AI insights.
        </div>
      )}

      {/* ── Free-form query ───────────────────────────────────────────── */}
      <div className="glass-card p-4">
        <p className="text-sm font-medium text-carbon-700 mb-3">Ask About Your Farm</p>
        <div className="flex gap-2">
          <input
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleQuery()}
            placeholder={t('ai.query')}
            className="input-field flex-1 text-sm"
            disabled={noLocation}
          />
          <button
            onClick={handleQuery}
            disabled={queryLoading || !query.trim() || noLocation}
            className="btn-primary px-4 flex items-center gap-1.5 shrink-0"
          >
            <Send className="w-4 h-4" />{t('ai.send')}
          </button>
        </div>
        <div className="mt-3">
          <AIResponse
            text={typeof queryAnswer === 'string' ? queryAnswer : null}
            source={querySource}
            loading={queryLoading}
          />
        </div>
        {queryResult?.context_used && (
          <div className="mt-2 grid grid-cols-2 md:grid-cols-3 gap-2">
            {Object.entries(queryResult.context_used).slice(0, 6).map(([k, v]) => (
              <div key={k} className="bg-carbon-50 rounded-lg px-2 py-1 text-xs">
                <span className="text-carbon-400">{k.replace(/_/g, ' ')}: </span>
                <span className="text-carbon-700 font-mono">{String(v).slice(0, 20)}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── Verification explanation ──────────────────────────────────── */}
      <Accordion title={t('ai.explanation')} icon={Lightbulb} color="earth" defaultOpen>
        <div className="space-y-3">
          <button
            onClick={handleExplain}
            disabled={explainLoading || noLocation}
            className="btn-secondary text-xs py-2 px-4"
          >
            {explainLoading ? 'Generating…' : 'Generate Explanation'}
          </button>
          <AIResponse
            text={explainResult?.explanation}
            source={explainResult?.source}
            loading={explainLoading}
          />
        </div>
      </Accordion>

      {/* ── Alert narratives ──────────────────────────────────────────── */}
      <Accordion title={t('ai.alerts')} icon={AlertTriangle} color="amber">
        <div className="space-y-3">
          <button
            onClick={handleAlerts}
            disabled={alertLoading || noLocation}
            className="btn-secondary text-xs py-2 px-4"
          >
            {alertLoading ? 'Analyzing…' : 'Analyze Alerts'}
          </button>
          {alertResult && (
            <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
              <p className="text-sm text-carbon-700 leading-relaxed">
                {alertResult.context || alertResult.narrative || JSON.stringify(alertResult)}
              </p>
              {alertResult.source && (
                <p className="text-[10px] font-mono text-carbon-400 mt-2">
                  Source: {alertResult.source}
                </p>
              )}
            </div>
          )}
          {alertLoading && <AIResponse loading />}
        </div>
      </Accordion>

      {/* ── Certificate ───────────────────────────────────────────────── */}
      <Accordion title={t('ai.certificate')} icon={Award} color="sky">
        <div className="space-y-3">
          <button
            onClick={handleCertificate}
            disabled={certLoading || noLocation}
            className="btn-secondary text-xs py-2 px-4"
          >
            {certLoading ? 'Generating…' : 'Generate Certificate'}
          </button>

          {certLoading && <AIResponse loading />}

          {certText && (
            <div className="space-y-2">
              <pre className="bg-earth-50 border border-earth-200 rounded-xl p-4 text-xs text-carbon-700 whitespace-pre-wrap font-mono leading-relaxed overflow-x-auto">
                {certText.text}
              </pre>
              {certResult?.fingerprint && (
                <p className="text-[10px] font-mono text-carbon-400">
                  🔐 Fingerprint: {String(certResult.fingerprint).slice(0, 32)}…
                </p>
              )}
              {certResult?.verification_level && (
                <div className="flex gap-4 text-xs">
                  <span className="text-carbon-500">
                    Level: <strong className="text-carbon-800">{certResult.verification_level}</strong>
                  </span>
                  <span className="text-carbon-500">
                    Credits: <strong className="text-earth-700">
                      {(certResult.credits_earned ?? 0).toFixed(4)} tCO₂e
                    </strong>
                  </span>
                  <span className="text-carbon-400">Source: {certText.source}</span>
                </div>
              )}
            </div>
          )}

          {!certLoading && !certText && certResult && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-3 text-xs text-red-600">
              Certificate generated but text format unexpected. Raw: {JSON.stringify(certResult).slice(0, 200)}
            </div>
          )}
        </div>
      </Accordion>
    </motion.div>
  )
}
