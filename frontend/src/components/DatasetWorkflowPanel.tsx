"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import {
  normalizeUploadedDatasetAction,
  runUploadedDatasetWorkflowAction
} from "@/app/actions";

export function DatasetWorkflowPanel({
  datasetId,
  datasetName
}: {
  datasetId: number;
  datasetName: string;
}) {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  function run(action: "normalize" | "workflow") {
    setMessage(null);
    startTransition(async () => {
      const result =
        action === "normalize"
          ? await normalizeUploadedDatasetAction(datasetId)
          : await runUploadedDatasetWorkflowAction(datasetId);

      setMessage({ type: result.ok ? "success" : "error", text: result.message });
      if (result.ok) {
        router.refresh();
      }
    });
  }

  return (
    <div className="panel">
      <div className="panel-header">
        <div>
          <h2>Dataset Workflow</h2>
          <p className="section-note">Actions below apply only to {datasetName}.</p>
        </div>
      </div>
      <div className="panel-body dataset-workflow-actions">
        <button
          className="button secondary"
          disabled={isPending}
          onClick={() => run("normalize")}
          type="button"
        >
          {isPending ? "Working..." : "Normalize Dataset"}
        </button>
        <button
          className="button"
          disabled={isPending}
          onClick={() => run("workflow")}
          type="button"
        >
          {isPending ? "Working..." : "Run Dataset Workflow"}
        </button>
        {message ? <div className={`message ${message.type}`}>{message.text}</div> : null}
      </div>
    </div>
  );
}
