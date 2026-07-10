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
}

export function TermsDialog({ resourceId, resourceName, onAccept, onCancel }: TermsDialogProps) {
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
    setAccepting(true);
    try {
      await acceptResourceTerms(resourceId);
      onAccept();
    } catch {
      setError("Failed to accept terms. Please try again.");
      setAccepting(false);
    }
  };

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
          Dataset Terms — {resourceName}
        </h2>
        <p style={{ fontSize: "0.85rem", color: "var(--color-text-secondary)", marginBottom: "var(--spacing-md)" }}>
          Please review and accept the terms before using this data resource.
        </p>

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
            {accepting ? "Accepting..." : "Accept & Continue"}
          </button>
        </div>
      </div>
    </div>
  );
}
