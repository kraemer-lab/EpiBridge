import type React from "react";

const BUNDLE_STATUS_LABELS: Record<string, string> = {
  draft: "Draft",
  submitted: "Submitted",
  approved_for_execution: "Approved for Execution",
  rejected: "Rejected",
  superseded: "Superseded",
};

const BUNDLE_STATUS_STYLES: Record<string, React.CSSProperties> = {
  draft: { background: "#f0f0f0", color: "#666" },
  submitted: { background: "#cce5ff", color: "#004085" },
  approved_for_execution: { background: "#d4edda", color: "#155724" },
  rejected: { background: "#f8d7da", color: "#721c24" },
  superseded: { background: "#fff3cd", color: "#856404" },
};

export function formatBundleStatus(status: string): string {
  return BUNDLE_STATUS_LABELS[status] || status.charAt(0).toUpperCase() + status.slice(1);
}

export function bundleStatusStyle(status: string): React.CSSProperties {
  return (
    BUNDLE_STATUS_STYLES[status] || { background: "#f0f0f0", color: "#666" }
  );
}
