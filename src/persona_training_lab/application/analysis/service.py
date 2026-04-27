from __future__ import annotations

from dataclasses import dataclass

from persona_training_lab.application.ports.repositories import AnalysisReadRepositoryPort


@dataclass(slots=True, frozen=True)
class AnalysisResultSummary:
    result_id: str
    title: str
    subtitle: str
    left_title: str
    left_subtitle: str
    left_profile_match: str
    left_stability: str
    left_contradiction: str
    right_title: str
    right_subtitle: str
    right_profile_match: str
    right_stability: str
    right_contradiction: str
    delta_profile_match: str
    delta_stability: str
    delta_contradiction: str
    insight_1: str
    insight_2: str
    insight_3: str
    delta_1: str
    delta_2: str
    delta_3: str
    sample_1_title: str
    sample_1_left: str
    sample_1_right: str
    sample_2_title: str
    sample_2_left: str
    sample_2_right: str


@dataclass(slots=True)
class AnalysisService:
    analysis_repo: AnalysisReadRepositoryPort

    def list_analysis_results(self) -> list[AnalysisResultSummary]:
        rows = self.analysis_repo.list_analysis_results()
        return [
            AnalysisResultSummary(
                result_id=row.get("result_id", ""),
                title=row.get("title", ""),
                subtitle=row.get("subtitle", ""),
                left_title=row.get("left_title", ""),
                left_subtitle=row.get("left_subtitle", ""),
                left_profile_match=row.get("left_profile_match", ""),
                left_stability=row.get("left_stability", ""),
                left_contradiction=row.get("left_contradiction", ""),
                right_title=row.get("right_title", ""),
                right_subtitle=row.get("right_subtitle", ""),
                right_profile_match=row.get("right_profile_match", ""),
                right_stability=row.get("right_stability", ""),
                right_contradiction=row.get("right_contradiction", ""),
                delta_profile_match=row.get("delta_profile_match", ""),
                delta_stability=row.get("delta_stability", ""),
                delta_contradiction=row.get("delta_contradiction", ""),
                insight_1=row.get("insight_1", ""),
                insight_2=row.get("insight_2", ""),
                insight_3=row.get("insight_3", ""),
                delta_1=row.get("delta_1", ""),
                delta_2=row.get("delta_2", ""),
                delta_3=row.get("delta_3", ""),
                sample_1_title=row.get("sample_1_title", ""),
                sample_1_left=row.get("sample_1_left", ""),
                sample_1_right=row.get("sample_1_right", ""),
                sample_2_title=row.get("sample_2_title", ""),
                sample_2_left=row.get("sample_2_left", ""),
                sample_2_right=row.get("sample_2_right", ""),
            )
            for row in rows
        ]
