"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { DataResource, getAdminResources } from "@/lib/api";

const PROVIDER_LABELS: Record<string, string> = {
  csv: "CSV Dataset",
  duckdb: "DuckDB Database",
  postgres: "PostgreSQL Database",
  excel: "Excel Spreadsheet",
  parquet: "Parquet Dataset",
};

export default function AdminPage() {
  const [resources, setResources] = useState<DataResource[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getAdminResources()
      .then(setResources)
      .catch(() => setError("Failed to load resources"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <>
      <h2 style={{ fontSize: "1.1rem", fontWeight: 600, marginBottom: "var(--spacing-md)" }}>
        Data Resources
      </h2>

      {loading ? (
        <div className="card empty-state">Loading...</div>
      ) : error ? (
        <div className="card empty-state">{error}</div>
      ) : resources.length === 0 ? (
        <div className="card empty-state">No resources registered.</div>
      ) : (
        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          <table className="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Type</th>
                <th>Version</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {resources.map((r) => (
                <tr key={r.id}>
                  <td style={{ fontWeight: 500 }}>{r.name}</td>
                  <td style={{ color: "var(--color-text-secondary)" }}>
                    {PROVIDER_LABELS[r.provider_type] || r.provider_type}
                  </td>
                  <td style={{ color: "var(--color-text-secondary)" }}>
                    {r.version}
                  </td>
                  <td>
                    <span
                      style={{
                        display: "inline-block",
                        padding: "2px 8px",
                        borderRadius: "4px",
                        fontSize: "0.8rem",
                        fontWeight: 600,
                        background:
                          r.status === "active"
                            ? "var(--color-success-bg, #e6f7e6)"
                            : "var(--color-warning-bg, #fff3e0)",
                        color:
                          r.status === "active"
                            ? "var(--color-success, #2e7d32)"
                            : "var(--color-warning, #e65100)",
                      }}
                    >
                      {r.status}
                    </span>
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
