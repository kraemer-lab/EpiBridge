"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ExecutionRequest, getAdminExecutionRequests } from "@/lib/api";

const STATUS_FILTERS = [
  { value: "pending", label: "Pending" },
  { value: "running", label: "Running" },
  { value: "completed", label: "Completed" },
  { value: "failed", label: "Failed" },
  { value: "cancelled", label: "Cancelled" },
  { value: "all", label: "All" },
];

const ACTIVE_STATUSES = new Set(["pending", "running"]);

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
    case "cancelled":
      return { background: "#fff3cd", color: "#856404" };
    default:
      return { background: "#f0f0f0", color: "#666" };
  }
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleString();
}

export default function AdminExecutionsPage() {
  const [requests, setRequests] = useState<ExecutionRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState("pending");
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const shouldPoll = ACTIVE_STATUSES.has(statusFilter);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getAdminExecutionRequests();
      setRequests(data);
    } catch {
      setError("Failed to load execution requests");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    if (shouldPoll) {
      pollRef.current = setInterval(load, 3000);
    }
    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
      }
    };
  }, [shouldPoll, load]);

  const filteredRequests =
    statusFilter === "all"
      ? requests
      : requests.filter((r) => r.status === statusFilter);

  return (
    <>
      <h2 style={{ fontSize: "1.1rem", fontWeight: 600, marginBottom: "var(--spacing-sm)" }}>
        Execution Monitoring
      </h2>

      <div style={{ display: "flex", gap: "var(--spacing-xs)", marginBottom: "var(--spacing-md)", flexWrap: "wrap" }}>
        {STATUS_FILTERS.map((opt) => (
          <button
            key={opt.value}
            onClick={() => setStatusFilter(opt.value)}
            style={{
              padding: "4px 12px",
              fontSize: "0.85rem",
              background:
                statusFilter === opt.value
                  ? "var(--color-primary, #1976d2)"
                  : "transparent",
              color:
                statusFilter === opt.value
                  ? "#fff"
                  : "var(--color-text-secondary)",
              border: "1px solid",
              borderColor:
                statusFilter === opt.value
                  ? "var(--color-primary, #1976d2)"
                  : "var(--color-border)",
              borderRadius: "4px",
              cursor: "pointer",
              fontWeight: statusFilter === opt.value ? 600 : 400,
            }}
          >
            {opt.label}
            {shouldPoll && opt.value === statusFilter ? " (auto)" : ""}
          </button>
        ))}

        <button
          onClick={load}
          style={{
            marginLeft: "auto",
            padding: "4px 12px",
            fontSize: "0.85rem",
            background: "transparent",
            color: "var(--color-primary, #1976d2)",
            border: "1px solid var(--color-primary, #1976d2)",
            borderRadius: "4px",
            cursor: "pointer",
          }}
          disabled={loading}
        >
          {loading ? "Refreshing…" : "Refresh"}
        </button>
      </div>

      {error && (
        <div
          style={{
            padding: "8px 12px",
            marginBottom: "var(--spacing-md)",
            background: "#f8d7da",
            color: "#721c24",
            borderRadius: "4px",
            fontSize: "0.85rem",
          }}
        >
          {error}
        </div>
      )}

      {loading && requests.length === 0 ? (
        <div className="card empty-state">Loading...</div>
      ) : error && requests.length === 0 ? (
        <div className="card empty-state">{error}</div>
      ) : filteredRequests.length === 0 ? (
        <div className="card empty-state">
          {statusFilter === "all"
            ? "No execution requests found."
            : `No ${statusFilter} execution requests.`}
        </div>
      ) : (
        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          <table className="table">
            <thead>
              <tr>
                <th>Analysis</th>
                <th>Status</th>
                <th>Project</th>
                <th>Runtime</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {filteredRequests.map((r) => (
                <tr key={r.id}>
                  <td style={{ fontWeight: 500 }}>
                    {r.analysis_name}
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
                      {r.status.charAt(0).toUpperCase() + r.status.slice(1)}
                    </span>
                  </td>
                  <td style={{ color: "var(--color-text-secondary)", fontSize: "0.85rem", fontFamily: "var(--font-mono)" }}>
                    {r.project_id.slice(0, 8)}
                  </td>
                  <td style={{ color: "var(--color-text-secondary)" }}>
                    {r.runtime}
                  </td>
                  <td style={{ color: "var(--color-text-secondary)", whiteSpace: "nowrap" }}>
                    {formatTime(r.created_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
