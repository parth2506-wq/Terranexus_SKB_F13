"""
Sentinel-5P TROPOMI macro-validation simulator.

PURPOSE
-------
Our pixel-level (10m) methane reduction calculations from Sentinel-1/2 + models
produce a *bottom-up* estimate of CH₄ abatement per farm. This must be
cross-validated against *top-down* atmospheric observations from the Sentinel-5P
TROPOMI instrument (CH₄ column density, ~7 km native resolution, re-gridded
to 0.1°).

Building a live TROPOMI pipeline requires NetCDF handling, SciHub/Copernicus
async queries, background-field subtraction (Varon et al., 2018 style plume
analysis), and wind-corrected spatial averaging. This simulator emulates the
*statistical output* of that pipeline so downstream code and dashboards can
be developed against a realistic interface.

WHAT THIS CLASS DOES
--------------------
Given a farm bounding box and our bottom-up CH₄ reduction estimate, it:
  1. Simulates a regional TROPOMI XCH4 anomaly (ppb above background) using
     a physically grounded emission-to-column conversion
  2. Computes a validation score: how well does the bottom-up estimate align
     with the (simulated) top-down observation?
  3. Returns structured output identical in shape to what a real pipeline
     would produce — so swapping in the real implementation is a drop-in.

WHAT THIS CLASS DOES NOT DO
---------------------------
  - Fetch real NetCDF files from Copernicus
  - Run actual plume detection
  - Account for real wind fields

Calibration constants are from:
  Lauvaux et al. (2022), "Global assessment of oil and gas methane ultra-emitters"
  Varon et al. (2018), "Quantifying methane point sources from fine-scale satellite observations"
"""
from __future__ import annotations

import hashlib
import logging
import math
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Literal, Optional

import numpy as np

logger = logging.getLogger(__name__)


# ── Physical constants ────────────────────────────────────────────────

# Conversion: kg CH4 per hectare per season → XCH4 anomaly in ppb
# Derived from mass-balance over 0.1° grid cell, assuming 500m boundary-layer
# height and typical monsoon wind speeds (2-5 m/s). This is a first-order
# Gaussian-plume approximation.
CH4_MASS_TO_PPB_FACTOR = 0.0042       # ppb per kg-CH4/ha/season, regional avg
TROPOMI_BACKGROUND_PPB = 1870.0       # Global mean XCH4 (2024)
TROPOMI_NOISE_PPB      = 12.0         # Typical per-pixel retrieval noise
GRID_CELL_DEG          = 0.1          # TROPOMI re-grid resolution


# ── Data transfer object ──────────────────────────────────────────────

@dataclass
class ValidationResult:
    """Output of TROPOMI macro-validation."""

    # ── Inputs ─────────────────────────────────────────────────────────
    bbox:                         list[float]
    bottom_up_reduction_kg_ha:    float
    area_ha:                      float

    # ── Simulated TROPOMI observation ──────────────────────────────────
    tropomi_xch4_mean_ppb:        float
    tropomi_xch4_anomaly_ppb:     float    # vs. regional background
    tropomi_pixels_observed:      int
    observation_uncertainty_ppb:  float

    # ── Validation metrics ─────────────────────────────────────────────
    expected_anomaly_ppb:         float    # what bottom-up predicts
    residual_ppb:                 float    # observed - expected
    residual_sigma:               float    # residual / uncertainty
    validation_score:             float    # [0, 1], 1 = perfect alignment
    validation_status:            str      # "VALIDATED" | "MARGINAL" | "DIVERGENT"

    # ── Metadata ───────────────────────────────────────────────────────
    simulated:                    bool = True
    generated_at:                 str  = ""
    seed:                         Optional[int] = None
    notes:                        list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


# ── Simulator ─────────────────────────────────────────────────────────

class Sentinel5PSimulator:
    """
    Simulates Sentinel-5P TROPOMI macro-validation output.

    Usage:
        sim = Sentinel5PSimulator()
        result = sim.validate(
            bbox=[80.25, 13.07, 80.29, 13.11],
            bottom_up_reduction_kg_ha=185.0,
            area_ha=4.5,
        )
        if result.validation_status == "VALIDATED":
            ...
    """

    def __init__(
        self,
        background_ppb:     float = TROPOMI_BACKGROUND_PPB,
        noise_ppb:          float = TROPOMI_NOISE_PPB,
        mass_to_ppb_factor: float = CH4_MASS_TO_PPB_FACTOR,
        deterministic:      bool  = True,
    ):
        """
        Args:
            background_ppb:     Regional background XCH4 column density.
            noise_ppb:          Per-pixel retrieval noise (1-sigma).
            mass_to_ppb_factor: Emission → column conversion factor.
            deterministic:      If True, use bbox-hashed seed for reproducibility.
        """
        self.background_ppb     = background_ppb
        self.noise_ppb          = noise_ppb
        self.mass_to_ppb_factor = mass_to_ppb_factor
        self.deterministic      = deterministic

    # ── Public API ────────────────────────────────────────────────────

    def validate(
        self,
        bbox: list[float],
        bottom_up_reduction_kg_ha: float,
        area_ha: float,
        baseline_kg_ha: float = 480.0,
    ) -> ValidationResult:
        """
        Perform macro-validation.

        Args:
            bbox:                      [min_lon, min_lat, max_lon, max_lat]
            bottom_up_reduction_kg_ha: Our pixel-level CH₄ reduction (kg/ha/season).
            area_ha:                   Farm area in hectares.
            baseline_kg_ha:            Conventional-flooding baseline emission.

        Returns:
            ValidationResult with synthesised TROPOMI observation and alignment score.
        """
        self._validate_inputs(bbox, bottom_up_reduction_kg_ha, area_ha)

        # Reproducible per-bbox randomness
        seed = self._bbox_seed(bbox) if self.deterministic else None
        rng  = np.random.default_rng(seed)

        # Step 1: Bottom-up emission → expected column anomaly
        actual_emission_kg_ha   = max(0.0, baseline_kg_ha - bottom_up_reduction_kg_ha)
        expected_anomaly_ppb    = actual_emission_kg_ha * self.mass_to_ppb_factor

        # Step 2: Simulate TROPOMI observation
        # Real TROPOMI would observe background + true_anomaly + retrieval_noise
        # We add a small bias (regional error) representing real-world divergence
        true_anomaly   = expected_anomaly_ppb * rng.uniform(0.85, 1.15)  # ±15% natural variability
        retrieval_noise = rng.normal(0, self.noise_ppb)
        observed_mean  = self.background_ppb + true_anomaly + retrieval_noise

        # Pixel count from bbox size (TROPOMI re-grid at 0.1°)
        bbox_width_deg  = max(GRID_CELL_DEG, bbox[2] - bbox[0])
        bbox_height_deg = max(GRID_CELL_DEG, bbox[3] - bbox[1])
        n_pixels = max(1, int(
            math.ceil(bbox_width_deg / GRID_CELL_DEG) *
            math.ceil(bbox_height_deg / GRID_CELL_DEG)
        ))
        # Observation uncertainty scales as noise / sqrt(N)
        obs_uncertainty = self.noise_ppb / math.sqrt(n_pixels)

        # Step 3: Validation metrics
        observed_anomaly = observed_mean - self.background_ppb
        residual         = observed_anomaly - expected_anomaly_ppb
        residual_sigma   = abs(residual) / max(obs_uncertainty, 0.1)
        score            = self._compute_score(residual_sigma)
        status           = self._classify_status(residual_sigma)

        notes: list[str] = []
        if n_pixels < 4:
            notes.append("low_pixel_count_high_uncertainty")
        if bottom_up_reduction_kg_ha > baseline_kg_ha:
            notes.append("bottom_up_exceeds_baseline_implausible")

        logger.info(
            "S5P validation: %s (score=%.2f, residual=%.2f ppb, %dσ)",
            status, score, residual, int(residual_sigma),
        )

        return ValidationResult(
            bbox=bbox,
            bottom_up_reduction_kg_ha=bottom_up_reduction_kg_ha,
            area_ha=area_ha,
            tropomi_xch4_mean_ppb=round(observed_mean, 2),
            tropomi_xch4_anomaly_ppb=round(observed_anomaly, 3),
            tropomi_pixels_observed=n_pixels,
            observation_uncertainty_ppb=round(obs_uncertainty, 3),
            expected_anomaly_ppb=round(expected_anomaly_ppb, 3),
            residual_ppb=round(residual, 3),
            residual_sigma=round(residual_sigma, 2),
            validation_score=round(score, 3),
            validation_status=status,
            simulated=True,
            generated_at=datetime.now(timezone.utc).isoformat(),
            seed=seed,
            notes=notes,
        )

    # ── Internal ──────────────────────────────────────────────────────

    @staticmethod
    def _validate_inputs(bbox: list[float], reduction: float, area: float) -> None:
        if len(bbox) != 4:
            raise ValueError("bbox must be [min_lon, min_lat, max_lon, max_lat]")
        min_lon, min_lat, max_lon, max_lat = bbox
        if not (-180 <= min_lon < max_lon <= 180):
            raise ValueError(f"invalid longitude range: {min_lon}..{max_lon}")
        if not (-90  <= min_lat < max_lat <= 90):
            raise ValueError(f"invalid latitude range: {min_lat}..{max_lat}")
        if reduction < 0:
            raise ValueError(f"reduction cannot be negative: {reduction}")
        if area <= 0:
            raise ValueError(f"area must be positive: {area}")

    @staticmethod
    def _bbox_seed(bbox: list[float]) -> int:
        """Deterministic seed from bbox for reproducibility."""
        key = f"{bbox[0]:.4f},{bbox[1]:.4f},{bbox[2]:.4f},{bbox[3]:.4f}"
        return int(hashlib.md5(key.encode()).hexdigest()[:8], 16)

    @staticmethod
    def _compute_score(residual_sigma: float) -> float:
        """
        Score decays exponentially with residual in σ units.
          0σ → 1.00
          1σ → 0.61
          2σ → 0.37
          3σ → 0.22
        """
        return float(math.exp(-0.5 * residual_sigma))

    @staticmethod
    def _classify_status(residual_sigma: float) -> str:
        if residual_sigma < 1.0:
            return "VALIDATED"
        if residual_sigma < 2.5:
            return "MARGINAL"
        return "DIVERGENT"
