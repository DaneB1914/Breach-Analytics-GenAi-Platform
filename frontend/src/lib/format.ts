import type { Severity } from "./types";

export function formatDate(value: string | null): string {
  if (!value) {
    return "Not set";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "Not set";
  }

  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "UTC",
    timeZoneName: "short"
  }).format(date);
}

export function severityClass(severity: Severity): string {
  const normalized = (severity || "unknown").toLowerCase();

  if (["critical", "high", "medium", "low"].includes(normalized)) {
    return normalized;
  }

  return "unknown";
}

export function displayValue(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === "") {
    return "Not set";
  }

  return String(value);
}
