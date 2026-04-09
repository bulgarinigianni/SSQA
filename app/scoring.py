"""Weighted scoring engine for sport-science paper quality assessment.

Scoring pipeline:
1. Determine study design → sets the maximum possible score (cap)
2. Compute base methodology score within that cap
3. Apply bonuses (institutional authority, journal prestige)
4. Apply COI filter (nullifies bonuses, heavy penalty)
5. Apply elite-athlete exception for small samples
6. Clamp to [1, 10] and classify into category
"""

from __future__ import annotations

from .models import AnalysisResult, ConfidenceReport, ExtractedData, ScoringBreakdown

# ---------------------------------------------------------------------------
# 1. Study Design Caps
# ---------------------------------------------------------------------------
DESIGN_CAPS: dict[str, float] = {
    "meta_analysis": 10.0,
    "systematic_review": 10.0,
    "rct": 10.0,
    "consensus_statement": 9.0,
    "prospective_cohort": 8.0,
    "cross_sectional": 7.0,
    "case_series": 5.5,
    "case_study": 5.0,
    "narrative_review": 6.0,
    "expert_opinion": 6.0,
    "other": 6.0,
}

DESIGN_LABELS: dict[str, str] = {
    "meta_analysis": "Meta-Analysis",
    "systematic_review": "Systematic Review",
    "rct": "Randomized Controlled Trial",
    "consensus_statement": "Consensus Statement",
    "prospective_cohort": "Prospective Cohort",
    "cross_sectional": "Cross-Sectional Study",
    "case_series": "Case Series",
    "case_study": "Case Study / Case Report",
    "narrative_review": "Narrative Review",
    "expert_opinion": "Expert Opinion",
    "other": "Other Design",
}

# ---------------------------------------------------------------------------
# 2. Institutional Authority Bonuses
# ---------------------------------------------------------------------------
ELITE_INSTITUTIONS: list[str] = [
    # International organizations
    "aspetar",
    "ioc",
    "international olympic committee",
    "fifa",
    "uefa",
    "world athletics",
    "wada",
    "fina",
    "world aquatics",
    # Top research centres
    "australian institute of sport",
    "ais",
    "english institute of sport",
    "insep",
    "karolinska",
    "loughborough university",
    "liverpool john moores",
    "norwegian school of sport sciences",
    "german sport university cologne",
    "sporthilfe",
    # Elite clubs with research departments
    "fc barcelona",
    "barcelona",
    "real madrid",
    "juventus",
    "bayern munich",
    "bayern münchen",
    "ac milan",
    "manchester united",
    "manchester city",
    "liverpool fc",
    "paris saint-germain",
    "psg",
    "ajax",
    "arsenal",
    "chelsea",
    "inter milan",
    "atletico madrid",
    # Elite national teams / federations
    "rfef",
    "figc",
    "dfb",
    "fa ",
    "knvb",
    "cbf",
]

INSTITUTIONAL_BONUS = 0.5

# ---------------------------------------------------------------------------
# 3. Journal Prestige Bonuses
# ---------------------------------------------------------------------------
ELITE_JOURNALS: list[str] = [
    "british journal of sports medicine",
    "bjsm",
    "medicine and science in sports and exercise",
    "medicine & science in sports & exercise",
    "msse",
    "sports medicine",
    "american journal of sports medicine",
    "ajsm",
    "journal of orthopaedic & sports physical therapy",
    "jospt",
    "journal of sports sciences",
    "journal of science and medicine in sport",
    "jsams",
    "scandinavian journal of medicine & science in sports",
    "international journal of sports physiology and performance",
    "ijspp",
    "european journal of sport science",
    "ejss",
    "journal of strength and conditioning research",
    "jscr",
    "journal of athletic training",
    "clinical journal of sport medicine",
    "knee surgery sports traumatology arthroscopy",
    "kssta",
    "the lancet",
    "lancet",
    "new england journal of medicine",
    "nejm",
    "bmj",
    "jama",
    "nature",
    "science",
]

JOURNAL_BONUS = 0.5

# ---------------------------------------------------------------------------
# 4. COI Penalty
# ---------------------------------------------------------------------------
COI_PENALTY = 3.0  # Points deducted when COI detected

# ---------------------------------------------------------------------------
# 5. Sample size thresholds
# ---------------------------------------------------------------------------
SAMPLE_SIZE_GOOD = 50
SAMPLE_SIZE_MODERATE = 20
SAMPLE_SIZE_SMALL = 10

ELITE_POPULATION_TYPES = {"elite", "professional"}


def _match_institution(affiliations: list[str]) -> list[str]:
    """Return list of matched elite institutions."""
    matches = []
    combined = " ".join(affiliations).lower()
    for inst in ELITE_INSTITUTIONS:
        if inst in combined:
            matches.append(inst)
    return matches


def _match_journal(journal: str | None) -> str | None:
    """Return the matched elite journal name or None."""
    if not journal:
        return None
    j_lower = journal.lower()
    for ej in ELITE_JOURNALS:
        if ej in j_lower or j_lower in ej:
            return ej
    return None


def _base_methodology_score_rct(data: ExtractedData, cap: float) -> tuple[float, int | None, int | None]:
    """Score an RCT using PEDro criteria. Returns (score, pedro_score, pedro_answered)."""
    if data.pedro_criteria is None:
        # If LLM couldn't extract PEDro, give a conservative mid-range score
        return cap * 0.5, None, None

    pedro = data.pedro_criteria
    pedro_score = pedro.score()
    pedro_answered = pedro.answered_count()

    # PEDro is out of 10; scale to cap
    # Score = (pedro_score / 10) * cap
    score = (pedro_score / 10.0) * cap
    return score, pedro_score, pedro_answered


def _base_methodology_score_generic(data: ExtractedData, cap: float) -> float:
    """Score a non-RCT study based on available methodology indicators.

    The score starts at 60% of the cap (every published paper deserves a
    baseline) and then adjusts up/down based on quality signals.
    """
    base = cap * 0.6
    adjustments = 0.0

    # Factor 1: Sample size (relative to design expectations)
    if data.sample_size is not None:
        if data.sample_size >= SAMPLE_SIZE_GOOD:
            adjustments += cap * 0.15
        elif data.sample_size >= SAMPLE_SIZE_MODERATE:
            adjustments += cap * 0.08
        elif data.sample_size >= SAMPLE_SIZE_SMALL:
            adjustments += 0.0  # neutral — expected for some designs
        else:
            adjustments -= cap * 0.05  # slight penalty, not catastrophic

    # Factor 2: Statistical rigor
    if data.effect_size_reported is True:
        adjustments += cap * 0.08
    if data.confidence_intervals_reported is True:
        adjustments += cap * 0.07

    # Factor 3: Methodology description quality
    if data.statistical_methods:
        adjustments += cap * 0.05

    # Clamp within [cap * 0.3, cap]
    return max(cap * 0.3, min(cap, base + adjustments))


def _sample_size_adjustment(data: ExtractedData) -> tuple[float, bool]:
    """Calculate sample size penalty/bonus. Returns (adjustment, elite_exception_applied)."""
    if data.sample_size is None:
        return 0.0, False

    is_elite = data.population_type in ELITE_POPULATION_TYPES

    if data.sample_size < SAMPLE_SIZE_SMALL:
        if is_elite:
            # Elite exception: no penalty for small samples
            return 0.0, True
        return -1.0, False

    if data.sample_size < SAMPLE_SIZE_MODERATE:
        if is_elite:
            return 0.0, True
        return -0.5, False

    if data.sample_size >= SAMPLE_SIZE_GOOD:
        return 0.3, False

    return 0.0, False


def _classify(score: float, coi_detected: bool) -> tuple[str, str]:
    """Classify the final score into a category. Returns (category_key, label).

    BLACK FLAG is reserved exclusively for COI-compromised papers.
    """
    if coi_detected:
        return "black_flag", "BLACK FLAG"
    if score >= 8.5:
        return "gold_standard", "GOLD STANDARD"
    if score >= 7.0:
        return "practical_evidence", "PRACTICAL EVIDENCE"
    if score >= 5.0:
        return "exploratory", "EXPLORATORY"
    return "weak", "WEAK"


def _build_explanation(data: ExtractedData, breakdown: ScoringBreakdown) -> str:
    """Generate a human-readable explanation of the score."""
    parts: list[str] = []

    design_label = DESIGN_LABELS.get(data.study_design or "other", "Unknown Design")
    parts.append(f"Study classified as {design_label} (score cap: {breakdown.design_cap}/10).")

    if breakdown.pedro_score is not None:
        parts.append(
            f"PEDro score: {breakdown.pedro_score}/10 "
            f"({breakdown.pedro_answered}/10 criteria assessable)."
        )

    if breakdown.sample_size_adjustment != 0:
        if breakdown.sample_size_adjustment > 0:
            parts.append(f"Large sample size bonus: +{breakdown.sample_size_adjustment:.1f}.")
        else:
            parts.append(f"Small sample size penalty: {breakdown.sample_size_adjustment:.1f}.")

    if breakdown.elite_exception_applied:
        n = data.sample_size or "unknown"
        parts.append(
            f"Elite athlete exception applied: sample of {n} accepted "
            f"as population is {data.population_type}."
        )

    if breakdown.institutional_bonus > 0:
        names = ", ".join(breakdown.institutional_matches[:3])
        parts.append(f"Institutional authority bonus: +{breakdown.institutional_bonus:.1f} ({names}).")

    if breakdown.journal_bonus > 0:
        parts.append(
            f"Elite journal bonus: +{breakdown.journal_bonus:.1f} ({breakdown.journal_match})."
        )

    if breakdown.coi_detected:
        parts.append(
            "CONFLICT OF INTEREST DETECTED: funder sells the tested product. "
            f"COI penalty: -{breakdown.coi_penalty:.1f}. All bonuses nullified."
        )

    # Final verdict
    cat = breakdown.category_label
    score = breakdown.final_score
    if cat == "GOLD STANDARD":
        parts.append(f"Verdict: {cat} ({score:.1f}/10) — high-quality evidence suitable for direct application.")
    elif cat == "PRACTICAL EVIDENCE":
        parts.append(f"Verdict: {cat} ({score:.1f}/10) — solid evidence with practical applicability.")
    elif cat == "EXPLORATORY":
        parts.append(f"Verdict: {cat} ({score:.1f}/10) — interesting findings but limited generalizability.")
    elif cat == "WEAK":
        parts.append(f"Verdict: {cat} ({score:.1f}/10) — methodological limitations reduce confidence.")
    else:
        parts.append(
            f"Verdict: {cat} ({score:.1f}/10) — evidence compromised by conflicts of interest or critical flaws."
        )

    return " ".join(parts)


def compute_confidence(data: ExtractedData) -> ConfidenceReport:
    """Assess how complete the extraction was."""
    key_fields = {
        "title": data.title,
        "authors": data.authors if data.authors else None,
        "year": data.year,
        "journal": data.journal,
        "study_design": data.study_design,
        "sample_size": data.sample_size,
        "population_type": data.population_type,
        "affiliations": data.affiliations if data.affiliations else None,
        "funding_sources": data.funding_sources if data.funding_sources else None,
        "conflict_of_interest_statement": data.conflict_of_interest_statement,
        "funder_sells_product": data.funder_sells_product,
        "statistical_methods": data.statistical_methods,
        "effect_size_reported": data.effect_size_reported,
        "main_findings_summary": data.main_findings_summary,
    }

    total = len(key_fields)
    missing = [k for k, v in key_fields.items() if v is None]
    extracted = total - len(missing)
    pct = round((extracted / total) * 100, 1)

    if pct >= 80:
        level = "high"
    elif pct >= 55:
        level = "medium"
    else:
        level = "low"

    return ConfidenceReport(
        total_fields=total,
        extracted_fields=extracted,
        missing_fields=missing,
        confidence_pct=pct,
        level=level,
    )


def score_paper(data: ExtractedData, filename: str = "unknown.pdf") -> AnalysisResult:
    """Run the full scoring pipeline on extracted paper data."""
    design = data.study_design or "other"
    cap = DESIGN_CAPS.get(design, 6.0)

    # --- Base methodology score ---
    pedro_score = None
    pedro_answered = None
    if design == "rct":
        base, pedro_score, pedro_answered = _base_methodology_score_rct(data, cap)
    else:
        base = _base_methodology_score_generic(data, cap)

    # --- Sample size adjustment ---
    sample_adj, elite_exception = _sample_size_adjustment(data)

    # --- Bonuses ---
    inst_matches = _match_institution(data.affiliations)
    inst_bonus = INSTITUTIONAL_BONUS if inst_matches else 0.0

    journal_match = _match_journal(data.journal)
    j_bonus = JOURNAL_BONUS if journal_match else 0.0

    # --- COI Filter ---
    coi_detected = data.funder_sells_product is True
    coi_pen = 0.0
    bonuses_nullified = False

    if coi_detected:
        coi_pen = COI_PENALTY
        bonuses_nullified = True

    # --- Compute raw and final ---
    raw = base + sample_adj
    if bonuses_nullified:
        raw = raw - coi_pen
    else:
        raw = raw + inst_bonus + j_bonus

    # Clamp to [1, cap] then [1, 10]
    final = max(1.0, min(cap, raw))
    final = round(final, 1)

    # --- Classify ---
    category, category_label = _classify(final, coi_detected)

    # --- Build breakdown ---
    breakdown = ScoringBreakdown(
        design_category=design,
        design_cap=cap,
        base_methodology_score=round(base, 2),
        pedro_score=pedro_score,
        pedro_answered=pedro_answered,
        sample_size_adjustment=sample_adj,
        elite_exception_applied=elite_exception,
        institutional_bonus=inst_bonus if not bonuses_nullified else 0.0,
        institutional_matches=inst_matches,
        journal_bonus=j_bonus if not bonuses_nullified else 0.0,
        journal_match=journal_match,
        coi_detected=coi_detected,
        coi_penalty=coi_pen,
        bonuses_nullified=bonuses_nullified,
        raw_score=round(raw, 2),
        final_score=final,
        category=category,
        category_label=category_label,
        explanation="",
    )
    breakdown.explanation = _build_explanation(data, breakdown)

    # --- Confidence ---
    confidence = compute_confidence(data)

    return AnalysisResult(
        filename=filename,
        extracted=data,
        scoring=breakdown,
        confidence=confidence,
    )
