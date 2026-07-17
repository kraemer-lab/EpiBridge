"use client";

import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@/lib/AuthContext";
import {
  AnalysisBundle,
  AuditEvent,
  BundleFile,
  getAdminBundles,
  getAdminBundle,
  getAdminBundleFiles,
  getAdminBundleFileContent,
  getAuditEvents,
  getGovernanceStatus,
  approveBundle,
  rejectBundle,
  supersedeBundle,
  triggerAdminBundleAiReview,
  downloadAdminBundleFile,
  downloadAdminBundleZip,
} from "@/lib/api";
import { formatBundleStatus, bundleStatusStyle } from "@/lib/status";
import LogViewer from "@/components/LogViewer";
import { CodeBlock } from "@/components/CodeBlock";
import { RejectDialog } from "@/components/RejectDialog";
import { ConfirmationDialog } from "@/components/ConfirmationDialog";
import AIReviewCard from "@/components/AIReviewCard";
import type { AIReview } from "@/components/AIReviewCard";

const STATUS_FILTERS = [
  { value: "submitted", label: "Awaiting Review" },
  { value: "approved_for_execution", label: "Approved" },
  { value: "rejected", label: "Rejected" },
  { value: "superseded", label: "Superseded" },
  { value: "all", label: "All Bundles" },
];

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

function formatSize(bytes: number): string {
  if (bytes === 0) return "0 bytes";
  if (bytes < 1024) return `${bytes} bytes`;
  return `${(bytes / 1024).toFixed(1)} KB`;
}

function buildStatusBadge(status: string): { background: string; color: string; label: string } {
  switch (status) {
    case "environment_ready":
      return { background: "#d4edda", color: "#155724", label: "Ready" };
    case "environment_building":
      return { background: "#cce5ff", color: "#004085", label: "Building" };
    case "environment_build_failed":
      return { background: "#f8d7da", color: "#721c24", label: "Failed" };
    default:
      return { background: "#f0f0f0", color: "#666", label: "Not built" };
  }
}

const sectionHeader: React.CSSProperties = {
  fontSize: "0.85rem",
  fontWeight: 600,
  marginBottom: "var(--spacing-xs)",
  marginTop: "var(--spacing-md)",
  color: "var(--color-text)",
};

const detailRow: React.CSSProperties = {
  display: "flex",
  gap: "var(--spacing-md)",
  fontSize: "0.85rem",
  padding: "3px 0",
};

const detailLabel: React.CSSProperties = {
  color: "var(--color-text-secondary)",
  minWidth: "140px",
  flexShrink: 0,
};

const detailValue: React.CSSProperties = {
  color: "var(--color-text)",
};

export default function AdminAnalysesPage() {
  const { user } = useAuth();
  const [bundles, setBundles] = useState<AnalysisBundle[]>([]);
  const [govStatus, setGovStatus] = useState<{ prevent_self_moderation: boolean } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [rejectTarget, setRejectTarget] = useState<string | null>(null);
  const [approveTarget, setApproveTarget] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState("submitted");
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [bundleAudit, setBundleAudit] = useState<Record<string, AuditEvent[]>>({});
  const [bundleFiles, setBundleFiles] = useState<Record<string, BundleFile[]>>({});
  const [bundleFileTotalSize, setBundleFileTotalSize] = useState<Record<string, number>>({});
  const [filesLoading, setFilesLoading] = useState<Record<string, boolean>>({});
  const [viewedFile, setViewedFile] = useState<Record<string, string | null>>({});
  const [fileContent, setFileContent] = useState<Record<string, string>>({});
  const [fileContentLoading, setFileContentLoading] = useState<Record<string, boolean>>({});
  const [aiReviewTriggerId, setAiReviewTriggerId] = useState<string | null>(null);
  const [aiStatus, setAiStatus] = useState<Record<string, AIReview | null>>({});

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [data, gov] = await Promise.all([
        getAdminBundles(),
        getGovernanceStatus().catch(() => null),
      ]);
      setBundles(data);
      setGovStatus(gov);
    } catch {
      setError("Failed to load analyses");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const filteredBundles =
    statusFilter === "all"
      ? bundles
      : bundles.filter((b) => b.status === statusFilter);

  const handleAction = async (
    _actionLabel: string,
    bundleId: string,
    apiFn: (id: string) => Promise<AnalysisBundle>,
  ) => {
    setActionError(null);
    setActionLoading(true);
    try {
      await apiFn(bundleId);
      await load();
    } catch (e) {
      setActionError(e instanceof Error ? e.message : "Action failed");
    } finally {
      setActionLoading(false);
    }
  };

  const handleExpand = async (bundleId: string) => {
    if (expandedId === bundleId) {
      setExpandedId(null);
      return;
    }
    setExpandedId(bundleId);
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
    if (!bundleFiles[bundleId]) {
      setFilesLoading((prev) => ({ ...prev, [bundleId]: true }));
      try {
        const result = await getAdminBundleFiles(bundleId);
        setBundleFiles((prev) => ({ ...prev, [bundleId]: result.files }));
        setBundleFileTotalSize((prev) => ({ ...prev, [bundleId]: result.total_size }));
      } catch {
        setBundleFiles((prev) => ({ ...prev, [bundleId]: [] }));
      } finally {
        setFilesLoading((prev) => ({ ...prev, [bundleId]: false }));
      }
    }
    try {
      const freshBundle = await getAdminBundle(bundleId);
      setAiStatus((prev) => ({
        ...prev,
        [bundleId]: freshBundle.ai_review ?? null,
      }));
    } catch {
      const existing = bundles.find((b) => b.id === bundleId);
      if (existing) {
        setAiStatus((prev) => ({
          ...prev,
          [bundleId]: existing.ai_review ?? null,
        }));
      }
    }
  };

  const handleViewFile = async (bundleId: string, path: string) => {
    if (viewedFile[bundleId] === path) {
      setViewedFile((prev) => ({ ...prev, [bundleId]: null }));
      return;
    }
    setViewedFile((prev) => ({ ...prev, [bundleId]: path }));
    if (!fileContent[`${bundleId}:${path}`]) {
      setFileContentLoading((prev) => ({ ...prev, [`${bundleId}:${path}`]: true }));
      try {
        const content = await getAdminBundleFileContent(bundleId, path);
        setFileContent((prev) => ({ ...prev, [`${bundleId}:${path}`]: content }));
      } catch {
        setFileContent((prev) => ({ ...prev, [`${bundleId}:${path}`]: "Failed to load file content." }));
      } finally {
        setFileContentLoading((prev) => ({ ...prev, [`${bundleId}:${path}`]: false }));
      }
    }
  };

  const handleTriggerAiReview = async (bundleId: string) => {
    setAiReviewTriggerId(bundleId);
    setAiStatus((prev) => ({
      ...prev,
      [bundleId]: {
        id: "",
        status: "pending",
        summary: null,
        assessment: null,
        assessment_confidence: null,
        reviewer_notes: null,
      },
    }));
    try {
      const updated = await triggerAdminBundleAiReview(bundleId);
      setAiStatus((prev) => ({
        ...prev,
        [bundleId]: updated.ai_review ?? null,
      }));
    } catch {
      // Polling below will recover from any transient errors
    }
    const poll = setInterval(async () => {
      try {
        const refreshed = await getAdminBundle(bundleId);
        const review = refreshed.ai_review;
        if (review && review.status !== "pending") {
          setAiStatus((prev) => ({ ...prev, [bundleId]: review }));
          clearInterval(poll);
          setAiReviewTriggerId(null);
        }
      } catch {
        clearInterval(poll);
        setAiReviewTriggerId(null);
      }
    }, 5000);
  };

  const pendingReviewId = expandedId && aiStatus[expandedId]?.status === "pending" ? expandedId : null;

  useEffect(() => {
    if (!pendingReviewId) return;

    const poll = setInterval(async () => {
      try {
        const refreshed = await getAdminBundle(pendingReviewId);
        const r = refreshed.ai_review;
        if (r && r.status !== "pending") {
          setAiStatus((prev) => ({ ...prev, [pendingReviewId]: r }));
          clearInterval(poll);
        }
      } catch {
        clearInterval(poll);
      }
    }, 5000);

    return () => clearInterval(poll);
  }, [pendingReviewId]);

  const handleDownloadFile = async (bundleId: string, path: string) => {
    try {
      await downloadAdminBundleFile(bundleId, path);
    } catch {
      // silent
    }
  };

  const handleDownloadAll = async (bundleId: string) => {
    try {
      await downloadAdminBundleZip(bundleId);
    } catch {
      // silent
    }
  };

  const canReview = user?.capabilities.includes("bundle.review");

  return (
    <>
      <h2 style={{ fontSize: "1.1rem", fontWeight: 600, marginBottom: "var(--spacing-sm)" }}>
        Analysis Operations
      </h2>

      <div style={{ display: "flex", gap: "var(--spacing-xs)", marginBottom: "var(--spacing-md)", flexWrap: "wrap" }}>
        {STATUS_FILTERS.map((opt) => (
          <button
            key={opt.value}
            onClick={() => setStatusFilter(opt.value)}
            style={{
              padding: "4px 12px",
              fontSize: "0.85rem",
              background:
                statusFilter === opt.value
                  ? "var(--color-primary, #1976d2)"
                  : "transparent",
              color:
                statusFilter === opt.value
                  ? "#fff"
                  : "var(--color-text-secondary)",
              border: "1px solid",
              borderColor:
                statusFilter === opt.value
                  ? "var(--color-primary, #1976d2)"
                  : "var(--color-border)",
              borderRadius: "4px",
              cursor: "pointer",
              fontWeight: statusFilter === opt.value ? 600 : 400,
            }}
          >
            {opt.label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="card empty-state">Loading...</div>
      ) : error ? (
        <div className="card empty-state">{error}</div>
      ) : filteredBundles.length === 0 ? (
        <div className="card empty-state">
          {statusFilter === "submitted"
            ? "No analyses awaiting review."
            : `No bundles with status "${formatBundleStatus(statusFilter)}".`}
        </div>
      ) : (
        <>
        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          <table className="table">
            <thead>
              <tr>
                <th>Project</th>
                <th>Name</th>
                <th>Status</th>
                <th>Runtime</th>
                <th>Version</th>
                <th>Inspect</th>
              </tr>
            </thead>
            <tbody>
              {filteredBundles.map((b) => {
                const badge = bundleStatusStyle(b.status);
                return (
                  <tr key={b.id}>
                    <td style={{ color: "var(--color-text-secondary)" }}>
                      {b.project_name || b.project_id.slice(0, 8)}
                    </td>
                    <td style={{ fontWeight: 500 }}>{b.name}</td>
                    <td>
                      <span
                        style={{
                          display: "inline-block",
                          padding: "2px 8px",
                          borderRadius: "4px",
                          fontSize: "0.8rem",
                          fontWeight: 600,
                          ...badge,
                        }}
                      >
                        {formatBundleStatus(b.status)}
                      </span>
                    </td>
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
                        }}
                      >
                        Inspect
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {expandedId && (() => {
          const b = filteredBundles.find((x) => x.id === expandedId);
          if (!b) return null;
          const buildBadge = buildStatusBadge(b.build_status);
          const close = () => setExpandedId(null);
          return (
            <div
              style={{
                position: "fixed",
                inset: 0,
                background: "rgba(0,0,0,0.4)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                zIndex: 1000,
              }}
              onClick={close}
            >
              <div
                className="card"
                style={{
                  maxWidth: "720px",
                  width: "90%",
                  maxHeight: "80vh",
                  overflowY: "auto",
                  padding: 0,
                  fontSize: "0.85rem",
                }}
                onClick={(e) => e.stopPropagation()}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    padding: "var(--spacing-md) var(--spacing-lg)",
                    borderBottom: "1px solid var(--color-border)",
                  }}
                >
                  <h3 style={{ margin: 0, fontSize: "1rem", fontWeight: 600 }}>
                    Analysis Detail
                  </h3>
                  <button
                    onClick={close}
                    style={{
                      background: "none",
                      border: "none",
                      cursor: "pointer",
                      fontSize: "1.2rem",
                      color: "var(--color-text-secondary)",
                      padding: "4px",
                      lineHeight: 1,
                    }}
                    aria-label="Close"
                  >
                    ×
                  </button>
                </div>

                <div style={{ padding: "var(--spacing-lg)" }}>
                  {canReview && b.status === "submitted" && govStatus?.prevent_self_moderation === true && b.submitted_by_id === user?.id && !user?.capabilities.includes("governance.self_regulate") && (
                    <div style={{
                      padding: "12px 16px",
                      marginBottom: "var(--spacing-lg)",
                      background: "#fff3cd",
                      border: "1px solid #ffc107",
                      borderRadius: "4px",
                      color: "#856404",
                      fontSize: "0.85rem",
                      lineHeight: 1.6,
                    }}>
                      <strong>Independent moderation required.</strong><br />
                      You submitted this analysis bundle for institutional review.
                      Another authorised moderator must approve or reject it.
                    </div>
                  )}
                  {/* Overview */}
                  <section aria-label="Analysis Overview">
                    <h3 style={sectionHeader}>Overview</h3>
                    {b.rejection_reason && (
                      <div style={{ ...detailRow, flexDirection: "column", gap: "2px", marginBottom: "var(--spacing-sm)", padding: "8px 12px", background: "#f8d7da", borderRadius: "4px" }}>
                        <span style={detailLabel}>Rejection reason</span>
                        <span style={detailValue}>{b.rejection_reason}</span>
                      </div>
                    )}
                    {b.description && (
                      <div style={detailRow}>
                        <span style={detailLabel}>Description</span>
                        <span style={detailValue}>{b.description}</span>
                      </div>
                    )}
                    <div style={detailRow}>
                      <span style={detailLabel}>Entrypoint</span>
                      <span style={{ ...detailValue, fontFamily: "var(--font-mono)", fontSize: "0.8rem" }}>{b.entrypoint || "—"}</span>
                    </div>
                    <div style={detailRow}>
                      <span style={detailLabel}>Interpreter</span>
                      <span style={detailValue}>{b.interpreter}</span>
                    </div>
                    {b.arguments && (
                      <div style={detailRow}>
                        <span style={detailLabel}>Arguments</span>
                        <span style={{ ...detailValue, fontFamily: "var(--font-mono)", fontSize: "0.8rem" }}>{b.arguments}</span>
                      </div>
                    )}
                    <div style={detailRow}>
                      <span style={detailLabel}>Resources</span>
                      <span style={detailValue}>
                        {b.resource_identifiers.length > 0
                          ? b.resource_identifiers.join(", ")
                          : "—"}
                      </span>
                    </div>
                  <div style={detailRow}>
                      <span style={detailLabel}>Environment</span>
                      <span style={detailValue}>{b.display_runtime}</span>
                    </div>
                  <div style={detailRow}>
                    <span style={detailLabel}>Build strategy</span>
                    <span style={{
                      display: "inline-block",
                      padding: "2px 8px",
                      borderRadius: "4px",
                      fontSize: "0.8rem",
                      fontWeight: 600,
                      ...(b.build_strategy === "custom"
                        ? { background: "#fff3cd", color: "#856404" }
                        : { background: "#d4edda", color: "#155724" }),
                    }}>
                      {b.build_strategy === "custom" ? "Custom" : "Institutional"}
                    </span>
                  </div>
                  </section>

                  {/* Build */}
                  <section aria-label="Build Information">
                    <h3 style={sectionHeader}>Build</h3>
                  <div style={detailRow}>
                    <span style={detailLabel}>Status</span>
                    <span
                      style={{
                        display: "inline-block",
                        padding: "2px 8px",
                        borderRadius: "4px",
                        fontSize: "0.8rem",
                        fontWeight: 600,
                        background: buildBadge.background,
                        color: buildBadge.color,
                      }}
                    >
                      {buildBadge.label}
                    </span>
                  </div>
                  {b.build_error && (
                    <div style={detailRow}>
                      <span style={detailLabel}>Error</span>
                      <span style={{
                        ...detailValue,
                        color: "#c62828",
                        fontFamily: "var(--font-mono)",
                        fontSize: "0.8rem",
                        whiteSpace: "pre-wrap",
                      }}
                      >
                        {b.build_error}
                      </span>
                    </div>
                  )}
                  {b.build_log && (
                    <div style={{ marginTop: "var(--spacing-xs)" }}>
                      <LogViewer log={b.build_log} title="Build Log" maxHeight="200px" />
                    </div>
                  )}
                  </section>

                  {/* AI Review */}
                  <section aria-label="AI Review">
                    <AIReviewCard
                      review={aiStatus[b.id] ?? null}
                      title="AI Analysis Summary"
                      onRefresh={
                        aiStatus[b.id]?.status !== "pending"
                          ? () => handleTriggerAiReview(b.id)
                          : undefined
                      }
                      refreshing={aiReviewTriggerId === b.id}
                    />
                  </section>

                  {/* Bundle Files */}
                  <section aria-label="Bundle Files">
                    <h3 style={sectionHeader}>Bundle Files</h3>
                  {filesLoading[b.id] ? (
                    <div style={{ color: "var(--color-text-secondary)", fontSize: "0.85rem" }}>
                      Loading files...
                    </div>
                  ) : bundleFiles[b.id] && bundleFiles[b.id].length > 0 ? (
                    <>
                      <div style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        marginBottom: "var(--spacing-sm)",
                      }}
                      >
                        <span style={{ fontSize: "0.8rem", color: "var(--color-text-secondary)" }}>
                          {bundleFiles[b.id].length} file{bundleFiles[b.id].length !== 1 ? "s" : ""}
                          {bundleFileTotalSize[b.id] > 0 ? ` — ${formatSize(bundleFileTotalSize[b.id])}` : ""}
                        </span>
                        <button className="btn btn-sm" onClick={() => handleDownloadAll(b.id)}>
                          Download All
                        </button>
                      </div>
                      <table className="table" style={{ fontSize: "0.85rem" }}>
                        <thead>
                          <tr>
                            <th>File</th>
                            <th>Size</th>
                            <th></th>
                            <th></th>
                          </tr>
                        </thead>
                        <tbody>
                          {bundleFiles[b.id].map((f) => (
                            <tr key={f.path}>
                              <td style={{
                                fontWeight: 500,
                                fontFamily: "var(--font-mono)",
                                fontSize: "0.8rem",
                              }}
                              >
                                {f.path}
                              </td>
                              <td style={{ color: "var(--color-text-secondary)" }}>
                                {formatSize(f.size)}
                              </td>
                              <td>
                                <button
                                  className="btn"
                                  style={{
                                    fontSize: "0.75rem",
                                    padding: "1px 6px",
                                    color: "var(--color-primary, #1976d2)",
                                  }}
                                  onClick={() => handleViewFile(b.id, f.path)}
                                >
                                  {viewedFile[b.id] === f.path ? "Close" : "View"}
                                </button>
                              </td>
                              <td>
                                <button
                                  className="btn"
                                  style={{
                                    fontSize: "0.75rem",
                                    padding: "1px 6px",
                                  }}
                                  onClick={() => handleDownloadFile(b.id, f.path)}
                                >
                                  Download
                                </button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                      {viewedFile[b.id] && (() => {
                        const viewPath = viewedFile[b.id]!;
                        const cacheKey = `${b.id}:${viewPath}`;
                        const isLoading = fileContentLoading[cacheKey];
                        const content = fileContent[cacheKey];
                        return (
                          <div style={{ marginTop: "var(--spacing-sm)" }}>
                            {isLoading ? (
                              <div style={{ color: "var(--color-text-secondary)", fontSize: "0.85rem" }}>
                                Loading file content...
                              </div>
                            ) : content ? (
                              <CodeBlock code={content} language={viewPath.split(".").pop()} />
                            ) : null}
                          </div>
                        );
                      })()}
                    </>
                  ) : (
                    <div style={{ color: "var(--color-text-secondary)", fontSize: "0.85rem" }}>
                      No files in this bundle.
                    </div>
                  )}

                  </section>

                  {/* Governance History */}
                  <section aria-label={`Governance History - ${b.name}`}>
                    <h3 style={sectionHeader}>Governance History</h3>
                  {!bundleAudit[b.id] ? (
                    <div style={{ color: "var(--color-text-secondary)", fontSize: "0.85rem" }}>
                      Loading...
                    </div>
                  ) : bundleAudit[b.id].length === 0 ? (
                    <div style={{ color: "var(--color-text-secondary)", fontSize: "0.85rem" }}>
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
                          <span style={{ fontWeight: 500 }}>
                            {eventLabel(e.event_type)}
                          </span>
                          <span style={{ color: "var(--color-text-secondary)" }}>
                            {e.actor_display_name} —{" "}
                            {formatTime(e.occurred_at)}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                  </section>

                  {/* Governance Actions */}
                  {canReview && (() => {
                    const isSubmitted = b.status === "submitted";
                    const isApprovedForExec = b.status === "approved_for_execution";
                    if (!isSubmitted && !isApprovedForExec) return null;

                    const blockedBySelfModeration =
                      govStatus?.prevent_self_moderation === true
                      && b.submitted_by_id === user?.id
                      && !user?.capabilities.includes("governance.self_regulate");

                    return (
                      <section
                        aria-label="Governance Actions"
                        style={{
                          paddingTop: "var(--spacing-md)",
                        }}
                      >
                        {isApprovedForExec && blockedBySelfModeration && (
                          <span style={{ color: "var(--color-text-secondary)", fontSize: "0.85rem", fontStyle: "italic" }}>
                            Independent moderation required.
                             Another authorised moderator must supersede this analysis.
                          </span>
                        )}
                        {isSubmitted && !blockedBySelfModeration && (
                          <div style={{ display: "flex", gap: "var(--spacing-sm)" }}>
                            <button
                              className="btn btn-sm"
                              style={{
                                background: "var(--color-success, #2e7d32)",
                                color: "#fff",
                                border: "none",
                              }}
                              onClick={() => setApproveTarget(b.id)}
                              disabled={actionLoading}
                            >
                              {actionLoading ? "Processing…" : "Approve"}
                            </button>
                            <button
                              className="btn btn-sm"
                              style={{
                                background: "var(--color-danger, #c62828)",
                                color: "#fff",
                                border: "none",
                              }}
                              onClick={() => setRejectTarget(b.id)}
                              disabled={actionLoading}
                            >
                              {actionLoading ? "Processing…" : "Reject"}
                            </button>
                          </div>
                        )}
                        {isApprovedForExec && !blockedBySelfModeration && (
                          <button
                            className="btn btn-sm"
                            style={{
                              background: "#fff3cd",
                              color: "#856404",
                              border: "1px solid #856404",
                            }}
                            onClick={() =>
                              handleAction("Supersede", b.id, supersedeBundle)
                            }
                            disabled={actionLoading}
                          >
                            {actionLoading ? "Processing…" : "Supersede"}
                          </button>
                        )}
                      </section>
                    );
                  })()}
                </div>
              </div>
            </div>
          );
        })()}

      {rejectTarget && (
        <RejectDialog
          title="Analysis Bundle"
          onConfirm={async (reason) => {
            setActionError(null);
            setActionLoading(true);
            try {
              await rejectBundle(rejectTarget, reason);
              setRejectTarget(null);
              await load();
            } catch (e) {
              setActionError(e instanceof Error ? e.message : "Rejection failed");
            } finally {
              setActionLoading(false);
            }
          }}
          onCancel={() => setRejectTarget(null)}
        />
      )}

      {approveTarget && (
        <ConfirmationDialog
          title="Approve Analysis?"
          message={
            <span>
              This Analysis Bundle will be approved for execution.
              <br /><br />
              Confirm that you are satisfied the submitted analysis
              is appropriate to proceed to execution.
              <br /><br />
              <strong>You are making an institutional governance decision.</strong>
            </span>
          }
          confirmLabel="Approve Analysis"
          onConfirm={() => {
            const id = approveTarget;
            setApproveTarget(null);
            handleAction("Approve", id, approveBundle);
          }}
          onCancel={() => setApproveTarget(null)}
        />
      )}

      {actionError && (
        <div
          style={{
            padding: "8px 12px",
            marginBottom: "var(--spacing-md)",
            background: "#f8d7da",
            color: "#721c24",
            borderRadius: "4px",
            fontSize: "0.85rem",
          }}
        >
          {actionError}
        </div>
      )}
        </>
      )}
    </>
  );
}
