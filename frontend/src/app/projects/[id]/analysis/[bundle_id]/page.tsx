"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { AnalysisBundle, getProjectBundle, createExecutionRequest } from "@/lib/api";

export default function AnalysisDetailPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.id as string;
  const bundleId = params.bundle_id as string;

  const [bundle, setBundle] = useState<AnalysisBundle | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    getProjectBundle(projectId, bundleId)
      .then(setBundle)
      .catch(() => setError("Failed to load analysis bundle"))
      .finally(() => setLoading(false));
  }, [projectId, bundleId]);

  const handleRun = async () => {
    setRunning(true);
    try {
      await createExecutionRequest(projectId, {
        analysis_bundle_id: bundleId,
      });
      router.push(`/projects/${projectId}/jobs`);
    } catch {
      setError("Failed to create execution request");
      setRunning(false);
    }
  };

  if (loading) return <div className="card empty-state">Loading...</div>;
  if (error) return <div className="card empty-state">{error}</div>;
  if (!bundle) return <div className="card empty-state">Not found</div>;

  return (
    <div>
      <Link
        href={`/projects/${projectId}/analysis`}
        style={{ color: "var(--color-text-secondary)", fontSize: "0.85rem", textDecoration: "none" }}
      >
        &larr; Back to Analysis
      </Link>

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginTop: "var(--spacing-md)", marginBottom: "var(--spacing-lg)" }}>
        <div>
          <h2 style={{ fontSize: "1.1rem", fontWeight: 600, marginBottom: "var(--spacing-xs)" }}>
            {bundle.name}
          </h2>
          <span
            style={{
              display: "inline-block",
              padding: "2px 8px",
              borderRadius: "4px",
              fontSize: "0.8rem",
              fontWeight: 600,
              background: "var(--color-surface)",
              color: "var(--color-text-secondary)",
            }}
          >
            {bundle.status.charAt(0).toUpperCase() + bundle.status.slice(1)}
          </span>
        </div>
        <div style={{ display: "flex", gap: "var(--spacing-sm)" }}>
          <button className="btn btn-primary" onClick={handleRun} disabled={running}>
            {running ? "Submitting..." : "Run Analysis"}
          </button>
          <Link
            href={`/projects/${projectId}/analysis/${bundleId}/edit`}
            className="btn"
            style={{ textDecoration: "none" }}
          >
            Edit
          </Link>
        </div>
      </div>

      <div className="card" style={{ maxWidth: "640px" }}>
        <div style={{ marginBottom: "var(--spacing-md)" }}>
          <div style={{ fontSize: "0.8rem", color: "var(--color-text-secondary)", marginBottom: "var(--spacing-xs)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>
            Runtime
          </div>
          <div>{bundle.runtime}</div>
        </div>

        <div style={{ marginBottom: "var(--spacing-md)" }}>
          <div style={{ fontSize: "0.8rem", color: "var(--color-text-secondary)", marginBottom: "var(--spacing-xs)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>
            Version
          </div>
          <div>{bundle.version}</div>
        </div>

        {bundle.description && (
          <div style={{ marginBottom: "var(--spacing-md)" }}>
            <div style={{ fontSize: "0.8rem", color: "var(--color-text-secondary)", marginBottom: "var(--spacing-xs)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>
              Description
            </div>
            <div style={{ lineHeight: 1.6 }}>{bundle.description}</div>
          </div>
        )}

        <div style={{ marginBottom: "var(--spacing-md)" }}>
          <div style={{ fontSize: "0.8rem", color: "var(--color-text-secondary)", marginBottom: "var(--spacing-xs)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>
            Entrypoint
          </div>
          <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.9rem" }}>{bundle.entrypoint}</div>
        </div>

        <div style={{ marginBottom: "var(--spacing-md)" }}>
          <div style={{ fontSize: "0.8rem", color: "var(--color-text-secondary)", marginBottom: "var(--spacing-xs)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>
            Data Resources
          </div>
          {bundle.resource_identifiers.length > 0 ? (
            <ul style={{ margin: 0, paddingLeft: "var(--spacing-lg)" }}>
              {bundle.resource_identifiers.map((id) => (
                <li key={id} style={{ marginBottom: "var(--spacing-xs)" }}>{id}</li>
              ))}
            </ul>
          ) : (
            <div style={{ color: "var(--color-text-secondary)" }}>None</div>
          )}
        </div>

        <div style={{ marginBottom: "var(--spacing-md)" }}>
          <div style={{ fontSize: "0.8rem", color: "var(--color-text-secondary)", marginBottom: "var(--spacing-xs)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>
            Expected Outputs
          </div>
          {bundle.outputs.length > 0 ? (
            <ul style={{ margin: 0, paddingLeft: "var(--spacing-lg)" }}>
              {bundle.outputs.map((o, i) => (
                <li key={i} style={{ marginBottom: "var(--spacing-xs)" }}>{o}</li>
              ))}
            </ul>
          ) : (
            <div style={{ color: "var(--color-text-secondary)" }}>None specified</div>
          )}
        </div>

        <div style={{ display: "flex", gap: "var(--spacing-xl)", paddingTop: "var(--spacing-md)", borderTop: "1px solid var(--color-border)" }}>
          <div>
            <div style={{ fontSize: "0.8rem", color: "var(--color-text-secondary)", marginBottom: "var(--spacing-xs)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>
              Created
            </div>
            <div>{new Date(bundle.created_at).toLocaleDateString()}</div>
          </div>
          <div>
            <div style={{ fontSize: "0.8rem", color: "var(--color-text-secondary)", marginBottom: "var(--spacing-xs)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>
              Updated
            </div>
            <div>{new Date(bundle.updated_at).toLocaleDateString()}</div>
          </div>
        </div>
      </div>
    </div>
  );
}
