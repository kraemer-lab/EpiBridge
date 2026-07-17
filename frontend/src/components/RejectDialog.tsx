"use client";

import { useState } from "react";

interface RejectDialogProps {
  title: string;
  onConfirm: (reason: string) => Promise<void>;
  onCancel: () => void;
}

const MAX_REASON_LENGTH = 2000;

export function RejectDialog({ title, onConfirm, onCancel }: RejectDialogProps) {
  const [reason, setReason] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const trimmed = reason.trim();
  const canSubmit = trimmed.length > 0 && trimmed.length <= MAX_REASON_LENGTH && !submitting;

  const handleSubmit = async () => {
    if (!canSubmit) return;
    setSubmitting(true);
    setError(null);
    try {
      await onConfirm(trimmed);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Rejection failed");
      setSubmitting(false);
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
        zIndex: 1100,
      }}
    >
      <div
        className="card"
        style={{
          maxWidth: "560px",
          width: "90%",
          padding: "var(--spacing-lg)",
        }}
      >
        <h2 style={{ fontSize: "1.1rem", fontWeight: 600, marginBottom: "var(--spacing-md)" }}>
          Reject {title}
        </h2>

        <label
          htmlFor="rejection-reason"
          style={{
            display: "block",
            fontSize: "0.9rem",
            fontWeight: 500,
            marginBottom: "var(--spacing-xs)",
          }}
        >
          Reason for rejection
        </label>
        <p style={{ fontSize: "0.85rem", color: "var(--color-text-secondary)", marginBottom: "var(--spacing-sm)" }}>
          Please explain what should be changed before this work can be resubmitted.
        </p>

        <textarea
          id="rejection-reason"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          maxLength={MAX_REASON_LENGTH}
          rows={5}
          style={{
            width: "100%",
            padding: "var(--spacing-sm)",
            border: "1px solid var(--color-border)",
            borderRadius: "var(--radius-md)",
            fontSize: "0.9rem",
            resize: "vertical",
            boxSizing: "border-box",
          }}
          autoFocus
        />

        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginTop: "var(--spacing-xs)",
            fontSize: "0.8rem",
            color: "var(--color-text-secondary)",
          }}
        >
          <span>
            {reason.length === 0
              ? "Required"
              : !trimmed
                ? "Cannot be only whitespace"
                : `${reason.length} / ${MAX_REASON_LENGTH}`}
          </span>
          {reason.length > 0 && !trimmed && (
            <span style={{ color: "#d32f2f" }}>Cannot be only whitespace</span>
          )}
        </div>

        {error && (
          <div style={{ color: "#d32f2f", marginTop: "var(--spacing-sm)", fontSize: "0.9rem" }}>
            {error}
          </div>
        )}

        <div
          style={{
            display: "flex",
            gap: "var(--spacing-md)",
            justifyContent: "flex-end",
            marginTop: "var(--spacing-md)",
          }}
        >
          <button className="btn" onClick={onCancel} disabled={submitting}>
            Cancel
          </button>
          <button
            className="btn btn-primary"
            onClick={handleSubmit}
            disabled={!canSubmit}
            style={!canSubmit ? {} : { background: "var(--color-danger, #c62828)", color: "#fff", border: "none" }}
          >
            {submitting ? "Rejecting…" : "Reject"}
          </button>
        </div>
      </div>
    </div>
  );
}
