"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { getAdminSettings, getAIStatus, AIStatus, updateAdminSetting } from "@/lib/api";

function aiStatusWarning(reason: string | null): string {
  switch (reason) {
    case "provider_unreachable":
      return "The AI service is not running. Run make enable-ai on the server to start it.";
    case "model_missing":
      return "The AI model is not available. Run make enable-ai on the server to download it.";
    case "provider_error":
      return "The AI service returned an error. Check the platform logs.";
    default:
      return "The AI subsystem is not ready. Run make enable-ai on the server to prepare it.";
  }
}

function MaxDurationInput({
  settings,
  updateAdminSetting,
  setSettings,
  setSuccess,
  setError,
}: {
  settings: Record<string, string> | null;
  updateAdminSetting: (key: string, value: string) => Promise<{ key: string; value: string }>;
  setSettings: (updater: (prev: Record<string, string> | null) => Record<string, string> | null) => void;
  setSuccess: (msg: string | null) => void;
  setError: (msg: string | null) => void;
}) {
  const storedMinutes = settings?.["max_task_duration_seconds"]
    ? Math.round(Number(settings["max_task_duration_seconds"]) / 60)
    : 60;
  const [draft, setDraft] = useState(storedMinutes);
  const [saving, setSaving] = useState(false);

  useEffect(() => { setDraft(storedMinutes); }, [storedMinutes]);

  const changed = draft !== storedMinutes;

  const handleUpdate = async () => {
    if (isNaN(draft) || draft < 1 || draft > 1440) return;
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      const seconds = String(draft * 60);
      const updated = await updateAdminSetting("max_task_duration_seconds", seconds);
      setSettings((prev) => ({ ...prev, "max_task_duration_seconds": updated.value }));
      setSuccess("Maximum job duration updated");
    } catch {
      setError("Failed to update maximum job duration");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={{ display: "flex", alignItems: "center", gap: "var(--spacing-sm)" }}>
      <input
        type="number"
        min={1}
        max={1440}
        value={draft}
        onChange={(e) => setDraft(parseInt(e.target.value, 10) || 0)}
        style={{
          width: "80px",
          padding: "var(--spacing-sm)",
          border: "1px solid var(--color-border)",
          borderRadius: "var(--radius-md)",
          fontSize: "0.9rem",
          textAlign: "center",
        }}
      />
      <span style={{ fontSize: "0.9rem", color: "var(--color-text-secondary)" }}>
        minutes
      </span>
      <button
        className="btn btn-primary"
        onClick={handleUpdate}
        disabled={!changed || saving || isNaN(draft) || draft < 1 || draft > 1440}
        style={{
          opacity: !changed || saving ? 0.5 : 1,
          cursor: !changed || saving ? "not-allowed" : "pointer",
        }}
      >
        {saving ? "Saving..." : "Update"}
      </button>
    </div>
  );
}

export default function AdminSettingsPage() {
  const [settings, setSettings] = useState<Record<string, string> | null>(null);
  const [aiStatus, setAiStatus] = useState<AIStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const fetchSettings = useCallback(async () => {
    try {
      const data = await getAdminSettings();
      setSettings(data);
    } catch {
      setError("Failed to load settings");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSettings();
  }, [fetchSettings]);

  useEffect(() => {
    getAIStatus().then(setAiStatus).catch(() => setAiStatus(null));
  }, []);

  const handleToggle = async (key: string, currentValue: string) => {
    const newValue = currentValue === "true" ? "false" : "true";
    setSaving(key);
    setError(null);
    setSuccess(null);
    try {
      const updated = await updateAdminSetting(key, newValue);
      setSettings((prev) => ({ ...prev, [key]: updated.value }));
      const labels: Record<string, string> = {
        ai_review_enabled: "AI-assisted bundle review",
        prevent_self_moderation: "Governance independence",
      };
      setSuccess(
        `${labels[key] || key} ${newValue === "true" ? "enabled" : "disabled"}`,
      );
    } catch {
      setError("Failed to update setting");
    } finally {
      setSaving(null);
    }
  };

  if (loading) {
    return <div className="card empty-state">Loading...</div>;
  }

  const aiEnabled = settings?.["ai_review_enabled"] === "true";
  const moderationEnabled = settings?.["prevent_self_moderation"] !== "false";
  const autoExecuteEnabled = settings?.["auto_execute_approved_bundles"] !== "false";
  const aiUnavailable = aiStatus !== null && !aiStatus.ready;
  const toggleDisabled = saving === "ai_review_enabled" || (aiUnavailable && !aiEnabled);

  return (
    <div>
      <h2 className="page-title">Settings</h2>

      {error && (
        <div
          className="card"
          style={{
            background: "#f8d7da",
            color: "#721c24",
            padding: "var(--spacing-md)",
            marginBottom: "var(--spacing-lg)",
          }}
        >
          {error}
        </div>
      )}

      {success && (
        <div
          className="card"
          style={{
            background: success.includes("enabled") ? "#d4edda" : "#d1ecf1",
            color: success.includes("enabled") ? "#155724" : "#0c5460",
            padding: "var(--spacing-md)",
            marginBottom: "var(--spacing-lg)",
          }}
        >
          {success}
        </div>
      )}

      {aiUnavailable && !aiEnabled && (
        <div
          className="card"
          style={{
            background: "#fff3cd",
            color: "#856404",
            padding: "var(--spacing-md)",
            marginBottom: "var(--spacing-lg)",
            maxWidth: "600px",
          }}
        >
          <strong>AI subsystem not ready</strong>
          <p style={{ margin: "var(--spacing-xs) 0 0 0", fontSize: "0.85rem" }}>
            {aiStatusWarning(aiStatus?.reason)}
          </p>
        </div>
      )}

      {aiUnavailable && aiEnabled && (
        <div
          className="card"
          style={{
            background: "#f8d7da",
            color: "#721c24",
            padding: "var(--spacing-md)",
            marginBottom: "var(--spacing-lg)",
            maxWidth: "600px",
          }}
        >
          <strong>AI subsystem unavailable</strong>
          <p style={{ margin: "var(--spacing-xs) 0 0 0", fontSize: "0.85rem" }}>
            AI-assisted bundle review is enabled but the AI subsystem is not operational.
            {" "}Run make enable-ai on the server to restore it.
          </p>
        </div>
      )}

      <div className="card" style={{ maxWidth: "600px" }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <div>
            <h3 style={{ fontSize: "1rem", fontWeight: 600, margin: 0 }}>
              Enable AI-assisted bundle review
            </h3>
            <p
              style={{
                fontSize: "0.85rem",
                color: "var(--color-text-secondary)",
                marginTop: "var(--spacing-xs)",
                marginBottom: 0,
              }}
            >
              When enabled, submitted analysis bundles will be automatically
              reviewed by the configured AI model. AI reviews are advisory only
              and do not replace human review.
            </p>
          </div>
          <button
            className="btn"
            onClick={() => handleToggle("ai_review_enabled", aiEnabled ? "true" : "false")}
            disabled={toggleDisabled}
            title={
              toggleDisabled && aiUnavailable && !aiEnabled
                ? "AI subsystem must be operational before enabling"
                : undefined
            }
            style={{
              minWidth: "80px",
              background: aiEnabled ? "#d4edda" : "#f0f0f0",
              color: aiEnabled ? "#155724" : "#666",
              border: aiEnabled ? "1px solid #c3e6cb" : "1px solid #ddd",
              opacity: toggleDisabled ? 0.5 : 1,
              cursor: toggleDisabled ? "not-allowed" : "pointer",
            }}
          >
            {saving === "ai_review_enabled"
              ? "..."
              : aiEnabled
                ? "Enabled"
                : "Disabled"}
          </button>
        </div>
      </div>

      <div className="card" style={{ maxWidth: "600px", marginTop: "var(--spacing-lg)" }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <div>
            <h3 style={{ fontSize: "1rem", fontWeight: 600, margin: 0 }}>
              Prevent self-moderation
            </h3>
            <p
              style={{
                fontSize: "0.85rem",
                color: "var(--color-text-secondary)",
                marginTop: "var(--spacing-xs)",
                marginBottom: 0,
              }}
            >
              When enabled, the actor who submits a bundle or requests execution
              cannot review, approve, reject, or release that same item.
            </p>
          </div>
          <button
            className="btn"
            onClick={() => handleToggle("prevent_self_moderation", moderationEnabled ? "true" : "false")}
            disabled={saving === "prevent_self_moderation"}
            style={{
              minWidth: "80px",
              background: moderationEnabled ? "#d4edda" : "#f0f0f0",
              color: moderationEnabled ? "#155724" : "#666",
              border: moderationEnabled ? "1px solid #c3e6cb" : "1px solid #ddd",
              opacity: saving === "prevent_self_moderation" ? 0.5 : 1,
              cursor: saving === "prevent_self_moderation" ? "not-allowed" : "pointer",
            }}
          >
            {saving === "prevent_self_moderation"
              ? "..."
              : moderationEnabled
                ? "Enabled"
                : "Disabled"}
          </button>
        </div>
      </div>

      <div className="card" style={{ maxWidth: "600px", marginTop: "var(--spacing-lg)" }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <div>
            <h3 style={{ fontSize: "1rem", fontWeight: 600, margin: 0 }}>
              Automatically execute approved analysis bundles
            </h3>
            <p
              style={{
                fontSize: "0.85rem",
                color: "var(--color-text-secondary)",
                marginTop: "var(--spacing-xs)",
                marginBottom: 0,
              }}
            >
              When enabled, an execution request is automatically created when
              the build completes after bundle approval. Researchers may still
              manually create additional execution requests for the same bundle.
            </p>
          </div>
          <button
            className="btn"
            onClick={() => handleToggle("auto_execute_approved_bundles", autoExecuteEnabled ? "true" : "false")}
            disabled={saving === "auto_execute_approved_bundles"}
            style={{
              minWidth: "80px",
              background: autoExecuteEnabled ? "#d4edda" : "#f0f0f0",
              color: autoExecuteEnabled ? "#155724" : "#666",
              border: autoExecuteEnabled ? "1px solid #c3e6cb" : "1px solid #ddd",
              opacity: saving === "auto_execute_approved_bundles" ? 0.5 : 1,
              cursor: saving === "auto_execute_approved_bundles" ? "not-allowed" : "pointer",
            }}
          >
            {saving === "auto_execute_approved_bundles"
              ? "..."
              : autoExecuteEnabled
                ? "Enabled"
                : "Disabled"}
          </button>
        </div>
      </div>

      <div className="card" style={{ maxWidth: "600px", marginTop: "var(--spacing-lg)" }}>
        <div>
          <h3 style={{ fontSize: "1rem", fontWeight: 600, margin: 0 }}>
            Maximum Job Duration
          </h3>
          <p
            style={{
              fontSize: "0.85rem",
              color: "var(--color-text-secondary)",
              marginTop: "var(--spacing-xs)",
              marginBottom: "var(--spacing-md)",
            }}
          >
            The maximum time a validation, build or execution task may run before
            it is automatically terminated.
          </p>
          <MaxDurationInput
            settings={settings}
            updateAdminSetting={updateAdminSetting}
            setSettings={setSettings}
            setSuccess={setSuccess}
            setError={setError}
          />
        </div>
      </div>
    </div>
  );
}
