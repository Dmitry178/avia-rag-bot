"""Multi-lane retrieval configuration for heterogeneous knowledge-base chapters."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RetrievalLane:
    """
    One retrieval corpus with its own top-k quota.
    """

    id: str
    content_types: frozenset[str]
    top_k: int
    source_label: str


SOP_LANE = RetrievalLane(
    id="sop",
    content_types=frozenset({"sop"}),
    top_k=8,
    source_label="Chapters 01–12 (operational SOP)",
)

FAQ_LANE = RetrievalLane(
    id="faq",
    content_types=frozenset({"faq"}),
    top_k=5,
    source_label="Chapter 14 FAQ + per-chapter FAQ (01–12)",
)

DECISION_TREE_LANE = RetrievalLane(
    id="decision_tree",
    content_types=frozenset({"decision_tree"}),
    top_k=3,
    source_label="Chapter 16 (decision trees)",
)

SCENARIO_LANE = RetrievalLane(
    id="scenario",
    content_types=frozenset({"scenario"}),
    top_k=3,
    source_label="Chapter 17 (practical scenarios)",
)

RETRIEVAL_LANES: tuple[RetrievalLane, ...] = (
    SOP_LANE,
    FAQ_LANE,
    DECISION_TREE_LANE,
    SCENARIO_LANE,
)

LANE_BY_ID: dict[str, RetrievalLane] = {lane.id: lane for lane in RETRIEVAL_LANES}

# FAISS returns global top rows; fetch extra rows so filtered lanes still fill their quota.
LANE_SEARCH_OVERSAMPLE = 10
LANE_SEARCH_MIN_FETCH = 80
