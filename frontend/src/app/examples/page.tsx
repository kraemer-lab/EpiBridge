"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { ExampleAnalysis, getExampleAnalyses } from "@/lib/api";

export default function ExamplesPage() {
  const [examples, setExamples] = useState<ExampleAnalysis[]>([]);

  const load = useCallback(async () => {
    try {
      const data = await getExampleAnalyses();
      setExamples(data);
    } catch {
      setExamples([]);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <>
      <h1 className="page-title">Example Analyses</h1>
      <p style={{ color: "var(--color-text-secondary)", marginBottom: "var(--spacing-lg)", lineHeight: 1.6 }}>
        Published example analyses demonstrating analysis patterns using institutional data resources.
        Study these examples to understand how Analysis Bundles work.
      </p>

      {examples.length === 0 ? (
        <div className="card empty-state">
          No example analyses available.
        </div>
      ) : (
        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          <table className="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Environment</th>
                <th>Data Resources</th>
                <th>Description</th>
              </tr>
            </thead>
            <tbody>
              {examples.map((ex) => (
                <tr key={ex.identifier}>
                  <td style={{ fontWeight: 500 }}>
                    <Link
                      href={`/examples/${ex.identifier}`}
                      style={{ color: "var(--color-primary)", textDecoration: "none" }}
                    >
                      {ex.name}
                    </Link>
                  </td>
                  <td style={{ color: "var(--color-text-secondary)" }}>
                    {ex.execution_environment_identifier ? (
                      <Link
                        href={`/environments/${ex.execution_environment_identifier}`}
                        style={{ color: "var(--color-primary)", textDecoration: "none" }}
                      >
                        {ex.execution_environment_identifier}
                      </Link>
                    ) : "—"}
                  </td>
                  <td style={{ color: "var(--color-text-secondary)" }}>
                    {ex.data_resource_identifiers.length > 0
                      ? ex.data_resource_identifiers.join(", ")
                      : "—"}
                  </td>
                  <td style={{ color: "var(--color-text-secondary)" }}>
                    {ex.description || "—"}
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
