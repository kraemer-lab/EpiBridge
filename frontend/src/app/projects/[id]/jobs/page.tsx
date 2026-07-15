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
    case "cancelled":
      return { background: "#fff3cd", color: "#856404" };
    default:
      return { background: "#f0f0f0", color: "#666" };
  }
}

export default function ProjectJobsPage() {
  const params = useParams();
  const projectId = params.id as string;

  const [requests, setRequests] = useState<ExecutionRequest[]>([]);
  const [loading, setLoading] = useState(true);

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
          </tr>
        </thead>
        <tbody>
          {requests.map((r) => (
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
                  {r.status}
                </span>
              </td>
              <td style={{ color: "var(--color-text-secondary)" }}>
                {new Date(r.created_at).toLocaleString()}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
