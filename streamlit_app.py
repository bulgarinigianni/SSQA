"""Sport Science Quality Analyzer — Streamlit UI."""

from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path

import streamlit as st

from app.config import settings
from app.extractor import InvalidAPIKeyError, QuotaExhaustedError, extract_paper_data
from app.models import AnalysisResult, ConfidenceReport, ExtractedData, ScoringBreakdown
from app.pdf_parser import extract_text
from app.scoring import score_paper

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="SSQA — Sport Science Quality Analyzer",
    page_icon="🏋️",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@500;700&display=swap');

.main .block-container { max-width: 1100px; padding-top: 2rem; }

/* Category badges */
.cat-badge {
    display: inline-block; padding: 4px 14px; border-radius: 20px;
    font-size: 12px; font-weight: 700; letter-spacing: .5px; text-transform: uppercase;
}
.cat-gold       { background: #fef3c7; color: #92400e; border: 1px solid #fcd34d; }
.cat-practical  { background: #e5e7eb; color: #374151; border: 1px solid #d1d5db; }
.cat-exploratory{ background: #fef9c3; color: #854d0e; border: 1px solid #fde68a; }
.cat-weak       { background: #dbeafe; color: #1e40af; border: 1px solid #93c5fd; }
.cat-black      { background: #1f2937; color: #f87171; border: 1px solid #374151; }
.cat-error      { background: #fee2e2; color: #991b1b; border: 1px solid #fca5a5; }

/* Methodology badge */
.meth-badge {
    display: inline-block; padding: 3px 10px; border-radius: 12px;
    font-size: 11px; font-weight: 600;
    background: #f5f3ff; color: #7c3aed; border: 1px solid #ddd6fe;
}

/* Score ring (pure CSS) */
.score-ring-container {
    display: flex; align-items: center; justify-content: center;
}

/* Criteria grid */
.criteria-grid {
    display: flex; flex-wrap: wrap; gap: 6px; margin: 8px 0;
}
.criteria-cell {
    display: flex; flex-direction: column; align-items: center;
    min-width: 60px; padding: 4px 6px; border-radius: 6px;
    font-size: 11px; text-align: center;
}
.criteria-cell .key { font-weight: 700; font-size: 12px; font-family: 'JetBrains Mono', monospace; }
.criteria-cell .lbl { font-size: 9px; color: #6b7280; margin-top: 2px; }
.cell-met     { background: #d1fae5; color: #065f46; }
.cell-not-met { background: #fee2e2; color: #991b1b; }
.cell-unknown { background: #f3f4f6; color: #9ca3af; }
.cell-critical { border: 2px solid #7c3aed; }

/* Detail rows */
.detail-row { display: flex; justify-content: space-between; padding: 4px 0; font-size: 13px; border-bottom: 1px solid #f3f4f6; }
.detail-label { color: #6b7280; }
.detail-value { font-weight: 600; }
.val-pos { color: #059669; }
.val-neg { color: #ef4444; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown("# Sport Science Quality Analyzer")
st.caption("AI-powered audit tool for sport-science research quality assessment — v1.0")

# ---------------------------------------------------------------------------
# API Key
# ---------------------------------------------------------------------------
with st.expander("Gemini API Key (required)", expanded=not bool(st.session_state.get("api_key"))):
    st.markdown(
        "Enter your Gemini API key to enable paper analysis. "
        "Stored only in this session, never persisted. "
        "[Get a free key](https://aistudio.google.com/apikey)"
    )
    key_input = st.text_input(
        "API Key", type="password",
        value=st.session_state.get("api_key", ""),
        label_visibility="collapsed",
        placeholder="Paste your Gemini API key here",
    )
    if key_input:
        st.session_state["api_key"] = key_input.strip()
        st.success("Key active")
    elif st.session_state.get("api_key"):
        pass
    else:
        server_key = settings.gemini_api_key
        if server_key:
            st.info("Using server-configured key")
        else:
            st.warning("No key configured — analysis will fail")


def _resolve_key() -> str:
    key = st.session_state.get("api_key", "").strip() or settings.gemini_api_key
    if not key:
        st.error("No Gemini API key. Paste one above before analyzing.")
        st.stop()
    return key


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------
st.markdown("## Upload Research Papers")
st.markdown("Upload one or more PDF files for quality assessment (max 10).")

uploaded = st.file_uploader(
    "Upload PDFs", type=["pdf"], accept_multiple_files=True,
    label_visibility="collapsed",
)

if uploaded and len(uploaded) > 10:
    st.warning("Maximum 10 files — only the first 10 will be analyzed.")
    uploaded = uploaded[:10]

# ---------------------------------------------------------------------------
# Analysis pipeline
# ---------------------------------------------------------------------------

def _run_async(coro):
    """Run an async coroutine from sync Streamlit context."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


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
                base_methodology_score=0, raw_score=0,
                final_score=0, category="error",
                category_label="ERROR",
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


# ---------------------------------------------------------------------------
# Analyze button
# ---------------------------------------------------------------------------
if uploaded:
    if st.button("Analyze Papers", type="primary", use_container_width=True):
        api_key = _resolve_key()
        results: list[AnalysisResult] = []
        progress = st.progress(0, text="Starting analysis...")

        for i, f in enumerate(uploaded):
            progress.progress(
                (i) / len(uploaded),
                text=f"Analyzing {f.name} ({i+1}/{len(uploaded)})...",
            )
            try:
                r = _analyze_one(f.read(), f.name, api_key)
                results.append(r)
            except QuotaExhaustedError:
                st.error(
                    "Gemini API quota exhausted. Try again later or use a different key."
                )
                break
            except InvalidAPIKeyError:
                st.error(
                    "Invalid Gemini API key. Verify it at https://aistudio.google.com/apikey"
                )
                break

        progress.progress(1.0, text="Done!")
        st.session_state["results"] = results

# ---------------------------------------------------------------------------
# Helper functions for rendering
# ---------------------------------------------------------------------------
DESIGN_LABELS = {
    "meta_analysis": "Meta-Analysis", "systematic_review": "Systematic Review",
    "rct": "RCT", "consensus_statement": "Consensus Statement",
    "prospective_cohort": "Prospective Cohort", "cross_sectional": "Cross-Sectional",
    "case_series": "Case Series", "case_study": "Case Study",
    "narrative_review": "Narrative Review", "expert_opinion": "Expert Opinion",
    "other": "Other",
}

POP_LABELS = {
    "elite": "Elite Athletes", "professional": "Professional Athletes",
    "sub_elite": "Sub-Elite", "amateur": "Amateur", "recreational": "Recreational",
    "university_students": "University Students", "youth_academy": "Youth Academy",
    "general_population": "General Population", "mixed": "Mixed", "other": "Other",
}

CTX_LABELS = {"field": "Field", "laboratory": "Laboratory", "mixed": "Mixed", "unclear": "Unclear"}


def _cat_badge(category: str, label: str) -> str:
    cls_map = {
        "gold_standard": "cat-gold", "practical_evidence": "cat-practical",
        "exploratory": "cat-exploratory", "weak": "cat-weak",
        "black_flag": "cat-black", "error": "cat-error",
    }
    cls = cls_map.get(category, "cat-weak")
    return f'<span class="cat-badge {cls}">{label}</span>'


def _meth_badge(tool: str, s) -> str:
    if tool == "Generic":
        return ""
    extra = ""
    if tool == "PEDro" and s.pedro_score is not None:
        extra = f": {s.pedro_score}/10"
    elif tool == "AMSTAR-2" and s.amstar2_met is not None:
        extra = f": {s.amstar2_met}/16"
    elif tool == "NOS" and s.nos_score is not None:
        extra = f": {s.nos_score}/9"
    elif tool == "GRADE" and s.grade_met is not None:
        extra = f": {s.grade_met}/8"
    return f'<span class="meth-badge">{tool}{extra}</span>'


def _norm_color(pct: float) -> str:
    if pct >= 85: return "#d97706"
    if pct >= 70: return "#6b7280"
    if pct >= 50: return "#b45309"
    if pct >= 30: return "#2563eb"
    return "#1f2937"


def _criteria_html(key: str, label: str, val, critical: bool = False) -> str:
    if val is True:
        cls = "cell-met"
    elif val is False:
        cls = "cell-not-met"
    else:
        cls = "cell-unknown"
    crit = " cell-critical" if critical else ""
    return f'<div class="criteria-cell {cls}{crit}"><span class="key">{key}</span><span class="lbl">{label}</span></div>'


# ---------------------------------------------------------------------------
# Render results
# ---------------------------------------------------------------------------
if "results" in st.session_state and st.session_state["results"]:
    results: list[AnalysisResult] = st.session_state["results"]

    st.markdown("---")
    st.markdown("## Results")

    # Batch summary table
    if len(results) > 1:
        import pandas as pd
        rows = []
        for r in results:
            s = r.scoring
            e = r.extracted
            flags = ""
            if s.coi_detected:
                flags = "COI"
            elif s.predatory_journal_detected:
                flags = "PRED"
            else:
                flags = "OK"
            rows.append({
                "File": r.filename,
                "Score": f"{s.final_score:.1f}/{s.design_cap}",
                "Quality %": f"{s.normalized_score:.0f}%",
                "Category": s.category_label,
                "Design": DESIGN_LABELS.get(e.study_design or "", e.study_design or "—"),
                "N": e.sample_size if e.sample_size is not None else "—",
                "Flags": flags,
                "Confidence": f"{r.confidence.confidence_pct:.0f}%",
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        st.markdown("")

    # Detail cards
    for idx, r in enumerate(results):
        s = r.scoring
        e = r.extracted
        c = r.confidence

        if r.error:
            st.error(f"**{r.filename}**: {r.error}")
            continue

        with st.container(border=True):
            # Header row
            col_score, col_meta = st.columns([1, 4])

            with col_score:
                norm_color = _norm_color(s.normalized_score)
                st.markdown(
                    f'<div style="text-align:center;padding:10px 0">'
                    f'<div style="font-family:JetBrains Mono,monospace;font-size:32px;font-weight:700;color:{norm_color}">'
                    f'{s.normalized_score:.0f}%</div>'
                    f'<div style="font-size:13px;color:#9ca3af">{s.final_score:.1f} / {s.design_cap}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            with col_meta:
                title = e.title or r.filename
                authors = ", ".join(e.authors[:3]) if e.authors else "Unknown authors"
                if e.authors and len(e.authors) > 3:
                    authors += " et al."
                year_str = f" ({e.year})" if e.year else ""
                journal_str = f" — {e.journal}" if e.journal else ""

                badges = _cat_badge(s.category, s.category_label)
                mb = _meth_badge(s.methodology_tool, s)
                if mb:
                    badges += " " + mb

                st.markdown(
                    f'<div style="font-size:17px;font-weight:700;margin-bottom:2px">{title}</div>'
                    f'<div style="font-size:13px;color:#6b7280;margin-bottom:8px">{authors}{year_str}{journal_str}</div>'
                    f'{badges}',
                    unsafe_allow_html=True,
                )

            # Details in columns
            c1, c2 = st.columns(2)

            with c1:
                st.markdown("#### Study Information")
                info_rows = [
                    ("Design", DESIGN_LABELS.get(e.study_design or "", "—")),
                    ("Sample Size", str(e.sample_size) if e.sample_size is not None else "—"),
                    ("Population", POP_LABELS.get(e.population_type or "", "—")),
                    ("Sport", e.sport or "—"),
                    ("Context", CTX_LABELS.get(e.ecological_context or "", "—")),
                    ("Control Group", "Yes" if e.has_control_group is True else ("No" if e.has_control_group is False else "—")),
                    ("Registered Protocol", "Yes" if e.registered_protocol is True else ("No" if e.registered_protocol is False else "—")),
                ]
                if e.doi:
                    info_rows.append(("DOI", e.doi))
                html = ""
                for lbl, val in info_rows:
                    html += f'<div class="detail-row"><span class="detail-label">{lbl}</span><span class="detail-value">{val}</span></div>'
                st.markdown(html, unsafe_allow_html=True)

            with c2:
                st.markdown("#### Scoring Breakdown")
                score_rows = [
                    ("Design Cap", f"{s.design_cap}/10", ""),
                    ("Base Methodology", f"{s.base_methodology_score:.1f}", ""),
                    ("Sample Adj.", f"{'+' if s.sample_size_adjustment > 0 else ''}{s.sample_size_adjustment:.1f}",
                     "val-pos" if s.sample_size_adjustment > 0 else ("val-neg" if s.sample_size_adjustment < 0 else "")),
                ]
                if s.large_sample_bonus > 0:
                    score_rows.append(("Large Sample (N>=100)", f"+{s.large_sample_bonus:.1f}", "val-pos"))
                if s.elite_exception_applied:
                    score_rows.append(("Elite Exception", "Applied", "val-pos"))
                if s.registered_protocol_bonus > 0:
                    score_rows.append(("Registered Protocol", f"+{s.registered_protocol_bonus:.1f}", "val-pos"))
                score_rows.append((
                    "Institution Bonus",
                    "Nullified (COI)" if s.bonuses_nullified else (f"+{s.institutional_bonus:.1f}" if s.institutional_bonus > 0 else "0.0"),
                    "" if s.bonuses_nullified else ("val-pos" if s.institutional_bonus > 0 else ""),
                ))
                score_rows.append((
                    "Journal Bonus",
                    "Nullified (COI)" if s.bonuses_nullified else (f"+{s.journal_bonus:.1f}" if s.journal_bonus > 0 else "0.0"),
                    "" if s.bonuses_nullified else ("val-pos" if s.journal_bonus > 0 else ""),
                ))
                if s.coi_detected:
                    score_rows.append((f"COI Penalty ({s.coi_severity or 'obvious'})", f"-{s.coi_penalty:.1f}", "val-neg"))
                if s.predatory_journal_detected:
                    score_rows.append(("Predatory Journal", "BLACK FLAG", "val-neg"))
                score_rows.append(("Final Score", f"{s.final_score:.1f} / {s.design_cap}", ""))
                score_rows.append(("Relative Quality", f"{s.normalized_score:.0f}%", ""))

                html = ""
                for lbl, val, cls in score_rows:
                    cls_attr = f' class="detail-value {cls}"' if cls else ' class="detail-value"'
                    html += f'<div class="detail-row"><span class="detail-label">{lbl}</span><span{cls_attr}>{val}</span></div>'
                st.markdown(html, unsafe_allow_html=True)

            # Funding & COI + Confidence
            c3, c4 = st.columns(2)

            with c3:
                st.markdown("#### Funding & Conflicts")
                coi_val = f"YES ({s.coi_severity or 'obvious'})" if s.coi_detected else "No"
                coi_cls = "val-neg" if s.coi_detected else "val-pos"
                html = f'<div class="detail-row"><span class="detail-label">COI Detected</span><span class="detail-value {coi_cls}">{coi_val}</span></div>'
                if e.coi_severity == "ambiguous" and not s.coi_detected:
                    html += '<div class="detail-row"><span class="detail-label">COI Severity</span><span class="detail-value" style="color:#eab308">Ambiguous (not penalized)</span></div>'
                funders = ", ".join(e.funding_sources) if e.funding_sources else "Not reported"
                html += f'<div class="detail-row"><span class="detail-label">Funders</span><span class="detail-value">{funders}</span></div>'
                if e.product_tested:
                    html += f'<div class="detail-row"><span class="detail-label">Product Tested</span><span class="detail-value">{e.product_tested}</span></div>'
                st.markdown(html, unsafe_allow_html=True)
                if e.conflict_of_interest_statement:
                    coi_text = e.conflict_of_interest_statement[:200]
                    if len(e.conflict_of_interest_statement) > 200:
                        coi_text += "..."
                    st.caption(f'*"{coi_text}"*')

            with c4:
                st.markdown("#### Extraction Confidence")
                conf_color = {"high": "#059669", "medium": "#eab308", "low": "#ef4444"}.get(c.level, "#6b7280")
                st.markdown(
                    f'<div class="detail-row"><span class="detail-label">Data Extracted</span>'
                    f'<span class="detail-value">{c.extracted_fields}/{c.total_fields} fields ({c.confidence_pct:.0f}%)</span></div>',
                    unsafe_allow_html=True,
                )
                st.progress(c.confidence_pct / 100)
                if c.missing_fields:
                    st.caption(f"Missing: {', '.join(c.missing_fields)}")
                if e.extraction_notes:
                    st.caption(f"*{e.extraction_notes}*")

            # Methodology criteria grids
            if e.pedro_criteria and e.study_design == "rct":
                st.markdown("#### PEDro Scale (C2-C11 scored)")
                pc = e.pedro_criteria
                cells = [
                    ("C1", "Eligibility", pc.c1_eligibility_specified),
                    ("C2", "Random Alloc.", pc.c2_random_allocation),
                    ("C3", "Concealed", pc.c3_concealed_allocation),
                    ("C4", "Baseline", pc.c4_baseline_comparable),
                    ("C5", "Blind Subj.", pc.c5_blinding_subjects),
                    ("C6", "Blind Ther.", pc.c6_blinding_therapists),
                    ("C7", "Blind Assess.", pc.c7_blinding_assessors),
                    ("C8", "Follow-up", pc.c8_adequate_followup),
                    ("C9", "ITT", pc.c9_intention_to_treat),
                    ("C10", "Between-Grp", pc.c10_between_group),
                    ("C11", "Point&Var", pc.c11_point_variability),
                ]
                html = '<div class="criteria-grid">' + "".join(_criteria_html(k, l, v) for k, l, v in cells) + "</div>"
                st.markdown(html, unsafe_allow_html=True)
                if s.pedro_score is not None:
                    st.caption(f"PEDro Score: {s.pedro_score}/10")

            if e.amstar2_criteria and e.study_design in ("meta_analysis", "systematic_review"):
                st.markdown("#### AMSTAR-2 (critical items highlighted)")
                ac = e.amstar2_criteria
                CRITICAL = {"A2", "A4", "A7", "A9", "A11", "A13", "A15"}
                items = [
                    ("A1", "PICO", ac.a1_pico),
                    ("A2", "Protocol", ac.a2_protocol_registered),
                    ("A3", "Design", ac.a3_study_design_explained),
                    ("A4", "Search", ac.a4_comprehensive_search),
                    ("A5", "Dup Select", ac.a5_duplicate_selection),
                    ("A6", "Dup Extract", ac.a6_duplicate_extraction),
                    ("A7", "Excluded", ac.a7_excluded_studies_listed),
                    ("A8", "Described", ac.a8_studies_described),
                    ("A9", "RoB", ac.a9_risk_of_bias_assessed),
                    ("A10", "Funding", ac.a10_funding_reported),
                    ("A11", "Stats", ac.a11_statistical_methods),
                    ("A12", "RoB Impact", ac.a12_rob_impact_assessed),
                    ("A13", "RoB Interp", ac.a13_rob_in_interpretation),
                    ("A14", "Heterogen.", ac.a14_heterogeneity_discussed),
                    ("A15", "Pub Bias", ac.a15_publication_bias),
                    ("A16", "COI", ac.a16_coi_disclosed),
                ]
                html = '<div class="criteria-grid">' + "".join(
                    _criteria_html(k, l, v, critical=(k in CRITICAL)) for k, l, v in items
                ) + "</div>"
                st.markdown(html, unsafe_allow_html=True)
                if s.amstar2_met is not None:
                    st.caption(f"Criteria Met: {s.amstar2_met}/16")

            if e.nos_criteria and e.study_design in ("prospective_cohort", "cross_sectional"):
                st.markdown("#### Newcastle-Ottawa Scale (9 stars)")
                nc = e.nos_criteria
                domains = [
                    ("Selection", [
                        ("S1", "Representat.", nc.s1_representativeness),
                        ("S2", "Non-Exposed", nc.s2_non_exposed_selection),
                        ("S3", "Exposure", nc.s3_exposure_ascertainment),
                        ("S4", "Outcome Abs.", nc.s4_outcome_not_present),
                    ]),
                    ("Comparability", [
                        ("C1", "Primary", nc.c1_primary_factor),
                        ("C2", "Additional", nc.c2_additional_factor),
                    ]),
                    ("Outcome", [
                        ("O1", "Assessment", nc.o1_outcome_assessment),
                        ("O2", "FU Length", nc.o2_followup_length),
                        ("O3", "FU Adequacy", nc.o3_followup_adequacy),
                    ]),
                ]
                for domain_name, items in domains:
                    st.caption(f"**{domain_name}**")
                    html = '<div class="criteria-grid">' + "".join(
                        _criteria_html(k, l, v) for k, l, v in items
                    ) + "</div>"
                    st.markdown(html, unsafe_allow_html=True)
                if s.nos_score is not None:
                    st.caption(f"Stars Awarded: {s.nos_score}/9")

            if e.grade_criteria and e.study_design == "consensus_statement":
                st.markdown("#### GRADE Consensus Quality (8 items)")
                gc = e.grade_criteria
                items = [
                    ("G1", "Search", gc.g1_systematic_search),
                    ("G2", "Graded", gc.g2_evidence_graded),
                    ("G3", "Method", gc.g3_consensus_method),
                    ("G4", "Panel", gc.g4_panel_composition),
                    ("G5", "COI Mgmt", gc.g5_coi_management),
                    ("G6", "Strength", gc.g6_recommendation_strength),
                    ("G7", "Gaps", gc.g7_evidence_gaps),
                    ("G8", "Review", gc.g8_external_review),
                ]
                html = '<div class="criteria-grid">' + "".join(
                    _criteria_html(k, l, v) for k, l, v in items
                ) + "</div>"
                st.markdown(html, unsafe_allow_html=True)
                if s.grade_met is not None:
                    st.caption(f"Criteria Met: {s.grade_met}/8")

            # Explanation
            st.markdown(f"**Assessment:** {s.explanation}")

# ---------------------------------------------------------------------------
# Scoring Reference (always visible, collapsed)
# ---------------------------------------------------------------------------
st.markdown("---")
with st.expander("Scoring Parameters Reference"):

    r1, r2 = st.columns(2)

    with r1:
        st.markdown("##### Study Design Caps")
        st.markdown("""
| Design | Max Score |
|---|---|
| Meta-Analysis | 10 |
| Systematic Review | 10 |
| RCT | 10 |
| Consensus Statement | 9 |
| Prospective Cohort | 8 |
| Cross-Sectional | 7 |
| Narrative Review / Expert Opinion | 6 |
| Case Series | 5.5 |
| Case Study | 5 |
""")

    with r2:
        st.markdown("##### Quality Categories")
        st.markdown("""
| Category | Score Range |
|---|---|
| GOLD STANDARD | >= 8.5 |
| PRACTICAL EVIDENCE | 7.0 - 8.4 |
| EXPLORATORY | 5.0 - 6.9 |
| WEAK | < 5.0 |
| BLACK FLAG | Predatory journal |
""")

    st.markdown("##### Bonuses & Penalties")
    st.markdown("""
| Modifier | Value | Condition |
|---|---|---|
| Elite Institution | +0.5 | Aspetar, IOC, UEFA, top clubs, etc. |
| Elite Journal | +0.5 | BJSM, MSSE, AJSM, Lancet, etc. |
| Large Sample | +0.4 | N >= 100 |
| Registered Protocol | +0.5 | Pre-registered on ClinicalTrials.gov, PROSPERO, OSF |
| Good Sample | +0.3 | N >= 50 |
| COI Penalty | -3.0 | Obvious COI + all bonuses nullified |
| Small Sample | -0.5 / -1.0 | N < 20 / N < 10 (waived for elite athletes) |
| Predatory Journal | BLACK FLAG | Score forced to 1.0 |
""")

    st.markdown("##### Methodology Assessment Tools")
    st.markdown("""
| Tool | Applies To | Scoring |
|---|---|---|
| **PEDro** | RCTs | Sum of C2-C11 (max 10), ratio x cap |
| **AMSTAR-2** | SR & Meta-Analyses | Weighted: critical x1.5, ratio x cap |
| **NOS** | Cohort & Cross-Sectional | Stars / assessable, ratio x cap |
| **GRADE** | Consensus Statements | Met / assessable, ratio x cap |
| **Generic** | All other designs | Starts at 60% cap, adjusted |
""")
