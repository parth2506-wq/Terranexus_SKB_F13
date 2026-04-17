import React, { useState } from 'react'
import { motion } from 'framer-motion'
import { useTranslation } from 'react-i18next'
import { useApp } from '../../context/AppContext'
import { retireCredits } from '../../services/api'
import MetricCard from '../ui/MetricCard'
import { Coins, ArrowDownCircle, Leaf, Car, Droplets } from 'lucide-react'
import clsx from 'clsx'

// Inline tree SVG — Trees doesn't exist in lucide-react 0.383
const TreeIcon = ({ className }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 22V13" /><path d="M9 7l3-4 3 4H9z" />
    <path d="M7 12l5-7 5 7H7z" /><path d="M5 17l7-10 7 10H5z" />
  </svg>
)

function ImpactBadge({ icon: Icon, value, label, border, bg, textColor }) {
  return (
    <div className={clsx('flex flex-col items-center text-center rounded-2xl p-4 border', bg, border)}>
      <Icon className={clsx('w-6 h-6 mb-2 opacity-70', textColor)} />
      <p className={clsx('text-xl font-display text-carbon-900')}>{value ?? '—'}</p>
      <p className="text-xs text-carbon-500 mt-0.5">{label}</p>
    </div>
  )
}

export default function CreditsPanel() {
  const { t } = useTranslation()
  const { panelData, farmId } = useApp()
  const [retiring, setRetiring] = useState(false)
  const [retireAmount, setRetireAmount] = useState('')
  const [retireMsg, setRetireMsg] = useState('')
  const data = panelData.credits

  if (!data) return (
    <div className="flex items-center justify-center h-48 text-carbon-400 text-sm">
      No credits data. Run analysis first.
    </div>
  )

  const calc   = data.calculation || {}
  const impact = data.impact_metrics || {}
  const wallet = data.wallet || {}
  const txs    = Array.isArray(wallet.transactions) ? wallet.transactions : []

  const handleRetire = async () => {
    const amt = parseFloat(retireAmount)
    if (!amt || amt <= 0) { setRetireMsg('Enter a valid positive amount'); return }
    setRetiring(true)
    setRetireMsg('')
    try {
      const result = await retireCredits(farmId, amt, 'certificate')
      const d = result?.data
      if (d?.status === 'success' || d?.retired) {
        setRetireMsg(`✅ Retired ${amt.toFixed(4)} credits. New balance: ${(d?.total_balance ?? 0).toFixed(4)}`)
        setRetireAmount('')
      } else {
        setRetireMsg(`❌ ${d?.error || 'Retirement failed'}`)
      }
    } catch (e) {
      setRetireMsg('❌ Retirement failed: ' + e.message)
    }
    setRetiring(false)
  }

  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="space-y-5">
      <div className="flex items-center gap-2">
        <Coins className="w-5 h-5 text-amber-600" />
        <h2 className="section-title mb-0">{t('credits.title')}</h2>
      </div>

      {/* ── Wallet hero ──────────────────────────────────────────────── */}
      <div className="glass-card p-5 bg-gradient-to-br from-earth-50 to-amber-50/40 border border-earth-200/60">
        <div className="flex items-start justify-between mb-4 flex-wrap gap-3">
          <div>
            <p className="text-xs text-carbon-500 uppercase tracking-wider">{t('credits.balance')}</p>
            <p className="text-4xl font-display text-earth-700">
              {(data.total_balance ?? 0).toFixed(4)}
            </p>
            <p className="text-sm font-mono text-carbon-400">{t('credits.unit')}</p>
          </div>
          <div className="text-right">
            <p className="text-xs text-carbon-500">{t('credits.earned')} this season</p>
            <p className="text-2xl font-display text-earth-600">
              {(data.credits_earned ?? 0).toFixed(4)}
            </p>
            <p className="text-sm font-mono text-carbon-400">
              ≈ ${(data.usd_value ?? 0).toFixed(2)} USD
            </p>
          </div>
        </div>
        <div className="grid grid-cols-3 gap-3">
          {[
            ['Reduction', `${(calc.reduction_pct ?? 0).toFixed(1)}%`],
            ['CO₂e Reduced', `${(calc.reduction_co2e_t ?? 0).toFixed(3)}t`],
            ['Level × Mult', `${data.verification_level || '—'} × ${calc.verification_multiplier ?? 0}`],
          ].map(([label, value]) => (
            <div key={label} className="bg-white/60 rounded-xl p-2 text-center">
              <p className="text-[10px] text-carbon-400">{label}</p>
              <p className="text-sm font-display text-carbon-900">{value}</p>
            </div>
          ))}
        </div>
      </div>

      {/* ── Calculation breakdown ────────────────────────────────────── */}
      <div className="glass-card p-4">
        <p className="text-sm font-medium text-carbon-700 mb-3">Credit Calculation</p>
        <div className="space-y-0">
          {[
            ['Area',              `${calc.area_ha ?? '—'} ha`],
            ['Season',            `${calc.season_days ?? '—'} days`],
            ['Baseline Emissions',`${(calc.baseline_kg_ha ?? 0).toFixed(1)} kg CH₄/ha`],
            ['Actual Emissions',  `${(calc.actual_kg_ha ?? 0).toFixed(1)} kg CH₄/ha`],
            ['Reduction',         `${(calc.reduction_kg_ha ?? 0).toFixed(1)} kg CH₄/ha (${(calc.reduction_pct ?? 0).toFixed(1)}%)`],
            ['Total Reduction',   `${(calc.total_reduction_t_ch4 ?? 0).toFixed(4)} t CH₄`],
            ['GWP-100 (AR6)',     `${calc.gwp_100_ch4 ?? 27.9} × CO₂e`],
            ['Gross CO₂e',        `${(calc.reduction_co2e_t ?? 0).toFixed(4)} t CO₂e`],
            ['Multiplier',        `${calc.verification_multiplier ?? 0} (${calc.verification_level || '—'})`],
            ['Credits Earned',    `${(calc.credits_earned ?? 0).toFixed(4)} tCO₂e`],
            ['Price/Credit',      `$${calc.price_per_credit_usd ?? 15}`],
            ['USD Value',         `$${(calc.usd_value ?? 0).toFixed(2)}`],
          ].map(([label, value], i) => (
            <div key={label}
              className={clsx(
                'flex justify-between py-2 text-xs',
                i < 9 ? 'border-b border-carbon-100' : 'font-medium text-sm bg-earth-50 rounded-lg px-2 mt-1'
              )}>
              <span className="text-carbon-500">{label}</span>
              <span className="font-mono text-carbon-800">{value}</span>
            </div>
          ))}
        </div>
      </div>

      {/* ── Impact metrics ───────────────────────────────────────────── */}
      <div>
        <p className="section-title text-base">Environmental Impact</p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <ImpactBadge
            icon={Leaf}
            value={`${(impact.co2e_reduced_tonnes ?? 0).toFixed(2)}t`}
            label="CO₂e Reduced"
            bg="bg-earth-50" border="border-earth-200" textColor="text-earth-600"
          />
          <ImpactBadge
            icon={Droplets}
            value={`${((impact.water_saved_m3_total ?? 0) / 1000).toFixed(1)}k m³`}
            label="Water Saved"
            bg="bg-sky-50" border="border-sky-200" textColor="text-sky-600"
          />
          {/* Trees with inline SVG */}
          <div className="flex flex-col items-center text-center rounded-2xl p-4 border bg-earth-50 border-earth-200">
            <TreeIcon className="w-6 h-6 mb-2 text-earth-600 opacity-70" />
            <p className="text-xl font-display text-carbon-900">
              {(impact.trees_equivalent ?? 0).toLocaleString()}
            </p>
            <p className="text-xs text-carbon-500 mt-0.5">Trees Equivalent</p>
          </div>
          <ImpactBadge
            icon={Car}
            value={`${((impact.car_km_equivalent ?? 0) / 1000).toFixed(0)}k km`}
            label="Car km Avoided"
            bg="bg-amber-50" border="border-amber-200" textColor="text-amber-600"
          />
        </div>
      </div>

      {/* ── Retire credits ───────────────────────────────────────────── */}
      <div className="glass-card p-4">
        <p className="text-sm font-medium text-carbon-700 mb-3 flex items-center gap-2">
          <ArrowDownCircle className="w-4 h-4 text-red-400" /> {t('credits.retire')}
        </p>
        <div className="flex gap-2">
          <input
            type="number"
            placeholder="0.0000"
            value={retireAmount}
            onChange={e => setRetireAmount(e.target.value)}
            className="input-field flex-1 text-sm"
            min="0" step="0.0001"
          />
          <button
            onClick={handleRetire}
            disabled={retiring}
            className="btn-secondary text-sm px-4 flex items-center gap-1.5 shrink-0"
          >
            {retiring
              ? <div className="w-4 h-4 border-2 border-earth-500 border-t-transparent rounded-full animate-spin" />
              : <ArrowDownCircle className="w-4 h-4" />}
            Retire
          </button>
        </div>
        {retireMsg && (
          <p className={`text-xs mt-2 ${retireMsg.startsWith('✅') ? 'text-earth-600' : 'text-red-500'}`}>
            {retireMsg}
          </p>
        )}
      </div>

      {/* ── Transaction history ──────────────────────────────────────── */}
      {txs.length > 0 && (
        <div className="glass-card p-4">
          <p className="text-sm font-medium text-carbon-700 mb-3">{t('credits.history')}</p>
          <div className="space-y-0">
            {txs.map((tx, i) => (
              <div key={i} className="flex items-center justify-between text-xs border-b border-carbon-100 py-2 last:border-0">
                <span className="font-mono text-carbon-400">{String(tx.tx_id || '').slice(0, 12)}…</span>
                <span className={`font-medium ${tx.tx_type === 'EARN' ? 'text-earth-600' : 'text-red-500'}`}>
                  {tx.tx_type === 'EARN' ? '+' : '-'}{Math.abs(tx.amount ?? 0).toFixed(4)} tCO₂e
                </span>
                <span className="text-carbon-500">{tx.tx_type}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </motion.div>
  )
}
