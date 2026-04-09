from __future__ import annotations

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

    pedro_criteria: PEDroCriteria | None = Field(
        None, description="PEDro criteria — only for RCT designs"
    )

    statistical_methods: str | None = None
    effect_size_reported: bool | None = None
    confidence_intervals_reported: bool | None = None
    main_findings_summary: str | None = None

    extraction_notes: str | None = Field(
        None,
        description="Any difficulties or ambiguities encountered during extraction",
    )


class ScoringBreakdown(BaseModel):
    """Detailed breakdown of how the final score was computed."""

    design_category: str
    design_cap: float
    base_methodology_score: float
    pedro_score: int | None = None
    pedro_answered: int | None = None
    sample_size_adjustment: float = 0.0
    elite_exception_applied: bool = False
    institutional_bonus: float = 0.0
    institutional_matches: list[str] = Field(default_factory=list)
    journal_bonus: float = 0.0
    journal_match: str | None = None
    coi_detected: bool = False
    coi_penalty: float = 0.0
    bonuses_nullified: bool = False
    raw_score: float
    final_score: float
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
