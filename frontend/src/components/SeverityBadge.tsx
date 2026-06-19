import { severityClass } from "@/lib/format";
import type { Severity } from "@/lib/types";

export function SeverityBadge({ severity }: { severity: Severity }) {
  const label = severity || "unknown";

  return <span className={`badge ${severityClass(severity)}`}>{label}</span>;
}
