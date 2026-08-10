"""FAQ regex helpers for schema-driven chunking."""

import re


def build_faq_pair_regex(question_marker: str, answer_marker: str) -> re.Pattern[str]:
    """
    Build regex that extracts FAQ pairs using literal markers.
    """

    question = re.escape(question_marker)
    answer = re.escape(answer_marker)
    pattern = (
        rf"(?:^|\n)\s*(?:\*\s+)?{question}\s*(?P<question>.+?)\s*\n"
        rf"\s*(?:\*\s+)?{answer}\s*(?P<answer>.+?)"
        rf"(?=\n\s*(?:\*\s+)?{question}|\Z)"
    )

    return re.compile(pattern, re.DOTALL)
