"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/AuthContext";
import {
  AnalysisBundle,
  BundleFile,
  DataResource,
  ExecutionEnvironment,
  getProjectBundle,
  getProjectResources,
  getBundleFiles,
  getExecutionEnvironments,
  uploadBundleZip,
  importBundleZip,
  uploadBundleFile,
  deleteBundleFile,
  clearBundleFiles,
  submitBundle,
  approveBundle,
  rejectBundle,
  supersedeBundle,
  createExecutionRequest,
  updateProjectBundle,
  triggerAiReview,
  getAIStatus,
  AIStatus,
  checkResourceTerms,
  BundleValidationStatus,
  createValidationRequest,
  getBundleValidations,
  getBundleValidationStatus,
  ValidationRequest,
} from "@/lib/api";
import { formatBundleStatus, bundleStatusStyle } from "@/lib/status";
import LogViewer from "@/components/LogViewer";
import { TermsDialog } from "@/components/TermsDialog";

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
  const [termsResourceId, setTermsResourceId] = useState<string | null>(null);
  const [termsResourceName, setTermsResourceName] = useState<string>("");
  const [bundleFiles, setBundleFiles] = useState<BundleFile[]>([]);
  const [filesLoading, setFilesLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadMode, setUploadMode] = useState<"zip" | "import" | "single" | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [environments, setEnvironments] = useState<ExecutionEnvironment[]>([]);
  const [projectResources, setProjectResources] = useState<DataResource[]>([]);
  const [selectedResources, setSelectedResources] = useState<string[]>([]);
  const [savingDraft, setSavingDraft] = useState(false);
  const [aiStatus, setAiStatus] = useState<AIStatus | null>(null);

  const initializedRef = useRef(false);

  // Workspace form state
  const [editName, setEditName] = useState("");
  const [editEnvId, setEditEnvId] = useState("");
  const [editEntrypoint, setEditEntrypoint] = useState("");
  const [editInterpreter, setEditInterpreter] = useState("python");
  const [editArguments, setEditArguments] = useState("");
  const [editBuildStrategy, setEditBuildStrategy] = useState("institutional");
  const [editVersion, setEditVersion] = useState("");
  const [editDescription, setEditDescription] = useState("");

  // Validation state
  const [validations, setValidations] = useState<ValidationRequest[]>([]);
  const [validationStatus, setValidationStatus] = useState<BundleValidationStatus | null>(null);
  const [validationLoading, setValidationLoading] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);

  // Expanded validation log
  const [expandedValidation, setExpandedValidation] = useState<string | null>(null);

  const fetchValidationState = useCallback(async () => {
    if (!bundleId) return;
    try {
      const [vList, status] = await Promise.all([
        getBundleValidations(projectId, bundleId),
        getBundleValidationStatus(projectId, bundleId),
      ]);
      setValidations(vList);
      setValidationStatus(status);
    } catch {
      // Validation API may not be available in all deployments
    }
  }, [projectId, bundleId]);

  useEffect(() => {
    if (bundle?.status === "draft") {
      fetchValidationState();
    }
  }, [bundle?.status, fetchValidationState]);

  const handleRunValidation = async () => {
    setValidationLoading(true);
    setValidationError(null);
    try {
      // Save pending changes first — same pattern as handleSubmit
      await updateProjectBundle(projectId, bundleId, {
        name: editName,
        execution_environment_id: editEnvId || undefined,
        entrypoint: editEntrypoint || undefined,
        interpreter: editInterpreter as any,
        arguments: editArguments || undefined,
        build_strategy: editBuildStrategy,
        version: editVersion || undefined,
        description: editDescription || undefined,
        resource_identifiers: selectedResources.length > 0 ? selectedResources : undefined,
      });
    } catch {
      setValidationError("Failed to save changes before validation");
      setValidationLoading(false);
      return;
    }

    try {
      await createValidationRequest(projectId, bundleId, {
        analysis_bundle_id: bundleId,
      });
      // Poll for completion
      const poll = setInterval(async () => {
        const vList = await getBundleValidations(projectId, bundleId);
        setValidations(vList);
        const latest = vList[0];
        if (latest && (latest.status === "completed" || latest.status === "failed" || latest.status === "cancelled")) {
          clearInterval(poll);
          setValidationLoading(false);
          await fetchValidationState();
        }
      }, 3000);
    } catch (e) {
      setValidationError(e instanceof Error ? e.message : "Failed to start validation");
      setValidationLoading(false);
    }
  };

  const fetchBundle = useCallback(async () => {
    const b = await getProjectBundle(projectId, bundleId);
    setBundle(b);
    if (!initializedRef.current) {
      initializedRef.current = true;
      setEditName(b.name);
      setEditEnvId(b.execution_environment_id || "");
      setEditEntrypoint(b.entrypoint);
      setEditInterpreter(b.interpreter || "python");
      setEditArguments(b.arguments || "");
      setEditBuildStrategy(b.build_strategy || "institutional");
      setEditVersion(b.version);
      setEditDescription(b.description);
      setSelectedResources(b.resource_identifiers);
    }
    return b;
  }, [projectId, bundleId]);

  useEffect(() => {
    fetchBundle()
      .catch(() => setError("Failed to load analysis bundle"))
      .finally(() => setLoading(false));
  }, [fetchBundle]);

  useEffect(() => {
    getAIStatus().then(setAiStatus).catch(() => setAiStatus(null));
  }, []);

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
        const updated = await getProjectBundle(projectId, bundleId);
        setBundle(updated);
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
    const shouldPoll =
      bundle &&
      bundle.status === "approved_for_execution" &&
      !BUILD_TERMINAL.includes(bundle.build_status);
    if (!shouldPoll) {
      if (buildPollRef.current) {
        clearInterval(buildPollRef.current);
        buildPollRef.current = null;
      }
      return;
    }

    buildPollRef.current = setInterval(async () => {
      try {
        const updated = await getProjectBundle(projectId, bundleId);
        setBundle(updated);
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
  }, [bundle?.status, bundle?.build_status, projectId, bundleId]);

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

  const handleSubmit = async () => {
    // Save pending changes first
    try {
      await updateProjectBundle(projectId, bundleId, {
        name: editName,
        execution_environment_id: editEnvId || undefined,
        entrypoint: editEntrypoint || undefined,
        interpreter: editInterpreter as any,
        arguments: editArguments || undefined,
        build_strategy: editBuildStrategy,
        version: editVersion || undefined,
        description: editDescription || undefined,
        resource_identifiers: selectedResources.length > 0 ? selectedResources : undefined,
      });
    } catch {
      setError("Failed to save changes before submission");
      return;
    }

    // Re-fetch to get fresh resource identifiers for terms check
    const fresh = await getProjectBundle(projectId, bundleId);
    if (fresh.resource_identifiers.length > 0) {
      try {
        const result = await checkResourceTerms(fresh.resource_identifiers);
        const unaccepted = result.results.filter(
          (r) => r.has_terms && !r.accepted,
        );
        if (unaccepted.length > 0) {
          setTermsResourceId(unaccepted[0].resource_id || "");
          setTermsResourceName(unaccepted[0].title || "");
          return;
        }
      } catch {
        // If terms check fails, proceed to backend enforcement
      }
    }
    performAction("Submit", () => submitBundle(projectId, bundleId));
  };

  const handleTermsAccept = () => {
    setTermsResourceId(null);
    setTermsResourceName("");
    handleSubmit();
  };

  const handleTermsCancel = () => {
    setTermsResourceId(null);
    setTermsResourceName("");
  };

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

  const loadFiles = useCallback(async () => {
    setFilesLoading(true);
    setFileError(null);
    try {
      const result = await getBundleFiles(projectId, bundleId);
      setBundleFiles(result.files);
    } catch {
      setBundleFiles([]);
    } finally {
      setFilesLoading(false);
    }
  }, [projectId, bundleId]);

  useEffect(() => {
    if (bundle) {
      loadFiles();
    }
  }, [bundle?.source_path, loadFiles]);

  const handleFileUploadZip = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setFileError(null);
    try {
      await uploadBundleZip(projectId, bundleId, file);
      await loadFiles();
      await fetchBundle();
    } catch (e) {
      setFileError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setUploading(false);
      setUploadMode(null);
      e.target.value = "";
    }
  };

  const handleFileImportZip = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setFileError(null);
    try {
      await importBundleZip(projectId, bundleId, file);
      await loadFiles();
      await fetchBundle();
    } catch (e) {
      setFileError(e instanceof Error ? e.message : "Import failed");
    } finally {
      setUploading(false);
      setUploadMode(null);
      e.target.value = "";
    }
  };

  const handleFileUploadSingle = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setFileError(null);
    try {
      await uploadBundleFile(projectId, bundleId, file);
      await loadFiles();
      await fetchBundle();
    } catch (e) {
      setFileError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setUploading(false);
      setUploadMode(null);
      e.target.value = "";
    }
  };

  const handleDeleteFile = async (path: string) => {
    setFileError(null);
    try {
      await deleteBundleFile(projectId, bundleId, path);
      await loadFiles();
      await fetchBundle();
    } catch (e) {
      setFileError(e instanceof Error ? e.message : "Failed to delete file");
    }
  };

  const handleClearFiles = async () => {
    setFileError(null);
    try {
      await clearBundleFiles(projectId, bundleId);
      await loadFiles();
      await fetchBundle();
    } catch (e) {
      setFileError(e instanceof Error ? e.message : "Failed to clear files");
    }
  };

  useEffect(() => {
    if (bundle?.status === "draft") {
      getExecutionEnvironments().then(setEnvironments).catch(() => {});
      getProjectResources(projectId)
        .then(setProjectResources)
        .catch(() => {});
    }
  }, [bundle?.status, projectId]);

  // Entrypoint candidates from files
  const entrypointCandidates = useMemo(() => {
    const candidates = bundleFiles.filter((f) => {
      const topLevel = !f.path.includes("/");
      const ext = f.path.split(".").pop()?.toLowerCase();
      return topLevel && (ext === "py" || ext === "r" || ext === "sh");
    });
    return candidates.map((f) => f.path);
  }, [bundleFiles]);

  const handleSaveDraft = async () => {
    setSavingDraft(true);
    setError(null);
    try {
      await updateProjectBundle(projectId, bundleId, {
        name: editName,
        execution_environment_id: editEnvId || undefined,
        entrypoint: editEntrypoint || undefined,
        interpreter: editInterpreter as any,
        arguments: editArguments || undefined,
        build_strategy: editBuildStrategy,
        version: editVersion || undefined,
        description: editDescription || undefined,
        resource_identifiers: selectedResources.length > 0 ? selectedResources : undefined,
      });
      router.push(`/projects/${projectId}/analysis`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save draft");
      setSavingDraft(false);
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

  const isDraft = bundle.status === "draft";

  if (!isDraft) {
    return (
      <div>
        {termsResourceId && (
          <TermsDialog
            resourceId={termsResourceId}
            resourceName={termsResourceName}
            onAccept={handleTermsAccept}
            onCancel={handleTermsCancel}
          />
        )}

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

        {aiStatus?.review_enabled && (
        <div className="card" style={{ maxWidth: "640px", marginTop: "var(--spacing-lg)" }}>
          <h3 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "var(--spacing-md)" }}>
            AI Analysis Summary
          </h3>

          {aiStatus === null && (
            <div style={{ marginBottom: "var(--spacing-md)" }}>
              <div style={{ color: "var(--color-text-secondary)" }}>Checking AI availability...</div>
            </div>
          )}

          {aiStatus !== null && !aiStatus.ready && (
            <div style={{ marginBottom: "var(--spacing-md)" }}>
              <div style={{ color: "var(--color-text-secondary)" }}>
                AI assistance is not available
                {aiStatus.reason === "provider_unreachable" && " (AI service unreachable)"}
                {aiStatus.reason === "model_missing" && " (AI model not found)"}
                {aiStatus.reason === "provider_error" && " (AI service error)"}
                {aiStatus.reason === null && ""}
              </div>
            </div>
          )}

          {aiStatus !== null && aiStatus.ready && bundle.ai_review?.status === "pending" && (
            <div style={{ marginBottom: "var(--spacing-md)" }}>
              <div>Status: Pending</div>
            </div>
          )}

          {aiStatus !== null && aiStatus.ready && bundle.ai_review?.status === "completed" && (
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

          {aiStatus !== null && aiStatus.ready && (bundle.ai_review?.status === "unavailable" || bundle.ai_review?.status === "failed") && (
            <div style={{ marginBottom: "var(--spacing-md)" }}>
              <div>Status: Unavailable</div>
            </div>
          )}

          {aiStatus !== null && aiStatus.ready && bundle.ai_review?.status !== "pending" && (
            <button
              className="btn"
              onClick={handleTriggerReview}
              disabled={reviewing}
            >
              {reviewing ? "Processing..." : reviewActionLabel()}
            </button>
          )}
        </div>
        )}
      </div>
    );
  }

  return (
    <div>
      {termsResourceId && (
        <TermsDialog
          resourceId={termsResourceId}
          resourceName={termsResourceName}
          onAccept={handleTermsAccept}
          onCancel={handleTermsCancel}
        />
      )}

      <Link
        href={`/projects/${projectId}/analysis`}
        style={{ color: "var(--color-text-secondary)", fontSize: "0.85rem", textDecoration: "none" }}
      >
        &larr; Back to Analysis
      </Link>

      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          marginTop: "var(--spacing-md)",
          marginBottom: "var(--spacing-lg)",
        }}
      >
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "var(--spacing-sm)", marginBottom: "var(--spacing-xs)" }}>
            <input
              type="text"
              value={editName}
              onChange={(e) => setEditName(e.target.value)}
              autoFocus
              style={{
                fontSize: "1.1rem",
                fontWeight: 600,
                border: "none",
                borderBottom: "2px solid transparent",
                padding: "2px 0",
                outline: "none",
                background: "transparent",
                color: "inherit",
                width: "300px",
              }}
              onFocus={(e) => e.target.select()}
            />
          </div>
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
            {formatBundleStatus(bundle.status)} &mdash; Editable
          </span>
        </div>
        <div>
          <div style={{ display: "flex", gap: "var(--spacing-sm)", marginBottom: "var(--spacing-xs)" }}>
            <button
              className="btn"
              onClick={handleSaveDraft}
              disabled={savingDraft}
            >
              {savingDraft ? "Saving..." : "Save and Close"}
            </button>
            {user?.capabilities.includes("bundle.submit") && (
              <button
                className="btn btn-primary"
                onClick={handleSubmit}
                disabled={actionLoading !== null}
              >
                {actionLoading === "Submit" ? "Submitting…" : "Submit for Review"}
              </button>
            )}
          </div>
          {error && (
            <div style={{ color: "#d32f2f", fontSize: "0.85rem", textAlign: "right" }}>
              {error}
            </div>
          )}
        </div>
      </div>

      <div style={{ maxWidth: "720px" }}>
        <div className="card" style={{ marginBottom: "var(--spacing-lg)" }}>
          <h3
            style={{
              fontSize: "0.85rem",
              fontWeight: 600,
              textTransform: "uppercase",
              letterSpacing: "0.05em",
              color: "var(--color-text-secondary)",
              marginBottom: "var(--spacing-md)",
            }}
          >
            Overview
          </h3>

          <div style={{ marginBottom: "var(--spacing-md)" }}>
            <label
              htmlFor="edit-description"
              style={{ fontSize: "0.8rem", color: "var(--color-text-secondary)", marginBottom: "var(--spacing-xs)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em", display: "block" }}
            >
              Description
            </label>
            <textarea
              id="edit-description"
              value={editDescription}
              onChange={(e) => setEditDescription(e.target.value)}
              rows={2}
              placeholder="Optional description of your analysis"
              style={{
                width: "100%",
                padding: "var(--spacing-xs) var(--spacing-sm)",
                border: "1px solid var(--color-border)",
                borderRadius: "var(--radius-md)",
                fontSize: "0.9rem",
                resize: "vertical",
              }}
            />
          </div>

          <div style={{ display: "flex", gap: "var(--spacing-xl)" }}>
            <div>
              <label
                htmlFor="edit-version-overview"
                style={{ fontSize: "0.8rem", color: "var(--color-text-secondary)", marginBottom: "var(--spacing-xs)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em", display: "block" }}
              >
                Version
              </label>
              <input
                id="edit-version-overview"
                type="text"
                value={editVersion}
                onChange={(e) => setEditVersion(e.target.value)}
                placeholder="1.0.0"
                style={{
                  width: "120px",
                  padding: "var(--spacing-xs) var(--spacing-sm)",
                  border: "1px solid var(--color-border)",
                  borderRadius: "var(--radius-md)",
                  fontSize: "0.9rem",
                }}
              />
            </div>
            <div style={{ paddingTop: "1.4rem", fontSize: "0.85rem", color: "var(--color-text-secondary)" }}>
              <span style={{ fontWeight: 600 }}>Created</span>: {new Date(bundle.created_at).toLocaleDateString()}
            </div>
          </div>
        </div>

        <div className="card" style={{ marginBottom: "var(--spacing-lg)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "var(--spacing-sm)" }}>
            <h3
              style={{
                fontSize: "0.85rem",
                fontWeight: 600,
                textTransform: "uppercase",
                letterSpacing: "0.05em",
                color: "var(--color-text-secondary)",
                margin: 0,
              }}
            >
              Files
            </h3>
            <div style={{ display: "flex", gap: "var(--spacing-xs)" }}>
              {uploadMode === null && !uploading && (
                <>
                  <button
                    className="btn"
                    style={{ fontSize: "0.8rem", padding: "2px 10px" }}
                    onClick={() => setUploadMode("zip")}
                  >
                    Upload ZIP
                  </button>
                  <button
                    className="btn"
                    style={{ fontSize: "0.8rem", padding: "2px 10px" }}
                    onClick={() => setUploadMode("single")}
                  >
                    Add File
                  </button>
                  {bundleFiles.length > 0 && (
                    <button
                      className="btn"
                      style={{ fontSize: "0.8rem", padding: "2px 10px", color: "#d32f2f" }}
                      onClick={handleClearFiles}
                    >
                      Clear
                    </button>
                  )}
                </>
              )}
            </div>
          </div>

          {fileError && (
            <div style={{ color: "#d32f2f", fontSize: "0.85rem", marginBottom: "var(--spacing-sm)" }}>
              {fileError}
            </div>
          )}

          {uploading && (
            <div style={{ color: "var(--color-text-secondary)", fontSize: "0.85rem", marginBottom: "var(--spacing-sm)" }}>
              Uploading...
            </div>
          )}

          {uploadMode === "zip" && (
            <div style={{ marginBottom: "var(--spacing-sm)" }}>
              <div style={{ fontSize: "0.85rem", color: "var(--color-text-secondary)", marginBottom: "var(--spacing-xs)" }}>
                Replace all bundle contents with a ZIP archive:
              </div>
              <div style={{ display: "flex", gap: "var(--spacing-sm)", alignItems: "center" }}>
                <label
                  className="btn btn-primary"
                  style={{ fontSize: "0.85rem", padding: "4px 12px", cursor: "pointer" }}
                >
                  {bundleFiles.length > 0 ? "Replace from ZIP" : "Upload ZIP"}
                  <input
                    type="file"
                    accept=".zip"
                    style={{ display: "none" }}
                    onChange={handleFileUploadZip}
                    disabled={uploading}
                  />
                </label>
                <span style={{ fontSize: "0.8rem", color: "var(--color-text-secondary)" }}>
                  or{" "}
                  <button
                    className="btn"
                    style={{ fontSize: "0.8rem", padding: "2px 8px", border: "none", background: "none", cursor: "pointer", color: "var(--color-primary)", textDecoration: "underline" }}
                    onClick={() => setUploadMode("import")}
                  >
                    import into existing files
                  </button>
                </span>
                <button
                  className="btn"
                  style={{ fontSize: "0.8rem", padding: "2px 8px" }}
                  onClick={() => setUploadMode(null)}
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          {uploadMode === "import" && (
            <div style={{ marginBottom: "var(--spacing-sm)" }}>
              <div style={{ fontSize: "0.85rem", color: "var(--color-text-secondary)", marginBottom: "var(--spacing-xs)" }}>
                Import additional files from a ZIP archive (new files will be added, existing files with the same name will be replaced):
              </div>
              <div style={{ display: "flex", gap: "var(--spacing-sm)", alignItems: "center" }}>
                <label
                  className="btn btn-primary"
                  style={{ fontSize: "0.85rem", padding: "4px 12px", cursor: "pointer" }}
                >
                  Import ZIP
                  <input
                    type="file"
                    accept=".zip"
                    style={{ display: "none" }}
                    onChange={handleFileImportZip}
                    disabled={uploading}
                  />
                </label>
                <button
                  className="btn"
                  style={{ fontSize: "0.8rem", padding: "2px 8px" }}
                  onClick={() => setUploadMode(null)}
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          {uploadMode === "single" && (
            <div style={{ marginBottom: "var(--spacing-sm)" }}>
              <div style={{ fontSize: "0.85rem", color: "var(--color-text-secondary)", marginBottom: "var(--spacing-xs)" }}>
                Upload a single file:
              </div>
              <div style={{ display: "flex", gap: "var(--spacing-sm)", alignItems: "center" }}>
                <label
                  className="btn btn-primary"
                  style={{ fontSize: "0.85rem", padding: "4px 12px", cursor: "pointer" }}
                >
                  Choose File
                  <input
                    type="file"
                    style={{ display: "none" }}
                    onChange={handleFileUploadSingle}
                    disabled={uploading}
                  />
                </label>
                <button
                  className="btn"
                  style={{ fontSize: "0.8rem", padding: "2px 8px" }}
                  onClick={() => setUploadMode(null)}
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          {filesLoading ? (
            <div style={{ color: "var(--color-text-secondary)", fontSize: "0.85rem" }}>
              Loading files...
            </div>
          ) : bundleFiles.length > 0 ? (
            <div>
              <div style={{ fontSize: "0.8rem", color: "var(--color-text-secondary)", marginBottom: "var(--spacing-sm)" }}>
                {bundleFiles.length} file{bundleFiles.length !== 1 ? "s" : ""} —
                {bundleFiles.reduce((sum, f) => sum + f.size, 0) > 1024
                  ? `${(bundleFiles.reduce((sum, f) => sum + f.size, 0) / 1024).toFixed(1)} KB`
                  : `${bundleFiles.reduce((sum, f) => sum + f.size, 0)} bytes`}
              </div>
              <table className="table" style={{ fontSize: "0.85rem" }}>
                <thead>
                  <tr>
                    <th>File</th>
                    <th>Size</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {bundleFiles.map((f) => (
                    <tr key={f.path}>
                      <td style={{ fontWeight: 500, fontFamily: "var(--font-mono)", fontSize: "0.8rem" }}>
                        {f.path}
                      </td>
                      <td style={{ color: "var(--color-text-secondary)" }}>
                        {f.size > 1024
                          ? `${(f.size / 1024).toFixed(1)} KB`
                          : `${f.size} bytes`}
                      </td>
                      <td>
                        <button
                          className="btn"
                          style={{ fontSize: "0.75rem", padding: "1px 6px", color: "#d32f2f" }}
                          onClick={() => handleDeleteFile(f.path)}
                        >
                          Remove
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div style={{ color: "var(--color-text-secondary)", fontSize: "0.85rem", lineHeight: 1.8 }}>
              <div>No files uploaded yet. Upload a ZIP archive containing your analysis code to get started, or add individual files.</div>
              <div style={{ marginTop: "var(--spacing-sm)" }}>
                <Link
                  href="/templates"
                  style={{ color: "var(--color-primary)", textDecoration: "none" }}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Browse Bundle Templates →
                </Link>
              </div>
              <div>
                <Link
                  href="/examples"
                  style={{ color: "var(--color-primary)", textDecoration: "none" }}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Browse Example Analyses →
                </Link>
              </div>
            </div>
          )}
        </div>

        <div className="card" style={{ marginBottom: "var(--spacing-lg)" }}>
          <h3
            style={{
              fontSize: "0.85rem",
              fontWeight: 600,
              textTransform: "uppercase",
              letterSpacing: "0.05em",
              color: "var(--color-text-secondary)",
              marginBottom: "var(--spacing-md)",
            }}
          >
            Execution
          </h3>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--spacing-md)" }}>
            <div>
              <label
                htmlFor="edit-env"
                style={{ fontSize: "0.8rem", color: "var(--color-text-secondary)", marginBottom: "var(--spacing-xs)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em", display: "block" }}
              >
                Environment
              </label>
              <select
                id="edit-env"
                value={editEnvId}
                onChange={(e) => setEditEnvId(e.target.value)}
                style={{
                  width: "100%",
                  padding: "var(--spacing-xs) var(--spacing-sm)",
                  border: "1px solid var(--color-border)",
                  borderRadius: "var(--radius-md)",
                  fontSize: "0.9rem",
                  background: "var(--color-bg)",
                }}
              >
                <option value="">Select environment...</option>
                {environments.map((env) => (
                  <option key={env.id} value={env.id}>
                    {env.display_name}
                  </option>
                ))}
              </select>
              <div style={{ marginTop: "var(--spacing-xs)", fontSize: "0.8rem" }}>
                {editEnvId && environments.find((e) => e.id === editEnvId) ? (
                  <Link
                    href={`/environments/${environments.find((e) => e.id === editEnvId)?.identifier}`}
                    style={{ color: "var(--color-primary)", textDecoration: "none" }}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    View {environments.find((e) => e.id === editEnvId)?.display_name} details →
                  </Link>
                ) : (
                  <Link
                    href="/environments"
                    style={{ color: "var(--color-primary)", textDecoration: "none" }}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    Browse Execution Environments →
                  </Link>
                )}
              </div>

              {user?.capabilities.includes("build.customize") && (
                <label
                  style={{
                    display: "flex",
                    alignItems: "flex-start",
                    gap: "var(--spacing-sm)",
                    cursor: "pointer",
                    marginTop: "var(--spacing-sm)",
                    paddingTop: "var(--spacing-sm)",
                    borderTop: "1px solid var(--color-border)",
                  }}
                >
                  <input
                    type="checkbox"
                    checked={editBuildStrategy === "custom"}
                    onChange={(e) =>
                      setEditBuildStrategy(
                        e.target.checked ? "custom" : "institutional",
                      )
                    }
                    style={{ marginTop: "2px" }}
                  />
                  <div>
                    <div style={{ fontWeight: 500, fontSize: "0.85rem" }}>
                      Custom Build
                    </div>
                    <div
                      style={{
                        fontSize: "0.75rem",
                        color: "var(--color-text-secondary)",
                      }}
                    >
                      {editEnvId
                        ? `Build custom Dockerfile on top of ${environments.find((e) => e.id === editEnvId)?.display_name || "selected environment"}`
                        : "Select an execution environment first"}
                    </div>
                  </div>
                </label>
              )}
            </div>

            <div>
              <label
                htmlFor="edit-entrypoint"
                style={{ fontSize: "0.8rem", color: "var(--color-text-secondary)", marginBottom: "var(--spacing-xs)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em", display: "block" }}
              >
                Entrypoint
              </label>
              {bundleFiles.length > 0 && entrypointCandidates.length > 0 ? (
                <select
                  id="edit-entrypoint"
                  value={editEntrypoint}
                  onChange={(e) => setEditEntrypoint(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "var(--spacing-xs) var(--spacing-sm)",
                    border: "1px solid var(--color-border)",
                    borderRadius: "var(--radius-md)",
                    fontSize: "0.9rem",
                    background: "var(--color-bg)",
                    fontFamily: "var(--font-mono)",
                  }}
                >
                  <option value="">Select entrypoint...</option>
                  {entrypointCandidates.map((ep) => (
                    <option key={ep} value={ep}>
                      {ep}
                    </option>
                  ))}
                </select>
              ) : bundleFiles.length > 0 ? (
                <div style={{ fontSize: "0.85rem", color: "var(--color-text-secondary)", fontStyle: "italic" }}>
                  No entrypoint candidates detected. Add a .py, .R, or .sh file at the top level.
                </div>
              ) : (
                <div style={{ fontSize: "0.85rem", color: "var(--color-text-secondary)", fontStyle: "italic" }}>
                  Upload files to select an entrypoint.
                </div>
              )}
            </div>

            <div>
              <label
                htmlFor="edit-interpreter"
                style={{ fontSize: "0.8rem", color: "var(--color-text-secondary)", marginBottom: "var(--spacing-xs)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em", display: "block" }}
              >
                Interpreter
              </label>
              <select
                id="edit-interpreter"
                value={editInterpreter}
                onChange={(e) => setEditInterpreter(e.target.value)}
                style={{
                  width: "100%",
                  padding: "var(--spacing-xs) var(--spacing-sm)",
                  border: "1px solid var(--color-border)",
                  borderRadius: "var(--radius-md)",
                  fontSize: "0.9rem",
                  background: "var(--color-bg)",
                }}
              >
                <option value="python">Python</option>
                <option value="shell">Shell</option>
                <option value="r">R</option>
              </select>
            </div>

            <div>
              <label
                htmlFor="edit-version-exec"
                style={{ fontSize: "0.8rem", color: "var(--color-text-secondary)", marginBottom: "var(--spacing-xs)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em", display: "block" }}
              >
                Version
              </label>
              <input
                id="edit-version-exec"
                type="text"
                value={editVersion}
                onChange={(e) => setEditVersion(e.target.value)}
                placeholder="1.0.0"
                style={{
                  width: "100%",
                  padding: "var(--spacing-xs) var(--spacing-sm)",
                  border: "1px solid var(--color-border)",
                  borderRadius: "var(--radius-md)",
                  fontSize: "0.9rem",
                }}
              />
            </div>

            <div>
              <label
                htmlFor="edit-arguments"
                style={{ fontSize: "0.8rem", color: "var(--color-text-secondary)", marginBottom: "var(--spacing-xs)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em", display: "block" }}
              >
                Arguments
              </label>
              <input
                id="edit-arguments"
                type="text"
                value={editArguments}
                onChange={(e) => setEditArguments(e.target.value)}
                placeholder="--verbose"
                style={{
                  width: "100%",
                  padding: "var(--spacing-xs) var(--spacing-sm)",
                  border: "1px solid var(--color-border)",
                  borderRadius: "var(--radius-md)",
                  fontSize: "0.9rem",
                }}
              />
            </div>
          </div>

          <div style={{ marginTop: "var(--spacing-md)" }}>
            <div style={{ fontSize: "0.8rem", color: "var(--color-text-secondary)", marginBottom: "var(--spacing-xs)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>
              Data Resources
            </div>
            {projectResources.length > 0 ? (
              <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-xs)" }}>
                {projectResources.map((r) => (
                  <label
                    key={r.id}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "var(--spacing-sm)",
                      fontSize: "0.9rem",
                      cursor: "pointer",
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={selectedResources.includes(r.identifier)}
                      onChange={() =>
                        setSelectedResources((prev) =>
                          prev.includes(r.identifier)
                            ? prev.filter((id) => id !== r.identifier)
                            : [...prev, r.identifier]
                        )
                      }
                    />
                    {r.name}
                    <span style={{ color: "var(--color-text-secondary)", fontSize: "0.8rem" }}>
                      ({r.identifier})
                    </span>
                  </label>
                ))}
              </div>
            ) : (
              <div style={{ color: "var(--color-text-secondary)", fontSize: "0.85rem", lineHeight: 1.6 }}>
                No data resources allocated to this project.{" "}
                <Link
                  href={`/projects/${projectId}/resources`}
                  style={{ color: "var(--color-primary)", textDecoration: "none" }}
                >
                  Add resources from the Resources tab →
                </Link>
              </div>
            )}
            {selectedResources.length > 0 && (
              <div style={{ marginTop: "var(--spacing-sm)", fontSize: "0.8rem" }}>
                <Link
                  href={`/projects/${projectId}/resources`}
                  style={{ color: "var(--color-primary)", textDecoration: "none" }}
                >
                  View all project Data Resources →
                </Link>
              </div>
            )}
          </div>
        </div>

        <div className="card" style={{ marginBottom: "var(--spacing-lg)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "var(--spacing-sm)" }}>
            <h3
              style={{
                fontSize: "0.85rem",
                fontWeight: 600,
                textTransform: "uppercase",
                letterSpacing: "0.05em",
                color: "var(--color-text-secondary)",
                margin: 0,
              }}
            >
              Validation Run
            </h3>
            {validationStatus?.is_validated && (
              <span style={{ fontSize: "0.8rem", color: "#2e7d32", fontWeight: 600 }}>
                ✅ Validated
              </span>
            )}
            {validationStatus?.has_changed && (
              <span style={{ fontSize: "0.8rem", color: "#ed6c02", fontWeight: 600 }}>
                ⚠️ Bundle has changed since validation
              </span>
            )}
          </div>

          <div style={{ marginBottom: "var(--spacing-md)" }}>
            <button
              className="btn btn-primary"
              onClick={handleRunValidation}
              disabled={validationLoading || !editEnvId || bundleFiles.length === 0}
              title={
                validationLoading
                  ? "Validation in progress"
                  : !editEnvId && bundleFiles.length === 0
                    ? "Select an execution environment and upload analysis files"
                    : !editEnvId
                      ? "Select an execution environment"
                      : bundleFiles.length === 0
                        ? "Upload analysis files first"
                        : "Run validation"
              }
            >
              {validationLoading ? "Running..." : "Run Validation"}
            </button>
            {validationError && (
              <div style={{ color: "#d32f2f", fontSize: "0.85rem", marginTop: "var(--spacing-xs)" }}>
                {validationError}
              </div>
            )}
            {!editEnvId && bundleFiles.length === 0 && (
              <div style={{ color: "var(--color-text-secondary)", fontSize: "0.8rem", marginTop: "var(--spacing-xs)" }}>
                Select an execution environment and upload analysis files to enable validation.
              </div>
            )}
            {!editEnvId && bundleFiles.length > 0 && (
              <div style={{ color: "var(--color-text-secondary)", fontSize: "0.8rem", marginTop: "var(--spacing-xs)" }}>
                Select an execution environment to enable validation.
              </div>
            )}
            {editEnvId && bundleFiles.length === 0 && (
              <div style={{ color: "var(--color-text-secondary)", fontSize: "0.8rem", marginTop: "var(--spacing-xs)" }}>
                Upload analysis files to enable validation.
              </div>
            )}
          </div>

          {validations.length > 0 && (
            <div>
              <table className="table" style={{ fontSize: "0.85rem" }}>
                <thead>
                  <tr>
                    <th>Run</th>
                    <th>Status</th>
                    <th>Files</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {validations.slice(0, 5).map((v, i) => (
                    <tr key={v.id}>
                      <td style={{ fontWeight: 500 }}>#{validations.length - i}</td>
                      <td>
                        <span
                          style={{
                            color: v.status === "completed" ? "#2e7d32"
                              : v.status === "failed" ? "#d32f2f"
                              : v.status === "running" ? "#1565c0"
                              : "var(--color-text-secondary)",
                            fontWeight: 600,
                          }}
                        >
                          {v.status}
                        </span>
                      </td>
                      <td style={{ color: "var(--color-text-secondary)" }}>
                        {v.output_files?.length ?? 0} file{(v.output_files?.length ?? 0) !== 1 ? "s" : ""}
                      </td>
                      <td>
                        <button
                          className="btn"
                          style={{ fontSize: "0.75rem", padding: "1px 6px" }}
                          onClick={() =>
                            setExpandedValidation(
                              expandedValidation === v.id ? null : v.id
                            )
                          }
                        >
                          {expandedValidation === v.id ? "Hide Log" : "View Log"}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {expandedValidation && (
            <div style={{ marginTop: "var(--spacing-sm)" }}>
              {(() => {
                const v = validations.find((r) => r.id === expandedValidation);
                if (!v) return null;
                return (
                  <div>
                    <LogViewer log={v.log} title={`Validation Log: ${v.name}`} maxHeight="300px" />
                    {v.output_files && v.output_files.length > 0 && (
                      <div style={{ marginTop: "var(--spacing-sm)" }}>
                        <div style={{ fontSize: "0.8rem", color: "var(--color-text-secondary)", marginBottom: "var(--spacing-xs)", fontWeight: 600 }}>
                          Output Files
                        </div>
                        <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-xs)" }}>
                          {v.output_files.map((f) => (
                            <div key={f.filename} style={{ fontSize: "0.85rem", fontFamily: "var(--font-mono)" }}>
                              {f.filename} — {f.size > 1024 ? `${(f.size / 1024).toFixed(1)} KB` : `${f.size} bytes`}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })()}
            </div>
          )}
        </div>

        <div
          className="card"
          style={{
            marginBottom: "var(--spacing-lg)",
            border: "1px dashed var(--color-border)",
            background: "var(--color-bg)",
          }}
        >
          <h3
            style={{
              fontSize: "0.85rem",
              fontWeight: 600,
              textTransform: "uppercase",
              letterSpacing: "0.05em",
              color: "var(--color-text-secondary)",
              marginBottom: "var(--spacing-sm)",
            }}
          >
            Readiness
          </h3>
          <div style={{ color: "var(--color-text-secondary)", fontSize: "0.85rem", lineHeight: 1.6 }}>
            To submit your analysis for institutional review, ensure the following are configured: analysis files, execution environment, entrypoint, and data resources. Save your draft to persist changes.
            {validationStatus?.is_validated && (
              <div style={{ marginTop: "var(--spacing-sm)", color: "#2e7d32" }}>
                ✅ Your analysis has been validated against representative data and is ready for review.
              </div>
            )}
            {validationStatus?.has_changed && (
              <div style={{ marginTop: "var(--spacing-sm)", color: "#ed6c02" }}>
                ⚠️ Your bundle has changed since the last validation. Run validation again to confirm your changes still work.
              </div>
            )}
            {!validationStatus?.last_validation_id && (
              <div style={{ marginTop: "var(--spacing-sm)", color: "var(--color-text-secondary)" }}>
                Run validation first to confirm your analysis works against representative data before submitting for review.
              </div>
            )}
          </div>
        </div>

        <div style={{ display: "flex", gap: "var(--spacing-xl)", marginBottom: "var(--spacing-lg)", color: "var(--color-text-secondary)", fontSize: "0.85rem" }}>
          <div>
            <span style={{ fontWeight: 600 }}>Created</span>: {new Date(bundle.created_at).toLocaleDateString()}
          </div>
          <div>
            <span style={{ fontWeight: 600 }}>Updated</span>: {new Date(bundle.updated_at).toLocaleDateString()}
          </div>
        </div>
      </div>
    </div>
  );
}
