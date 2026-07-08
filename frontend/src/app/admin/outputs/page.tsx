"use client";

import { useEffect, useState } from "react";
import {
  OutputSetListItem,
  AuditEvent,
  getAdminOutputSets,
  getAdminOutputSet,
  approveOutputSet,
  rejectOutputSet,
  releaseOutputSet,
  getAuditEvents,
} from "@/lib/api";

function eventLabel(eventType: string): string {
  const labels: Record<string, string> = {
    "output_set.created": "Output set created",
    "output_set.approved": "Output approved",
    "output_set.rejected": "Output rejected",
    "output_set.released": "Output released",
    "execution.started": "Execution started",
    "execution.completed": "Execution completed",
    "execution.failed": "Execution failed",
  };
  return labels[eventType] || eventType;
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleString();
}

function statusBadge(status: string): { background: string; color: string; label: string } {
  switch (status) {
    case "pending_review":
      return { background: "#fff3e0", color: "#e65100", label: "Pending Review" };
    case "approved":
      return { background: "#e3f2fd", color: "#1565c0", label: "Approved" };
    case "rejected":
      return { background: "#f8d7da", color: "#721c24", label: "Rejected" };
    case "released":
      return { background: "#d4edda", color: "#155724", label: "Released" };
    default:
      return { background: "#f0f0f0", color: "#666", label: status };
  }
}

export default function AdminOutputsPage() {
  const [sets, setSets] = useState<OutputSetListItem[]>([]);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [expandedOutputs, setExpandedOutputs] = useState<{ filename: string; size: number }[]>([]);
  const [outputAudit, setOutputAudit] = useState<Record<string, AuditEvent[]>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    getAdminOutputSets()
      .then(setSets)
      .catch(() => setError("Failed to load output sets"))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const handleExpand = async (id: string) => {
    if (expandedId === id) {
      setExpandedId(null);
      setExpandedOutputs([]);
      return;
    }
    try {
      const outputSet = await getAdminOutputSet(id);
      setExpandedOutputs(outputSet.outputs);
    } catch {
      setExpandedOutputs([]);
    }
    if (!outputAudit[id]) {
      try {
        const res = await getAuditEvents({
          resource_type: "output_set",
          resource_id: id,
          limit: 20,
        });
        setOutputAudit((prev) => ({ ...prev, [id]: res.items }));
      } catch {
        setOutputAudit((prev) => ({ ...prev, [id]: [] }));
      }
    }
    setExpandedId(id);
  };

  const handleApprove = async (id: string) => {
    await approveOutputSet(id);
    load();
  };

  const handleReject = async (id: string) => {
    await rejectOutputSet(id);
    load();
  };

  const handleRelease = async (id: string) => {
    await releaseOutputSet(id);
    load();
  };

  return (
    <>
      <h2 style={{ fontSize: "1.1rem", fontWeight: 600, marginBottom: "var(--spacing-md)" }}>
        Execution Outputs
      </h2>

      {loading ? (
        <div className="card empty-state">Loading...</div>
      ) : error ? (
        <div className="card empty-state">{error}</div>
      ) : sets.length === 0 ? (
        <div className="card empty-state">No output sets registered yet.</div>
      ) : (
        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          <table className="table">
            <thead>
              <tr>
                <th>Analysis</th>
                <th>Files</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {sets.map((s) => {
                const badge = statusBadge(s.status);
                return (
                  <>
                    <tr key={s.id}>
                      <td style={{ fontWeight: 500 }}>
                        <button
                          onClick={() => handleExpand(s.id)}
                          style={{
                            background: "none",
                            border: "none",
                            cursor: "pointer",
                            fontWeight: 600,
                            fontSize: "0.9rem",
                            padding: 0,
                            color: "var(--color-text)",
                            textDecoration: expandedId === s.id ? "underline" : "none",
                          }}
                        >
                          {s.execution_request_name || s.execution_request_id.slice(0, 8)}
                        </button>
                      </td>
                      <td style={{ color: "var(--color-text-secondary)", fontSize: "0.85rem" }}>
                        {s.file_count} file{s.file_count !== 1 ? "s" : ""}
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
                        <div style={{ display: "flex", gap: "var(--spacing-xs)" }}>
                          {s.status === "pending_review" && (
                            <>
                              <button
                                className="btn btn-sm"
                                style={{ background: "var(--color-success, #2e7d32)", color: "#fff", border: "none" }}
                                onClick={() => handleApprove(s.id)}
                              >
                                Approve
                              </button>
                              <button
                                className="btn btn-sm"
                                style={{ background: "var(--color-danger, #c62828)", color: "#fff", border: "none" }}
                                onClick={() => handleReject(s.id)}
                              >
                                Reject
                              </button>
                            </>
                          )}
                          {s.status === "approved" && (
                            <button
                              className="btn btn-sm"
                              style={{ background: "var(--color-primary, #1976d2)", color: "#fff", border: "none" }}
                              onClick={() => handleRelease(s.id)}
                            >
                              Release
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                    {expandedId === s.id && (
                      <tr key={`${s.id}-detail`}>
                        <td colSpan={4} style={{ padding: "0 16px 8px 16px" }}>
                          {expandedOutputs.length > 0 && (
                            <div style={{ fontSize: "0.85rem", color: "var(--color-text-secondary)", marginBottom: "var(--spacing-sm)" }}>
                              <strong style={{ display: "block", marginBottom: "4px" }}>Artefacts:</strong>
                              {expandedOutputs.map((o) => (
                                <div key={o.filename} style={{ padding: "2px 0" }}>
                                  {o.filename} — {o.size > 1024 ? `${(o.size / 1024).toFixed(1)} KB` : `${o.size} bytes`}
                                </div>
                              ))}
                            </div>
                          )}
                          <div style={{ fontSize: "0.85rem" }}>
                            <strong style={{ display: "block", marginBottom: "4px" }}>Audit History:</strong>
                            {!outputAudit[s.id] ? (
                              <div style={{ color: "var(--color-text-secondary)" }}>Loading...</div>
                            ) : outputAudit[s.id].length === 0 ? (
                              <div style={{ color: "var(--color-text-secondary)" }}>No audit events.</div>
                            ) : (
                              outputAudit[s.id].map((e) => (
                                <div
                                  key={e.id}
                                  style={{
                                    display: "flex",
                                    justifyContent: "space-between",
                                    padding: "3px 0",
                                    borderBottom: "1px solid var(--color-border, #eee)",
                                  }}
                                >
                                  <span style={{ fontWeight: 500 }}>{eventLabel(e.event_type)}</span>
                                  <span style={{ color: "var(--color-text-secondary)" }}>
                                    {e.actor_display_name} — {formatTime(e.occurred_at)}
                                  </span>
                                </div>
                              ))
                            )}
                          </div>
                        </td>
                      </tr>
                    )}
                  </>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
