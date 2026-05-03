import { PanelHeader } from "@/app/layout/AppHeader";
import { useTranslation } from "@/shared/i18n";
import { useTraceStore } from "../store";

export function TracePanel() {
  const { t } = useTranslation();
  const events = useTraceStore((state) => state.events);
  const requestId = useTraceStore((state) => state.requestId);

  return (
    <>
      <PanelHeader title={t("panels.trace")} />

      <div className="app-panel__body">
        {requestId === null && events.length === 0 ? (
          <p className="trace-empty">{t("trace.empty")}</p>
        ) : null}

        {requestId ? (
          <p className="trace-empty" style={{ paddingBottom: 0 }}>
            {t("trace.requestId", { id: requestId })}
          </p>
        ) : null}

        {events.map((event, index) => (
          <article key={`${event.step}-${index}`} className="trace-step">
            <h3 className="trace-step__title">
              {t(`trace.steps.${event.step}`)}
              {event.duration_ms
                ? ` · ${t("trace.durationMs", { ms: event.duration_ms })}`
                : ""}
            </h3>
            <pre className="trace-step__body">{JSON.stringify(event.data, null, 2)}</pre>
          </article>
        ))}
      </div>
    </>
  );
}
