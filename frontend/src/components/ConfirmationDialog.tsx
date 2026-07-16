"use client";

import { useState } from "react";

interface ConfirmationDialogProps {
  title: string;
  message: string;
  confirmLabel: string;
  onConfirm: (reason?: string) => void;
  onCancel: () => void;
  requireReason?: boolean;
  reasonLabel?: string;
}

const MAX_REASON_LENGTH = 2000;

export function ConfirmationDialog({
  title,
  message,
  confirmLabel,
  onConfirm,
  onCancel,
  requireReason,
  reasonLabel = "Reason for cancellation",
}: ConfirmationDialogProps) {
  const [reason, setReason] = useState("");

  const trimmed = reason.trim();
  const canConfirm = !requireReason || (trimmed.length > 0 && trimmed.length <= MAX_REASON_LENGTH);

  const handleConfirm = () => {
    if (!canConfirm) return;
    onConfirm(requireReason ? trimmed : undefined);
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
          maxWidth: "560px",
          width: "90%",
          padding: "var(--spacing-lg)",
        }}
      >
        <h2 style={{ fontSize: "1.1rem", fontWeight: 600, marginBottom: "var(--spacing-md)" }}>
          {title}
        </h2>

        <div
          style={{
            fontSize: "0.9rem",
            lineHeight: 1.6,
            marginBottom: "var(--spacing-md)",
            whiteSpace: "pre-wrap",
          }}
        >
          {message}
        </div>

        {requireReason && (
          <>
            <label
              htmlFor="confirm-reason"
              style={{
                display: "block",
                fontSize: "0.9rem",
                fontWeight: 500,
                marginBottom: "var(--spacing-xs)",
              }}
            >
              {reasonLabel}
            </label>
            <textarea
              id="confirm-reason"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              maxLength={MAX_REASON_LENGTH}
              rows={4}
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
                justifyContent: "flex-end",
                marginTop: "var(--spacing-xs)",
                fontSize: "0.8rem",
                color: "var(--color-text-secondary)",
              }}
            >
              {reason.length === 0
                ? "Required"
                : !trimmed
                  ? "Cannot be only whitespace"
                  : `${reason.length} / ${MAX_REASON_LENGTH}`}
            </div>
          </>
        )}

        <div
          style={{
            display: "flex",
            gap: "var(--spacing-md)",
            justifyContent: "flex-end",
            marginTop: "var(--spacing-md)",
          }}
        >
          <button className="btn" onClick={onCancel}>
            Cancel
          </button>
          <button
            className="btn btn-primary"
            onClick={handleConfirm}
            disabled={!canConfirm}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
