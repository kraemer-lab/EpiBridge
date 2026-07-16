"use client";

import AIAdvisoryBanner from "./AIAdvisoryBanner";

interface AIReview {
  id: string;
  status: string;
  summary: string | null;
  assessment: string | null;
  assessment_confidence: string | null;
  reviewer_notes: string | null;
}

interface Props {
  review: AIReview | null;
  loading?: boolean;
  onRefresh?: () => void;
  refreshing?: boolean;
  title?: string;
}

export type { AIReview };

export default function AIReviewCard({
  review,
  loading,
  onRefresh,
  refreshing,
  title = "AI Assessment",
}: Props) {
  if (loading) {
    return (
      <div className="card" style={{ marginTop: "var(--spacing-lg)" }}>
        <h3 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "var(--spacing-md)" }}>
          {title}
        </h3>
        <div style={{ color: "var(--color-text-secondary)" }}>Checking AI availability...</div>
      </div>
    );
  }

  if (!review) {
    return (
      <div className="card" style={{ marginTop: "var(--spacing-lg)" }}>
        <h3 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "var(--spacing-md)" }}>
          {title}
        </h3>
        <div style={{ marginBottom: "var(--spacing-md)" }}>
          <div style={{ color: "var(--color-text-secondary)" }}>No AI assessment available.</div>
        </div>
        {onRefresh && (
          <button className="btn" onClick={onRefresh} disabled={refreshing}>
            {refreshing ? "Processing..." : "Generate AI Assessment"}
          </button>
        )}
      </div>
    );
  }

  if (review.status === "pending") {
    return (
      <div className="card" style={{ marginTop: "var(--spacing-lg)" }}>
        <h3 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "var(--spacing-md)" }}>
          {title}
        </h3>
        <div style={{ marginBottom: "var(--spacing-md)" }}>
          <div>Status: Pending</div>
        </div>
      </div>
    );
  }

  if (review.status === "unavailable" || review.status === "failed") {
    return (
      <div className="card" style={{ marginTop: "var(--spacing-lg)" }}>
        <h3 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "var(--spacing-md)" }}>
          {title}
        </h3>
        <div style={{ marginBottom: "var(--spacing-md)" }}>
          <div>Status: Unavailable</div>
        </div>
        {onRefresh && (
          <button className="btn" onClick={onRefresh} disabled={refreshing}>
            {refreshing ? "Processing..." : "Generate AI Assessment"}
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="card" style={{ marginTop: "var(--spacing-lg)" }}>
      <h3 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "var(--spacing-md)" }}>
        {title}
      </h3>

      <AIAdvisoryBanner />

      <div style={{ marginBottom: "var(--spacing-md)" }}>
        <div
          style={{
            fontSize: "0.8rem",
            color: "var(--color-text-secondary)",
            marginBottom: "var(--spacing-xs)",
            fontWeight: 600,
            textTransform: "uppercase",
            letterSpacing: "0.05em",
          }}
        >
          Status
        </div>
        <div>Completed</div>
      </div>

      {review.summary && (
        <div style={{ marginBottom: "var(--spacing-md)" }}>
          <div
            style={{
              fontSize: "0.8rem",
              color: "var(--color-text-secondary)",
              marginBottom: "var(--spacing-xs)",
              fontWeight: 600,
              textTransform: "uppercase",
              letterSpacing: "0.05em",
            }}
          >
            Summary
          </div>
          <div style={{ lineHeight: 1.6, whiteSpace: "pre-wrap" }}>{review.summary}</div>
        </div>
      )}

      {review.reviewer_notes && (
        <div style={{ marginBottom: "var(--spacing-md)" }}>
          <div
            style={{
              fontSize: "0.8rem",
              color: "var(--color-text-secondary)",
              marginBottom: "var(--spacing-xs)",
              fontWeight: 600,
              textTransform: "uppercase",
              letterSpacing: "0.05em",
            }}
          >
            Findings
          </div>
          <div style={{ lineHeight: 1.6, whiteSpace: "pre-wrap" }}>
            {review.reviewer_notes}
          </div>
        </div>
      )}

      {review.assessment_confidence && (
        <div
          style={{
            fontSize: "0.8rem",
            color: "var(--color-text-secondary)",
            marginTop: "var(--spacing-sm)",
          }}
        >
          Confidence: {review.assessment_confidence}
        </div>
      )}

      {onRefresh && (
        <button className="btn" onClick={onRefresh} disabled={refreshing} style={{ marginTop: "var(--spacing-md)" }}>
          {refreshing ? "Processing..." : "Refresh AI Assessment"}
        </button>
      )}
    </div>
  );
}
