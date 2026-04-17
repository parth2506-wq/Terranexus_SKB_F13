import React from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useTranslation } from 'react-i18next'
import { useApp } from '../../context/AppContext'
import clsx from 'clsx'
import {
  LayoutDashboard, Satellite, Layers, Droplets, Flame,
  ShieldCheck, Coins, BarChart3, Bot, FileDown, Globe, Leaf
} from 'lucide-react'

const tabs = [
  { id: 'dashboard',     icon: LayoutDashboard, key: 'dashboard' },
  { id: 'satellite',     icon: Satellite,       key: 'satellite' },
  { id: 'fusion',        icon: Layers,          key: 'fusion' },
  { id: 'awd',           icon: Droplets,        key: 'awd' },
  { id: 'methane',       icon: Flame,           key: 'methane' },
  { id: 'verification',  icon: ShieldCheck,     key: 'verification' },
  { id: 'credits',       icon: Coins,           key: 'credits' },
  { id: 'analytics',     icon: BarChart3,       key: 'analytics' },
  { id: 'ai',            icon: Bot,             key: 'ai' },
  { id: 'report',        icon: FileDown,        key: 'report' },
]

const LANGS = [
  { code: 'en', label: 'EN' },
  { code: 'hi', label: 'हि' },
  { code: 'mr', label: 'म' },
]

export default function Sidebar() {
  const { t, i18n } = useTranslation()
  const { activeTab, setActiveTab, hasRun, dataSource } = useApp()

  return (
    <motion.aside
      initial={{ x: -80, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      className="flex flex-col w-[72px] bg-white/90 backdrop-blur-md border-r border-carbon-200/60 shadow-sm z-20 shrink-0"
    >
      {/* Logo */}
      <div className="flex items-center justify-center h-16 border-b border-carbon-100">
        <div className="w-9 h-9 bg-gradient-to-br from-earth-500 to-earth-700 rounded-xl flex items-center justify-center shadow-sm">
          <Leaf className="w-5 h-5 text-white" />
        </div>
      </div>

      {/* Nav items */}
      <nav className="flex-1 overflow-y-auto py-3 flex flex-col gap-1 px-2">
        {tabs.map(({ id, icon: Icon, key }) => {
          const isActive = activeTab === id
          const isDisabled = id !== 'dashboard' && !hasRun
          return (
            <button
              key={id}
              onClick={() => !isDisabled && setActiveTab(id)}
              title={t(`nav.${key}`)}
              disabled={isDisabled}
              className={clsx(
                'relative group flex flex-col items-center justify-center w-full py-2.5 rounded-xl transition-all duration-200',
                isActive
                  ? 'bg-earth-600 text-white shadow-sm'
                  : isDisabled
                    ? 'text-carbon-300 cursor-not-allowed'
                    : 'text-carbon-500 hover:text-carbon-800 hover:bg-earth-50'
              )}
            >
              <Icon className="w-5 h-5" />
              <span className="text-[9px] mt-0.5 font-medium leading-none tracking-wide">
                {t(`nav.${key}`).split(' ')[0]}
              </span>

              {/* Active indicator */}
              {isActive && (
                <motion.div
                  layoutId="activeTab"
                  className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-6 bg-earth-300 rounded-r-full"
                />
              )}

              {/* Tooltip */}
              <div className="absolute left-full ml-2 px-2.5 py-1.5 bg-carbon-900 text-white text-xs rounded-lg
                             opacity-0 group-hover:opacity-100 pointer-events-none whitespace-nowrap z-50
                             transition-opacity duration-150 shadow-lg">
                {t(`nav.${key}`)}
                {isDisabled && <span className="ml-1 text-carbon-400">(run analysis first)</span>}
              </div>
            </button>
          )
        })}
      </nav>

      {/* Data source indicator */}
      {dataSource && (
        <div className="px-2 py-1.5">
          <div className={clsx(
            'w-full flex items-center justify-center rounded-lg py-1 text-[8px] font-mono font-medium',
            dataSource === 'live' ? 'bg-earth-100 text-earth-700' :
            dataSource === 'cached' ? 'bg-sky-100 text-sky-700' :
            'bg-amber-100 text-amber-700'
          )}>
            {dataSource === 'live' ? '● LIVE' : dataSource === 'cached' ? '◉ CACHE' : '◎ DEMO'}
          </div>
        </div>
      )}

      {/* Language switcher */}
      <div className="border-t border-carbon-100 px-2 py-3 flex flex-col gap-1">
        <div className="flex items-center justify-center mb-1">
          <Globe className="w-3.5 h-3.5 text-carbon-400" />
        </div>
        {LANGS.map(({ code, label }) => (
          <button
            key={code}
            onClick={() => i18n.changeLanguage(code)}
            className={clsx(
              'w-full py-1 rounded-lg text-xs font-medium transition-all',
              i18n.language === code
                ? 'bg-earth-100 text-earth-700'
                : 'text-carbon-400 hover:text-carbon-700 hover:bg-carbon-50'
            )}
          >
            {label}
          </button>
        ))}
      </div>
    </motion.aside>
  )
}
