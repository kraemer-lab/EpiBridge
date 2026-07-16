"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import { ExecutionRequest, getProjectExecutionRequests } from "@/lib/api";

function statusStyle(status: string): React.CSSProperties {
  switch (status) {
    case "pending":
      return { background: "#f0f0f0", color: "#666" };
    case "running":
      return { background: "#cce5ff", color: "#004085" };
    case "completed":
      return { background: "#d4edda", color: "#155724" };
    case "failed":
      return { background: "#f8d7da", color: "#721c24" };
    case "cancelling":
    case "cancelled":
      return { background: "#fff3cd", color: "#856404" };
    default:
      return { background: "#f0f0f0", color: "#666" };
  }
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleString();
}

export default function ProjectJobsPage() {
  const params = useParams();
  const projectId = params.id as string;

  const [requests, setRequests] = useState<ExecutionRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const fetch = useCallback(() => {
    getProjectExecutionRequests(projectId)
      .then(setRequests)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [projectId]);

  useEffect(() => {
    fetch();
    const interval = setInterval(fetch, 3000);
    return () => clearInterval(interval);
  }, [fetch]);

  const detailRow: React.CSSProperties = {
    display: "flex",
    gap: "var(--spacing-md)",
    fontSize: "0.85rem",
    padding: "3px 0",
  };

  const detailLabel: React.CSSProperties = {
    color: "var(--color-text-secondary)",
    minWidth: "120px",
    flexShrink: 0,
  };

  const detailValue: React.CSSProperties = {
    color: "var(--color-text)",
  };

  if (loading) return <div className="card empty-state">Loading...</div>;

  if (requests.length === 0) {
    return (
      <div className="card empty-state">
        No execution requests yet. Run an analysis to get started.
      </div>
    );
  }

  return (
    <div>
      <table className="table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Status</th>
            <th>Created</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {requests.map((r) => (
            <tr key={r.id}>
              <td style={{ fontWeight: 500 }}>
                {r.name}
              </td>
              <td>
                <span
                  style={{
                    display: "inline-block",
                    padding: "2px 8px",
                    borderRadius: "4px",
                    fontSize: "0.8rem",
                    fontWeight: 600,
                    ...statusStyle(r.status),
                  }}
                >
                  {r.status}
                </span>
              </td>
              <td style={{ color: "var(--color-text-secondary)" }}>
                {formatTime(r.created_at)}
              </td>
              <td>
                {r.status === "cancelled" && (
                  <button
                    onClick={() => setExpandedId(expandedId === r.id ? null : r.id)}
                    style={{
                      background: "none",
                      border: "none",
                      cursor: "pointer",
                      fontSize: "0.85rem",
                      padding: 0,
                      color: "var(--color-primary, #1976d2)",
                    }}
                  >
                    {expandedId === r.id ? "Hide details" : "Details"}
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {expandedId && (() => {
        const detail = requests.find((r) => r.id === expandedId);
        if (!detail || detail.status !== "cancelled") return null;
        return (
          <div
            className="card"
            style={{
              marginTop: "var(--spacing-md)",
              padding: "var(--spacing-lg)",
              borderTop: "3px solid #856404",
              fontSize: "0.85rem",
            }}
          >
            <h3 style={{ fontSize: "0.85rem", fontWeight: 600, marginBottom: "var(--spacing-xs)", color: "var(--color-text)" }}>
              Cancellation Details
            </h3>
            {detail.cancelled_by_id && (
              <div style={detailRow}>
                <span style={detailLabel}>Cancelled by</span>
                <span style={detailValue}>
                  {detail.cancelled_by_display_name || detail.cancelled_by_id}
                  {detail.cancelled_by_email ? ` (${detail.cancelled_by_email})` : ""}
                </span>
              </div>
            )}
            {detail.cancelled_at && (
              <div style={detailRow}>
                <span style={detailLabel}>Cancelled at</span>
                <span style={detailValue}>{formatTime(detail.cancelled_at)}</span>
              </div>
            )}
            {detail.cancellation_reason && (
              <div style={detailRow}>
                <span style={detailLabel}>Reason</span>
                <span style={detailValue}>{detail.cancellation_reason}</span>
              </div>
            )}
          </div>
        );
      })()}
    </div>
  );
}
