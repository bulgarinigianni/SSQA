"""Sport Science Quality Analyzer — Streamlit UI v2."""

from __future__ import annotations

import asyncio
import json
import math
import tempfile
from pathlib import Path

import streamlit as st
from streamlit_js_eval import streamlit_js_eval

from app.config import settings
from app.extractor import InvalidAPIKeyError, QuotaExhaustedError, extract_paper_data
from app.models import AnalysisResult, ConfidenceReport, ExtractedData, ScoringBreakdown
from app.pdf_parser import extract_text
from app.scoring import score_paper

# ── Page config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SSQA — Sport Science Quality Analyzer",
    page_icon="🏋️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Inject V2 CSS + hide Streamlit chrome ─────────────────────────────────
_V2_CSS = Path("static/css/v2.css").read_text()

st.markdown(f"""
<style>
{_V2_CSS}

/* Hide Streamlit chrome */
#MainMenu, footer {{ visibility: hidden; }}
[data-testid="stHeader"] {{ display: none !important; }}
[data-testid="stToolbar"] {{ display: none !important; }}
.stDeployButton {{ display: none !important; }}
div[data-testid="stDecoration"] {{ display: none !important; }}

/* Main padding */
.block-container {{
    padding-top: 0 !important;
    padding-bottom: 2rem !important;
    max-width: 1100px;
}}

/* Sidebar */
[data-testid="stSidebar"] > div:first-child {{
    background: var(--surface);
    border-right: 1px solid var(--border);
    padding-top: 0 !important;
}}

/* Sidebar collapse/expand button — always visible and styled */
[data-testid="collapsedControl"] {{
    display: flex !important;
    visibility: visible !important;
    opacity: 1 !important;
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-left: none !important;
    border-radius: 0 8px 8px 0 !important;
    padding: 10px 5px !important;
    box-shadow: 2px 1px 6px rgba(0,0,0,0.08) !important;
    top: 50% !important;
    position: fixed !important;
    left: 0 !important;
    z-index: 9999 !important;
    cursor: pointer !important;
}}
[data-testid="collapsedControl"] svg {{
    fill: var(--accent) !important;
    color: var(--accent) !important;
    width: 18px !important;
    height: 18px !important;
}}

/* Streamlit buttons → V2 style */
.stButton > button[kind="primary"] {{
    background: var(--accent) !important; color: white !important;
    border: none !important; border-radius: 6px !important;
    font-weight: 500 !important; font-family: var(--font) !important;
    padding: 10px 20px !important;
}}
.stButton > button {{
    border-radius: 6px !important; font-weight: 500 !important;
    font-family: var(--font) !important;
}}

/* File uploader */
[data-testid="stFileUploader"] section {{
    border: 2px dashed var(--border) !important;
    border-radius: var(--radius) !important;
    background: var(--surface) !important;
    padding: 40px 24px !important;
    text-align: center;
    transition: all 0.2s;
}}
[data-testid="stFileUploader"] section:hover {{
    border-color: var(--accent) !important;
    background: #f0f5ff !important;
}}

/* Tabs */
[data-testid="stTabs"] [role="tab"] {{
    font-family: var(--font) !important; font-size: 13px !important;
    font-weight: 500 !important; color: var(--text-secondary) !important;
    padding: 12px 18px !important;
}}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {{
    color: var(--accent) !important;
}}
[data-testid="stTabs"] [data-baseweb="tab-highlight"] {{
    background-color: var(--accent) !important;
}}
[data-testid="stTabs"] [data-baseweb="tab-border"] {{
    background-color: var(--border) !important;
}}

/* Progress */
.stProgress > div > div > div > div {{
    background-color: var(--accent) !important; border-radius: 3px !important;
}}

/* Expander */
details[data-testid="stExpander"] {{
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    background: var(--surface) !important;
    margin-bottom: 8px;
}}
details[data-testid="stExpander"] summary {{
    font-family: var(--font) !important; font-weight: 500 !important;
    font-size: 14px !important; padding: 12px 18px !important;
}}

/* st.html wrapper */
[data-testid="stHtml"] {{ font-family: var(--font); color: var(--text); }}
</style>
""", unsafe_allow_html=True)


# ── Persistent API key via browser localStorage ──────────────────────────
if "api_key" not in st.session_state:
    stored = streamlit_js_eval(
        js_expressions='localStorage.getItem("gemini_api_key") || ""',
        key="load_api_key",
    )
    if stored:
        st.session_state["api_key"] = stored


def _save_key_to_browser(key: str):
    safe = json.dumps(key)
    streamlit_js_eval(
        js_expressions=f"localStorage.setItem('gemini_api_key', {safe})",
        key="save_api_key",
    )


# ── Async helper ──────────────────────────────────────────────────────────
def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ── Analysis pipeline ─────────────────────────────────────────────────────
def _analyze_one(pdf_bytes: bytes, filename: str, api_key: str) -> AnalysisResult:
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(pdf_bytes)
        tmp_path = Path(tmp.name)
    try:
        text = extract_text(tmp_path)
        extracted = _run_async(extract_paper_data(text, api_key=api_key))
        return score_paper(extracted, filename=filename)
    except (QuotaExhaustedError, InvalidAPIKeyError):
        raise
    except Exception as exc:
        return AnalysisResult(
            filename=filename,
            extracted=ExtractedData(),
            scoring=ScoringBreakdown(
                design_category="other", design_cap=0,
                base_methodology_score=0, raw_score=0, final_score=0,
                category="error", category_label="ERROR",
                explanation=f"Analysis failed: {exc}",
            ),
            confidence=ConfidenceReport(
                total_fields=0, extracted_fields=0,
                confidence_pct=0, level="low",
            ),
            error=str(exc),
        )
    finally:
        tmp_path.unlink(missing_ok=True)


def _resolve_key() -> str:
    key = st.session_state.get("api_key", "").strip() or settings.gemini_api_key
    if not key:
        st.error("No Gemini API key configured. Paste your key in the sidebar before analyzing.")
        st.stop()
    return key


# ── V2 HTML helpers ───────────────────────────────────────────────────────

def _ring_html(pct: int, size: int = 100, stroke: int = 6) -> str:
    r = (size - stroke) / 2
    c = 2 * math.pi * r
    off = c * (1 - pct / 100)
    if pct >= 85:   color = "#ca8a04"
    elif pct >= 70: color = "#475569"
    elif pct >= 50: color = "#9a3412"
    elif pct >= 30: color = "#2563eb"
    else:           color = "#111827"
    return (
        f'<div style="width:{size}px;height:{size}px;position:relative;flex-shrink:0">'
        f'<svg width="{size}" height="{size}">'
        f'<circle cx="{size/2}" cy="{size/2}" r="{r:.1f}" fill="none" stroke="#e2e5ea" stroke-width="{stroke}"/>'
        f'<circle cx="{size/2}" cy="{size/2}" r="{r:.1f}" fill="none" stroke="{color}" stroke-width="{stroke}"'
        f' stroke-dasharray="{c:.2f}" stroke-dashoffset="{off:.2f}" stroke-linecap="round"'
        f' transform="rotate(-90 {size/2} {size/2})"/>'
        f'</svg>'
        f'<div style="position:absolute;inset:0;display:grid;place-items:center;'
        f'font-family:\'JetBrains Mono\',monospace;font-weight:700;font-size:{int(size*0.22)}px;color:{color}">'
        f'{pct}%</div>'
        f'</div>'
    )


def _badge(category: str, label: str) -> str:
    return f'<span class="cat-badge cat-{category}">{label}</span>'


def _crit(code: str, ok) -> str:
    if ok is True:    cls, sym = "ok", "✓"
    elif ok is False: cls, sym = "no", "✗"
    else:             cls, sym = "unknown", "·"
    return f'<div class="crit {cls}"><span>{sym}</span><span>{code}</span></div>'


def _banner(tone: str, icon: str, text: str, mod: str = "") -> str:
    mod_html = f'<span class="banner-mod">{mod}</span>' if mod else ""
    return (
        f'<div class="banner {tone}">'
        f'<div class="banner-icon">{icon}</div>'
        f'<div style="flex:1">{text}</div>'
        f'{mod_html}'
        f'</div>'
    )


def _brk(label: str, val: str, note: str = "", bar: int | None = None, muted: bool = False) -> str:
    cls = "brk-row muted-row" if muted else "brk-row"
    bar_html = f'<span class="bar"><i style="width:{min(bar, 100)}%"></i></span>' if bar is not None else ""
    note_html = f'<span class="note">{note}</span>' if note else ""
    return f'<div class="{cls}"><span class="lbl">{label}</span>{bar_html}{note_html}<span class="val">{val}</span></div>'


def _methodology_html(ed: ExtractedData, sc: ScoringBreakdown) -> str:
    tool = sc.methodology_tool

    if tool == "PEDro" and ed.pedro_criteria:
        p = ed.pedro_criteria
        crits = [
            ("C1", p.c1_eligibility_specified), ("C2", p.c2_random_allocation),
            ("C3", p.c3_concealed_allocation), ("C4", p.c4_baseline_comparable),
            ("C5", p.c5_blinding_subjects), ("C6", p.c6_blinding_therapists),
            ("C7", p.c7_blinding_assessors), ("C8", p.c8_adequate_followup),
            ("C9", p.c9_intention_to_treat), ("C10", p.c10_between_group),
            ("C11", p.c11_point_variability),
        ]
        score = sc.pedro_score if sc.pedro_score is not None else sum(1 for _, v in crits[1:] if v is True)
        bar = round(score / 10 * 100)
        pills = "".join(_crit(k, v) for k, v in crits)
        return (
            f'<div class="card">'
            f'<div class="row between" style="margin-bottom:10px">'
            f'<div><span style="font-size:16px;font-weight:600">🔬 PEDro</span>'
            f'<span class="muted" style="margin-left:8px;font-size:13px">scale 0–10</span></div>'
            f'<div style="font-family:JetBrains Mono,monospace;font-size:20px;font-weight:700">'
            f'{score}<span class="muted" style="font-size:14px"> / 10</span></div></div>'
            f'<div style="height:6px;background:#e2e5ea;border-radius:3px;overflow:hidden;margin-bottom:4px">'
            f'<div style="width:{bar}%;height:100%;background:#475569"></div></div>'
            f'<div class="crit-grid">{pills}</div>'
            f'</div>'
        )

    if tool == "AMSTAR-2" and ed.amstar2_criteria:
        a = ed.amstar2_criteria
        crits = [
            ("A1", a.a1_pico), ("A2", a.a2_protocol_registered),
            ("A3", a.a3_study_design_explained), ("A4", a.a4_comprehensive_search),
            ("A5", a.a5_duplicate_selection), ("A6", a.a6_duplicate_extraction),
            ("A7", a.a7_excluded_studies_listed), ("A8", a.a8_studies_described),
            ("A9", a.a9_risk_of_bias_assessed), ("A10", a.a10_funding_reported),
            ("A11", a.a11_statistical_methods), ("A12", a.a12_rob_impact_assessed),
            ("A13", a.a13_rob_in_interpretation), ("A14", a.a14_heterogeneity_discussed),
            ("A15", a.a15_publication_bias), ("A16", a.a16_coi_disclosed),
        ]
        met = sc.amstar2_met if sc.amstar2_met is not None else sum(1 for _, v in crits if v is True)
        bar = round(met / 16 * 100)
        pills = "".join(_crit(k, v) for k, v in crits)
        return (
            f'<div class="card">'
            f'<div class="row between" style="margin-bottom:10px">'
            f'<div><span style="font-size:16px;font-weight:600">🔬 AMSTAR-2</span>'
            f'<span class="muted" style="margin-left:8px;font-size:13px">16 criteria · 7 critical</span></div>'
            f'<div style="font-family:JetBrains Mono,monospace;font-size:20px;font-weight:700">'
            f'{met}<span class="muted" style="font-size:14px"> / 16</span></div></div>'
            f'<div style="height:6px;background:#e2e5ea;border-radius:3px;overflow:hidden;margin-bottom:4px">'
            f'<div style="width:{bar}%;height:100%;background:#475569"></div></div>'
            f'<div class="crit-grid">{pills}</div>'
            f'<p class="muted" style="font-size:12px;margin-top:8px">★ Critical: A2, A4, A7, A9, A11, A13, A15 — weight ×1.5</p>'
            f'</div>'
        )

    if tool == "NOS" and ed.nos_criteria:
        n = ed.nos_criteria
        crits = [
            ("S1", n.s1_representativeness), ("S2", n.s2_non_exposed_selection),
            ("S3", n.s3_exposure_ascertainment), ("S4", n.s4_outcome_not_present),
            ("C1", n.c1_primary_factor), ("C2", n.c2_additional_factor),
            ("O1", n.o1_outcome_assessment), ("O2", n.o2_followup_length),
            ("O3", n.o3_followup_adequacy),
        ]
        score = sc.nos_score if sc.nos_score is not None else sum(1 for _, v in crits if v is True)
        bar = round(score / 9 * 100)
        pills = "".join(_crit(k, v) for k, v in crits)
        return (
            f'<div class="card">'
            f'<div class="row between" style="margin-bottom:10px">'
            f'<div><span style="font-size:16px;font-weight:600">🔬 Newcastle-Ottawa Scale</span></div>'
            f'<div style="font-family:JetBrains Mono,monospace;font-size:20px;font-weight:700">'
            f'{score}<span class="muted" style="font-size:14px"> / 9</span></div></div>'
            f'<div style="height:6px;background:#e2e5ea;border-radius:3px;overflow:hidden;margin-bottom:4px">'
            f'<div style="width:{bar}%;height:100%;background:#475569"></div></div>'
            f'<div class="crit-grid">{pills}</div>'
            f'</div>'
        )

    if tool == "GRADE" and ed.grade_criteria:
        g = ed.grade_criteria
        crits = [
            ("G1", g.g1_systematic_search), ("G2", g.g2_evidence_graded),
            ("G3", g.g3_consensus_method), ("G4", g.g4_panel_composition),
            ("G5", g.g5_coi_management), ("G6", g.g6_recommendation_strength),
            ("G7", g.g7_evidence_gaps), ("G8", g.g8_external_review),
        ]
        met = sc.grade_met if sc.grade_met is not None else sum(1 for _, v in crits if v is True)
        pills = "".join(_crit(k, v) for k, v in crits)
        return (
            f'<div class="card">'
            f'<div class="row between" style="margin-bottom:10px">'
            f'<div><span style="font-size:16px;font-weight:600">🔬 GRADE</span>'
            f'<span class="muted" style="margin-left:8px;font-size:13px">Consensus assessment</span></div>'
            f'<div style="font-family:JetBrains Mono,monospace;font-size:20px;font-weight:700">'
            f'{met}<span class="muted" style="font-size:14px"> / 8</span></div></div>'
            f'<div class="crit-grid">{pills}</div>'
            f'</div>'
        )

    return (
        f'<div class="card">'
        f'<div class="row between">'
        f'<span style="font-size:16px;font-weight:600">🔬 {tool or "Generic"}</span>'
        f'<div style="font-family:JetBrains Mono,monospace;font-size:20px;font-weight:700">'
        f'{sc.base_methodology_score:.1f}<span class="muted" style="font-size:14px"> / {sc.design_cap:.1f}</span></div>'
        f'</div></div>'
    )


def _render_result_html(r: AnalysisResult, filename: str) -> str:
    """Build full V2 result HTML for st.html()."""
    ed = r.extracted
    sc = r.scoring
    c = r.confidence
    pct = round(sc.normalized_score)

    authors_list = ed.authors or []
    authors = ", ".join(authors_list[:3]) + (" et al." if len(authors_list) > 3 else "")
    subtitle = " · ".join(filter(None, [authors, ed.journal, str(ed.year) if ed.year else ""]))

    tool_label = sc.methodology_tool or "Generic"
    if sc.pedro_score is not None:   tool_label += f" {sc.pedro_score}/10"
    elif sc.nos_score is not None:    tool_label += f" {sc.nos_score}/9"
    elif sc.amstar2_met is not None:  tool_label += f" {sc.amstar2_met}/16"
    elif sc.grade_met is not None:    tool_label += f" {sc.grade_met}/8"

    sample_html = ""
    if ed.sample_size:
        pop = (ed.population_type or "").replace("_", " ")
        sample_html = (
            f'<div style="border-left:1px solid #e2e5ea"></div>'
            f'<div class="score-stat">'
            f'<div class="num" style="font-size:20px">n={ed.sample_size}</div>'
            f'<div class="lbl">{pop or "participants"}</div>'
            f'</div>'
        )

    subtitle_html = f'<div class="result-subtitle">{subtitle}</div>' if subtitle else ""
    verdict_html = (
        f'<div class="explanation">'
        f'<strong class="eyebrow">AI Verdict</strong>'
        f'{sc.explanation}'
        f'</div>'
    ) if sc.explanation else ""

    hero = (
        f'<div class="card">'
        f'<div class="result-header">'
        f'{_ring_html(pct)}'
        f'<div>'
        f'{_badge(sc.category, sc.category_label)}'
        f'<div class="result-title" style="margin-top:10px">{ed.title or filename}</div>'
        f'{subtitle_html}'
        f'<div class="score-stats">'
        f'<div class="score-stat">'
        f'<div class="num">{sc.final_score:.1f}<span class="cap"> /{sc.design_cap:.1f}</span></div>'
        f'<div class="lbl">Score / Cap</div>'
        f'</div>'
        f'<div style="border-left:1px solid #e2e5ea"></div>'
        f'<div class="score-stat">'
        f'<div class="num" style="font-size:20px">{tool_label}</div>'
        f'<div class="lbl">Tool</div>'
        f'</div>'
        f'{sample_html}'
        f'</div>'
        f'</div>'
        f'</div>'
        f'{verdict_html}'
        f'</div>'
    )

    # Signal banners
    sample_bonus = (sc.sample_size_adjustment or 0) + (sc.large_sample_bonus or 0)
    banners = []
    if sc.institutional_bonus > 0:
        inst = ", ".join(sc.institutional_matches or [])
        banners.append(_banner("blue", "★", f"<b>Elite institution</b> · {inst}", f"+{sc.institutional_bonus:.1f}"))
    if sc.journal_bonus > 0:
        banners.append(_banner("purple", "🏆", f"<b>Elite journal</b> · {sc.journal_match or ed.journal or ''}", f"+{sc.journal_bonus:.1f}"))
    if sc.registered_protocol_bonus > 0:
        banners.append(_banner("green", "✓", "<b>Registered protocol</b> (ClinicalTrials.gov / PROSPERO / OSF)", f"+{sc.registered_protocol_bonus:.1f}"))
    if sample_bonus > 0:
        pop = (ed.population_type or "").replace("_", " ")
        banners.append(_banner("blue", "★", f"<b>Sample bonus</b> · {pop or f'n={ed.sample_size}'}", f"+{sample_bonus:.1f}"))
    if sc.coi_detected and sc.coi_penalty < 0:
        coi_text = (ed.conflict_of_interest_statement or "")[:120]
        banners.append(_banner("amber", "⚠", f"<b>Conflict of interest ({sc.coi_severity})</b> · {coi_text}", f"{sc.coi_penalty:.1f}"))
    if sc.predatory_journal_detected:
        banners.append(_banner("black", "🏴", f"<b>Predatory journal</b> · {sc.predatory_journal_match or ''}"))

    banners_html = (
        '<div class="stack" style="margin-bottom:20px">' + "".join(banners) + "</div>"
    ) if banners else ""

    # Methodology grid
    method_html = _methodology_html(ed, sc)

    # Metrics row
    metric_cells = []
    if ed.study_design:
        metric_cells.append(
            f'<div class="metric"><div class="lbl">Study design</div>'
            f'<div class="val" style="font-size:14px;text-transform:capitalize">{ed.study_design.replace("_"," ")}</div></div>'
        )
    if ed.sample_size:
        pop = (ed.population_type or "").replace("_", " ")
        metric_cells.append(
            f'<div class="metric"><div class="lbl">Sample</div>'
            f'<div class="val">n = {ed.sample_size}</div>'
            f'{"" if not pop else f"<div class=sub2>{pop}</div>"}</div>'
        )
    if ed.journal:
        metric_cells.append(
            f'<div class="metric"><div class="lbl">Journal</div>'
            f'<div class="val" style="font-size:14px">{ed.journal}</div>'
            f'{"" if not ed.year else f"<div class=sub2>{ed.year}</div>"}</div>'
        )
    metrics_html = (
        f'<div class="metric-grid" style="margin-top:20px;margin-bottom:20px">{"".join(metric_cells)}</div>'
    ) if metric_cells else ""

    # Score breakdown
    bar_pct = round(sc.base_methodology_score / sc.design_cap * 100) if sc.design_cap > 0 else 0
    brk_rows = [_brk(f"Base score ({sc.methodology_tool})", f"{sc.base_methodology_score:.1f}", bar=bar_pct)]
    if sample_bonus:
        brk_rows.append(_brk("Sample bonus", f"+{sample_bonus:.1f}"))
    if sc.institutional_bonus > 0:
        brk_rows.append(_brk("Elite institution", f"+{sc.institutional_bonus:.1f}", note=", ".join(sc.institutional_matches or [])))
    if sc.journal_bonus > 0:
        brk_rows.append(_brk("Elite journal", f"+{sc.journal_bonus:.1f}", note=sc.journal_match or ""))
    if sc.registered_protocol_bonus > 0:
        brk_rows.append(_brk("Registered protocol", f"+{sc.registered_protocol_bonus:.1f}"))
    if sc.coi_penalty:
        brk_rows.append(_brk("CoI penalty", f"{sc.coi_penalty:.1f}", muted=True))
    if sc.predatory_journal_detected:
        brk_rows.append(_brk("Predatory → score forced 1.0", "FLAG", muted=True))
    cap_note = f' → capped {sc.final_score:.1f}' if sc.raw_score != sc.final_score else ""
    brk_rows.append(
        f'<div class="brk-row total">'
        f'<span class="lbl">Final score</span>'
        f'<span class="val">{sc.raw_score:.1f}{cap_note}</span>'
        f'</div>'
    )
    breakdown = (
        f'<div class="card">'
        f'<h3>Score breakdown</h3>'
        f'<div class="brk">{"".join(brk_rows)}</div>'
        f'</div>'
    )

    # Main finding
    finding_html = ""
    if ed.main_findings_summary:
        finding_html = (
            f'<div class="card">'
            f'<h3>Main finding</h3>'
            f'<p style="font-size:14.5px;line-height:1.65">{ed.main_findings_summary}</p>'
            f'</div>'
        )

    # Funding & COI
    funding_html = ""
    if ed.funding_sources or ed.conflict_of_interest_statement:
        funders = ", ".join(ed.funding_sources) if ed.funding_sources else "Not reported"
        coi = ed.conflict_of_interest_statement or ""
        coi_part = f'<div class="muted" style="font-size:12.5px;margin-top:4px">COI: {coi}</div>' if coi else ""
        funding_html = (
            f'<div class="card compact">'
            f'<div class="eyebrow" style="margin-bottom:4px">Funding</div>'
            f'<div style="font-size:13.5px">{funders}</div>'
            f'{coi_part}'
            f'</div>'
        )

    # Confidence
    conf_pct = round(c.confidence_pct)
    conf_color = {"high": "#059669", "medium": "#ca8a04", "low": "#dc2626"}.get(c.level, "#6b7280")
    conf_cls = {"high": "high", "medium": "med", "low": "low"}.get(c.level, "low")
    confidence_html = (
        f'<div class="card compact">'
        f'<div class="conf-row">'
        f'<span class="conf-label">Extraction confidence</span>'
        f'<div class="conf-bar"><div class="conf-fill {conf_cls}" style="width:{conf_pct}%"></div></div>'
        f'<span class="conf-text" style="color:{conf_color}">'
        f'{c.level.upper()} · {c.extracted_fields}/{c.total_fields}'
        f'</span>'
        f'</div>'
        f'</div>'
    )

    return (
        hero
        + banners_html
        + method_html
        + metrics_html
        + breakdown
        + finding_html
        + funding_html
        + confidence_html
    )


# ── Sidebar ───────────────────────────────────────────────────────────────
with st.sidebar:
    st.html("""
    <div style="background:var(--surface);border-bottom:1px solid var(--border);
                padding:16px 20px;margin:-1rem -1rem 1.2rem -1rem">
      <div style="display:flex;align-items:center;gap:10px">
        <div style="width:32px;height:32px;background:var(--accent);border-radius:8px;
                    display:flex;align-items:center;justify-content:center;
                    color:white;font-weight:700;font-size:13px;flex-shrink:0">SQ</div>
        <div>
          <div style="font-size:15px;font-weight:600;line-height:1.2">Sport Science QA</div>
          <div style="font-size:11px;color:var(--text-secondary)">v2.0</div>
        </div>
      </div>
    </div>
    """)

    st.markdown("**🔑 Gemini API Key**")
    key_input = st.text_input(
        "API Key", type="password",
        value=st.session_state.get("api_key", ""),
        label_visibility="collapsed",
        placeholder="AIzaSy...",
    )
    if key_input:
        new_key = key_input.strip()
        if new_key != st.session_state.get("api_key", ""):
            st.session_state["api_key"] = new_key
            _save_key_to_browser(new_key)
    elif not st.session_state.get("api_key") and settings.gemini_api_key:
        st.session_state["api_key"] = settings.gemini_api_key

    key_set = bool(st.session_state.get("api_key"))
    dot_color = "#059669" if key_set else "#dc2626"
    key_text = "Saved in browser ✓" if key_set else "Not configured"
    st.html(f"""
    <div style="display:flex;align-items:center;gap:6px;font-size:12px;color:var(--text-secondary);margin-bottom:4px">
      <div style="width:7px;height:7px;border-radius:50%;background:{dot_color}"></div>
      {key_text}
    </div>
    <div style="font-size:10px;color:var(--text-secondary);margin-bottom:6px">
      Stored in your browser only — never shared with other users.
    </div>
    <a href="https://aistudio.google.com/apikey" target="_blank"
       style="font-size:11px;color:var(--accent);text-decoration:none">
      Get a free key at Google AI Studio →
    </a>
    """)

    st.html('<div style="border-top:1px solid var(--border);margin:1rem 0"></div>')

    # ── Verdict scale ──────────────────────────────────────────────────────
    st.html("""
    <div style="font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.8px;
                color:var(--text-secondary);margin-bottom:10px">Verdict Scale</div>
    <div class="scale-row"><span class="cat-badge cat-gold_standard" style="font-size:11px;padding:3px 10px">🥇 Gold Standard</span><span class="rng">≥ 8.5</span></div>
    <div class="scale-row"><span class="cat-badge cat-practical_evidence" style="font-size:11px;padding:3px 10px">🔵 Practical Evidence</span><span class="rng">7.0–8.4</span></div>
    <div class="scale-row"><span class="cat-badge cat-exploratory" style="font-size:11px;padding:3px 10px">🔬 Exploratory</span><span class="rng">5.0–6.9</span></div>
    <div class="scale-row"><span class="cat-badge cat-weak" style="font-size:11px;padding:3px 10px">⚠️ Weak</span><span class="rng">&lt; 5.0</span></div>
    <div class="scale-row"><span class="cat-badge cat-black_flag" style="font-size:11px;padding:3px 10px">🏴 Black Flag</span><span class="rng">predatory</span></div>

    <div style="border-top:1px solid var(--border);margin:1rem 0"></div>
    <div style="font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.8px;
                color:var(--text-secondary);margin-bottom:10px">Quality % (ring)</div>
    <div style="display:flex;flex-direction:column;gap:5px;margin-bottom:1rem">
      <span class="chip chip-gold">Excellent ≥ 85%</span>
      <span class="chip chip-silver">Good 70–84%</span>
      <span class="chip chip-bronze">Fair 50–69%</span>
      <span class="chip chip-blue">Poor 30–49%</span>
      <span class="chip chip-black">Critical &lt; 30%</span>
    </div>
    """)

    st.html('<div style="border-top:1px solid var(--border);margin:1rem 0"></div>')

    # ── Scoring reference (full) ───────────────────────────────────────────
    with st.expander("📐 Study Design Caps"):
        st.html("""
        <table style="width:100%;font-size:12px;border-collapse:collapse">
          <thead>
            <tr style="border-bottom:1px solid var(--border)">
              <th style="text-align:left;padding:4px 0;color:var(--text-secondary);font-weight:600">Design</th>
              <th style="text-align:right;padding:4px 0;color:var(--text-secondary);font-weight:600">Max</th>
            </tr>
          </thead>
          <tbody style="color:var(--text)">
            <tr><td style="padding:4px 0">Meta-Analysis</td><td style="text-align:right;font-family:monospace;font-weight:600">10</td></tr>
            <tr><td style="padding:4px 0">Systematic Review</td><td style="text-align:right;font-family:monospace;font-weight:600">10</td></tr>
            <tr><td style="padding:4px 0">RCT</td><td style="text-align:right;font-family:monospace;font-weight:600">10</td></tr>
            <tr><td style="padding:4px 0">Consensus Statement</td><td style="text-align:right;font-family:monospace;font-weight:600">9</td></tr>
            <tr><td style="padding:4px 0">Prospective Cohort</td><td style="text-align:right;font-family:monospace;font-weight:600">8</td></tr>
            <tr><td style="padding:4px 0">Cross-Sectional</td><td style="text-align:right;font-family:monospace;font-weight:600">7</td></tr>
            <tr><td style="padding:4px 0">Narrative Review / Expert Opinion</td><td style="text-align:right;font-family:monospace;font-weight:600">6</td></tr>
            <tr><td style="padding:4px 0">Case Series</td><td style="text-align:right;font-family:monospace;font-weight:600">5.5</td></tr>
            <tr><td style="padding:4px 0">Case Study</td><td style="text-align:right;font-family:monospace;font-weight:600">5</td></tr>
          </tbody>
        </table>
        """)

    with st.expander("💰 Bonuses & Penalties"):
        st.html("""
        <div style="font-size:12px;line-height:2;color:var(--text)">
          <div style="display:flex;justify-content:space-between;border-bottom:1px solid var(--border);padding-bottom:4px;margin-bottom:4px;color:var(--text-secondary);font-weight:600;font-size:11px">
            <span>Modifier</span><span>Value</span>
          </div>
          <div style="display:flex;justify-content:space-between">
            <span>Elite institution</span>
            <span style="font-family:monospace;color:#059669;font-weight:600">+0.5</span>
          </div>
          <div style="display:flex;justify-content:space-between">
            <span>Elite journal</span>
            <span style="font-family:monospace;color:#059669;font-weight:600">+0.5</span>
          </div>
          <div style="display:flex;justify-content:space-between">
            <span>Registered protocol</span>
            <span style="font-family:monospace;color:#059669;font-weight:600">+0.5</span>
          </div>
          <div style="display:flex;justify-content:space-between">
            <span>Large sample (N ≥ 100)</span>
            <span style="font-family:monospace;color:#059669;font-weight:600">+0.4</span>
          </div>
          <div style="display:flex;justify-content:space-between">
            <span>Good sample (N ≥ 50)</span>
            <span style="font-family:monospace;color:#059669;font-weight:600">+0.3</span>
          </div>
          <div style="display:flex;justify-content:space-between;border-top:1px dashed var(--border);margin-top:4px;padding-top:4px">
            <span>Obvious COI (+ nullifies bonuses)</span>
            <span style="font-family:monospace;color:#dc2626;font-weight:600">−3.0</span>
          </div>
          <div style="display:flex;justify-content:space-between">
            <span>Small sample (N &lt; 20)</span>
            <span style="font-family:monospace;color:#dc2626;font-weight:600">−0.5</span>
          </div>
          <div style="display:flex;justify-content:space-between">
            <span>Very small sample (N &lt; 10)</span>
            <span style="font-family:monospace;color:#dc2626;font-weight:600">−1.0</span>
          </div>
          <div style="display:flex;justify-content:space-between">
            <span>Predatory journal</span>
            <span style="font-family:monospace;color:#dc2626;font-weight:600">→ 1.0</span>
          </div>
        </div>
        """)

    with st.expander("🔬 Methodology Tools"):
        st.html("""
        <div style="font-size:12px;color:var(--text);line-height:1.6">
          <div style="margin-bottom:10px">
            <div style="font-weight:600;margin-bottom:2px">PEDro <span style="color:var(--text-secondary);font-weight:400">→ RCTs</span></div>
            <div style="color:var(--text-secondary)">11 items (C1 descriptive, C2–C11 scored). Sum of C2–C11 ÷ 10 × design cap.</div>
          </div>
          <div style="margin-bottom:10px">
            <div style="font-weight:600;margin-bottom:2px">AMSTAR-2 <span style="color:var(--text-secondary);font-weight:400">→ Systematic Reviews &amp; Meta-Analyses</span></div>
            <div style="color:var(--text-secondary)">16 items, 7 critical (A2, A4, A7, A9, A11, A13, A15). Critical ×1.5, others ×1.0.</div>
          </div>
          <div style="margin-bottom:10px">
            <div style="font-weight:600;margin-bottom:2px">NOS <span style="color:var(--text-secondary);font-weight:400">→ Cohort &amp; Cross-Sectional</span></div>
            <div style="color:var(--text-secondary)">9 stars: Selection (S1–S4), Comparability (C1–C2), Outcome (O1–O3).</div>
          </div>
          <div style="margin-bottom:10px">
            <div style="font-weight:600;margin-bottom:2px">GRADE <span style="color:var(--text-secondary);font-weight:400">→ Consensus Statements</span></div>
            <div style="color:var(--text-secondary)">8 items: search, grading, method, panel, COI, strength, gaps, review.</div>
          </div>
          <div>
            <div style="font-weight:600;margin-bottom:2px">Generic <span style="color:var(--text-secondary);font-weight:400">→ All other designs</span></div>
            <div style="color:var(--text-secondary)">Starts at 60% of cap, adjusted by sample size, effect sizes, CIs.</div>
          </div>
        </div>
        """)

    with st.expander("📋 Special Rules"):
        st.html("""
        <div style="font-size:12px;color:var(--text);line-height:1.7">
          <div style="margin-bottom:8px">
            <span style="font-weight:600">Elite Athlete Exception</span><br>
            <span style="color:var(--text-secondary)">Small sample penalty waived when population is elite/professional (e.g. N=15 national team players).</span>
          </div>
          <div style="margin-bottom:8px">
            <span style="font-weight:600">COI Filter</span><br>
            <span style="color:var(--text-secondary)">Only applied when COI is <em>obvious</em> (funder undeniably sells the tested product). Ambiguous COI is flagged but not penalized.</span>
          </div>
          <div style="margin-bottom:8px">
            <span style="font-weight:600">Black Flag</span><br>
            <span style="color:var(--text-secondary)">Reserved exclusively for predatory journals. Score forced to 1.0. COI alone does not trigger Black Flag.</span>
          </div>
          <div style="margin-bottom:8px">
            <span style="font-weight:600">Null-on-Unknown</span><br>
            <span style="color:var(--text-secondary)">If data cannot be reliably extracted, it is left null — never invented.</span>
          </div>
          <div>
            <span style="font-weight:600">Quality % explained</span><br>
            <span style="color:var(--text-secondary)">Score as % of the design cap (e.g. 6.5/7 = 93%). Enables fair comparison across study types regardless of design caps.</span>
          </div>
        </div>
        """)


# ── Main area ─────────────────────────────────────────────────────────────
st.html("""
<div style="background:var(--surface);border-bottom:1px solid var(--border);
            padding:16px 32px;margin:-2rem -1rem 0 -1rem;
            display:flex;align-items:center;gap:16px;box-shadow:var(--shadow)">
  <div style="width:36px;height:36px;background:var(--accent);border-radius:8px;
              display:flex;align-items:center;justify-content:center;
              color:white;font-weight:700;font-size:14px;flex-shrink:0">SQ</div>
  <h1 style="font-size:18px;font-weight:600;letter-spacing:-0.3px;margin:0">
    Sport Science Quality Analyzer
    <span style="color:var(--text-secondary);font-weight:400;font-size:14px;margin-left:8px">v2.0</span>
  </h1>
</div>
""")

tab_single, tab_batch = st.tabs(["Single PDF", "Batch Analysis"])

# ── Tab 1: Single ─────────────────────────────────────────────────────────
with tab_single:
    st.markdown("")
    uploaded_single = st.file_uploader(
        "Upload a PDF for methodological quality assessment (max 50 MB)",
        type=["pdf"],
        accept_multiple_files=False,
    )

    if uploaded_single:
        if st.button("Analyze Paper", type="primary", key="btn_single"):
            api_key = _resolve_key()
            with st.spinner("Gemini is analyzing the paper..."):
                try:
                    result = _analyze_one(uploaded_single.read(), uploaded_single.name, api_key)
                    st.session_state["single_result"] = result
                    st.session_state["single_filename"] = uploaded_single.name
                except QuotaExhaustedError:
                    st.error("Gemini API quota exhausted. Try again later or use a different key.")
                    st.stop()
                except InvalidAPIKeyError:
                    st.error("Invalid Gemini API key. Verify it at https://aistudio.google.com/apikey")
                    st.stop()

    if "single_result" in st.session_state:
        r: AnalysisResult = st.session_state["single_result"]
        fname: str = st.session_state.get("single_filename", "paper.pdf")

        if r.error:
            st.error(f"❌ Analysis failed: {r.error}")
        else:
            st.html(f"""
            <div class="row between" style="margin:12px 0">
              <div class="row">
                <span class="eyebrow">FILE</span>
                <span style="font-weight:600;max-width:500px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{fname}</span>
              </div>
            </div>
            """)
            st.html(_render_result_html(r, fname))

    elif not uploaded_single:
        st.html("""
        <div class="card" style="margin-top:16px">
          <h2>How it works</h2>
          <p class="sub">Automated extraction and scoring pipeline.</p>
          <ol style="padding-left:18px;font-size:13.5px;line-height:1.9;color:#1a1d23">
            <li><b>Extraction</b> · AI reads abstract, methods, sample size, funding and conflicts of interest</li>
            <li><b>Tool selection</b> · PEDro (RCT) / AMSTAR-2 (SR/Meta) / NOS (Cohort) / GRADE (Consensus) / Generic</li>
            <li><b>Scoring</b> · Raw score + institution/journal/sample bonuses + COI penalty</li>
            <li><b>Verdict</b> · 5-tier scale (Gold → Black Flag) + normalized quality ring for fair cross-design comparison</li>
          </ol>
          <div class="row wrap" style="gap:6px;margin-top:14px">
            <span class="chip chip-silver">⚡ 24h caching</span>
            <span class="chip chip-silver">🛡 COI detector</span>
            <span class="chip chip-silver">🏴 predatory check</span>
          </div>
        </div>
        """)

# ── Tab 2: Batch ──────────────────────────────────────────────────────────
with tab_batch:
    st.markdown("")
    uploaded_batch = st.file_uploader(
        "Upload up to 10 PDFs to compare them in a single run",
        type=["pdf"],
        accept_multiple_files=True,
        key="batch_uploader",
    )

    if uploaded_batch:
        if len(uploaded_batch) > 10:
            st.warning("Maximum 10 files — only the first 10 will be analyzed.")
            uploaded_batch = uploaded_batch[:10]
        st.caption(f"{len(uploaded_batch)} file(s) selected")

    if uploaded_batch:
        if st.button("Analyze Batch", type="primary", key="btn_batch"):
            api_key = _resolve_key()
            results: list[AnalysisResult] = []
            progress = st.progress(0, text="Starting batch analysis...")
            for i, f in enumerate(uploaded_batch):
                progress.progress(i / len(uploaded_batch), text=f"Analyzing {f.name} ({i+1}/{len(uploaded_batch)})...")
                try:
                    r = _analyze_one(f.read(), f.name, api_key)
                    results.append(r)
                except QuotaExhaustedError:
                    st.error("Gemini API quota exhausted. Try again later.")
                    break
                except InvalidAPIKeyError:
                    st.error("Invalid API key.")
                    break
            progress.progress(1.0, text="Done!")
            st.session_state["batch_results"] = results

    if "batch_results" in st.session_state and st.session_state["batch_results"]:
        results: list[AnalysisResult] = st.session_state["batch_results"]

        cat_order = ["gold_standard", "practical_evidence", "exploratory", "weak", "black_flag", "error"]
        results_sorted = sorted(
            results,
            key=lambda r: (cat_order.index(r.scoring.category) if r.scoring.category in cat_order else 99,
                           -r.scoring.final_score),
        )

        counts: dict[str, int] = {}
        for r in results:
            counts[r.scoring.category] = counts.get(r.scoring.category, 0) + 1

        pill_defs = [
            ("gold_standard", "🥇 Gold Standard"),
            ("practical_evidence", "🔵 Practical Evidence"),
            ("exploratory", "🔬 Exploratory"),
            ("weak", "⚠️ Weak"),
            ("black_flag", "🏴 Black Flag"),
        ]
        pills_html = "".join(
            f'<span class="summary-pill cat-{k}">{lbl} · {counts[k]}</span>'
            for k, lbl in pill_defs if k in counts
        )
        st.html(f'<div class="summary-row" style="margin-bottom:16px">{pills_html}</div>')

        for r in results_sorted:
            sc = r.scoring
            ed = r.extracted
            pct = round(sc.normalized_score)
            tool_label = sc.methodology_tool or "Generic"
            if sc.pedro_score is not None:   tool_label += f" {sc.pedro_score}/10"
            elif sc.nos_score is not None:    tool_label += f" {sc.nos_score}/9"
            elif sc.amstar2_met is not None:  tool_label += f" {sc.amstar2_met}/16"
            title_display = ed.title or r.filename or "Paper"
            exp_label = f"{sc.category_label} · {sc.final_score:.1f}/{sc.design_cap:.1f} · {title_display[:60]}"

            with st.expander(exp_label):
                if r.error:
                    st.error(f"Analysis failed: {r.error}")
                else:
                    st.html(_render_result_html(r, r.filename))
