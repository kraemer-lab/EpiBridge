"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import {
  ExecutionRequest,
  Output,
  getProjectExecutionRequests,
  getExecutionRequestOutputs,
  getOutputDownloadUrl,
} from "@/lib/api";

function statusStyle(status: string): React.CSSProperties {
  switch (status) {
    case "completed":
      return { background: "#d4edda", color: "#155724" };
    case "failed":
      return { background: "#f8d7da", color: "#721c24" };
    default:
      return { background: "#f0f0f0", color: "#666" };
  }
}

function outputStatusBadge(status: string): { background: string; color: string; label: string } {
  switch (status) {
    case "released":
      return { background: "#d4edda", color: "#155724", label: "Released" };
    default:
      return { background: "#f0f0f0", color: "#666", label: status };
  }
}

export default function ProjectOutputsPage() {
  const params = useParams();
  const projectId = params.id as string;

  const [requests, setRequests] = useState<ExecutionRequest[]>([]);
  const [selectedRequestId, setSelectedRequestId] = useState<string | null>(null);
  const [outputs, setOutputs] = useState<Output[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getProjectExecutionRequests(projectId)
      .then((reqs) => {
        setRequests(reqs);
        const completed = reqs.find((r) => r.status === "completed");
        if (completed) {
          setSelectedRequestId(completed.id);
          return getExecutionRequestOutputs(projectId, completed.id).then(setOutputs);
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [projectId]);

  const handleSelectRequest = (requestId: string) => {
    setSelectedRequestId(requestId);
    getExecutionRequestOutputs(projectId, requestId)
      .then(setOutputs)
      .catch(() => setOutputs([]));
  };

  const selectedRequest = requests.find((r) => r.id === selectedRequestId);

  if (loading) return <div className="card empty-state">Loading...</div>;

  return (
    <div>
      {requests.length > 1 && (
        <div style={{ marginBottom: "var(--spacing-lg)" }}>
          <label
            style={{
              fontSize: "0.8rem",
              fontWeight: 600,
              textTransform: "uppercase",
              letterSpacing: "0.05em",
              color: "var(--color-text-secondary)",
              marginRight: "var(--spacing-sm)",
            }}
          >
            Execution Request:
          </label>
          <select
            value={selectedRequestId ?? ""}
            onChange={(e) => handleSelectRequest(e.target.value)}
            style={{
              padding: "var(--spacing-xs) var(--spacing-sm)",
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--color-border)",
              fontSize: "0.9rem",
            }}
          >
            {requests.map((r) => (
              <option key={r.id} value={r.id}>
                {r.analysis_name} — {r.status}
              </option>
            ))}
          </select>
        </div>
      )}

      {selectedRequest && selectedRequest.status === "completed" && outputs.length === 0 && (
        <div className="card empty-state">
          Outputs are pending review. They will appear here once released.
        </div>
      )}

      {selectedRequest && selectedRequest.status !== "completed" && (
        <div className="card empty-state">
          Outputs will appear here once the execution completes.
        </div>
      )}

      {outputs.length > 0 && (
        <table className="table">
          <thead>
            <tr>
              <th>Filename</th>
              <th>Size</th>
              <th>Status</th>
              <th>Download</th>
            </tr>
          </thead>
          <tbody>
            {outputs.map((o) => {
              const badge = outputStatusBadge(o.status);
              return (
                <tr key={o.id}>
                  <td style={{ fontWeight: 500 }}>{o.filename}</td>
                  <td style={{ color: "var(--color-text-secondary)" }}>
                    {o.size > 1024
                      ? `${(o.size / 1024).toFixed(1)} KB`
                      : `${o.size} bytes`}
                  </td>
                  <td>
                    <span
                      style={{
                        display: "inline-block",
                        padding: "2px 8px",
                        borderRadius: "4px",
                        fontSize: "0.8rem",
                        fontWeight: 600,
                        background: badge.background,
                        color: badge.color,
                      }}
                    >
                      {badge.label}
                    </span>
                  </td>
                  <td>
                    <a
                      href={getOutputDownloadUrl(projectId, selectedRequestId!, o.id)}
                      className="btn"
                      style={{ textDecoration: "none", fontSize: "0.85rem" }}
                      download
                    >
                      Download
                    </a>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}

      {requests.length === 0 && (
        <div className="card empty-state">
          No execution requests yet. Run an analysis to see outputs.
        </div>
      )}
    </div>
  );
}
