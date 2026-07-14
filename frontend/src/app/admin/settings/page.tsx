"use client";

import { useCallback, useEffect, useState } from "react";
import { getAdminSettings, getAIStatus, AIStatus, updateAdminSetting } from "@/lib/api";

function aiStatusWarning(reason: string | null): string {
  switch (reason) {
    case "provider_unreachable":
      return "The AI service is not running. Run make ai on the server to start it.";
    case "model_missing":
      return "The AI model is not available. Run make ai on the server to download it.";
    case "provider_error":
      return "The AI service returned an error. Check the platform logs.";
    default:
      return "The AI subsystem is not ready. Run make ai on the server to prepare it.";
  }
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
      setSuccess(
        `AI-assisted bundle review ${newValue === "true" ? "enabled" : "disabled"}`,
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
            {" "}Run make ai on the server to restore it.
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
    </div>
  );
}
