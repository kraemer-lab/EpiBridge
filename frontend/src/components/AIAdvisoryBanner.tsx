export default function AIAdvisoryBanner() {
  return (
    <div
      style={{
        padding: "8px 12px",
        marginBottom: "var(--spacing-md)",
        background: "#fff8e1",
        border: "1px solid #ffe082",
        borderRadius: "4px",
        fontSize: "0.8rem",
        color: "#6d4c00",
        lineHeight: 1.5,
      }}
    >
      <strong>AI Advisory</strong>
      <br />
      This assessment is provided to assist institutional review.
      AI-generated findings may be incomplete or incorrect and must
      not replace human judgement. Moderators remain responsible for
      all governance decisions.
    </div>
  );
}
