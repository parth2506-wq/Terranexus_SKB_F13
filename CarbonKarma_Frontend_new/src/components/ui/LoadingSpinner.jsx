import React from 'react'
import { motion } from 'framer-motion'

export default function LoadingSpinner({ size = 'md', text, className = '' }) {
  const sizes = { sm: 'w-4 h-4', md: 'w-8 h-8', lg: 'w-12 h-12' }
  return (
    <div className={`flex flex-col items-center justify-center gap-3 ${className}`}>
      <motion.div
        className={`${sizes[size]} border-3 border-earth-200 border-t-earth-600 rounded-full`}
        style={{ borderWidth: 3 }}
        animate={{ rotate: 360 }}
        transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
      />
      {text && <p className="text-sm text-carbon-500 font-body">{text}</p>}
    </div>
  )
}

export function SkeletonCard({ className = '' }) {
  return (
    <div className={`glass-card p-4 animate-pulse ${className}`}>
      <div className="h-4 bg-carbon-200 rounded w-1/3 mb-3" />
      <div className="h-8 bg-carbon-100 rounded w-2/3 mb-2" />
      <div className="h-3 bg-carbon-100 rounded w-1/2" />
    </div>
  )
}
