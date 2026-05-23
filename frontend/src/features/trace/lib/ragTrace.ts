import type { TraceEvent } from "@/shared/api/types";

export interface RetrievedChunkInfo {
  citation_index: number;
  id: number;
  section: string;
  title: string;
  content_type: string;
  score: number | null;
  similarity: number | null;
  source_query: string | null;
  token_count: number;
  node_id: string;
  content_preview: string;
}

export interface TraceHit {
  id: number;
  title: string;
  section: string;
  similarity: number;
}

export interface RagMessageTrace {
  messageId: number;
  searchQueries: string[];
  traceSteps: TraceEvent[];
  chunks: RetrievedChunkInfo[];
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function parseTraceSteps(value: unknown): TraceEvent[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .filter(isRecord)
    .map((step) => ({
      step: String(step.step ?? ""),
      timestamp: String(step.timestamp ?? ""),
      duration_ms: Number(step.duration_ms ?? 0),
      data: isRecord(step.data) ? step.data : {},
    }))
    .filter((step) => step.step.length > 0);
}

function parseScore(value: unknown): number | null {
  if (value === null || value === undefined) {
    return null;
  }

  const score = Number(value);
  return Number.isFinite(score) ? score : null;
}

export function parseTraceHits(value: unknown): TraceHit[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .filter(isRecord)
    .map((hit) => ({
      id: Number(hit.id),
      title: String(hit.title ?? ""),
      section: String(hit.section ?? ""),
      similarity: parseScore(hit.similarity) ?? 0,
    }))
    .filter((hit) => Number.isFinite(hit.id));
}

function similarityByIdFromTrace(traceSteps: TraceEvent[]): Map<number, number> {
  const scores = new Map<number, number>();

  for (const step of traceSteps) {
    if (step.step !== "retrieval" && step.step !== "rerank") {
      continue;
    }

    for (const hit of parseTraceHits(step.data.hits)) {
      scores.set(hit.id, hit.similarity);
    }
  }

  return scores;
}

function parseRetrievedChunks(value: unknown): RetrievedChunkInfo[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .filter(isRecord)
    .map((chunk, index) => ({
      citation_index: Number(chunk.citation_index ?? index + 1),
      id: Number(chunk.id),
      section: String(chunk.section ?? ""),
      title: String(chunk.title ?? ""),
      content_type: String(chunk.content_type ?? ""),
      score: parseScore(chunk.score),
      similarity: parseScore(chunk.similarity) ?? parseScore(chunk.score),
      source_query: chunk.source_query == null ? null : String(chunk.source_query),
      token_count: Number(chunk.token_count ?? 0),
      node_id: String(chunk.node_id ?? ""),
      content_preview: String(chunk.content_preview ?? ""),
    }))
    .filter((chunk) => Number.isFinite(chunk.id));
}

function parseChunkIds(value: unknown): number[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value.map(Number).filter((id) => Number.isFinite(id));
}

function chunkIdsFromTrace(traceSteps: TraceEvent[]): number[] {
  const rerankStep = [...traceSteps].reverse().find((step) => step.step === "rerank");
  if (rerankStep && isRecord(rerankStep.data)) {
    const rerankHits = parseTraceHits(rerankStep.data.hits);
    if (rerankHits.length > 0) {
      return rerankHits.map((hit) => hit.id);
    }

    const rerankIds = parseChunkIds(rerankStep.data.chunk_ids);
    if (rerankIds.length > 0) {
      return rerankIds;
    }
  }

  const retrievalStep = [...traceSteps].reverse().find((step) => step.step === "retrieval");
  if (retrievalStep && isRecord(retrievalStep.data)) {
    const retrievalHits = parseTraceHits(retrievalStep.data.hits);
    if (retrievalHits.length > 0) {
      return retrievalHits.slice(0, 5).map((hit) => hit.id);
    }

    return parseChunkIds(retrievalStep.data.chunk_ids).slice(0, 5);
  }

  return [];
}

function buildFallbackChunks(metadata: Record<string, unknown>, traceSteps: TraceEvent[]): RetrievedChunkInfo[] {
  const chunkIds = parseChunkIds(metadata.retrieved_chunk_ids);
  const resolvedIds = chunkIds.length > 0 ? chunkIds : chunkIdsFromTrace(traceSteps);
  const similarityById = similarityByIdFromTrace(traceSteps);

  return resolvedIds.map((id, index) => ({
    citation_index: index + 1,
    id,
    section: "",
    title: "",
    content_type: "",
    score: similarityById.get(id) ?? null,
    similarity: similarityById.get(id) ?? null,
    source_query: null,
    token_count: 0,
    node_id: "",
    content_preview: "",
  }));
}

function parseSearchQueries(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value.map(String).filter((query) => query.length > 0);
}

export function extractRagTraceFromMetadata(metadata: Record<string, unknown>): Omit<
  RagMessageTrace,
  "messageId"
> | null {
  const traceSteps = parseTraceSteps(metadata.rag_trace);
  const searchQueries = parseSearchQueries(metadata.search_queries);
  let chunks = parseRetrievedChunks(metadata.retrieved_chunks);

  if (chunks.length === 0) {
    chunks = buildFallbackChunks(metadata, traceSteps);
  } else {
    const similarityById = similarityByIdFromTrace(traceSteps);

    chunks = chunks.map((chunk) => {
      const similarity = chunk.similarity ?? similarityById.get(chunk.id) ?? chunk.score;

      return {
        ...chunk,
        similarity,
        score: similarity,
      };
    });
  }

  if (traceSteps.length === 0 && chunks.length === 0 && searchQueries.length === 0) {
    return null;
  }

  return { searchQueries, traceSteps, chunks };
}

export function findLatestRagTrace(
  messages: Array<{ id: number; role: string; metadata: Record<string, unknown> }>,
): RagMessageTrace | null {
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    const message = messages[index];

    if (message.role !== "assistant") {
      continue;
    }

    const trace = extractRagTraceFromMetadata(message.metadata);
    if (trace === null) {
      continue;
    }

    return {
      messageId: message.id,
      ...trace,
    };
  }

  return null;
}
