"use client";

import { useCallback, useEffect, useState } from "react";
import {
  getAdminTermsStatus,
  getAdminResources,
  publishPlatformTerms,
  publishResourceTerms,
  getPlatformTermsCurrent,
} from "@/lib/api";
import type { DataResource } from "@/lib/api";

export default function AdminTermsPage() {
  const [platformStatus, setPlatformStatus] = useState<{
    has_terms: boolean;
    version: string | null;
    title: string | null;
    published_at: string | null;
  } | null>(null);
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
      const [status, allResources] = await Promise.all([
        getAdminTermsStatus(),
        getAdminResources(),
      ]);
      setPlatformStatus(status.platform);
      setResources(allResources);
      if (status.platform.has_terms) {
        const current = await getPlatformTermsCurrent();
        setPlatVersion("");
        setPlatTitle("");
        setPlatContent("");
      }
    } catch {
      setError("Failed to load terms status.");
    } finally {
      setLoading(false);
    }
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
        Terms of Service Management
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

        {platformStatus?.has_terms ? (
          <div style={{ marginBottom: "var(--spacing-md)", fontSize: "0.9rem" }}>
            <div style={{ marginBottom: "var(--spacing-xs)" }}>
              <strong>Current version:</strong> {platformStatus.version}
            </div>
            <div style={{ marginBottom: "var(--spacing-xs)" }}>
              <strong>Title:</strong> {platformStatus.title}
            </div>
            <div>
              <strong>Published:</strong>{" "}
              {platformStatus.published_at
                ? new Date(platformStatus.published_at).toLocaleDateString()
                : "—"}
            </div>
          </div>
        ) : (
          <div className="empty-state" style={{ marginBottom: "var(--spacing-md)" }}>
            No platform terms published yet.
          </div>
        )}

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
      <div className="card">
        <h3 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "var(--spacing-md)" }}>
          Data Resource Terms
        </h3>

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
  );
}
