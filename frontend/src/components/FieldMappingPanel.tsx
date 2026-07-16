"use client";

import { useMemo, useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import {
  normalizeUploadedDatasetAction,
  previewDatasetMappingsAction,
  saveDatasetMappingsAction
} from "@/app/actions";
import { formatDate } from "@/lib/format";
import type {
  DatasetFieldMapping,
  DatasetFieldMappingInput,
  DatasetSchema,
  MappingPreviewResponse
} from "@/lib/types";

const PREVIEW_FIELDS = [
  "timestamp",
  "source_system",
  "event_type",
  "username",
  "source_ip",
  "destination_ip",
  "asset",
  "action",
  "outcome",
  "severity",
  "mitre_technique_id",
  "message"
] as const;

type MappingSelection = Record<string, string>;

export function FieldMappingPanel({
  datasetId,
  datasetName,
  datasetStatus,
  schema,
  savedMappings
}: {
  datasetId: number;
  datasetName: string;
  datasetStatus: string;
  schema: DatasetSchema;
  savedMappings: DatasetFieldMapping[];
}) {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const [selection, setSelection] = useState<MappingSelection>(() =>
    initialSelection(schema, savedMappings)
  );
  const [preview, setPreview] = useState<MappingPreviewResponse | null>(null);
  const [message, setMessage] = useState<{
    type: "success" | "error" | "warning";
    text: string;
  } | null>(null);

  const isLocked = !["uploaded", "mapping_required", "ready_to_normalize", "failed"].includes(
    datasetStatus
  );
  const duplicateTargets = useMemo(() => findDuplicateTargets(selection), [selection]);
  const timestampSource = Object.entries(selection).find(([, target]) => target === "timestamp")?.[0];

  function updateTarget(sourceField: string, targetField: string) {
    setSelection((current) => ({ ...current, [sourceField]: targetField }));
    setPreview(null);
    setMessage(null);
  }

  function runAction(action: "save" | "preview" | "normalize") {
    setMessage(null);
    if (duplicateTargets.length > 0) {
      setMessage({
        type: "error",
        text: `Each target can be selected once. Resolve: ${duplicateTargets.join(", ")}.`
      });
      return;
    }
    if (action !== "preview" && !timestampSource) {
      setMessage({
        type: "error",
        text: "Map one source field to the required timestamp target before continuing."
      });
      return;
    }

    const mappings = toMappingInputs(selection);
    startTransition(async () => {
      if (action === "save") {
        const result = await saveDatasetMappingsAction(datasetId, mappings);
        setMessage({ type: result.ok ? "success" : "error", text: result.message });
        if (result.ok) router.refresh();
        return;
      }

      if (action === "preview") {
        const result = await previewDatasetMappingsAction(datasetId, mappings);
        setMessage({ type: result.ok ? "success" : "error", text: result.message });
        setPreview(result.preview);
        return;
      }

      const saved = await saveDatasetMappingsAction(datasetId, mappings);
      if (!saved.ok) {
        setMessage({ type: "error", text: saved.message });
        return;
      }
      const normalized = await normalizeUploadedDatasetAction(datasetId);
      setMessage({ type: normalized.ok ? "success" : "error", text: normalized.message });
      if (normalized.ok) router.refresh();
    });
  }

  return (
    <section className="section panel" aria-labelledby="field-mapping-title">
      <div className="panel-header mapping-header">
        <div>
          <div className="eyebrow">Active Dataset: {datasetName}</div>
          <h2 id="field-mapping-title">Field Mapping</h2>
          <p className="section-note">
            Review automatic suggestions, adjust target fields, and preview records before normalization.
          </p>
        </div>
        <div className="mapping-requirement">
          <strong>Required:</strong> timestamp
          <span>All other targets are optional.</span>
        </div>
      </div>

      <div className="panel-body mapping-body">
        {isLocked ? (
          <div className="message warning mapping-lock-message">
            This dataset is already {datasetStatus.replaceAll("_", " ")}. Its confirmed mapping is
            read-only so the investigation remains auditable.
          </div>
        ) : null}

        <div className="table-wrap">
          <table className="mapping-table">
            <thead>
              <tr>
                <th>Source Field</th>
                <th>Sample Values</th>
                <th>Suggestion</th>
                <th>Normalized Target</th>
              </tr>
            </thead>
            <tbody>
              {schema.fields.map((field) => (
                <tr key={field.source_field}>
                  <td className="mono">{field.source_field}</td>
                  <td>
                    <div className="sample-values">
                      {field.sample_values.length > 0
                        ? field.sample_values.map((value) => <span key={value}>{value}</span>)
                        : <span className="muted">No sample value</span>}
                    </div>
                  </td>
                  <td>
                    {field.suggested_target_field ? (
                      <div className="mapping-suggestion">
                        <span>{field.suggested_target_field}</span>
                        <span className="badge unknown">{field.confidence || "suggested"}</span>
                      </div>
                    ) : (
                      <span className="muted">No safe suggestion</span>
                    )}
                  </td>
                  <td>
                    <label className="sr-only" htmlFor={`mapping-${field.source_field}`}>
                      Target field for {field.source_field}
                    </label>
                    <select
                      id={`mapping-${field.source_field}`}
                      className="mapping-select"
                      disabled={isPending || isLocked}
                      onChange={(event) => updateTarget(field.source_field, event.target.value)}
                      value={selection[field.source_field] || ""}
                    >
                      <option value="">Unmapped</option>
                      {schema.target_fields.map((target) => (
                        <option key={target} value={target}>
                          {target}{schema.required_target_fields.includes(target) ? " (required)" : ""}
                        </option>
                      ))}
                    </select>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <p className="mapping-help">
          Unmapped recognized fields may still use safe automatic aliases during normalization.
          Unrecognized optional fields remain available in the preserved raw event.
        </p>

        <div className="mapping-actions">
          <button
            className="button secondary"
            disabled={isPending || isLocked}
            onClick={() => runAction("save")}
            type="button"
          >
            {isPending ? "Working..." : "Save Mapping"}
          </button>
          <button
            className="button secondary"
            disabled={isPending}
            onClick={() => runAction("preview")}
            type="button"
          >
            {isPending ? "Working..." : "Preview Normalized Records"}
          </button>
          <button
            className="button"
            disabled={isPending || isLocked}
            onClick={() => runAction("normalize")}
            type="button"
          >
            {isPending ? "Working..." : "Normalize Dataset"}
          </button>
        </div>
        {message ? <div className={`message ${message.type}`}>{message.text}</div> : null}

        {preview ? <MappingPreview preview={preview} /> : null}
      </div>
    </section>
  );
}

function MappingPreview({ preview }: { preview: MappingPreviewResponse }) {
  return (
    <div className="mapping-preview">
      <div>
        <h3>Normalized Preview</h3>
        <p className="section-note">Preview only. No event records have been inserted.</p>
      </div>
      {preview.warnings.map((warning) => (
        <div className="message warning" key={warning}>{warning}</div>
      ))}
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Record</th>
              {PREVIEW_FIELDS.map((field) => <th key={field}>{field}</th>)}
            </tr>
          </thead>
          <tbody>
            {preview.records.map((record) => (
              <tr key={record.record_number}>
                <td>{record.record_number}</td>
                {PREVIEW_FIELDS.map((field) => (
                  <td key={field}>
                    {field === "timestamp"
                      ? formatDate(record[field])
                      : record[field] || <span className="muted">Not mapped</span>}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function initialSelection(
  schema: DatasetSchema,
  savedMappings: DatasetFieldMapping[]
): MappingSelection {
  const saved = new Map(savedMappings.map((mapping) => [mapping.source_field, mapping.target_field]));
  return Object.fromEntries(
    schema.fields.map((field) => [
      field.source_field,
      saved.get(field.source_field) || field.suggested_target_field || ""
    ])
  );
}

function toMappingInputs(selection: MappingSelection): DatasetFieldMappingInput[] {
  return Object.entries(selection)
    .filter(([, targetField]) => Boolean(targetField))
    .map(([sourceField, targetField]) => ({
      source_field: sourceField,
      target_field: targetField,
      transformation_type: "direct",
      default_value: null
    }));
}

function findDuplicateTargets(selection: MappingSelection): string[] {
  const counts = new Map<string, number>();
  Object.values(selection).forEach((target) => {
    if (target) counts.set(target, (counts.get(target) || 0) + 1);
  });
  return [...counts.entries()].filter(([, count]) => count > 1).map(([target]) => target);
}
