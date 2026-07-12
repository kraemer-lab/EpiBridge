"use client";

import { useEffect, useState } from "react";
import { ExecutionEnvironment, getAdminExecutionEnvironments } from "@/lib/api";

function statusStyle(status: string): React.CSSProperties {
  if (status === "active") {
    return { background: "#e6f7e6", color: "#2e7d32" };
  }
  return { background: "#fff3e0", color: "#e65100" };
}

export default function AdminEnvironmentsPage() {
  const [environments, setEnvironments] = useState<ExecutionEnvironment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getAdminExecutionEnvironments()
      .then(setEnvironments)
      .catch(() => setError("Failed to load execution environments"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <>
      <h2 style={{ fontSize: "1.1rem", fontWeight: 600, marginBottom: "var(--spacing-md)" }}>
        Execution Environments
      </h2>

      {loading ? (
        <div className="card empty-state">Loading...</div>
      ) : error ? (
        <div className="card empty-state">{error}</div>
      ) : environments.length === 0 ? (
        <div className="card empty-state">No execution environments registered.</div>
      ) : (
        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          <table className="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Runtime</th>
                <th>Status</th>
                <th>Image</th>
              </tr>
            </thead>
            <tbody>
              {environments.map((env) => (
                <tr key={env.id}>
                  <td style={{ fontWeight: 500 }}>{env.display_name}</td>
                  <td style={{ color: "var(--color-text-secondary)" }}>
                    {env.runtime}
                  </td>
                  <td>
                    <span
                      style={{
                        display: "inline-block",
                        padding: "2px 8px",
                        borderRadius: "4px",
                        fontSize: "0.8rem",
                        fontWeight: 600,
                        ...statusStyle(env.status),
                      }}
                    >
                      {env.status}
                    </span>
                  </td>
                  <td style={{ color: "var(--color-text-secondary)", fontSize: "0.85rem" }}>
                    <code>{env.image_reference}</code>
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
