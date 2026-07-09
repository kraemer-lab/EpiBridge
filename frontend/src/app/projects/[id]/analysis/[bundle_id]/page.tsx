"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/AuthContext";
import {
  AnalysisBundle,
  getProjectBundle,
  submitBundle,
  approveBundle,
  rejectBundle,
  supersedeBundle,
  createExecutionRequest,
  triggerAiReview,
} from "@/lib/api";
import { formatBundleStatus, bundleStatusStyle } from "@/lib/status";
import LogViewer from "@/components/LogViewer";

const TERMINAL_STATUSES = ["completed", "failed", "unavailable"];

export default function AnalysisDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { user } = useAuth();
  const projectId = params.id as string;
  const bundleId = params.bundle_id as string;

  const [bundle, setBundle] = useState<AnalysisBundle | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [reviewing, setReviewing] = useState(false);

  const fetchBundle = useCallback(async () => {
    const b = await getProjectBundle(projectId, bundleId);
    setBundle(b);
    return b;
  }, [projectId, bundleId]);

  useEffect(() => {
    fetchBundle()
      .catch(() => setError("Failed to load analysis bundle"))
      .finally(() => setLoading(false));
  }, [fetchBundle]);

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    const review = bundle?.ai_review;
    if (!review || review.status !== "pending") {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
      return;
    }

    pollRef.current = setInterval(async () => {
      try {
        const updated = await fetchBundle();
        if (
          updated.ai_review &&
          TERMINAL_STATUSES.includes(updated.ai_review.status) &&
          pollRef.current
        ) {
          clearInterval(pollRef.current);
          pollRef.current = null;
        }
      } catch {
        if (pollRef.current) {
          clearInterval(pollRef.current);
          pollRef.current = null;
        }
      }
    }, 5000);

    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [bundle?.ai_review?.status, fetchBundle]);

  const buildPollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const BUILD_TERMINAL = ["environment_ready", "environment_build_failed"];

  useEffect(() => {
    if (!bundle || BUILD_TERMINAL.includes(bundle.build_status)) {
      if (buildPollRef.current) {
        clearInterval(buildPollRef.current);
        buildPollRef.current = null;
      }
      return;
    }

    buildPollRef.current = setInterval(async () => {
      try {
        const updated = await fetchBundle();
        if (BUILD_TERMINAL.includes(updated.build_status) && buildPollRef.current) {
          clearInterval(buildPollRef.current);
          buildPollRef.current = null;
        }
      } catch {
        if (buildPollRef.current) {
          clearInterval(buildPollRef.current);
          buildPollRef.current = null;
        }
      }
    }, 5000);

    return () => {
      if (buildPollRef.current) {
        clearInterval(buildPollRef.current);
        buildPollRef.current = null;
      }
    };
  }, [bundle?.build_status, fetchBundle]);

  const performAction = async (
    label: string,
    action: () => Promise<unknown>,
  ) => {
    setActionLoading(label);
    setError(null);
    try {
      await action();
      await fetchBundle();
    } catch (e) {
      setError(e instanceof Error ? e.message : `Failed to ${label.toLowerCase()}`);
    }
    setActionLoading(null);
  };

  const handleSubmit = () =>
    performAction("Submit", () => submitBundle(projectId, bundleId));

  const handleApprove = () =>
    performAction("Approve", () => approveBundle(bundleId));

  const handleReject = () =>
    performAction("Reject", () => rejectBundle(bundleId));

  const handleSupersede = () =>
    performAction("Supersede", () => supersedeBundle(bundleId));

  const handleRun = async () => {
    setActionLoading("Run");
    try {
      await createExecutionRequest(projectId, {
        analysis_bundle_id: bundleId,
      });
      router.push(`/projects/${projectId}/jobs`);
    } catch {
      setError("Failed to create execution request");
      setActionLoading(null);
    }
  };

  const handleTriggerReview = async () => {
    setReviewing(true);
    try {
      const updated = await triggerAiReview(projectId, bundleId);
      setBundle(updated);
    } catch {
      setError("Failed to trigger AI review");
    }
    setReviewing(false);
  };

  const reviewActionLabel = () => {
    if (!bundle?.ai_review) return "Generate AI Summary";
    return "Refresh AI Summary";
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
              ...bundleStatusStyle(bundle.status),
            }}
          >
            {formatBundleStatus(bundle.status)}
          </span>
          <div style={{ marginTop: "var(--spacing-sm)", fontSize: "0.85rem", fontWeight: 600 }}>
            {bundle.build_status === "environment_ready" && (
              <span style={{ color: "#2e7d32" }}>Ready to run</span>
            )}
            {(bundle.build_status === "environment_building" || (bundle.build_status === "environment_not_built" && bundle.status === "approved_for_execution")) && (
              <span style={{ color: "#ed6c02" }}>Preparing execution environment…</span>
            )}
            {bundle.build_status === "environment_build_failed" && (
              <span>
                <span style={{ color: "#d32f2f" }}>Execution environment could not be prepared</span>
                {bundle.build_log && (
                  <span style={{ display: "block", marginTop: "var(--spacing-sm)" }}>
                    <LogViewer log={bundle.build_log} title="Build Log (failed)" maxHeight="200px" />
                  </span>
                )}
              </span>
            )}
            {bundle.build_status === "environment_ready" && bundle.build_log && (
              <span style={{ display: "block", marginTop: "var(--spacing-sm)" }}>
                <LogViewer log={bundle.build_log} title="Build Log" maxHeight="200px" />
              </span>
            )}
          </div>
        </div>
        <div>
          <div style={{ display: "flex", gap: "var(--spacing-sm)", marginBottom: "var(--spacing-xs)" }}>
            {bundle.status === "draft" && user?.capabilities.includes("bundle.submit") && (
              <button
                className="btn btn-primary"
                onClick={handleSubmit}
                disabled={actionLoading !== null}
              >
                {actionLoading === "Submit" ? "Submitting…" : "Submit"}
              </button>
            )}
            {bundle.status === "submitted" && user?.capabilities.includes("bundle.review") && (
              <>
                <button
                  className="btn btn-primary"
                  onClick={handleApprove}
                  disabled={actionLoading !== null}
                >
                  {actionLoading === "Approve" ? "Approving…" : "Approve"}
                </button>
                <button
                  className="btn"
                  onClick={handleReject}
                  disabled={actionLoading !== null}
                >
                  {actionLoading === "Reject" ? "Rejecting…" : "Reject"}
                </button>
              </>
            )}
            {bundle.status === "approved_for_execution" && user?.capabilities.includes("execution.run") && (
              <button
                className="btn btn-primary"
                onClick={handleRun}
                disabled={actionLoading !== null}
              >
                {actionLoading === "Run" ? "Submitting…" : "Run Analysis"}
              </button>
            )}
            {bundle.status === "approved_for_execution" && user?.capabilities.includes("bundle.review") && (
              <button
                className="btn"
                onClick={handleSupersede}
                disabled={actionLoading !== null}
              >
                {actionLoading === "Supersede" ? "Superseding…" : "Supersede"}
              </button>
            )}
            <Link
              href={`/projects/${projectId}/analysis/${bundleId}/edit`}
              className="btn"
              style={{ textDecoration: "none" }}
            >
              Edit
            </Link>
          </div>
          {error && (
            <div style={{ color: "#d32f2f", fontSize: "0.85rem", textAlign: "right" }}>
              {error}
            </div>
          )}
        </div>
      </div>

      <div className="card" style={{ maxWidth: "640px" }}>
        <div style={{ marginBottom: "var(--spacing-md)" }}>
          <div style={{ fontSize: "0.8rem", color: "var(--color-text-secondary)", marginBottom: "var(--spacing-xs)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>
            Runtime
          </div>
          <div>{bundle.display_runtime}</div>
        </div>

        <div style={{ marginBottom: "var(--spacing-md)" }}>
          <div style={{ fontSize: "0.8rem", color: "var(--color-text-secondary)", marginBottom: "var(--spacing-xs)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>
            Build Strategy
          </div>
          <div>
            {bundle.build_strategy === "custom" ? (
              <span style={{ display: "inline-block", padding: "2px 8px", borderRadius: "4px", fontSize: "0.8rem", fontWeight: 600, background: "#e3f2fd", color: "#1565c0" }}>
                Custom Build
              </span>
            ) : (
              <span>Institutional Build</span>
            )}
          </div>
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
            Interpreter
          </div>
          <div>{bundle.interpreter === "python" ? "Python" : bundle.interpreter === "shell" ? "Shell" : bundle.interpreter === "r" ? "R" : bundle.interpreter}</div>
        </div>

        <div style={{ marginBottom: "var(--spacing-md)" }}>
          <div style={{ fontSize: "0.8rem", color: "var(--color-text-secondary)", marginBottom: "var(--spacing-xs)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>
            Entrypoint
          </div>
          <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.9rem" }}>{bundle.entrypoint}</div>
        </div>

        {bundle.arguments && (
          <div style={{ marginBottom: "var(--spacing-md)" }}>
            <div style={{ fontSize: "0.8rem", color: "var(--color-text-secondary)", marginBottom: "var(--spacing-xs)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>
              Arguments
            </div>
            <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.9rem" }}>{bundle.arguments}</div>
          </div>
        )}

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

      <div className="card" style={{ maxWidth: "640px", marginTop: "var(--spacing-lg)" }}>
        <h3 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "var(--spacing-md)" }}>
          AI Analysis Summary
        </h3>

        {bundle.ai_review === null && (
          <div style={{ marginBottom: "var(--spacing-md)" }}>
            <div>Not available for this deployment</div>
          </div>
        )}

        {bundle.ai_review?.status === "pending" && (
          <div style={{ marginBottom: "var(--spacing-md)" }}>
            <div>Status: Pending</div>
          </div>
        )}

        {bundle.ai_review?.status === "completed" && (
          <>
            <div style={{ marginBottom: "var(--spacing-md)" }}>
              <div style={{ fontSize: "0.8rem", color: "var(--color-text-secondary)", marginBottom: "var(--spacing-xs)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                Status
              </div>
              <div>Completed</div>
            </div>
            <div style={{ marginBottom: "var(--spacing-md)" }}>
              <div style={{ fontSize: "0.8rem", color: "var(--color-text-secondary)", marginBottom: "var(--spacing-xs)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                Summary
              </div>
              <div style={{ lineHeight: 1.6, whiteSpace: "pre-wrap" }}>{bundle.ai_review.summary}</div>
            </div>
            <div style={{ marginBottom: "var(--spacing-md)" }}>
              <div style={{ fontSize: "0.8rem", color: "var(--color-text-secondary)", marginBottom: "var(--spacing-xs)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                Assessment
              </div>
              <div style={{ lineHeight: 1.6, whiteSpace: "pre-wrap" }}>{bundle.ai_review.assessment}</div>
            </div>
            <div style={{ marginBottom: "var(--spacing-md)" }}>
              <div style={{ fontSize: "0.8rem", color: "var(--color-text-secondary)", marginBottom: "var(--spacing-xs)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                Assessment Confidence
              </div>
              <div>{bundle.ai_review.assessment_confidence}</div>
            </div>
            <div style={{ marginBottom: "var(--spacing-md)" }}>
              <div style={{ fontSize: "0.8rem", color: "var(--color-text-secondary)", marginBottom: "var(--spacing-xs)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                Reviewer Notes
              </div>
              <div style={{ lineHeight: 1.6, whiteSpace: "pre-wrap" }}>{bundle.ai_review.reviewer_notes}</div>
            </div>
          </>
        )}

        {(bundle.ai_review?.status === "unavailable" || bundle.ai_review?.status === "failed") && (
          <div style={{ marginBottom: "var(--spacing-md)" }}>
            <div>Status: Unavailable</div>
          </div>
        )}

        {bundle.ai_review?.status !== "pending" && (
          <button
            className="btn"
            onClick={handleTriggerReview}
            disabled={reviewing}
          >
            {reviewing ? "Processing..." : reviewActionLabel()}
          </button>
        )}
      </div>
    </div>
  );
}
