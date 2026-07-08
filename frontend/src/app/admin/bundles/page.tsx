"use client";

import { useEffect, useState } from "react";
import { AnalysisBundle, AuditEvent, getAdminBundles, getAuditEvents } from "@/lib/api";

function eventLabel(eventType: string): string {
  const labels: Record<string, string> = {
    "bundle.created": "Created",
    "bundle.submitted": "Submitted",
    "bundle.approved": "Approved",
    "bundle.rejected": "Rejected",
    "bundle.superseded": "Superseded",
    "execution.requested": "Execution requested",
    "execution.started": "Execution started",
    "execution.completed": "Execution completed",
    "execution.failed": "Execution failed",
  };
  return labels[eventType] || eventType;
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleString();
}

export default function AdminBundlesPage() {
  const [bundles, setBundles] = useState<AnalysisBundle[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [bundleAudit, setBundleAudit] = useState<Record<string, AuditEvent[]>>({});

  useEffect(() => {
    getAdminBundles()
      .then(setBundles)
      .catch(() => setError("Failed to load analysis bundles"))
      .finally(() => setLoading(false));
  }, []);

  const handleExpand = async (bundleId: string) => {
    if (expandedId === bundleId) {
      setExpandedId(null);
      return;
    }
    if (!bundleAudit[bundleId]) {
      try {
        const res = await getAuditEvents({
          resource_type: "analysis_bundle",
          resource_id: bundleId,
          limit: 20,
        });
        setBundleAudit((prev) => ({ ...prev, [bundleId]: res.items }));
      } catch {
        setBundleAudit((prev) => ({ ...prev, [bundleId]: [] }));
      }
    }
    setExpandedId(bundleId);
  };

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
                <th>History</th>
              </tr>
            </thead>
            <tbody>
              {bundles.map((b) => (
                <>
                  <tr key={b.id}>
                    <td style={{ fontWeight: 500 }}>{b.name}</td>
                    <td style={{ color: "var(--color-text-secondary)" }}>
                      {b.runtime}
                    </td>
                    <td style={{ color: "var(--color-text-secondary)" }}>
                      {b.version}
                    </td>
                    <td>
                      <button
                        onClick={() => handleExpand(b.id)}
                        style={{
                          background: "none",
                          border: "none",
                          cursor: "pointer",
                          fontSize: "0.85rem",
                          padding: 0,
                          color: "var(--color-primary, #1976d2)",
                          textDecoration: expandedId === b.id ? "underline" : "none",
                        }}
                      >
                        {expandedId === b.id ? "Hide" : "Show"} history
                      </button>
                    </td>
                  </tr>
                  {expandedId === b.id && (
                    <tr key={`${b.id}-audit`}>
                      <td colSpan={4} style={{ padding: "0 16px 8px 16px" }}>
                        {!bundleAudit[b.id] ? (
                          <div style={{ fontSize: "0.85rem", color: "var(--color-text-secondary)" }}>
                            Loading...
                          </div>
                        ) : bundleAudit[b.id].length === 0 ? (
                          <div style={{ fontSize: "0.85rem", color: "var(--color-text-secondary)" }}>
                            No audit events for this analysis.
                          </div>
                        ) : (
                          <div style={{ fontSize: "0.85rem" }}>
                            {bundleAudit[b.id].map((e) => (
                              <div
                                key={e.id}
                                style={{
                                  display: "flex",
                                  justifyContent: "space-between",
                                  padding: "4px 0",
                                  borderBottom: "1px solid var(--color-border, #eee)",
                                }}
                              >
                                <span style={{ fontWeight: 500 }}>{eventLabel(e.event_type)}</span>
                                <span style={{ color: "var(--color-text-secondary)" }}>
                                  {e.actor_display_name} — {formatTime(e.occurred_at)}
                                </span>
                              </div>
                            ))}
                          </div>
                        )}
                      </td>
                    </tr>
                  )}
                </>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
