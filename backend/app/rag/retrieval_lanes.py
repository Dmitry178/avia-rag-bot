"""Schema-driven multi-lane retrieval configuration."""

from dataclasses import dataclass
from functools import lru_cache

from app.core.config import settings
from etl.chunking_schema import RetrievalLanePresentation, load_runtime_schema_for_language


@dataclass(frozen=True)
class LanePresentation:
    """
    Runtime presentation and verification settings for one retrieval lane.
    """

    ui_priority: int = 0
    ui_variant: str | None = None
    exclude_from_generation_context: bool = False
    verification_strategy: str = "none"
    verification_no_match_token: str | None = None
    max_verification_candidates: int = 1


@dataclass(frozen=True)
class RetrievalLane:
    """
    One retrieval corpus with its own top-k quota and similarity threshold.
    """

    id: str
    content_types: frozenset[str]
    top_k: int
    source_label: str
    oversample: int = 10
    min_fetch: int = 80
    min_similarity: float = 0.4
    presentation: LanePresentation = LanePresentation()


@dataclass(frozen=True)
class RetrievalRuntime:
    """
    Per-language retrieval runtime loaded from chunking schema.
    """

    lanes: tuple[RetrievalLane, ...]
    lane_by_id: dict[str, RetrievalLane]


def _lane_presentation(schema_presentation: RetrievalLanePresentation | None) -> LanePresentation:
    if schema_presentation is None:
        return LanePresentation()

    return LanePresentation(
        ui_priority=schema_presentation.ui_priority,
        ui_variant=schema_presentation.ui_variant,
        exclude_from_generation_context=schema_presentation.exclude_from_generation_context,
        verification_strategy=schema_presentation.verification_strategy,
        verification_no_match_token=schema_presentation.verification_no_match_token,
        max_verification_candidates=schema_presentation.max_verification_candidates,
    )


@lru_cache(maxsize=8)
def get_retrieval_runtime(language_code: str) -> RetrievalRuntime:
    """
    Build retrieval lanes for one language from schema.
    """

    context = load_runtime_schema_for_language(language_code, str(settings.backend_root))
    lanes: list[RetrievalLane] = []

    for lane in context.schema.retrieval_lanes:
        lanes.append(
            RetrievalLane(
                id=lane.id,
                content_types=frozenset(lane.allowed_category_ids),
                top_k=lane.top_k,
                source_label=lane.description,
                oversample=lane.oversample,
                min_fetch=lane.min_fetch,
                min_similarity=lane.min_similarity,
                presentation=_lane_presentation(lane.presentation),
            )
        )

    lane_tuple = tuple(lanes)

    return RetrievalRuntime(
        lanes=lane_tuple,
        lane_by_id={lane.id: lane for lane in lane_tuple},
    )
