"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { runWorkflowAction } from "@/app/actions";

const actions = [
  { label: "Run ETL", step: "etl" as const },
  { label: "Run Detections", step: "detections" as const },
  { label: "Run Incidents", step: "incidents" as const },
  { label: "Run Full Workflow", step: "run-all" as const }
];

export function WorkflowPanel() {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  function handleRun(step: (typeof actions)[number]["step"]) {
    setMessage(null);
    startTransition(async () => {
      const result = await runWorkflowAction(step);
      setMessage({ type: result.ok ? "success" : "error", text: result.message });
      if (result.ok) {
        router.refresh();
      }
    });
  }

  return (
    <div className="panel" id="workflow">
      <div className="panel-header">
        <div>
          <h2>Workflow Panel</h2>
          <p className="section-note">Run ingestion, detection, and incident correlation from the UI.</p>
        </div>
      </div>
      <div className="panel-body">
        <div className="workflow-grid">
          {actions.map((action) => (
            <button
              className="button"
              disabled={isPending}
              key={action.step}
              onClick={() => handleRun(action.step)}
              type="button"
            >
              {isPending ? "Running..." : action.label}
            </button>
          ))}
        </div>
        {message ? <div className={`message ${message.type}`}>{message.text}</div> : null}
      </div>
    </div>
  );
}
