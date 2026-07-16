"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { summarizeIncidentAction } from "@/app/actions";
import { formatDate } from "@/lib/format";
import type { LLMSummary } from "@/lib/types";

export function SummaryPanel({
  incidentId,
  initialSummary,
  datasetId
}: {
  incidentId: number;
  initialSummary: LLMSummary | null;
  datasetId?: number;
}) {
  const router = useRouter();
  const [summary, setSummary] = useState(initialSummary);
  const [isPending, startTransition] = useTransition();
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  function handleGenerate() {
    setMessage(null);
    startTransition(async () => {
      const result = await summarizeIncidentAction(incidentId, datasetId);
      if (result.ok && result.summary) {
        setSummary(result.summary);
        setMessage({ type: "success", text: result.message });
        router.refresh();
      } else {
        setMessage({ type: "error", text: result.message });
      }
    });
  }

  return (
    <div className="panel">
      <div className="panel-header">
        <div>
          <h2>LLM Incident Summary</h2>
          <p className="section-note">Mock mode is used automatically when no API key is configured.</p>
        </div>
        <button className="button" disabled={isPending} onClick={handleGenerate} type="button">
          {isPending ? "Generating..." : "Generate Summary"}
        </button>
      </div>
      <div className="panel-body">
        {message ? <div className={`message ${message.type}`}>{message.text}</div> : null}
        {summary ? (
          <div className="summary-box">
            <div className="summary-block">
              <h3>Executive Summary</h3>
              <p>{summary.executive_summary}</p>
            </div>
            <div className="summary-block">
              <h3>Technical Summary</h3>
              <p>{summary.technical_summary}</p>
            </div>
            <div className="summary-block">
              <h3>Recommended Containment</h3>
              <ul>
                {summary.recommended_containment_steps.map((step) => (
                  <li key={step}>{step}</li>
                ))}
              </ul>
            </div>
            <div className="summary-block">
              <h3>Evidence Timeline</h3>
              <ul className="timeline">
                {summary.attack_timeline.map((item) => (
                  <li key={String(item.event_id)}>
                    <strong>Event {String(item.event_id)}</strong>{" "}
                    <span className="muted">{formatDate(String(item.timestamp || ""))}</span>
                    <br />
                    <span>{String(item.source_system || "unknown")} · {String(item.event_type || "event")}</span>
                  </li>
                ))}
              </ul>
            </div>
            <p className="section-note">
              Model: {summary.model_name || "unknown"} · Evidence event IDs:{" "}
              {summary.evidence_event_ids.join(", ")}
            </p>
          </div>
        ) : (
          <p className="muted">No summary has been generated for this incident yet.</p>
        )}
      </div>
    </div>
  );
}
