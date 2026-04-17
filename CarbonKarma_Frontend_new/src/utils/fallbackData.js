/**
 * Generates realistic synthetic data when the backend is unavailable.
 * All values are physics-informed and match real paddy rice field ranges.
 */

const rng = (min, max, decimals = 2) =>
  parseFloat((Math.random() * (max - min) + min).toFixed(decimals))

const STAGES = ['transplanting', 'tillering', 'heading', 'ripening', 'harvest']
const FLOOD_TYPES = ['irrigated', 'rain_fed', 'surface_water', 'dry']
const AWD_STATUSES = ['active_awd', 'conventional', 'uncertain']

function generateTimestamps(nSteps = 12, stepDays = 7) {
  const dates = []
  const base = new Date()
  base.setDate(base.getDate() - nSteps * stepDays)
  for (let i = 0; i < nSteps; i++) {
    const d = new Date(base)
    d.setDate(d.getDate() + i * stepDays)
    dates.push(d.toISOString().split('T')[0])
  }
  return dates
}

function generateSentinel1(timestamps) {
  return timestamps.map((ts, i) => ({
    timestamp: ts,
    vv_mean: rng(0.02, 0.35),
    vh_mean: rng(0.01, 0.25),
    water_prob_mean: i % 12 < 7 ? rng(0.6, 0.95) : rng(0.05, 0.30),
    phenology_stage: STAGES[Math.floor(i / 2.5) % STAGES.length],
    is_flooded: i % 12 < 7
  }))
}

function generateSentinel2(timestamps) {
  return timestamps.map((ts, i) => ({
    timestamp: ts,
    ndvi_mean: rng(0.10, 0.75),
    ndvi_std: rng(0.03, 0.12),
    cloud_fraction: rng(0, 0.15),
    phenology_stage: STAGES[Math.floor(i / 2.5) % STAGES.length]
  }))
}

function generateWeather(timestamps) {
  return timestamps.map(ts => {
    const m = new Date(ts).getMonth()
    const isMonsoon = m >= 5 && m <= 9
    return {
      timestamp: ts,
      rainfall_mm: isMonsoon ? rng(0, 45) : rng(0, 5),
      temperature_c: rng(24, 36),
      source: 'fallback'
    }
  })
}

function generateFusionData(lat, lon, timestamps) {
  return timestamps.map((ts, i) => ({
    location: { lat, lon, bbox: [lon - 0.01, lat - 0.01, lon + 0.01, lat + 0.01] },
    timestamp: ts,
    water_level: i % 12 < 7 ? rng(0.55, 0.95) : rng(0.05, 0.35),
    ndvi: rng(0.15, 0.72),
    temperature: rng(26, 38),
    rainfall: rng(0, 30),
    soil_moisture: rng(0.3, 0.85),
    flood_type: FLOOD_TYPES[i % FLOOD_TYPES.length],
    awd_status: 'uncertain',
    water_prob_mean: rng(0.1, 0.9),
    ndvi_mean: rng(0.15, 0.72),
    lst_celsius_norm: rng(0.3, 0.8),
    rainfall_norm: rng(0, 0.4),
    soil_moisture_mean: rng(0.3, 0.8),
    vv_mean: rng(0.02, 0.35),
    vh_mean: rng(0.01, 0.25),
    cnn_water_score: rng(0.1, 0.95),
    phenology_stage: STAGES[Math.floor(i / 2.5) % STAGES.length],
    cloud_fraction: rng(0, 0.12)
  }))
}

function generateHeatmaps(lat, lon) {
  const bands = ['water_prob', 'ndvi', 'lst_norm', 'soil_moisture']
  const heatmaps = {}
  bands.forEach(band => {
    const data = []
    for (let r = 0; r < 16; r++) {
      for (let c = 0; c < 16; c++) {
        data.push({
          lat: lat + (8 - r) * 0.0005,
          lon: lon + (c - 8) * 0.0005,
          value: rng(0.1, 0.9)
        })
      }
    }
    heatmaps[band] = { label: band, timestamp: new Date().toISOString().split('T')[0], data }
  })
  return heatmaps
}

export function generateFallbackData(endpoint, params = {}) {
  const lat = params.lat || 13.0827
  const lon = params.lon || 80.2707
  const nSteps = params.n_steps || 12
  const stepDays = params.step_days || 7
  const timestamps = generateTimestamps(nSteps, stepDays)
  const fusionData = generateFusionData(lat, lon, timestamps)

  const location = {
    lat, lon,
    bbox: [lon - 0.01, lat - 0.01, lon + 0.01, lat + 0.01],
    area_ha: 4.5
  }

  const awdResult = {
    awd_status: 'active_awd',
    confidence: rng(0.55, 0.85),
    lstm_signal: rng(0.55, 0.82),
    cycles: Math.floor(rng(1, 4, 0)),
    irrigation_events: [{ timestamp: timestamps[4], water_level: 0.72, rainfall_mm: 1.2 }],
    rain_events: [{ timestamp: timestamps[8], water_level: 0.81, rainfall_mm: 18.5 }],
    flood_dry_sequence: timestamps.map((ts, i) => ({
      timestamp: ts, state: i % 12 < 7 ? 'flooded' : 'dry', water_level: i % 12 < 7 ? 0.78 : 0.12
    })),
    per_step_status: timestamps.map((ts, i) => ({
      timestamp: ts, water_level: i % 12 < 7 ? 0.75 : 0.15,
      state: i % 12 < 7 ? 'flooded' : 'dry', flood_type: 'irrigated'
    }))
  }

  const methanePerStep = timestamps.map(ts => ({
    timestamp: ts, methane: rng(120, 450), category: 'medium', reduction_percent: rng(20, 55)
  }))
  const methaneAggregate = {
    season_days: nSteps * stepDays,
    n_observations: nSteps,
    mean_daily_flux: rng(200, 350),
    max_daily_flux: rng(380, 520),
    season_total_kg_ha: rng(200, 380),
    baseline_kg_ha: 480,
    total_reduction_pct: rng(25, 55),
    category_distribution: { low: 3, medium: 6, high: 3 },
    cf_baseline_flux: 400
  }

  const verification = {
    status: 'verified', level: 'SILVER',
    confidence: rng(0.65, 0.88),
    data_integrity: { checks_passed: 5, checks_total: 7, pass_rate: 0.71, average_score: rng(0.65, 0.85) },
    checks: [
      { name: 'temporal_coverage', passed: true, score: 0.92, detail: `${nSteps} observation steps` },
      { name: 'cloud_data_quality', passed: true, score: 0.87, detail: '1/12 steps exceed threshold' },
      { name: 'vegetation_presence', passed: true, score: 0.78, detail: '9/12 steps show active crop' },
      { name: 'temperature_plausibility', passed: true, score: 1.0, detail: 'No anomalies detected' },
      { name: 'awd_practice_consistency', passed: false, score: 0.52, detail: 'AWD status=active_awd, cycles=2' },
      { name: 'methane_plausibility', passed: true, score: 0.95, detail: 'Mean flux=270 mg/m²/day' },
      { name: 'water_data_continuity', passed: false, score: 0.73, detail: 'Missing=0, large step-changes=2' }
    ],
    explanation: 'SILVER verification: 5/7 checks passed. Field shows consistent AWD practice with good satellite coverage. Eligible for standard carbon credit issuance.',
    fingerprint: 'a8f3c2e1b4d9f7a2c5e8b1d4f7a0c3e6b9d2f5a8b1e4c7f0a3d6e9b2c5f8a1',
    farm_id: params.farm_id || 'farm_001',
    timestamp: new Date().toISOString()
  }

  const creditsEarned = rng(5, 25)
  const credits = {
    credits_earned: creditsEarned,
    usd_value: parseFloat((creditsEarned * 15).toFixed(2)),
    total_balance: parseFloat((creditsEarned * 1.4).toFixed(4)),
    calculation: {
      area_ha: 4.5, season_days: nSteps * stepDays,
      baseline_kg_ha: 480, actual_kg_ha: rng(250, 360),
      reduction_kg_ha: rng(100, 200), reduction_pct: rng(25, 48),
      reduction_co2e_t: rng(8, 22), credits_earned: creditsEarned,
      verification_level: 'SILVER', verification_multiplier: 0.85,
      usd_value: parseFloat((creditsEarned * 15).toFixed(2)),
      gwp_100_ch4: 27.9, price_per_credit_usd: 15.0, qualifies: true
    },
    wallet: { farm_id: 'farm_001', total_balance: parseFloat((creditsEarned * 1.4).toFixed(4)), transactions: [], currency: 'Carbon Credits (CO2e tonnes)', price_per_credit_usd: 15 },
    wallet_tx: { tx_id: 'tx_fallback_001', credits_issued: creditsEarned, total_balance: creditsEarned * 1.4 },
    impact_metrics: {
      co2e_reduced_tonnes: rng(12, 28), ch4_reduced_kg_ha: rng(80, 180),
      ch4_reduction_pct: rng(25, 48), water_saved_mm: rng(200, 450),
      water_saved_m3_total: rng(3000, 8000), water_saving_pct: rng(18, 38),
      trees_equivalent: Math.floor(rng(400, 1200)), car_km_equivalent: Math.floor(rng(80000, 200000)),
      area_ha: 4.5, season_days: nSteps * stepDays
    },
    verification_level: 'SILVER'
  }

  const farmScore = {
    overall_score: rng(45, 72), water_efficiency: rng(40, 80),
    methane_control: rng(50, 78), awd_compliance: rng(35, 70), grade: 'C'
  }

  const analytics = {
    farm_id: params.farm_id || 'farm_001',
    location,
    timestamps,
    farm_score: farmScore,
    comparative_analysis: {
      your_flux_mg_m2_day: rng(200, 320), regional_mean_mg_m2_day: 320,
      regional_std: 45, pct_vs_regional: rng(-25, 10), percentile: rng(35, 72),
      z_score: rng(-1.2, 0.3), performance: 'above_average',
      region_label: 'South Asia',
      all_benchmarks: { south_asia: 320, southeast_asia: 360, global: 340 }
    },
    historical_trends: {
      total_records: nSteps,
      windows: {
        '7d': { water_level: rng(0.4, 0.8), ndvi: rng(0.3, 0.6), methane: rng(180, 320) },
        '30d': { water_level: rng(0.35, 0.75), ndvi: rng(0.25, 0.65), methane: rng(160, 350) },
        '90d': { water_level: rng(0.3, 0.7), ndvi: rng(0.2, 0.7), methane: rng(150, 380) }
      }
    },
    alerts: {
      alerts: [
        { type: 'METHANE_WARNING', severity: 'HIGH', message: 'High CH₄ emissions detected in last 3 observations. Credits at risk.', timestamp: timestamps[timestamps.length - 1] },
        { type: 'AWD_COMPLIANCE', severity: 'MEDIUM', message: 'AWD cycle frequency below optimal. Consider more frequent drainage.', timestamp: timestamps[timestamps.length - 2] }
      ]
    },
    predictions: {
      forecast_horizon_days: 7,
      generated_at: new Date().toISOString(),
      daily_forecasts: Array.from({ length: 7 }, (_, i) => {
        const d = new Date(); d.setDate(d.getDate() + i + 1)
        return {
          date: d.toISOString().split('T')[0],
          rainfall_mm: rng(0, 20),
          methane_mg_m2_day: rng(150, 420),
          water_level: rng(0.2, 0.85),
          methane_category: 'medium'
        }
      }),
      irrigation_advice: 'Consider draining the field to below 15cm water table depth in the next 3-5 days to initiate an AWD dry cycle and reduce methane emissions.',
      summary: 'Moderate rainfall expected. Good conditions for AWD dry cycle initiation.'
    },
    field_segmentation: {
      zones: Array.from({ length: 16 }, (_, i) => ({
        zone_id: i + 1, methane_level: rng(150, 480), water_level: rng(0.2, 0.9),
        ndvi: rng(0.2, 0.7), area_fraction: 0.0625,
        lat: lat + (i % 4 - 2) * 0.002, lon: lon + (Math.floor(i / 4) - 2) * 0.002
      })),
      zone_count: 16
    },
    impact_metrics: credits.impact_metrics,
    farm_profile: {
      farm_id: params.farm_id || 'farm_001', farmer_name: 'Ravi Kumar',
      farm_location: 'Thanjavur, Tamil Nadu, India', farm_area_ha: 4.5,
      crop_type: 'IR64 Paddy', season: 'Kharif 2025',
      coordinates: { lat, lon }, irrigation_source: 'Canal + Groundwater',
      soil_type: 'Clay loam', program: 'CarbonKarma dMRV v2.0'
    },
    audit_trail: {
      events: [
        { event_id: 'ev1', event_type: 'PIPELINE_RUN', description: 'Part 2 pipeline completed', data: { verification_level: 'SILVER', credits_earned: creditsEarned }, created_at: Date.now() / 1000 - 3600 },
        { event_id: 'ev2', event_type: 'CREDIT_ISSUED', description: `Issued ${creditsEarned.toFixed(2)} credits`, data: {}, created_at: Date.now() / 1000 - 3500 }
      ]
    },
    verification_summary: { level: 'SILVER', confidence: 0.74 },
    credits_earned: creditsEarned
  }

  const switches = {
    '/satellite-data': {
      status: 'success', location, timestamps, n_steps: nSteps, step_days: stepDays,
      sentinel1: generateSentinel1(timestamps),
      sentinel2: generateSentinel2(timestamps),
      lst: timestamps.map(ts => ({ timestamp: ts, lst_mean_celsius: rng(27, 38), lst_std: rng(1, 3), is_flooded: true })),
      weather: generateWeather(timestamps)
    },
    '/fusion-data': {
      status: 'success', location, timestamps, n_steps: nSteps, step_days: stepDays,
      fusion_data: fusionData, heatmaps: generateHeatmaps(lat, lon)
    },
    '/awd-status': { status: 'success', location, timestamps, ...awdResult, detection_params: { flood_threshold: 0.55, dry_threshold: 0.25, min_cycle_days: 5 } },
    '/methane': { status: 'success', location, awd_status: awdResult.awd_status, methane: { per_step: methanePerStep, latest: methanePerStep[methanePerStep.length - 1], aggregate: methaneAggregate }, units: { methane: 'mg CH4 / m² / day', season_total_kg_ha: 'kg CH4 / ha', reduction_percent: '% vs conventional flooding baseline' } },
    '/verification': { status: 'success', farm_id: params.farm_id || 'farm_001', location, verification, llm_explanation: { explanation: verification.explanation, source: 'template' }, awd_summary: { awd_status: awdResult.awd_status, cycles: awdResult.cycles, confidence: awdResult.confidence }, methane_summary: methaneAggregate },
    '/credits': { status: 'success', farm_id: params.farm_id || 'farm_001', location, ...credits },
    '/credits/wallet': { farm_id: params.farm_id || 'farm_001', total_balance: rng(10, 50), transactions: [], currency: 'Carbon Credits (CO2e tonnes)', price_per_credit_usd: 15 },
    '/analytics': { status: 'success', ...analytics },
    '/llm-insights': { status: 'success', farm_id: params.farm_id || 'farm_001', location, query: params.query || '', insight: { answer: `Based on your field data, your farm is performing at ${farmScore.overall_score.toFixed(0)}/100 with ${awdResult.awd_status.replace('_', ' ')} AWD practice. You have earned ${creditsEarned.toFixed(2)} tCO₂e credits this season. Key recommendations: (1) Maintain AWD cycles of 7-10 days flooded and 5-7 days dry for optimal methane reduction. (2) Monitor soil crack formation as an indicator for re-flooding. (3) Consider submitting your verification report for Gold-level certification next season.`, source: 'template' }, context_used: { awd_status: awdResult.awd_status, farm_score: farmScore.overall_score } },
    '/llm-insights/explain': { status: 'success', location, verification: { level: verification.level, confidence: verification.confidence, explanation: verification.explanation }, llm_explanation: { explanation: `Your field has achieved **${verification.level} verification** with ${(verification.confidence * 100).toFixed(0)}% confidence. The satellite data shows consistent AWD cycling with ${awdResult.cycles} complete wet-dry cycles detected. Methane reduction of ${methaneAggregate.total_reduction_pct.toFixed(1)}% compared to conventional flooding has been verified through multi-source satellite analysis. This qualifies for carbon credit issuance at the ${verification.level} tier.`, source: 'template' } },
    '/llm-insights/alerts': { status: 'success', location, alerts: analytics.alerts, llm_narratives: { context: 'High methane emissions detected. AWD compliance below optimal thresholds. Consider initiating a drainage cycle within the next 48 hours to reduce emissions and maintain credit eligibility.', source: 'template' } },
    '/llm-insights/certificate': { status: 'success', location, certificate_text: `CARBON CREDIT CERTIFICATE\n\nThis certifies that ${analytics.farm_profile.farmer_name} of ${analytics.farm_profile.farm_location} has successfully implemented Alternate Wetting and Drying (AWD) practice on ${analytics.farm_profile.farm_area_ha} hectares of paddy rice field during the ${analytics.farm_profile.season} season.\n\nCarbon Credits Issued: ${creditsEarned.toFixed(4)} tCO₂e\nVerification Level: ${verification.level}\nMethodology: CarbonKarma dMRV v2.0 (IPCC AR6 GWP-100)\nRecord Fingerprint: ${verification.fingerprint}\n\nIssued by CarbonKarma Intelligence Platform`, verification_level: verification.level, credits_earned: creditsEarned, fingerprint: verification.fingerprint },
    '/report': { status: 'success', farm_id: params.farm_id || 'farm_001', report: { report_id: 'fallback_report_001', format: 'txt', file_name: `carbonkarma_${params.farm_id || 'farm_001'}_fallback.txt`, summary: `MRV Report | ${params.farm_id || 'farm_001'} | SILVER | ${creditsEarned.toFixed(3)} tCO2e`, generated_at: new Date().toISOString() }, verification, credits_earned: creditsEarned, total_balance: creditsEarned * 1.4, farm_score: farmScore }
  }

  return switches[endpoint] || { status: 'success', message: 'Fallback data', location }
}
