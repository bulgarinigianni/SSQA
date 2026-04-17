"""Weighted scoring engine for sport-science paper quality assessment.

Scoring pipeline:
1. Determine study design -> sets the maximum possible score (cap)
2. Compute base methodology score within that cap
3. Apply sample-size adjustments (elite exception + large-sample bonus)
4. Apply quality bonuses (institution, journal, field study, registered protocol)
5. Apply quality penalties (no control group)
6. Apply COI filter: only when OBVIOUS -> penalty + bonuses nullified (NOT black flag)
7. Check for predatory journal -> BLACK FLAG (only trigger for this category)
8. Clamp to [1, 10] and classify into category
"""

from __future__ import annotations

from .models import AMSTAR2Criteria, AnalysisResult, ConfidenceReport, ExtractedData, ScoringBreakdown

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
# 4. Predatory / Questionable Journals -> BLACK FLAG
# ---------------------------------------------------------------------------
PREDATORY_INDICATORS: list[str] = [
    # Known predatory publishers
    "omics international",
    "omics group",
    "science domain",
    "sciencedomain",
    "waset",
    "world academy of science",
    "david publishing",
    "iosr journal",
    "ijser",
    "ijsrp",
    "ijera",
    "iiste",
    "scienceopen",
    "zenodo",  # not a journal, preprint archive sometimes misused
    "academic journals inc",
    "granthaalayah",
    "sryahwa",
    "medwin publishers",
    "crimson publishers",
    "lupine publishers",
    "juniper publishers",
    "iris publishers",
    "scitechnol",
    "longdom",
    "hilaris",
    "imedpub",
    "allied academies",
    "pulsus",
    "insight medical publishing",
    "opast",
    "open access text",
    "biomedres",
    # Patterns / red-flag keywords (partial match)
    "predatory",
    "pay-to-publish",
]

# ---------------------------------------------------------------------------
# 5. COI Penalty (only for obvious COI)
# ---------------------------------------------------------------------------
COI_PENALTY_OBVIOUS = 3.0

# ---------------------------------------------------------------------------
# 6. Sample size thresholds
# ---------------------------------------------------------------------------
SAMPLE_SIZE_LARGE = 100
SAMPLE_SIZE_GOOD = 50
SAMPLE_SIZE_MODERATE = 20
SAMPLE_SIZE_SMALL = 10

LARGE_SAMPLE_BONUS = 0.4

ELITE_POPULATION_TYPES = {"elite", "professional"}

# ---------------------------------------------------------------------------
# 7. Additional bonuses
# ---------------------------------------------------------------------------
REGISTERED_PROTOCOL_BONUS = 0.5


# ===== Matching helpers =====

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


def _match_predatory(journal: str | None) -> str | None:
    """Return the matched predatory indicator or None."""
    if not journal:
        return None
    j_lower = journal.lower()
    for p in PREDATORY_INDICATORS:
        if p in j_lower:
            return p
    return None


# ===== Base methodology scoring =====

def _base_methodology_score_rct(data: ExtractedData, cap: float) -> tuple[float, int | None, int | None]:
    """Score an RCT using PEDro criteria. Returns (score, pedro_score, pedro_answered)."""
    if data.pedro_criteria is None:
        return cap * 0.5, None, None

    pedro = data.pedro_criteria
    pedro_score = pedro.score()
    pedro_answered = pedro.answered_count()

    score = (pedro_score / 10.0) * cap
    return score, pedro_score, pedro_answered


def _base_methodology_score_generic(data: ExtractedData, cap: float) -> float:
    """Score a non-RCT study based on available methodology indicators.

    Starts at 60% of cap, then adjusts based on quality signals.
    """
    base = cap * 0.6
    adjustments = 0.0

    if data.sample_size is not None:
        if data.sample_size >= SAMPLE_SIZE_GOOD:
            adjustments += cap * 0.15
        elif data.sample_size >= SAMPLE_SIZE_MODERATE:
            adjustments += cap * 0.08
        elif data.sample_size >= SAMPLE_SIZE_SMALL:
            adjustments += 0.0
        else:
            adjustments -= cap * 0.05

    if data.effect_size_reported is True:
        adjustments += cap * 0.08
    if data.confidence_intervals_reported is True:
        adjustments += cap * 0.07
    if data.statistical_methods:
        adjustments += cap * 0.05

    return max(cap * 0.3, min(cap, base + adjustments))


AMSTAR2_DESIGNS = {"meta_analysis", "systematic_review"}


def _base_methodology_score_amstar2(
    data: ExtractedData, cap: float
) -> tuple[float, int | None, int | None]:
    """Score a meta-analysis/systematic review using AMSTAR-2 weighted criteria.

    Critical criteria (7 items) are weighted 1.5×, non-critical (9) at 1.0×.
    When criteria are missing, falls back to 50% of cap.
    Returns (score, met_count, answered_count).
    """
    if data.amstar2_criteria is None:
        return cap * 0.5, None, None

    amstar = data.amstar2_criteria
    earned, max_possible = amstar.weighted_score()

    if max_possible == 0:
        return cap * 0.5, 0, 0

    ratio = earned / max_possible
    return ratio * cap, amstar.met_count(), amstar.answered_count()


NOS_DESIGNS = {"prospective_cohort", "cross_sectional"}


def _base_methodology_score_nos(
    data: ExtractedData, cap: float
) -> tuple[float, int | None, int | None]:
    """Score a cohort/cross-sectional study using the Newcastle-Ottawa Scale.

    9 items across 3 domains (Selection 4, Comparability 2, Outcome 3).
    Returns (score, nos_score, nos_answered).
    """
    if data.nos_criteria is None:
        return cap * 0.5, None, None

    nos = data.nos_criteria
    nos_score = nos.score()
    answered = nos.answered_count()

    if answered == 0:
        return cap * 0.5, 0, 0

    ratio = nos_score / answered
    return ratio * cap, nos_score, answered


# ===== Adjustments =====

def _sample_size_adjustment(data: ExtractedData) -> tuple[float, float, bool]:
    """Returns (standard_adjustment, large_sample_bonus, elite_exception_applied)."""
    if data.sample_size is None:
        return 0.0, 0.0, False

    is_elite = data.population_type in ELITE_POPULATION_TYPES
    std_adj = 0.0
    large_bonus = 0.0
    elite_exc = False

    # Large sample bonus (N >= 100)
    if data.sample_size >= SAMPLE_SIZE_LARGE:
        large_bonus = LARGE_SAMPLE_BONUS

    # Standard adjustment for small samples
    if data.sample_size < SAMPLE_SIZE_SMALL:
        if is_elite:
            elite_exc = True
        else:
            std_adj = -1.0
    elif data.sample_size < SAMPLE_SIZE_MODERATE:
        if is_elite:
            elite_exc = True
        else:
            std_adj = -0.5
    elif data.sample_size >= SAMPLE_SIZE_GOOD:
        std_adj = 0.3

    return std_adj, large_bonus, elite_exc


# ===== Classification =====

def _classify(score: float, predatory: bool) -> tuple[str, str]:
    """Classify the final score into a category.

    BLACK FLAG is reserved EXCLUSIVELY for predatory journals.
    COI papers keep their score-based category (with malus already applied).
    """
    if predatory:
        return "black_flag", "BLACK FLAG"
    if score >= 8.5:
        return "gold_standard", "GOLD STANDARD"
    if score >= 7.0:
        return "practical_evidence", "PRACTICAL EVIDENCE"
    if score >= 5.0:
        return "exploratory", "EXPLORATORY"
    return "weak", "WEAK"


# ===== Explanation builder =====

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

    if breakdown.amstar2_met is not None:
        parts.append(
            f"AMSTAR-2 assessment: {breakdown.amstar2_met}/16 criteria met "
            f"({breakdown.amstar2_answered}/16 assessable). "
            "Critical criteria weighted 1.5x in score calculation."
        )

    if breakdown.nos_score is not None:
        parts.append(
            f"NOS assessment: {breakdown.nos_score}/9 stars "
            f"({breakdown.nos_answered}/9 assessable)."
        )

    if breakdown.sample_size_adjustment != 0:
        if breakdown.sample_size_adjustment > 0:
            parts.append(f"Sample size bonus: +{breakdown.sample_size_adjustment:.1f}.")
        else:
            parts.append(f"Small sample size penalty: {breakdown.sample_size_adjustment:.1f}.")

    if breakdown.large_sample_bonus > 0:
        parts.append(f"Large sample (N>{SAMPLE_SIZE_LARGE}) bonus: +{breakdown.large_sample_bonus:.1f}.")

    if breakdown.elite_exception_applied:
        n = data.sample_size or "unknown"
        parts.append(
            f"Elite athlete exception applied: sample of {n} accepted "
            f"as population is {data.population_type}."
        )

    if breakdown.registered_protocol_bonus > 0:
        parts.append(f"Pre-registered protocol bonus: +{breakdown.registered_protocol_bonus:.1f}.")

    if breakdown.institutional_bonus > 0:
        names = ", ".join(breakdown.institutional_matches[:3])
        parts.append(f"Institutional authority bonus: +{breakdown.institutional_bonus:.1f} ({names}).")

    if breakdown.journal_bonus > 0:
        parts.append(
            f"Elite journal bonus: +{breakdown.journal_bonus:.1f} ({breakdown.journal_match})."
        )

    if breakdown.coi_detected:
        sev = breakdown.coi_severity or "obvious"
        parts.append(
            f"CONFLICT OF INTEREST ({sev}): funder sells the tested product. "
            f"COI penalty: -{breakdown.coi_penalty:.1f}. All bonuses nullified."
        )

    if breakdown.predatory_journal_detected:
        parts.append(
            f"PREDATORY JOURNAL DETECTED ({breakdown.predatory_journal_match}). "
            "Automatic BLACK FLAG — evidence from this source cannot be trusted."
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
    elif cat == "BLACK FLAG":
        parts.append(
            f"Verdict: {cat} ({score:.1f}/10) — published in a predatory journal; evidence unreliable."
        )

    return " ".join(parts)


# ===== Confidence =====

def compute_confidence(data: ExtractedData) -> ConfidenceReport:
    """Assess how complete the extraction was."""
    key_fields: dict[str, object] = {
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
        "has_control_group": data.has_control_group,
        "ecological_context": data.ecological_context,
        "main_findings_summary": data.main_findings_summary,
    }

    design = data.study_design or ""
    if design == "rct":
        key_fields["pedro_criteria"] = data.pedro_criteria
    elif design in AMSTAR2_DESIGNS:
        key_fields["amstar2_criteria"] = data.amstar2_criteria
    elif design in NOS_DESIGNS:
        key_fields["nos_criteria"] = data.nos_criteria

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


# ===== Main scoring pipeline =====

def score_paper(data: ExtractedData, filename: str = "unknown.pdf") -> AnalysisResult:
    """Run the full scoring pipeline on extracted paper data."""
    design = data.study_design or "other"
    cap = DESIGN_CAPS.get(design, 6.0)

    # --- 1. Base methodology score ---
    pedro_score = None
    pedro_answered = None
    amstar2_met = None
    amstar2_answered = None
    nos_score = None
    nos_answered = None
    methodology_tool = "Generic"

    if design == "rct":
        base, pedro_score, pedro_answered = _base_methodology_score_rct(data, cap)
        methodology_tool = "PEDro"
    elif design in AMSTAR2_DESIGNS:
        base, amstar2_met, amstar2_answered = _base_methodology_score_amstar2(data, cap)
        methodology_tool = "AMSTAR-2"
    elif design in NOS_DESIGNS:
        base, nos_score, nos_answered = _base_methodology_score_nos(data, cap)
        methodology_tool = "NOS"
    else:
        base = _base_methodology_score_generic(data, cap)

    # --- 2. Sample size adjustments ---
    sample_adj, large_bonus, elite_exception = _sample_size_adjustment(data)

    # --- 3. Quality bonuses ---
    inst_matches = _match_institution(data.affiliations)
    inst_bonus = INSTITUTIONAL_BONUS if inst_matches else 0.0

    journal_match = _match_journal(data.journal)
    j_bonus = JOURNAL_BONUS if journal_match else 0.0

    reg_bonus = REGISTERED_PROTOCOL_BONUS if data.registered_protocol is True else 0.0

    # --- 4. COI filter (only OBVIOUS = apply; ambiguous = ignore) ---
    coi_detected = (
        data.funder_sells_product is True
        and data.coi_severity == "obvious"
    )
    coi_pen = 0.0
    bonuses_nullified = False

    if coi_detected:
        coi_pen = COI_PENALTY_OBVIOUS
        bonuses_nullified = True

    # --- 6. Predatory journal check -> BLACK FLAG ---
    predatory_match = _match_predatory(data.journal)
    predatory_detected = predatory_match is not None

    # --- 7. Compute raw and final ---
    raw = base + sample_adj + large_bonus

    if bonuses_nullified:
        # COI: apply penalty, zero out all bonuses
        raw = raw - coi_pen
    else:
        raw = raw + inst_bonus + j_bonus + reg_bonus

    # Clamp to [1, cap]
    final = max(1.0, min(cap, raw))
    final = round(final, 1)

    # If predatory, force to 1.0
    if predatory_detected:
        final = 1.0

    # --- 8. Normalized score (percentage of cap) ---
    normalized = round((final / cap) * 100, 1) if cap > 0 else 0.0

    # --- 9. Classify ---
    category, category_label = _classify(final, predatory_detected)

    # --- Build breakdown ---
    breakdown = ScoringBreakdown(
        design_category=design,
        design_cap=cap,
        methodology_tool=methodology_tool,
        base_methodology_score=round(base, 2),
        pedro_score=pedro_score,
        pedro_answered=pedro_answered,
        amstar2_met=amstar2_met,
        amstar2_answered=amstar2_answered,
        nos_score=nos_score,
        nos_answered=nos_answered,
        sample_size_adjustment=sample_adj,
        large_sample_bonus=large_bonus,
        elite_exception_applied=elite_exception,
        institutional_bonus=inst_bonus if not bonuses_nullified else 0.0,
        institutional_matches=inst_matches,
        journal_bonus=j_bonus if not bonuses_nullified else 0.0,
        journal_match=journal_match,
        registered_protocol_bonus=reg_bonus if not bonuses_nullified else 0.0,
        coi_detected=coi_detected,
        coi_severity=data.coi_severity,
        coi_penalty=coi_pen,
        bonuses_nullified=bonuses_nullified,
        predatory_journal_detected=predatory_detected,
        predatory_journal_match=predatory_match,
        raw_score=round(raw, 2),
        final_score=final,
        normalized_score=normalized,
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
