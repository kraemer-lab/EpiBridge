"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  ExecutionRequest,
  ExecutionRequestDetail,
  getAdminExecutionRequests,
  getAdminExecutionRequest,
  cancelAdminExecutionRequest,
} from "@/lib/api";
import LogViewer from "@/components/LogViewer";
import { ConfirmationDialog } from "@/components/ConfirmationDialog";

const STATUS_FILTERS = [
  { value: "pending", label: "Pending" },
  { value: "running", label: "Running" },
  { value: "completed", label: "Completed" },
  { value: "failed", label: "Failed" },
  { value: "cancelled", label: "Cancelled" },
  { value: "all", label: "All" },
];

const ACTIVE_STATUSES = new Set(["pending", "running", "cancelling"]);
const NON_TERMINAL_STATUSES = new Set(["pending", "running", "cancelling"]);

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
    case "cancelling":
      return { background: "#fff3cd", color: "#856404" };
    default:
      return { background: "#f0f0f0", color: "#666" };
  }
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleString();
}

const sectionHeader: React.CSSProperties = {
  fontSize: "0.85rem",
  fontWeight: 600,
  marginBottom: "var(--spacing-xs)",
  marginTop: "var(--spacing-md)",
  color: "var(--color-text)",
};

const detailRow: React.CSSProperties = {
  display: "flex",
  gap: "var(--spacing-md)",
  fontSize: "0.85rem",
  padding: "3px 0",
};

const detailLabel: React.CSSProperties = {
  color: "var(--color-text-secondary)",
  minWidth: "140px",
  flexShrink: 0,
};

const detailValue: React.CSSProperties = {
  color: "var(--color-text)",
};

export default function AdminExecutionsPage() {
  const [requests, setRequests] = useState<ExecutionRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState("pending");
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [expandedData, setExpandedData] = useState<Record<string, ExecutionRequestDetail>>({});
  const [cancelTarget, setCancelTarget] = useState<string | null>(null);
  const [cancelError, setCancelError] = useState<string | null>(null);
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

  const handleExpand = async (id: string) => {
    if (expandedId === id) {
      setExpandedId(null);
      return;
    }
    setExpandedId(id);
    try {
      const detail = await getAdminExecutionRequest(id);
      setExpandedData((prev) => ({ ...prev, [id]: detail }));
    } catch {
      setExpandedData((prev) => ({ ...prev, [id]: null as unknown as ExecutionRequestDetail }));
    }
  };

  // Auto-refresh the expanded detail while in a non-terminal status
  const expandedDetail = expandedId ? expandedData[expandedId] : null;
  const shouldPollDetail = expandedDetail && NON_TERMINAL_STATUSES.has(expandedDetail.status);

  useEffect(() => {
    if (!shouldPollDetail || !expandedId) return;
    const interval = setInterval(async () => {
      try {
        const fresh = await getAdminExecutionRequest(expandedId);
        setExpandedData((prev) => ({ ...prev, [expandedId]: fresh }));
      } catch {
        // Silently ignore polling errors for detail
      }
    }, 3000);
    return () => clearInterval(interval);
  }, [shouldPollDetail, expandedId]);

  const handleCancelConfirm = async (reason?: string) => {
    if (!cancelTarget) return;
    setCancelError(null);
    try {
      await cancelAdminExecutionRequest(cancelTarget, reason || "");
      setCancelTarget(null);
      await load();
    } catch (e: unknown) {
      setCancelError(e instanceof Error ? e.message : "Cancellation failed");
    }
  };

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
          {loading ? "Refreshing\u2026" : "Refresh"}
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
        <>
        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          <table className="table">
            <thead>
              <tr>
                <th>Analysis</th>
                <th>Status</th>
                <th>Project</th>
                <th>Runtime</th>
                <th>Created</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {filteredRequests.map((r) => (
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
                  <td>
                    <button
                      onClick={() => handleExpand(r.id)}
                      style={{
                        background: "none",
                        border: "none",
                        cursor: "pointer",
                        fontSize: "0.85rem",
                        padding: 0,
                        color: "var(--color-primary, #1976d2)",
                        textDecoration: expandedId === r.id ? "underline" : "none",
                      }}
                    >
                      {expandedId === r.id ? "Hide" : "Inspect"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {expandedId && expandedData[expandedId] && (() => {
          const detail = expandedData[expandedId];
          return (
            <div
              className="card"
              style={{
                marginTop: "var(--spacing-md)",
                padding: "var(--spacing-lg)",
                borderTop: "3px solid var(--color-primary, #1976d2)",
                fontSize: "0.85rem",
              }}
            >
              {/* Overview */}
              <section aria-label="Execution Overview">
                <h3 style={sectionHeader}>Overview</h3>
                <div style={detailRow}>
                  <span style={detailLabel}>Status</span>
                  <span
                    style={{
                      display: "inline-block",
                      padding: "2px 8px",
                      borderRadius: "4px",
                      fontSize: "0.8rem",
                      fontWeight: 600,
                      ...statusStyle(detail.status),
                    }}
                  >
                    {detail.status.charAt(0).toUpperCase() + detail.status.slice(1)}
                  </span>
                </div>
                <div style={detailRow}>
                  <span style={detailLabel}>Analysis</span>
                  <span style={detailValue}>{detail.name}</span>
                </div>
                <div style={detailRow}>
                  <span style={detailLabel}>Runtime</span>
                  <span style={detailValue}>{detail.runtime}</span>
                </div>
                <div style={detailRow}>
                  <span style={detailLabel}>Timeout</span>
                  <span style={detailValue}>{detail.timeout_seconds}s</span>
                </div>
                <div style={detailRow}>
                  <span style={detailLabel}>Created</span>
                  <span style={detailValue}>{formatTime(detail.created_at)}</span>
                </div>
                <div style={detailRow}>
                  <span style={detailLabel}>Updated</span>
                  <span style={detailValue}>{formatTime(detail.updated_at)}</span>
                </div>
              </section>

              {/* Cancellation provenance */}
              {(detail.status === "cancelled" || detail.status === "cancelling") && (
                <section aria-label="Cancellation Details">
                  <h3 style={sectionHeader}>Cancellation</h3>
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
                </section>
              )}

              {/* Cancel action */}
              {(detail.status === "pending" || detail.status === "running") && (
                <section aria-label="Cancel Action" style={{ marginTop: "var(--spacing-md)" }}>
                  <button
                    onClick={() => setCancelTarget(detail.id)}
                    style={{
                      padding: "6px 16px",
                      fontSize: "0.85rem",
                      background: "#c62828",
                      color: "#fff",
                      border: "none",
                      borderRadius: "4px",
                      cursor: "pointer",
                      fontWeight: 600,
                    }}
                  >
                    Cancel Execution
                  </button>
                </section>
              )}

              {/* Error */}
              {detail.status === "failed" && (
                <section aria-label="Execution Error">
                  <h3 style={sectionHeader}>Error</h3>
                  <div style={{
                    padding: "8px 12px",
                    background: "#f8d7da",
                    borderRadius: "4px",
                    fontSize: "0.85rem",
                    lineHeight: 1.5,
                    color: "#721c24",
                  }}>
                    {detail.log || "Execution failed with no log output."}
                  </div>
                </section>
              )}

              {/* Execution Log */}
              {detail.log && detail.status !== "failed" && (
                <section aria-label="Execution Log">
                  <h3 style={sectionHeader}>Execution Log</h3>
                  <LogViewer log={detail.log} title="Execution Log" maxHeight="300px" />
                </section>
              )}
            </div>
          );
        })()}
        </>
      )}

      {cancelTarget && (
        <ConfirmationDialog
          title="Cancel Execution?"
          message={
            "This execution will be terminated and marked as cancelled.\n\n" +
            "This action should only be used when operational intervention is required."
          }
          confirmLabel="Cancel Execution"
          requireReason
          reasonLabel="Reason for cancellation"
          onConfirm={handleCancelConfirm}
          onCancel={() => { setCancelTarget(null); setCancelError(null); }}
        />
      )}

      {cancelError && (
        <div
          style={{
            position: "fixed",
            bottom: "16px",
            right: "16px",
            padding: "8px 16px",
            background: "#f8d7da",
            color: "#721c24",
            borderRadius: "4px",
            fontSize: "0.85rem",
            zIndex: 1001,
            boxShadow: "0 2px 8px rgba(0,0,0,0.15)",
          }}
        >
          {cancelError}
        </div>
      )}
    </>
  );
}
