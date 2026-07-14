const DECISION_TREE_NO_MATCH_TOKEN = "NO_DECISION_TREE_MATCH";

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

function normalizeDecisionTreeNoMatchLine(line: string): string {
  const trimmed = line.trim();
  const withoutWrappers = trimmed.replace(/^[`"'*_\s]+|[`"'*_\s.:;,!?]+$/g, "");

  return withoutWrappers.toUpperCase();
}

export function isDecisionTreeNoMatchGuidance(guidance: string): boolean {
  if (!guidance.trim()) {
    return true;
  }

  return guidance
    .split(/\r?\n/)
    .some((line) => normalizeDecisionTreeNoMatchLine(line) === DECISION_TREE_NO_MATCH_TOKEN);
}

export function parseDecisionTreeGuidance(metadata: Record<string, unknown>): DecisionTreeGuidance | null {
  const raw = metadata.decision_tree_guidance;
  if (!isRecord(raw)) {
    return null;
  }

  const chunkId = Number(raw.chunk_id);
  const title = String(raw.title ?? "");
  const guidance = String(raw.guidance ?? "").trim();

  if (!Number.isFinite(chunkId) || !title || !guidance || isDecisionTreeNoMatchGuidance(guidance)) {
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
