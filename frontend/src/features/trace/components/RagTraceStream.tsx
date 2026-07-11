import { useTranslation } from "@/shared/i18n";
import type { TraceEvent } from "@/shared/api/types";
import type { RagConfigSnapshot, RagMessageTrace, RetrievalLaneTrace, TraceHit } from "../lib/ragTrace";
import {
  parseRetrievalLanes,
  parseTraceHits,
  retrievalLanesFromTrace,
} from "../lib/ragTrace";

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
  "rag_config",
]);

const LANE_KEYS = new Set(["sop", "faq", "decision_tree", "scenario"]);

function formatSimilarity(score: number): string {
  return score.toFixed(4);
}

function stepLabel(t: (key: string) => string, step: string): string {
  if (TRACE_STEP_KEYS.has(step)) {
    return t(`trace.steps.${step}`);
  }

  return step;
}

function laneLabel(t: (key: string) => string, lane: string): string {
  if (LANE_KEYS.has(lane)) {
    return t(`trace.lanes.${lane}`);
  }

  return lane;
}

function chunkDisplaySimilarity(chunk: RagMessageTrace["chunks"][number]): number | null {
  return chunk.similarity ?? chunk.score;
}

function isHitTraceStep(event: TraceEvent): boolean {
  if (event.step === "retrieval") {
    return parseRetrievalLanes(event.data.lanes).length > 0 || parseTraceHits(event.data.hits).length > 0;
  }

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
            {hit.lane ? (
              <span className="trace-hit__lane" title={hit.lane_source || undefined}>
                {laneLabel(t, hit.lane)}
              </span>
            ) : null}
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

function RetrievalLaneSection({
  lane,
  chunkPreviewById,
  t,
}: {
  lane: RetrievalLaneTrace;
  chunkPreviewById: Map<number, string>;
  t: (key: string, params?: Record<string, string | number>) => string;
}) {
  return (
    <details className="trace-lane">
      <summary className="trace-lane__summary">
        <span className="trace-lane__title">{laneLabel(t, lane.lane)}</span>
        <span className="trace-lane__count">
          {t("trace.laneHitCount", { count: lane.hit_count, topK: lane.top_k })}
        </span>
      </summary>

      <p className="trace-lane__source">{lane.source_label}</p>

      {lane.hits.length === 0 ? (
        <p className="trace-empty trace-empty--compact">{t("trace.laneNoHits")}</p>
      ) : (
        <ol className="trace-hit-list">
          {lane.hits.map((hit, index) => (
            <TraceHitRow
              key={`${lane.lane}-${hit.id}-${index}`}
              hit={hit}
              index={index}
              chunkPreview={chunkPreviewById.get(hit.id) ?? ""}
              t={t}
            />
          ))}
        </ol>
      )}
    </details>
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
  const lanes = step === "retrieval" ? parseRetrievalLanes(data.lanes) : [];
  const hits = step === "rerank" ? parseTraceHits(data.hits) : [];

  if (lanes.length === 0 && hits.length === 0) {
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

      {lanes.length > 0 ? (
        <div className="trace-lane-list">
          {lanes.map((lane) => (
            <RetrievalLaneSection
              key={lane.lane}
              lane={lane}
              chunkPreviewById={chunkPreviewById}
              t={t}
            />
          ))}
        </div>
      ) : null}

      {hits.length > 0 ? (
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
      ) : null}
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
  if (event.step === "rag_config") {
    return null;
  }

  const lanes = event.step === "retrieval" ? parseRetrievalLanes(event.data.lanes) : [];
  const hits = parseTraceHits(event.data.hits);
  const itemCount = lanes.length > 0 ? lanes.reduce((sum, lane) => sum + lane.hits.length, 0) : hits.length;

  if (itemCount === 0) {
    return null;
  }

  return (
    <details className="trace-step">
      <summary className="trace-step__title">
        {stepLabel(t, event.step)}
        {event.duration_ms ? ` · ${t("trace.durationMs", { ms: event.duration_ms })}` : ""}
        <span className="trace-step__count">{itemCount}</span>
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

function RagConfigUsedSection({
  config,
  t,
}: {
  config: RagConfigSnapshot;
  t: (key: string, params?: Record<string, string | number>) => string;
}) {
  const enabledMethods = [
    config.use_hyde ? "hyde" : null,
    config.use_multi_query ? "multi_query" : null,
    config.use_query_rewriting ? "query_rewriting" : null,
    config.use_rerank ? "rerank" : null,
  ].filter((method): method is string => method !== null);

  return (
    <section className="rag-trace__section rag-trace__section--config">
      <h4 className="rag-trace__section-title">{t("trace.appliedRagConfig")}</h4>
      <dl className="rag-trace__config">
        <div className="rag-trace__config-row">
          <dt>{t("trace.appliedMethods")}</dt>
          <dd>
            {enabledMethods.length > 0
              ? enabledMethods.map((method) => t(`trace.steps.${method}`)).join(", ")
              : t("trace.appliedMethodsDirect")}
          </dd>
        </div>
        <div className="rag-trace__config-row">
          <dt>{t("rag.topChunks")}</dt>
          <dd>{config.top_chunks ?? 5}</dd>
        </div>
        <div className="rag-trace__config-row">
          <dt>{t("rag.useHistory")}</dt>
          <dd>
            {config.use_history == null
              ? t("trace.appliedHistoryUnknown")
              : config.use_history
                ? t("common.yes")
                : t("common.no")}
          </dd>
        </div>
      </dl>
      <p className="rag-trace__hint">{t("trace.staticChaptersHint")}</p>
    </section>
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

    for (const lane of parseRetrievalLanes(step.data.lanes)) {
      for (const hit of lane.hits) {
        if (hit.content_preview) {
          previewById.set(hit.id, hit.content_preview);
        }
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
  const retrievalLanes = retrievalLanesFromTrace(trace.traceSteps);
  const hitSteps = trace.traceSteps
    .filter(isHitTraceStep)
    .filter((event) => !(event.step === "retrieval" && retrievalLanes.length > 0));

  return (
    <div className="rag-trace">
      <header className="rag-trace__header">
        <span className="rag-trace__label">{t("trace.lastAnswer")}</span>
        <span className="rag-trace__meta">#{trace.messageId}</span>
      </header>

      {trace.ragConfig ? <RagConfigUsedSection config={trace.ragConfig} t={t} /> : null}

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

      {retrievalLanes.length > 0 ? (
        <section className="rag-trace__section">
          <h4 className="rag-trace__section-title">{t("trace.retrievalLanes")}</h4>
          <div className="trace-lane-list">
            {retrievalLanes.map((lane) => (
              <RetrievalLaneSection
                key={lane.lane}
                lane={lane}
                chunkPreviewById={chunkPreviewById}
                t={t}
              />
            ))}
          </div>
        </section>
      ) : null}

      {hitSteps.length > 0 ? (
        <section className="rag-trace__section rag-trace__section--steps">
          <h4 className="rag-trace__section-title">{t("trace.pipelineSteps")}</h4>
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
                    {chunk.retrieval_lane ? (
                      <span className="rag-chunk__lane">{laneLabel(t, chunk.retrieval_lane)}</span>
                    ) : null}
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
