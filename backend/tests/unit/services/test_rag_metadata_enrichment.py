"""Tests for RAG metadata enrichment helpers."""

from app.models.chunk_meta import ChunkMeta
from app.services.chat import ChatService


def test_enrich_rag_trace_steps_adds_missing_content_preview() -> None:
    chunk_map = {
        196: ChunkMeta(
            id=196,
            content="[Раздел: FAQ]\n[Тип: faq]\n\nЧто такое ЧС? Ответ...",
            content_type="faq",
            section="14. FAQ",
            title="Что такое чрезвычайная ситуация (ЧС)?",
            node_id="faq-196",
        ),
    }

    trace = [
        {
            "step": "retrieval",
            "duration_ms": 100,
            "data": {
                "hits": [
                    {
                        "id": 196,
                        "title": "Что такое чрезвычайная ситуация (ЧС)?",
                        "section": "14. FAQ",
                        "similarity": 0.6131,
                    },
                ],
            },
        },
    ]

    enriched = ChatService._enrich_rag_trace_steps(trace, chunk_map)

    assert enriched[0]["data"]["hits"][0]["content_preview"].startswith("[Раздел: FAQ]")


def test_chunk_ids_from_metadata_includes_trace_hits() -> None:
    metadata = {
        "retrieved_chunk_ids": [1],
        "rag_trace": [
            {
                "step": "retrieval",
                "data": {
                    "hits": [{"id": 196, "similarity": 0.5}],
                },
            },
        ],
    }

    chunk_ids = ChatService._chunk_ids_from_metadata(metadata)

    assert chunk_ids == {1, 196}
