export interface DecisionTreeGuidance {
  chunk_id: number;
  title: string;
  section: string;
  node_id: string;
  similarity: number;
  guidance: string;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

export function parseDecisionTreeGuidance(metadata: Record<string, unknown>): DecisionTreeGuidance | null {
  const raw = metadata.decision_tree_guidance;
  if (!isRecord(raw)) {
    return null;
  }

  const chunkId = Number(raw.chunk_id);
  const title = String(raw.title ?? "");
  const guidance = String(raw.guidance ?? "").trim();

  if (!Number.isFinite(chunkId) || !title || !guidance) {
    return null;
  }

  return {
    chunk_id: chunkId,
    title,
    section: String(raw.section ?? ""),
    node_id: String(raw.node_id ?? ""),
    similarity: Number(raw.similarity ?? 0),
    guidance,
  };
}
