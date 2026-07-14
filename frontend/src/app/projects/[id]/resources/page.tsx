"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import {
  DataResource,
  getProjectResources,
  getAdminResources,
  attachProjectResources,
  detachProjectResource,
  getResourceTermsCurrent,
} from "@/lib/api";
import { TermsDialog } from "@/components/TermsDialog";

const PROVIDER_LABELS: Record<string, string> = {
  csv: "CSV Dataset",
  duckdb: "DuckDB Database",
  postgres: "PostgreSQL Database",
  excel: "Excel Spreadsheet",
  parquet: "Parquet Dataset",
};

export default function ProjectResourcesPage() {
  const params = useParams();
  const projectId = params.id as string;

  const [attached, setAttached] = useState<DataResource[]>([]);
  const [available, setAvailable] = useState<DataResource[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [termsResource, setTermsResource] = useState<DataResource | null>(null);
  const [pendingIdentifier, setPendingIdentifier] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [all, project] = await Promise.all([
        getAdminResources(),
        getProjectResources(projectId),
      ]);
      const attachedIds = new Set(project.map((r) => r.id));
      setAttached(project);
      setAvailable(all.filter((r) => !attachedIds.has(r.id)));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load resources");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    load();
  }, [load]);

  const handleAttach = async (identifier: string) => {
    const resource = available.find((r) => r.identifier === identifier);
    if (!resource) return;
    try {
      const terms = await getResourceTermsCurrent(resource.id);
      if (terms) {
        setPendingIdentifier(identifier);
        setTermsResource(resource);
        return;
      }
    } catch {
      // No terms published — proceed directly
    }
    await doAttach(identifier);
  };

  const doAttach = async (identifier: string) => {
    try {
      await attachProjectResources(projectId, [identifier]);
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to attach resource");
    }
  };

  const handleTermsAccept = () => {
    setTermsResource(null);
    if (pendingIdentifier) {
      doAttach(pendingIdentifier);
      setPendingIdentifier(null);
    }
  };

  const handleTermsCancel = () => {
    setTermsResource(null);
    setPendingIdentifier(null);
  };

  const handleDetach = async (resourceId: string) => {
    try {
      await detachProjectResource(projectId, resourceId);
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to detach resource");
    }
  };

  return (
    <div>
      {termsResource && (
        <TermsDialog
          resourceId={termsResource.id}
          resourceName={termsResource.name}
          onAccept={handleTermsAccept}
          onCancel={handleTermsCancel}
          requireAcceptance={true}
        />
      )}

      <h2 style={{ fontSize: "1.1rem", fontWeight: 600, marginBottom: "var(--spacing-lg)" }}>
        Configure Resources
      </h2>

      {error && (
        <div
          style={{
            color: "#e65100",
            marginBottom: "var(--spacing-md)",
            fontSize: "0.9rem",
          }}
        >
          {error}
        </div>
      )}

      {loading ? (
        <div className="card empty-state">Loading...</div>
      ) : (
        <>
          <h3 style={{ fontSize: "0.95rem", fontWeight: 600, marginBottom: "var(--spacing-sm)" }}>
            Attached Data Resources
          </h3>
          {attached.length === 0 ? (
            <div className="card empty-state" style={{ marginBottom: "var(--spacing-lg)" }}>
              No resources attached. Select from the available resources below.
            </div>
          ) : (
            <div className="card" style={{ padding: 0, overflow: "hidden", marginBottom: "var(--spacing-lg)" }}>
              <table className="table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Type</th>
                    <th>Identifier</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {attached.map((r) => (
                    <tr key={r.id}>
                      <td style={{ fontWeight: 500 }}>{r.name}</td>
                      <td style={{ color: "var(--color-text-secondary)" }}>
                        {PROVIDER_LABELS[r.provider_type] || r.provider_type}
                      </td>
                      <td style={{ color: "var(--color-text-secondary)", fontFamily: "monospace", fontSize: "0.85rem" }}>
                        {r.identifier}
                      </td>
                      <td>
                        <button
                          className="btn"
                          style={{ fontSize: "0.8rem", padding: "2px 10px" }}
                          onClick={() => handleDetach(r.id)}
                        >
                          Detach
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <h3 style={{ fontSize: "0.95rem", fontWeight: 600, marginBottom: "var(--spacing-sm)" }}>
            Available Data Resources
          </h3>
          {available.length === 0 ? (
            <div className="card empty-state">
              All available resources are attached.
            </div>
          ) : (
            <div className="card" style={{ padding: 0, overflow: "hidden" }}>
              <table className="table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Type</th>
                    <th>Identifier</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {available.map((r) => (
                    <tr key={r.id}>
                      <td style={{ fontWeight: 500 }}>{r.name}</td>
                      <td style={{ color: "var(--color-text-secondary)" }}>
                        {PROVIDER_LABELS[r.provider_type] || r.provider_type}
                      </td>
                      <td style={{ color: "var(--color-text-secondary)", fontFamily: "monospace", fontSize: "0.85rem" }}>
                        {r.identifier}
                      </td>
                      <td>
                        <button
                          className="btn btn-primary"
                          style={{ fontSize: "0.8rem", padding: "2px 10px" }}
                          onClick={() => handleAttach(r.identifier)}
                        >
                          Attach
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  );
}
