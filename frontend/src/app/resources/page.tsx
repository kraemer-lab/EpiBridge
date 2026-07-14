"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { DataResource, getDataResources } from "@/lib/api";

const PROVIDER_LABELS: Record<string, string> = {
  csv: "CSV Dataset",
  duckdb: "DuckDB Database",
  postgres: "PostgreSQL Database",
  excel: "Excel Spreadsheet",
  parquet: "Parquet Dataset",
};

export default function ResourcesPage() {
  const [resources, setResources] = useState<DataResource[]>([]);

  const loadResources = useCallback(async () => {
    try {
      const data = await getDataResources();
      setResources(data);
    } catch {
      setResources([]);
    }
  }, []);

  useEffect(() => {
    loadResources();
  }, [loadResources]);

  return (
    <>
      <h1 className="page-title">Data Resources</h1>

      {resources.length === 0 ? (
        <div className="card empty-state">
          No data resources available.
        </div>
      ) : (
        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          <table className="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Type</th>
                <th>Version</th>
                <th>Description</th>
              </tr>
            </thead>
            <tbody>
              {resources.map((r) => (
                <tr key={r.id}>
                  <td style={{ fontWeight: 500 }}>
                    <Link
                      href={`/resources/${r.identifier}`}
                      style={{ color: "var(--color-primary)", textDecoration: "none" }}
                    >
                      {r.name}
                    </Link>
                  </td>
                  <td style={{ color: "var(--color-text-secondary)" }}>
                    {PROVIDER_LABELS[r.provider_type] || r.provider_type}
                  </td>
                  <td style={{ color: "var(--color-text-secondary)" }}>
                    {r.version}
                  </td>
                  <td style={{ color: "var(--color-text-secondary)" }}>
                    {r.description || "—"}
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
