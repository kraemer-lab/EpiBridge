"use client";

import { useEffect, useState } from "react";
import {
  ExecutionRequest,
  Output,
  getAdminOutputs,
  getAdminExecutionRequests,
  approveOutput,
  rejectOutput,
  releaseOutput,
} from "@/lib/api";

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
  const [outputs, setOutputs] = useState<Output[]>([]);
  const [requests, setRequests] = useState<ExecutionRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    Promise.all([
      getAdminOutputs(),
      getAdminExecutionRequests().catch(() => [] as ExecutionRequest[]),
    ])
      .then(([outs, reqs]) => {
        setOutputs(outs);
        setRequests(reqs);
      })
      .catch(() => setError("Failed to load outputs"))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const requestMap: Record<string, ExecutionRequest> = {};
  for (const r of requests) {
    requestMap[r.id] = r;
  }

  const handleApprove = async (id: string) => {
    await approveOutput(id);
    load();
  };

  const handleReject = async (id: string) => {
    await rejectOutput(id);
    load();
  };

  const handleRelease = async (id: string) => {
    await releaseOutput(id);
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
      ) : outputs.length === 0 ? (
        <div className="card empty-state">No outputs registered yet.</div>
      ) : (
        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          <table className="table">
            <thead>
              <tr>
                <th>Filename</th>
                <th>Analysis</th>
                <th>Size</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {outputs.map((o) => {
                const badge = statusBadge(o.status);
                const req = requestMap[o.execution_request_id];
                const analysisName = req ? req.analysis_name : o.execution_request_id.slice(0, 8);
                return (
                  <tr key={o.id} data-execution-request-id={o.execution_request_id}>
                    <td style={{ fontWeight: 500 }}>{o.filename}</td>
                    <td style={{ color: "var(--color-text-secondary)", fontSize: "0.85rem" }}>
                      {analysisName}
                    </td>
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
                      <div style={{ display: "flex", gap: "var(--spacing-xs)" }}>
                        {o.status === "pending_review" && (
                          <>
                            <button
                              className="btn btn-sm"
                              style={{ background: "var(--color-success, #2e7d32)", color: "#fff", border: "none" }}
                              onClick={() => handleApprove(o.id)}
                            >
                              Approve
                            </button>
                            <button
                              className="btn btn-sm"
                              style={{ background: "var(--color-danger, #c62828)", color: "#fff", border: "none" }}
                              onClick={() => handleReject(o.id)}
                            >
                              Reject
                            </button>
                          </>
                        )}
                        {o.status === "approved" && (
                          <button
                            className="btn btn-sm"
                            style={{ background: "var(--color-primary, #1976d2)", color: "#fff", border: "none" }}
                            onClick={() => handleRelease(o.id)}
                          >
                            Release
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
