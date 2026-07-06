"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { AnalysisBundle, getProjectBundles } from "@/lib/api";

export default function ProjectAnalysisPage() {
  const params = useParams();
  const projectId = params.id as string;

  const [bundles, setBundles] = useState<AnalysisBundle[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getProjectBundles(projectId)
      .then(setBundles)
      .catch(() => setError("Failed to load analysis bundles"))
      .finally(() => setLoading(false));
  }, [projectId]);

  return (
    <div>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "var(--spacing-md)",
        }}
      >
        <h2 style={{ fontSize: "1.1rem", fontWeight: 600, marginBottom: 0 }}>
          Analysis Bundles
        </h2>
        <button
          className="btn"
          style={{ opacity: 0.5, cursor: "not-allowed" }}
          disabled
          title="Bundle creation will be available in a future milestone"
        >
          Create Analysis
        </button>
      </div>

      {loading ? (
        <div className="card empty-state">Loading...</div>
      ) : error ? (
        <div className="card empty-state">{error}</div>
      ) : bundles.length === 0 ? (
        <div className="card empty-state">
          No analysis bundles. Bundle creation will be available in a future milestone.
        </div>
      ) : (
        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          <table className="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Runtime</th>
                <th>Version</th>
                <th>Resources</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {bundles.map((b) => (
                <tr key={b.id}>
                  <td style={{ fontWeight: 500 }}>{b.name}</td>
                  <td style={{ color: "var(--color-text-secondary)" }}>
                    {b.runtime}
                  </td>
                  <td style={{ color: "var(--color-text-secondary)" }}>
                    {b.version}
                  </td>
                  <td style={{ color: "var(--color-text-secondary)" }}>
                    {b.resource_identifiers.length > 0
                      ? b.resource_identifiers.join(", ")
                      : "—"}
                  </td>
                  <td style={{ color: "var(--color-text-secondary)" }}>
                    {new Date(b.created_at).toLocaleDateString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
