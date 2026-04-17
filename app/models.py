from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel, Field


class PEDroCriteria(BaseModel):
    """PEDro scale criteria C1-C11. C1 is descriptive only; scoring uses C2-C11."""

    c1_eligibility_specified: bool | None = Field(None, description="Eligibility criteria specified (descriptive only)")
    c2_random_allocation: bool | None = Field(None, description="Subjects randomly allocated")
    c3_concealed_allocation: bool | None = Field(None, description="Allocation was concealed")
    c4_baseline_comparable: bool | None = Field(None, description="Groups similar at baseline")
    c5_blinding_subjects: bool | None = Field(None, description="Blinding of subjects")
    c6_blinding_therapists: bool | None = Field(None, description="Blinding of therapists")
    c7_blinding_assessors: bool | None = Field(None, description="Blinding of assessors")
    c8_adequate_followup: bool | None = Field(None, description="Adequate follow-up (>85%)")
    c9_intention_to_treat: bool | None = Field(None, description="Intention-to-treat analysis")
    c10_between_group: bool | None = Field(None, description="Between-group statistical comparison")
    c11_point_variability: bool | None = Field(None, description="Point measures and variability reported")

    def score(self) -> int:
        """Calculate PEDro score from C2-C11 (max 10)."""
        criteria = [
            self.c2_random_allocation,
            self.c3_concealed_allocation,
            self.c4_baseline_comparable,
            self.c5_blinding_subjects,
            self.c6_blinding_therapists,
            self.c7_blinding_assessors,
            self.c8_adequate_followup,
            self.c9_intention_to_treat,
            self.c10_between_group,
            self.c11_point_variability,
        ]
        return sum(1 for c in criteria if c is True)

    def answered_count(self) -> int:
        """How many of C2-C11 had a definite answer (not None)."""
        criteria = [
            self.c2_random_allocation,
            self.c3_concealed_allocation,
            self.c4_baseline_comparable,
            self.c5_blinding_subjects,
            self.c6_blinding_therapists,
            self.c7_blinding_assessors,
            self.c8_adequate_followup,
            self.c9_intention_to_treat,
            self.c10_between_group,
            self.c11_point_variability,
        ]
        return sum(1 for c in criteria if c is not None)


class AMSTAR2Criteria(BaseModel):
    """AMSTAR-2 criteria for systematic reviews and meta-analyses.

    7 critical criteria (items 2, 4, 7, 9, 11, 13, 15) are weighted 1.5x in scoring.
    """

    CRITICAL_KEYS: ClassVar[frozenset[str]] = frozenset(
        {"a2", "a4", "a7", "a9", "a11", "a13", "a15"}
    )

    a1_pico: bool | None = Field(None, description="Research questions and inclusion criteria include PICO components")
    a2_protocol_registered: bool | None = Field(None, description="Protocol registered before the review (CRITICAL)")
    a3_study_design_explained: bool | None = Field(None, description="Study design selection explained")
    a4_comprehensive_search: bool | None = Field(None, description="Comprehensive literature search strategy used (CRITICAL)")
    a5_duplicate_selection: bool | None = Field(None, description="Study selection performed in duplicate")
    a6_duplicate_extraction: bool | None = Field(None, description="Data extraction performed in duplicate")
    a7_excluded_studies_listed: bool | None = Field(None, description="List of excluded studies with justifications provided (CRITICAL)")
    a8_studies_described: bool | None = Field(None, description="Included studies described in adequate detail")
    a9_risk_of_bias_assessed: bool | None = Field(None, description="Satisfactory risk of bias assessment for included studies (CRITICAL)")
    a10_funding_reported: bool | None = Field(None, description="Funding sources of included studies reported")
    a11_statistical_methods: bool | None = Field(None, description="Appropriate statistical methods used for meta-analysis (CRITICAL)")
    a12_rob_impact_assessed: bool | None = Field(None, description="Impact of risk of bias on results assessed")
    a13_rob_in_interpretation: bool | None = Field(None, description="Risk of bias accounted for in discussion/interpretation (CRITICAL)")
    a14_heterogeneity_discussed: bool | None = Field(None, description="Heterogeneity discussed and explored")
    a15_publication_bias: bool | None = Field(None, description="Publication bias investigated and discussed (CRITICAL)")
    a16_coi_disclosed: bool | None = Field(None, description="Conflicts of interest disclosed by review authors")

    def _all_criteria(self) -> dict[str, bool | None]:
        return {
            "a1": self.a1_pico,
            "a2": self.a2_protocol_registered,
            "a3": self.a3_study_design_explained,
            "a4": self.a4_comprehensive_search,
            "a5": self.a5_duplicate_selection,
            "a6": self.a6_duplicate_extraction,
            "a7": self.a7_excluded_studies_listed,
            "a8": self.a8_studies_described,
            "a9": self.a9_risk_of_bias_assessed,
            "a10": self.a10_funding_reported,
            "a11": self.a11_statistical_methods,
            "a12": self.a12_rob_impact_assessed,
            "a13": self.a13_rob_in_interpretation,
            "a14": self.a14_heterogeneity_discussed,
            "a15": self.a15_publication_bias,
            "a16": self.a16_coi_disclosed,
        }

    def weighted_score(self) -> tuple[float, float]:
        """Weighted AMSTAR-2 score. Critical items = 1.5x, others = 1.0x.

        Returns (earned, max_possible) considering only answered items.
        """
        earned = 0.0
        max_possible = 0.0
        for key, val in self._all_criteria().items():
            if val is None:
                continue
            w = 1.5 if key in self.CRITICAL_KEYS else 1.0
            max_possible += w
            if val is True:
                earned += w
        return earned, max_possible

    def met_count(self) -> int:
        return sum(1 for v in self._all_criteria().values() if v is True)

    def answered_count(self) -> int:
        return sum(1 for v in self._all_criteria().values() if v is not None)


class NOSCriteria(BaseModel):
    """Newcastle-Ottawa Scale for cohort and cross-sectional studies. Max 9 stars."""

    s1_representativeness: bool | None = Field(None, description="Representativeness of the exposed cohort or sample")
    s2_non_exposed_selection: bool | None = Field(None, description="Selection of the non-exposed cohort or comparison group")
    s3_exposure_ascertainment: bool | None = Field(None, description="Ascertainment of exposure or risk factor")
    s4_outcome_not_present: bool | None = Field(None, description="Outcome of interest not present at start of study")
    c1_primary_factor: bool | None = Field(None, description="Study controls for the most important confounding factor")
    c2_additional_factor: bool | None = Field(None, description="Study controls for additional confounding factors")
    o1_outcome_assessment: bool | None = Field(None, description="Assessment of outcome (independent blind assessment or record linkage)")
    o2_followup_length: bool | None = Field(None, description="Follow-up long enough for outcomes to occur")
    o3_followup_adequacy: bool | None = Field(None, description="Adequacy of follow-up of cohorts (low attrition or complete data)")

    def _all_items(self) -> dict[str, bool | None]:
        return {
            "s1": self.s1_representativeness,
            "s2": self.s2_non_exposed_selection,
            "s3": self.s3_exposure_ascertainment,
            "s4": self.s4_outcome_not_present,
            "c1": self.c1_primary_factor,
            "c2": self.c2_additional_factor,
            "o1": self.o1_outcome_assessment,
            "o2": self.o2_followup_length,
            "o3": self.o3_followup_adequacy,
        }

    def score(self) -> int:
        """Count stars (True values), max 9."""
        return sum(1 for v in self._all_items().values() if v is True)

    def answered_count(self) -> int:
        return sum(1 for v in self._all_items().values() if v is not None)


class ExtractedData(BaseModel):
    """Structured data extracted from a sport-science paper by the LLM."""

    title: str | None = None
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    journal: str | None = None
    doi: str | None = None

    study_design: str | None = Field(
        None,
        description="One of: meta_analysis, systematic_review, rct, prospective_cohort, "
        "cross_sectional, case_series, case_study, narrative_review, expert_opinion, consensus_statement, other",
    )

    sample_size: int | None = None
    population_type: str | None = Field(
        None,
        description="One of: elite, professional, sub_elite, amateur, recreational, university_students, "
        "youth_academy, general_population, mixed, other",
    )
    sport: str | None = None

    affiliations: list[str] = Field(default_factory=list)
    funding_sources: list[str] = Field(default_factory=list)
    conflict_of_interest_statement: str | None = None
    product_tested: str | None = Field(None, description="Specific product/supplement/device being tested")
    funder_sells_product: bool | None = Field(
        None,
        description="True if a funding source commercially sells the product being tested",
    )
    coi_severity: str | None = Field(
        None,
        description="One of: obvious, ambiguous, none. "
        "'obvious' = funder explicitly sells the tested product and authors have disclosed ties. "
        "'ambiguous' = potential link but not clearly stated. "
        "'none' = no conflict detected.",
    )

    pedro_criteria: PEDroCriteria | None = Field(
        None, description="PEDro criteria — only for RCT designs"
    )
    amstar2_criteria: AMSTAR2Criteria | None = Field(
        None, description="AMSTAR-2 criteria — only for meta-analysis / systematic review designs"
    )
    nos_criteria: NOSCriteria | None = Field(
        None, description="Newcastle-Ottawa Scale — only for prospective cohort / cross-sectional designs"
    )

    statistical_methods: str | None = None
    effect_size_reported: bool | None = None
    confidence_intervals_reported: bool | None = None
    has_control_group: bool | None = Field(
        None, description="True if the study includes a control/comparison group"
    )
    ecological_context: str | None = Field(
        None,
        description="One of: field, laboratory, mixed, unclear. "
        "'field' = data collected during real training/competition. "
        "'laboratory' = controlled lab environment.",
    )
    registered_protocol: bool | None = Field(
        None,
        description="True if the study protocol was pre-registered (e.g. ClinicalTrials.gov, PROSPERO, OSF)",
    )
    main_findings_summary: str | None = None

    extraction_notes: str | None = Field(
        None,
        description="Any difficulties or ambiguities encountered during extraction",
    )


class ScoringBreakdown(BaseModel):
    """Detailed breakdown of how the final score was computed."""

    design_category: str
    design_cap: float
    methodology_tool: str = "Generic"
    base_methodology_score: float
    pedro_score: int | None = None
    pedro_answered: int | None = None
    amstar2_met: int | None = None
    amstar2_answered: int | None = None
    nos_score: int | None = None
    nos_answered: int | None = None
    sample_size_adjustment: float = 0.0
    large_sample_bonus: float = 0.0
    elite_exception_applied: bool = False
    institutional_bonus: float = 0.0
    institutional_matches: list[str] = Field(default_factory=list)
    journal_bonus: float = 0.0
    journal_match: str | None = None
    registered_protocol_bonus: float = 0.0
    coi_detected: bool = False
    coi_severity: str | None = None
    coi_penalty: float = 0.0
    bonuses_nullified: bool = False
    predatory_journal_detected: bool = False
    predatory_journal_match: str | None = None
    raw_score: float
    final_score: float
    normalized_score: float = Field(
        0.0,
        description="Final score as percentage of design cap (0-100). "
        "Allows fair comparison across study designs.",
    )
    category: str
    category_label: str
    explanation: str


class ConfidenceReport(BaseModel):
    """How confident the system is in its extraction."""

    total_fields: int
    extracted_fields: int
    missing_fields: list[str] = Field(default_factory=list)
    confidence_pct: float
    level: str  # high, medium, low


class AnalysisResult(BaseModel):
    """Complete analysis result for a single paper."""

    filename: str
    extracted: ExtractedData
    scoring: ScoringBreakdown
    confidence: ConfidenceReport
    error: str | None = None
