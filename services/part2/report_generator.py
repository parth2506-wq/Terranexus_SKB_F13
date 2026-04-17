"""
CarbonKarma Part 2 — Report Generator.

Generates a structured PDF carbon credit MRV report using ReportLab.
Falls back to a plain-text report (.txt) if ReportLab is unavailable.

Report sections:
  1. Cover page — farm info, season, verification level badge
  2. Executive Summary — LLM narrative
  3. Satellite Observations — S1/S2/LST/Weather summary table
  4. AWD Analysis — cycle chart data, flood/dry sequence
  5. Methane Estimation — flux table, category distribution
  6. Carbon Credits — calculation breakdown, wallet balance
  7. Verification — checks table, fingerprint
  8. Appendix — data integrity, methodology notes
"""

from __future__ import annotations

import io
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import config

# ---------------------------------------------------------------------------
# ReportLab availability check
# ---------------------------------------------------------------------------
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm, cm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable, PageBreak,
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fmt(val, decimals=2, suffix=""):
    try:
        return f"{float(val):.{decimals}f}{suffix}"
    except (TypeError, ValueError):
        return str(val)


def _level_color(level: str):
    return {
        "GOLD": colors.HexColor("#B8860B"),
        "SILVER": colors.HexColor("#708090"),
        "BRONZE": colors.HexColor("#CD7F32"),
        "FAILED": colors.red,
    }.get(level, colors.grey)


# ---------------------------------------------------------------------------
# PDF report (ReportLab)
# ---------------------------------------------------------------------------

def _build_pdf(
    output_path: str,
    farm_profile: Dict,
    verification: Dict,
    awd_result: Dict,
    methane_data: Dict,
    credits_data: Dict,
    farm_score: Dict,
    satellite_summary: Dict,
    narrative: str,
    alerts: List[Dict],
) -> str:
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=20*mm, leftMargin=20*mm,
        topMargin=20*mm, bottomMargin=20*mm,
    )

    styles = getSampleStyleSheet()
    H1 = ParagraphStyle("H1", parent=styles["Heading1"], fontSize=18, spaceAfter=6, textColor=colors.HexColor("#1a5276"))
    H2 = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=13, spaceAfter=4, textColor=colors.HexColor("#1a5276"))
    BODY = styles["BodyText"]
    SMALL = ParagraphStyle("SMALL", parent=BODY, fontSize=8)
    CENTER = ParagraphStyle("CENTER", parent=BODY, alignment=TA_CENTER)
    BOLD  = ParagraphStyle("BOLD", parent=BODY, fontName="Helvetica-Bold")

    level = verification.get("level", "BRONZE")
    level_col = _level_color(level)

    story = []

    # ── Cover ──────────────────────────────────────────────────────────────
    story.append(Spacer(1, 20*mm))
    story.append(Paragraph("🌾 CarbonKarma dMRV Platform", ParagraphStyle("COVER_TITLE", parent=H1, fontSize=22, alignment=TA_CENTER)))
    story.append(Paragraph("Carbon Credit Monitoring, Reporting & Verification Report", CENTER))
    story.append(Spacer(1, 8*mm))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#1a5276")))
    story.append(Spacer(1, 4*mm))

    cover_data = [
        ["Farm ID",       farm_profile.get("farm_id", "N/A")],
        ["Farmer",        farm_profile.get("farmer_name", "N/A")],
        ["Location",      farm_profile.get("farm_location", "N/A")],
        ["Area",          f"{farm_profile.get('farm_area_ha', '?')} hectares"],
        ["Crop",          farm_profile.get("crop_type", "Paddy")],
        ["Season",        farm_profile.get("season", "N/A")],
        ["Report Date",   datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")],
        ["Verification",  level],
    ]
    t = Table(cover_data, colWidths=[55*mm, 110*mm])
    t.setStyle(TableStyle([
        ("FONTNAME",  (0,0), (-1,-1), "Helvetica"),
        ("FONTNAME",  (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTSIZE",  (0,0), (-1,-1), 10),
        ("BACKGROUND",(0,-1),(-1,-1), level_col),
        ("TEXTCOLOR", (0,-1),(-1,-1), colors.white),
        ("ROWBACKGROUNDS", (0,0), (-1,-2), [colors.white, colors.HexColor("#EAF2F8")]),
        ("GRID", (0,0), (-1,-1), 0.5, colors.lightgrey),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    story.append(t)
    story.append(PageBreak())

    # ── 1. Executive Summary ───────────────────────────────────────────────
    story.append(Paragraph("1. Executive Summary", H1))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.lightgrey))
    story.append(Spacer(1, 3*mm))
    for para in narrative.split("\n\n"):
        story.append(Paragraph(para.replace("\n", " "), BODY))
        story.append(Spacer(1, 2*mm))

    # ── 2. Verification ────────────────────────────────────────────────────
    story.append(Spacer(1, 5*mm))
    story.append(Paragraph("2. Verification Results", H1))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.lightgrey))
    story.append(Spacer(1, 3*mm))

    v_rows = [["Check", "Passed", "Score", "Detail"]]
    for chk in verification.get("checks", []):
        v_rows.append([
            chk["name"].replace("_", " ").title(),
            "✓" if chk["passed"] else "✗",
            f"{chk['score']:.3f}",
            chk["detail"][:60],
        ])
    vt = Table(v_rows, colWidths=[45*mm, 15*mm, 18*mm, 87*mm])
    vt.setStyle(TableStyle([
        ("FONTNAME",  (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",  (0,0), (-1,-1), 8),
        ("BACKGROUND",(0,0), (-1,0), colors.HexColor("#1a5276")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("GRID", (0,0), (-1,-1), 0.3, colors.lightgrey),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#EAF2F8")]),
        ("TOPPADDING", (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
    ]))
    # Colour the Passed column
    for i, chk in enumerate(verification.get("checks", []), start=1):
        col = colors.HexColor("#1e8449") if chk["passed"] else colors.HexColor("#cb4335")
        vt.setStyle(TableStyle([("TEXTCOLOR", (1, i), (1, i), col)]))
    story.append(vt)
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph(f"Fingerprint: {verification.get('fingerprint','')}", SMALL))

    # ── 3. AWD Analysis ────────────────────────────────────────────────────
    story.append(Spacer(1, 5*mm))
    story.append(Paragraph("3. AWD Practice Analysis", H1))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.lightgrey))
    story.append(Spacer(1, 3*mm))
    awd_rows = [
        ["AWD Status",    awd_result.get("awd_status", "N/A")],
        ["LSTM Signal",   _fmt(awd_result.get("lstm_signal"), 4)],
        ["Cycles Detected", str(awd_result.get("cycles", 0))],
        ["Confidence",    f"{awd_result.get('confidence', 0):.0%}"],
        ["Irrigation Events", str(len(awd_result.get("irrigation_events", [])))],
        ["Rain Events",   str(len(awd_result.get("rain_events", [])))],
    ]
    at = Table(awd_rows, colWidths=[70*mm, 95*mm])
    at.setStyle(TableStyle([
        ("FONTNAME",  (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTSIZE",  (0,0), (-1,-1), 10),
        ("GRID", (0,0), (-1,-1), 0.3, colors.lightgrey),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [colors.white, colors.HexColor("#EAF2F8")]),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    story.append(at)

    # ── 4. Methane Estimation ──────────────────────────────────────────────
    story.append(Spacer(1, 5*mm))
    story.append(Paragraph("4. Methane Estimation", H1))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.lightgrey))
    story.append(Spacer(1, 3*mm))
    agg = methane_data.get("aggregate", {})
    cat_dist = agg.get("category_distribution", {})
    meth_rows = [
        ["Mean Daily Flux",       f"{_fmt(agg.get('mean_daily_flux'))} mg CH₄/m²/day"],
        ["Peak Daily Flux",       f"{_fmt(agg.get('max_daily_flux'))} mg CH₄/m²/day"],
        ["Season Total",          f"{_fmt(agg.get('season_total_kg_ha'))} kg CH₄/ha"],
        ["CF Baseline",           f"{_fmt(agg.get('baseline_kg_ha'))} kg CH₄/ha"],
        ["Average Reduction",     f"{_fmt(agg.get('total_reduction_pct'))}%"],
        ["Low Steps",             str(cat_dist.get("low", 0))],
        ["Medium Steps",          str(cat_dist.get("medium", 0))],
        ["High Steps",            str(cat_dist.get("high", 0))],
    ]
    mt = Table(meth_rows, colWidths=[70*mm, 95*mm])
    mt.setStyle(TableStyle([
        ("FONTNAME",  (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTSIZE",  (0,0), (-1,-1), 10),
        ("GRID", (0,0), (-1,-1), 0.3, colors.lightgrey),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [colors.white, colors.HexColor("#EAF2F8")]),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    story.append(mt)

    # ── 5. Carbon Credits ──────────────────────────────────────────────────
    story.append(Spacer(1, 5*mm))
    story.append(Paragraph("5. Carbon Credits", H1))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.lightgrey))
    story.append(Spacer(1, 3*mm))
    calc = credits_data.get("calculation", {})
    cred_rows = [
        ["Baseline CO₂e",          f"{_fmt(calc.get('baseline_co2e_t'), 4)} tCO₂e"],
        ["Actual CO₂e",            f"{_fmt(calc.get('actual_co2e_t'), 4)} tCO₂e"],
        ["Reduction CO₂e",         f"{_fmt(calc.get('reduction_co2e_t'), 4)} tCO₂e"],
        ["Verification Multiplier", f"{_fmt(calc.get('verification_multiplier'))}x ({calc.get('verification_level')})"],
        ["Credits Earned",          f"{_fmt(credits_data.get('credits_earned'), 4)} tCO₂e"],
        ["USD Value",               f"${_fmt(credits_data.get('usd_value'))}"],
        ["Wallet Balance",          f"{_fmt(credits_data.get('total_balance'), 4)} tCO₂e"],
    ]
    ct = Table(cred_rows, colWidths=[70*mm, 95*mm])
    ct.setStyle(TableStyle([
        ("FONTNAME",  (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTSIZE",  (0,0), (-1,-1), 10),
        ("GRID", (0,0), (-1,-1), 0.3, colors.lightgrey),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [colors.white, colors.HexColor("#EAF2F8")]),
        ("BACKGROUND",(0,-3),(-1,-1), colors.HexColor("#d5f5e3")),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    story.append(ct)

    # ── 6. Farm Score ──────────────────────────────────────────────────────
    story.append(Spacer(1, 5*mm))
    story.append(Paragraph("6. Farm Sustainability Score", H1))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.lightgrey))
    story.append(Spacer(1, 3*mm))
    score_rows = [
        ["Overall Score",      f"{farm_score.get('overall_score', 0)} / 100 (Grade {farm_score.get('grade', 'N/A')})"],
        ["Water Efficiency",   f"{farm_score.get('water_efficiency', 0)} / 100"],
        ["Methane Control",    f"{farm_score.get('methane_control', 0)} / 100"],
        ["AWD Compliance",     f"{farm_score.get('awd_compliance', 0)} / 100"],
        ["Verification Quality", f"{farm_score.get('verification_quality', 0)} / 100"],
    ]
    st = Table(score_rows, colWidths=[70*mm, 95*mm])
    st.setStyle(TableStyle([
        ("FONTNAME",  (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTSIZE",  (0,0), (-1,-1), 10),
        ("GRID", (0,0), (-1,-1), 0.3, colors.lightgrey),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [colors.white, colors.HexColor("#EAF2F8")]),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    story.append(st)

    # ── Methodology ────────────────────────────────────────────────────────
    story.append(Spacer(1, 5*mm))
    story.append(Paragraph("7. Methodology", H1))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.lightgrey))
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph(
        "Satellite data: Sentinel-1 SAR (C-band, VV/VH), Sentinel-2 MSI (NDVI, B02-B08), "
        "Sentinel-3/Landsat (LST). Weather: Open-Meteo ERA5-Land. "
        "AI models: CNN water extractor, LSTM AWD detector, MLP methane estimator. "
        "GWP-100: CH4=27.9 (IPCC AR6). Baseline: 400 mg CH4/m2/day (IPCC Tier 1, tropical Asia). "
        "Credits: 1 credit = 1 tonne CO2e. Price: USD " + str(config.CREDIT_PRICE_USD) + "/credit.",
        SMALL
    ))

    doc.build(story)
    return output_path


# ---------------------------------------------------------------------------
# Text fallback
# ---------------------------------------------------------------------------

def _build_text_report(
    output_path: str,
    farm_profile: Dict,
    verification: Dict,
    awd_result: Dict,
    methane_data: Dict,
    credits_data: Dict,
    farm_score: Dict,
    narrative: str,
) -> str:
    lines = [
        "=" * 70,
        "CARBONKARMA dMRV REPORT",
        "=" * 70,
        f"Farm: {farm_profile.get('farmer_name')} | ID: {farm_profile.get('farm_id')}",
        f"Location: {farm_profile.get('farm_location')} | Area: {farm_profile.get('farm_area_ha')} ha",
        f"Season: {farm_profile.get('season')} | Crop: {farm_profile.get('crop_type')}",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "EXECUTIVE SUMMARY",
        "-" * 40,
        narrative,
        "",
        "VERIFICATION",
        "-" * 40,
        f"Level: {verification.get('level')} | Confidence: {verification.get('confidence'):.0%}",
        f"Fingerprint: {verification.get('fingerprint', '')[:32]}...",
        "",
        "AWD ANALYSIS",
        "-" * 40,
        f"Status: {awd_result.get('awd_status')} | Cycles: {awd_result.get('cycles')} | LSTM: {awd_result.get('lstm_signal'):.3f}",
        "",
        "METHANE",
        "-" * 40,
        f"Mean flux: {methane_data.get('aggregate', {}).get('mean_daily_flux', 0):.1f} mg/m2/day",
        f"Reduction: {methane_data.get('aggregate', {}).get('total_reduction_pct', 0):.1f}%",
        "",
        "CARBON CREDITS",
        "-" * 40,
        f"Credits earned: {credits_data.get('credits_earned', 0):.4f} tCO2e",
        f"USD value: ${credits_data.get('usd_value', 0):.2f}",
        f"Wallet balance: {credits_data.get('total_balance', 0):.4f} tCO2e",
        "",
        "FARM SCORE",
        "-" * 40,
        f"Overall: {farm_score.get('overall_score', 0)}/100 (Grade {farm_score.get('grade', 'N/A')})",
        "=" * 70,
    ]
    with open(output_path, "w") as f:
        f.write("\n".join(lines))
    return output_path


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_report(
    farm_id: str,
    farm_profile: Dict,
    verification: Dict,
    awd_result: Dict,
    methane_data: Dict,
    credits_data: Dict,
    farm_score: Dict,
    satellite_summary: Optional[Dict] = None,
    narrative: str = "",
    alerts: Optional[List[Dict]] = None,
) -> Dict[str, Any]:
    """
    Generate a complete MRV report (PDF or TXT fallback).

    Returns dict with file path, format, and report ID.
    """
    from db.store import get_store

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    Path(config.REPORT_OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

    if REPORTLAB_AVAILABLE:
        fname = f"carbonkarma_{farm_id}_{ts}.pdf"
        fpath = os.path.join(config.REPORT_OUTPUT_DIR, fname)
        try:
            _build_pdf(
                fpath, farm_profile, verification, awd_result,
                methane_data, credits_data, farm_score,
                satellite_summary or {}, narrative, alerts or [],
            )
            fmt = "pdf"
        except Exception as e:
            import logging; logging.getLogger(__name__).error("PDF generation failed: %s", e)
            fname = fname.replace(".pdf", ".txt")
            fpath = os.path.join(config.REPORT_OUTPUT_DIR, fname)
            _build_text_report(fpath, farm_profile, verification, awd_result, methane_data, credits_data, farm_score, narrative)
            fmt = "txt"
    else:
        fname = f"carbonkarma_{farm_id}_{ts}.txt"
        fpath = os.path.join(config.REPORT_OUTPUT_DIR, fname)
        _build_text_report(fpath, farm_profile, verification, awd_result, methane_data, credits_data, farm_score, narrative)
        fmt = "txt"

    summary = f"MRV Report | {farm_id} | {verification.get('level')} | {credits_data.get('credits_earned', 0):.3f} tCO2e"
    store = get_store()
    report_id = store.insert_report(
        farm_id=farm_id,
        report_type="FULL_MRV",
        summary=summary,
        data={"verification_level": verification.get("level"), "credits": credits_data.get("credits_earned")},
        pdf_path=fpath,
    )
    store.log_event(farm_id, "REPORT_GENERATED", f"Report {report_id} generated ({fmt})")

    return {
        "report_id": report_id,
        "format": fmt,
        "file_path": fpath,
        "file_name": fname,
        "summary": summary,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
