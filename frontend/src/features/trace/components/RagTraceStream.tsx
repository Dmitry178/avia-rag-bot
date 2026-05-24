import { useTranslation } from "@/shared/i18n";
import type { TraceEvent } from "@/shared/api/types";
import type { RagMessageTrace, TraceHit } from "../lib/ragTrace";
import { parseTraceHits } from "../lib/ragTrace";

const TRACE_STEP_KEYS = new Set([
  "retrieval",
  "generation",
  "router",
  "rerank",
  "hyde",
  "multi_query",
  "query_rewriting",
  "faq_match",
  "guard",
]);

function formatSimilarity(score: number): string {
  return score.toFixed(4);
}

function stepLabel(t: (key: string) => string, step: string): string {
  if (TRACE_STEP_KEYS.has(step)) {
    return t(`trace.steps.${step}`);
  }

  return step;
}

function chunkDisplaySimilarity(chunk: RagMessageTrace["chunks"][number]): number | null {
  return chunk.similarity ?? chunk.score;
}

function isHitTraceStep(event: TraceEvent): boolean {
  return parseTraceHits(event.data.hits).length > 0;
}

function TraceHitRow({
  hit,
  index,
  chunkPreview,
  t,
}: {
  hit: TraceHit;
  index: number;
  chunkPreview: string;
  t: (key: string) => string;
}) {
  const preview = chunkPreview || hit.content_preview;

  return (
    <li className="trace-hit">
      <details className="trace-hit__details">
        <summary className="trace-hit__summary">
          <span className="trace-hit__leading">
            <span className="trace-hit__chevron" aria-hidden="true">
              ▸
            </span>
            <span className="trace-hit__rank">{index + 1}</span>
          </span>
          <span className="trace-hit__similarity" title={t("trace.chunkSimilarity")}>
            {formatSimilarity(hit.similarity)}
          </span>
          <div className="trace-hit__content">
            <span className="trace-hit__title">{hit.title || `#${hit.id}`}</span>
            {hit.section ? <span className="trace-hit__section">{hit.section}</span> : null}
            <span className="trace-hit__id">#{hit.id}</span>
          </div>
        </summary>

        {preview ? (
          <pre className="trace-hit__preview">{preview}</pre>
        ) : (
          <p className="trace-hit__preview trace-hit__preview--empty">{t("trace.noChunkPreview")}</p>
        )}
      </details>
    </li>
  );
}

function TraceStepHits({
  step,
  data,
  chunkPreviewById,
  t,
}: {
  step: string;
  data: Record<string, unknown>;
  chunkPreviewById: Map<number, string>;
  t: (key: string, params?: Record<string, string | number>) => string;
}) {
  const hits = step === "retrieval" || step === "rerank" ? parseTraceHits(data.hits) : [];

  if (hits.length === 0) {
    return null;
  }

  const queryCount = Number(data.query_count);
  const candidateCount = Number(data.candidate_count);

  return (
    <div className="trace-step__hits">
      {step === "retrieval" && Number.isFinite(queryCount) && Number.isFinite(candidateCount) ? (
        <p className="trace-step__summary">
          {t("trace.retrievalSummary", {
            queryCount,
            candidateCount,
          })}
        </p>
      ) : null}

      <ol className="trace-hit-list">
        {hits.map((hit, index) => (
          <TraceHitRow
            key={`${hit.id}-${index}`}
            hit={hit}
            index={index}
            chunkPreview={chunkPreviewById.get(hit.id) ?? ""}
            t={t}
          />
        ))}
      </ol>
    </div>
  );
}

function CollapsibleTraceStep({
  event,
  chunkPreviewById,
  t,
}: {
  event: TraceEvent;
  chunkPreviewById: Map<number, string>;
  t: (key: string, params?: Record<string, string | number>) => string;
}) {
  const hits = parseTraceHits(event.data.hits);
  if (hits.length === 0) {
    return null;
  }

  return (
    <details className="trace-step">
      <summary className="trace-step__title">
        {stepLabel(t, event.step)}
        {event.duration_ms ? ` · ${t("trace.durationMs", { ms: event.duration_ms })}` : ""}
        <span className="trace-step__count">{hits.length}</span>
      </summary>
      <TraceStepHits
        step={event.step}
        data={event.data}
        chunkPreviewById={chunkPreviewById}
        t={t}
      />
    </details>
  );
}

function buildChunkPreviewById(trace: RagMessageTrace): Map<number, string> {
  const previewById = new Map<number, string>();

  for (const step of trace.traceSteps) {
    for (const hit of parseTraceHits(step.data.hits)) {
      if (hit.content_preview) {
        previewById.set(hit.id, hit.content_preview);
      }
    }
  }

  for (const chunk of trace.chunks) {
    if (chunk.content_preview) {
      previewById.set(chunk.id, chunk.content_preview);
    }
  }

  return previewById;
}

export function RagTraceStream({ trace }: { trace: RagMessageTrace | null }) {
  const { t } = useTranslation();

  if (trace === null) {
    return <p className="trace-empty">{t("trace.emptyRag")}</p>;
  }

  const chunkPreviewById = buildChunkPreviewById(trace);
  const hitSteps = trace.traceSteps.filter(isHitTraceStep);

  return (
    <div className="rag-trace">
      <header className="rag-trace__header">
        <span className="rag-trace__label">{t("trace.lastAnswer")}</span>
        <span className="rag-trace__meta">#{trace.messageId}</span>
      </header>

      {trace.searchQueries.length > 0 ? (
        <section className="rag-trace__section">
          <h4 className="rag-trace__section-title">{t("trace.searchQueries")}</h4>
          <ul className="rag-trace__queries">
            {trace.searchQueries.map((query, index) => (
              <li key={`${index}-${query}`} className="rag-trace__query">
                {query}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {hitSteps.length > 0 ? (
        <section className="rag-trace__section rag-trace__section--steps">
          {hitSteps.map((event, index) => (
            <CollapsibleTraceStep
              key={`${event.step}-${index}`}
              event={event}
              chunkPreviewById={chunkPreviewById}
              t={t}
            />
          ))}
        </section>
      ) : null}

      <section className="rag-trace__section">
        <h4 className="rag-trace__section-title">
          {t("trace.usedChunks", { count: trace.chunks.length })}
        </h4>
        <p className="rag-trace__hint">{t("trace.citationHint")}</p>

        {trace.chunks.length === 0 ? (
          <p className="trace-empty trace-empty--compact">{t("trace.noChunks")}</p>
        ) : (
          <ul className="rag-trace__chunks">
            {trace.chunks.map((chunk) => {
              const similarity = chunkDisplaySimilarity(chunk);

              return (
                <li key={`${chunk.citation_index}-${chunk.id}`} className="rag-chunk">
                  <div className="rag-chunk__header">
                    <span className="rag-chunk__citation">
                      {t("trace.chunkCitation", { index: chunk.citation_index })}
                    </span>
                    <span className="rag-chunk__id">#{chunk.id}</span>
                    {chunk.content_type ? (
                      <span className="rag-chunk__type">{chunk.content_type}</span>
                    ) : null}
                  </div>

                  {chunk.section || chunk.title ? (
                    <p className="rag-chunk__path">
                      {chunk.section}
                      {chunk.title ? ` · ${chunk.title}` : ""}
                    </p>
                  ) : null}

                  <dl className="rag-chunk__meta">
                    {similarity !== null ? (
                      <>
                        <dt>{t("trace.chunkSimilarity")}</dt>
                        <dd>{formatSimilarity(similarity)}</dd>
                      </>
                    ) : null}
                    {chunk.node_id ? (
                      <>
                        <dt>{t("trace.chunkNodeId")}</dt>
                        <dd>{chunk.node_id}</dd>
                      </>
                    ) : null}
                    {chunk.token_count > 0 ? (
                      <>
                        <dt>{t("trace.chunkTokens")}</dt>
                        <dd>{chunk.token_count}</dd>
                      </>
                    ) : null}
                    {chunk.source_query ? (
                      <>
                        <dt>{t("trace.chunkSourceQuery")}</dt>
                        <dd>{chunk.source_query}</dd>
                      </>
                    ) : null}
                  </dl>

                  {chunk.content_preview ? (
                    <pre className="rag-chunk__preview">{chunk.content_preview}</pre>
                  ) : null}
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </div>
  );
}
