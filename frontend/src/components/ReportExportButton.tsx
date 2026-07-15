"use client";

import { useState, useTransition } from "react";
import { exportIncidentReportAction } from "@/app/actions";

export function ReportExportButton({ incidentId }: { incidentId: number }) {
  const [isPending, startTransition] = useTransition();
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  function handleExport() {
    setMessage(null);
    startTransition(async () => {
      const result = await exportIncidentReportAction(incidentId);
      if (!result.ok || !result.content || !result.filename) {
        setMessage({ type: "error", text: result.message });
        return;
      }

      const blob = new Blob([result.content], { type: "text/markdown;charset=utf-8" });
      const downloadUrl = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = downloadUrl;
      link.download = result.filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(downloadUrl);

      setMessage({ type: "success", text: result.message });
    });
  }

  return (
    <div className="report-export">
      <button className="button" disabled={isPending} onClick={handleExport} type="button">
        {isPending ? "Preparing report..." : "Export Report"}
      </button>
      {message ? <div className={`message ${message.type}`}>{message.text}</div> : null}
    </div>
  );
}
