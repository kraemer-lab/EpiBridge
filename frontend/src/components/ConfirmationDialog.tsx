"use client";

interface ConfirmationDialogProps {
  title: string;
  message: string;
  confirmLabel: string;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmationDialog({
  title,
  message,
  confirmLabel,
  onConfirm,
  onCancel,
}: ConfirmationDialogProps) {
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

        <div
          style={{
            display: "flex",
            gap: "var(--spacing-md)",
            justifyContent: "flex-end",
          }}
        >
          <button className="btn" onClick={onCancel}>
            Cancel
          </button>
          <button
            className="btn btn-primary"
            onClick={onConfirm}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
