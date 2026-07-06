"use client";

import { useEffect, useState } from "react";
import { AnalysisBundle, getAdminBundles } from "@/lib/api";

export default function AdminBundlesPage() {
  const [bundles, setBundles] = useState<AnalysisBundle[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getAdminBundles()
      .then(setBundles)
      .catch(() => setError("Failed to load analysis bundles"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <>
      <h2 style={{ fontSize: "1.1rem", fontWeight: 600, marginBottom: "var(--spacing-md)" }}>
        Analysis Bundles
      </h2>

      {loading ? (
        <div className="card empty-state">Loading...</div>
      ) : error ? (
        <div className="card empty-state">{error}</div>
      ) : bundles.length === 0 ? (
        <div className="card empty-state">No analysis bundles registered.</div>
      ) : (
        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          <table className="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Runtime</th>
                <th>Version</th>
                <th>Resources</th>
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
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
