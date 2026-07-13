"use client";

import { useCallback, useEffect, useState } from "react";
import {
  getAdminTermsStatus,
  getAdminResources,
  publishPlatformTerms,
  publishResourceTerms,
} from "@/lib/api";
import type {
  AdminTermsStatus,
  DataResource,
  TermsVersionEntry,
} from "@/lib/api";

function VersionTable({
  title,
  currentId,
  history,
}: {
  title: string;
  currentId: string | null;
  history: TermsVersionEntry[];
}) {
  if (history.length === 0) {
    return (
      <div className="empty-state" style={{ marginBottom: "var(--spacing-md)" }}>
        None published.
      </div>
    );
  }
  return (
    <div className="card" style={{ padding: 0, overflow: "hidden", marginBottom: "var(--spacing-md)" }}>
      <table className="table">
        <thead>
          <tr>
            <th>{title}</th>
            <th>Version</th>
            <th>Published</th>
            <th>Acceptances</th>
          </tr>
        </thead>
        <tbody>
          {history.map((entry) => (
            <tr key={entry.id}>
              <td>
                {entry.title}
                {entry.id === currentId && (
                  <span
                    style={{
                      marginLeft: "var(--spacing-sm)",
                      display: "inline-block",
                      padding: "1px 6px",
                      borderRadius: "3px",
                      fontSize: "0.75rem",
                      fontWeight: 600,
                      background: "#e3f2fd",
                      color: "#1565c0",
                    }}
                  >
                    current
                  </span>
                )}
              </td>
              <td style={{ fontFamily: "var(--font-mono)", fontSize: "0.85rem" }}>
                {entry.version}
              </td>
              <td style={{ color: "var(--color-text-secondary)", fontSize: "0.85rem" }}>
                {entry.published_at
                  ? new Date(entry.published_at).toLocaleDateString()
                  : "—"}
              </td>
              <td style={{ textAlign: "center" }}>{entry.acceptance_count}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function AdminTermsPage() {
  const [status, setStatus] = useState<AdminTermsStatus | null>(null);
  const [resources, setResources] = useState<DataResource[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Platform publish form
  const [platVersion, setPlatVersion] = useState("");
  const [platTitle, setPlatTitle] = useState("");
  const [platContent, setPlatContent] = useState("");
  const [publishing, setPublishing] = useState(false);

  // Resource publish
  const [selectedResource, setSelectedResource] = useState<string>("");
  const [resVersion, setResVersion] = useState("");
  const [resTitle, setResTitle] = useState("");
  const [resContent, setResContent] = useState("");
  const [publishingRes, setPublishingRes] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const s = await getAdminTermsStatus();
      setStatus(s);
    } catch {
      setError("Failed to load terms status.");
      setLoading(false);
      return;
    }
    getAdminResources()
      .then(setResources)
      .catch(() => setResources([]));
    setLoading(false);
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handlePublishPlatform = async () => {
    if (!platVersion || !platTitle || !platContent) return;
    setPublishing(true);
    setError(null);
    setSuccess(null);
    try {
      await publishPlatformTerms({
        version: platVersion,
        title: platTitle,
        content: platContent,
      });
      setSuccess("Platform terms published.");
      setPlatVersion("");
      setPlatTitle("");
      setPlatContent("");
      await load();
    } catch {
      setError("Failed to publish platform terms.");
    } finally {
      setPublishing(false);
    }
  };

  const handlePublishResource = async () => {
    if (!selectedResource || !resVersion || !resTitle || !resContent) return;
    setPublishingRes(true);
    setError(null);
    setSuccess(null);
    try {
      await publishResourceTerms(selectedResource, {
        version: resVersion,
        title: resTitle,
        content: resContent,
      });
      setSuccess("Resource terms published.");
      setResVersion("");
      setResTitle("");
      setResContent("");
      setSelectedResource("");
      await load();
    } catch {
      setError("Failed to publish resource terms.");
    } finally {
      setPublishingRes(false);
    }
  };

  if (loading) return <div className="card empty-state">Loading...</div>;

  return (
    <div>
      <h2 style={{ fontSize: "1.1rem", fontWeight: 600, marginBottom: "var(--spacing-lg)" }}>
        Terms of Service — Published Versions
      </h2>

      {error && (
        <div style={{ color: "#d32f2f", marginBottom: "var(--spacing-md)", fontSize: "0.9rem" }}>
          {error}
        </div>
      )}
      {success && (
        <div style={{ color: "#2e7d32", marginBottom: "var(--spacing-md)", fontSize: "0.9rem" }}>
          {success}
        </div>
      )}

      {/* Platform Terms */}
      <div className="card" style={{ marginBottom: "var(--spacing-lg)" }}>
        <h3 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "var(--spacing-md)" }}>
          Platform Terms
        </h3>

        <VersionTable
          title="Version"
          currentId={status?.platform.current?.id ?? null}
          history={status?.platform.history ?? []}
        />

        <div style={{ borderTop: "1px solid var(--color-border)", paddingTop: "var(--spacing-md)" }}>
          <div style={{ fontSize: "0.9rem", fontWeight: 600, marginBottom: "var(--spacing-sm)" }}>
            Publish New Version
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-sm)" }}>
            <div style={{ display: "flex", gap: "var(--spacing-sm)" }}>
              <input
                placeholder="Version (e.g., 1.0.0)"
                value={platVersion}
                onChange={(e) => setPlatVersion(e.target.value)}
                style={{ flex: 1, padding: "6px 10px", borderRadius: "var(--radius-sm)", border: "1px solid var(--color-border)", fontSize: "0.9rem" }}
              />
              <input
                placeholder="Title"
                value={platTitle}
                onChange={(e) => setPlatTitle(e.target.value)}
                style={{ flex: 2, padding: "6px 10px", borderRadius: "var(--radius-sm)", border: "1px solid var(--color-border)", fontSize: "0.9rem" }}
              />
            </div>
            <textarea
              placeholder="Terms content (Markdown)"
              value={platContent}
              onChange={(e) => setPlatContent(e.target.value)}
              rows={6}
              style={{ padding: "6px 10px", borderRadius: "var(--radius-sm)", border: "1px solid var(--color-border)", fontSize: "0.9rem", fontFamily: "var(--font-mono)" }}
            />
            <div>
              <button
                className="btn btn-primary"
                onClick={handlePublishPlatform}
                disabled={publishing || !platVersion || !platTitle || !platContent}
              >
                {publishing ? "Publishing..." : "Publish Platform Terms"}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Resource Terms */}
      <div className="card" style={{ marginBottom: "var(--spacing-lg)" }}>
        <h3 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "var(--spacing-md)" }}>
          Data Resource Terms
        </h3>

        {status && status.resource_terms.length === 0 ? (
          <div className="empty-state" style={{ marginBottom: "var(--spacing-md)" }}>
            No data resources have published terms.
          </div>
        ) : (
          status?.resource_terms.map((rt) => (
            <div key={rt.resource_id} style={{ marginBottom: "var(--spacing-lg)" }}>
              <h4 style={{ fontSize: "0.95rem", fontWeight: 600, marginBottom: "var(--spacing-sm)" }}>
                {rt.resource_name}
              </h4>
              <VersionTable
                title="Version"
                currentId={rt.current?.id ?? null}
                history={rt.history}
              />
            </div>
          ))
        )}

        <div style={{ borderTop: "1px solid var(--color-border)", paddingTop: "var(--spacing-md)" }}>
          <div style={{ fontSize: "0.9rem", fontWeight: 600, marginBottom: "var(--spacing-sm)" }}>
            Publish New Version
          </div>
          {resources.length === 0 ? (
            <div className="empty-state">No data resources available.</div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-sm)" }}>
              <select
                value={selectedResource}
                onChange={(e) => setSelectedResource(e.target.value)}
                style={{ padding: "6px 10px", borderRadius: "var(--radius-sm)", border: "1px solid var(--color-border)", fontSize: "0.9rem" }}
              >
                <option value="">— Select data resource —</option>
                {resources.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.name} ({r.identifier})
                  </option>
                ))}
              </select>

              {selectedResource && (
                <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-sm)" }}>
                  <div style={{ display: "flex", gap: "var(--spacing-sm)" }}>
                    <input
                      placeholder="Version (e.g., 1.0.0)"
                      value={resVersion}
                      onChange={(e) => setResVersion(e.target.value)}
                      style={{ flex: 1, padding: "6px 10px", borderRadius: "var(--radius-sm)", border: "1px solid var(--color-border)", fontSize: "0.9rem" }}
                    />
                    <input
                      placeholder="Title"
                      value={resTitle}
                      onChange={(e) => setResTitle(e.target.value)}
                      style={{ flex: 2, padding: "6px 10px", borderRadius: "var(--radius-sm)", border: "1px solid var(--color-border)", fontSize: "0.9rem" }}
                    />
                  </div>
                  <textarea
                    placeholder="Terms content (Markdown)"
                    value={resContent}
                    onChange={(e) => setResContent(e.target.value)}
                    rows={6}
                    style={{ padding: "6px 10px", borderRadius: "var(--radius-sm)", border: "1px solid var(--color-border)", fontSize: "0.9rem", fontFamily: "var(--font-mono)" }}
                  />
                  <div>
                    <button
                      className="btn btn-primary"
                      onClick={handlePublishResource}
                      disabled={publishingRes || !resVersion || !resTitle || !resContent}
                    >
                      {publishingRes ? "Publishing..." : "Publish Resource Terms"}
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
