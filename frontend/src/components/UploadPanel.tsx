"use client";

import { FormEvent, useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import {
  normalizeUploadedDatasetAction,
  runUploadedDatasetWorkflowAction,
  uploadDatasetAction
} from "@/app/actions";
import { formatDate } from "@/lib/format";
import type { UploadedDatasetRecord } from "@/lib/types";

const sourceTypes = ["auth", "vpn", "cloud", "api", "endpoint", "generic"];

export function UploadPanel({ datasets }: { datasets: UploadedDatasetRecord[] }) {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  function handleUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const formData = new FormData(form);

    setMessage(null);
    startTransition(async () => {
      const result = await uploadDatasetAction(formData);
      setMessage({ type: result.ok ? "success" : "error", text: result.message });
      if (result.ok) {
        form.reset();
        router.refresh();
      }
    });
  }

  function handleDatasetAction(datasetId: number, action: "normalize" | "workflow") {
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
    <div className="panel" id="uploads">
      <div className="panel-header">
        <div>
          <h2>Upload Logs</h2>
          <p className="section-note">Upload CSV or JSON security logs for analyst-driven ingestion.</p>
        </div>
      </div>
      <div className="panel-body upload-panel-body">
        <form className="upload-form" onSubmit={handleUpload}>
          <label className="form-field">
            <span>Dataset name</span>
            <input name="name" placeholder="Example: June VPN export" required type="text" />
          </label>

          <label className="form-field">
            <span>Source type</span>
            <select name="source_type" required defaultValue="generic">
              {sourceTypes.map((sourceType) => (
                <option key={sourceType} value={sourceType}>
                  {sourceType}
                </option>
              ))}
            </select>
          </label>

          <label className="form-field">
            <span>CSV or JSON file</span>
            <input accept=".csv,.json,.ndjson,application/json,text/csv" name="file" required type="file" />
          </label>

          <label className="form-field full-width">
            <span>Description</span>
            <textarea name="description" placeholder="Optional investigation context" rows={3} />
          </label>

          <div className="form-actions full-width">
            <button className="button" disabled={isPending} type="submit">
              {isPending ? "Working..." : "Upload dataset"}
            </button>
          </div>
        </form>

        {message ? <div className={`message ${message.type}`}>{message.text}</div> : null}

        <UploadedDatasetsTable
          datasets={datasets}
          disabled={isPending}
          onAction={handleDatasetAction}
        />
      </div>
    </div>
  );
}

function UploadedDatasetsTable({
  datasets,
  disabled,
  onAction
}: {
  datasets: UploadedDatasetRecord[];
  disabled: boolean;
  onAction: (datasetId: number, action: "normalize" | "workflow") => void;
}) {
  if (datasets.length === 0) {
    return <p className="muted">No analyst uploads yet. Upload a CSV or JSON file to start.</p>;
  }

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Dataset</th>
            <th>Source</th>
            <th>Status</th>
            <th>Records</th>
            <th>Uploaded</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {datasets.map((dataset) => (
            <tr key={dataset.id}>
              <td>
                <strong>{dataset.name}</strong>
                <div className="muted">{dataset.files[0]?.original_filename || "No file"}</div>
              </td>
              <td>{dataset.source_type}</td>
              <td>
                <span className="badge unknown">{dataset.status.replaceAll("_", " ")}</span>
              </td>
              <td>{dataset.record_count}</td>
              <td>{formatDate(dataset.created_at)}</td>
              <td>
                <div className="table-actions">
                  <button
                    className="button secondary compact"
                    disabled={disabled}
                    onClick={() => onAction(dataset.id, "normalize")}
                    type="button"
                  >
                    Normalize
                  </button>
                  <button
                    className="button compact"
                    disabled={disabled}
                    onClick={() => onAction(dataset.id, "workflow")}
                    type="button"
                  >
                    Run workflow
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
