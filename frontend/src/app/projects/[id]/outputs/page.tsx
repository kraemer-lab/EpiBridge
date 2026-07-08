"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import {
  ExecutionRequest,
  OutputSet,
  getProjectExecutionRequests,
  getExecutionRequestOutputs,
  getOutputSetDownloadUrl,
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

export default function ProjectOutputsPage() {
  const params = useParams();
  const projectId = params.id as string;

  const [requests, setRequests] = useState<ExecutionRequest[]>([]);
  const [selectedRequestId, setSelectedRequestId] = useState<string | null>(null);
  const [outputSet, setOutputSet] = useState<OutputSet | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getProjectExecutionRequests(projectId)
      .then((reqs) => {
        setRequests(reqs);
        const completed = reqs.find((r) => r.status === "completed");
        if (completed) {
          setSelectedRequestId(completed.id);
          return getExecutionRequestOutputs(projectId, completed.id)
            .then(setOutputSet)
            .catch(() => setOutputSet(null));
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [projectId]);

  const handleSelectRequest = (requestId: string) => {
    setSelectedRequestId(requestId);
    getExecutionRequestOutputs(projectId, requestId)
      .then(setOutputSet)
      .catch(() => setOutputSet(null));
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

      {selectedRequest && selectedRequest.status === "completed" && !outputSet && (
        <div className="card empty-state">
          Outputs are pending review. They will appear here once released.
        </div>
      )}

      {selectedRequest && selectedRequest.status !== "completed" && (
        <div className="card empty-state">
          Outputs will appear here once the execution completes.
        </div>
      )}

      {outputSet && (
        <div>
          <div className="card" style={{ marginBottom: "var(--spacing-md)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <strong>Release Package</strong>
                <span style={{ marginLeft: "var(--spacing-sm)", color: "var(--color-text-secondary)", fontSize: "0.85rem" }}>
                  {outputSet.file_count} file{outputSet.file_count !== 1 ? "s" : ""}
                  {outputSet.release_package_size
                    ? ` — ${(outputSet.release_package_size / 1024).toFixed(1)} KB`
                    : ""}
                </span>
              </div>
              <a
                href={getOutputSetDownloadUrl(projectId, selectedRequestId!)}
                className="btn"
                style={{ textDecoration: "none" }}
                download
              >
                Download All
              </a>
            </div>
          </div>

          <table className="table">
            <thead>
              <tr>
                <th>Filename</th>
                <th>Size</th>
              </tr>
            </thead>
            <tbody>
              {outputSet.outputs.map((o) => (
                <tr key={o.id}>
                  <td style={{ fontWeight: 500 }}>{o.filename}</td>
                  <td style={{ color: "var(--color-text-secondary)" }}>
                    {o.size > 1024
                      ? `${(o.size / 1024).toFixed(1)} KB`
                      : `${o.size} bytes`}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {requests.length === 0 && (
        <div className="card empty-state">
          No execution requests yet. Run an analysis to see outputs.
        </div>
      )}
    </div>
  );
}
