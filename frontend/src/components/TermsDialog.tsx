"use client";

import { useEffect, useState } from "react";
import { getResourceTermsCurrent, acceptResourceTerms } from "@/lib/api";
import { Markdown } from "@/components/Markdown";
import type { TermsOfService } from "@/lib/api";

interface TermsDialogProps {
  resourceId: string;
  resourceName: string;
  onAccept: () => void;
  onCancel: () => void;
  requireAcceptance?: boolean;
}

export function TermsDialog({
  resourceId,
  resourceName,
  onAccept,
  onCancel,
  requireAcceptance = true,
}: TermsDialogProps) {
  const [terms, setTerms] = useState<TermsOfService | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [accepting, setAccepting] = useState(false);

  useEffect(() => {
    getResourceTermsCurrent(resourceId)
      .then(setTerms)
      .catch(() => setError("Failed to load terms."))
      .finally(() => setLoading(false));
  }, [resourceId]);

  const handleAccept = async () => {
    if (!requireAcceptance) {
      onAccept();
      return;
    }
    setAccepting(true);
    try {
      await acceptResourceTerms(resourceId);
      onAccept();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to accept terms.");
      setAccepting(false);
    }
  };

  const buttonLabel = requireAcceptance ? "Accept & Continue" : "Acknowledge & Continue";
  const busyLabel = requireAcceptance ? "Accepting..." : "Continue";

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
    >
      <div
        className="card"
        style={{
          maxWidth: "600px",
          width: "90%",
          maxHeight: "80vh",
          display: "flex",
          flexDirection: "column",
          padding: "var(--spacing-lg)",
        }}
      >
        <h2 style={{ fontSize: "1.1rem", fontWeight: 600, marginBottom: "var(--spacing-sm)" }}>
          {resourceName} — Terms of Service
        </h2>

        {terms && (
          <div style={{ marginBottom: "var(--spacing-sm)", fontSize: "0.85rem", color: "var(--color-text-secondary)" }}>
            <div style={{ fontWeight: 600 }}>{terms.title}</div>
            <div>
              Version {terms.version}
              {terms.published_at && (
                <span> — Published {new Date(terms.published_at).toLocaleDateString()}</span>
              )}
            </div>
          </div>
        )}

        {!requireAcceptance && (
          <p style={{ fontSize: "0.85rem", color: "var(--color-text-secondary)", marginBottom: "var(--spacing-md)" }}>
            This data resource is governed by published Terms of Service. Researchers must
            acknowledge these terms before submitting analyses using this resource.
          </p>
        )}

        {requireAcceptance && (
          <p style={{ fontSize: "0.85rem", color: "var(--color-text-secondary)", marginBottom: "var(--spacing-md)" }}>
            Please review and accept the terms before using this data resource.
          </p>
        )}

        {error && (
          <div style={{ color: "#d32f2f", marginBottom: "var(--spacing-md)", fontSize: "0.9rem" }}>
            {error}
          </div>
        )}

        <div
          style={{
            flex: 1,
            overflowY: "auto",
            marginBottom: "var(--spacing-md)",
            padding: "var(--spacing-md)",
            border: "1px solid var(--color-border)",
            borderRadius: "var(--radius-md)",
            background: "#fff",
            fontSize: "0.9rem",
            lineHeight: 1.6,
          }}
        >
          {loading ? (
            <div className="empty-state">Loading...</div>
          ) : terms ? (
            <Markdown content={terms.content} />
          ) : (
            <div className="empty-state">No terms available.</div>
          )}
        </div>

        <div style={{ display: "flex", gap: "var(--spacing-md)", justifyContent: "flex-end" }}>
          <button className="btn" onClick={onCancel} disabled={accepting}>
            Cancel
          </button>
          <button
            className="btn btn-primary"
            onClick={handleAccept}
            disabled={accepting || !terms}
          >
            {accepting ? busyLabel : buttonLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
