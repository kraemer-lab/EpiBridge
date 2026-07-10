"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/AuthContext";
import { getPlatformTermsCurrent, acceptPlatformTerms } from "@/lib/api";
import { Markdown } from "@/components/Markdown";
import type { TermsOfService } from "@/lib/api";

export default function TermsPage() {
  const router = useRouter();
  const { user, loading, logout } = useAuth();
  const [terms, setTerms] = useState<TermsOfService | null>(null);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [accepting, setAccepting] = useState(false);

  useEffect(() => {
    if (loading) return;
    if (!user) {
      router.push("/login");
      return;
    }
    if (!user.needs_platform_terms_acceptance) {
      router.push("/");
      return;
    }
    getPlatformTermsCurrent()
      .then(setTerms)
      .catch(() => setFetchError("Failed to load terms of service."));
  }, [user, loading, router]);

  const handleAccept = async () => {
    setAccepting(true);
    try {
      await acceptPlatformTerms();
      router.push("/");
    } catch {
      setFetchError("Failed to accept terms. Please try again.");
      setAccepting(false);
    }
  };

  const handleDecline = () => {
    logout();
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "var(--color-surface)",
      }}
    >
      <div
        className="card"
        style={{
          maxWidth: "720px",
          width: "100%",
          margin: "var(--spacing-xl)",
          padding: "var(--spacing-xl)",
        }}
      >
        <h1 style={{ fontSize: "1.3rem", fontWeight: 600, marginBottom: "var(--spacing-lg)" }}>
          Terms of Service
        </h1>

        {fetchError && (
          <div style={{ color: "#d32f2f", marginBottom: "var(--spacing-md)" }}>
            {fetchError}
          </div>
        )}

        {terms && (
          <div
            style={{
              maxHeight: "400px",
              overflowY: "auto",
              marginBottom: "var(--spacing-lg)",
              padding: "var(--spacing-md)",
              border: "1px solid var(--color-border)",
              borderRadius: "var(--radius-md)",
              background: "#fff",
              fontSize: "0.9rem",
              lineHeight: 1.6,
            }}
          >
            <Markdown content={terms.content} />
          </div>
        )}

        {!terms && !fetchError && (
          <div className="empty-state" style={{ marginBottom: "var(--spacing-lg)" }}>
            Loading terms...
          </div>
        )}

        <div style={{ display: "flex", gap: "var(--spacing-md)", justifyContent: "flex-end" }}>
          <button
            className="btn"
            onClick={handleDecline}
            disabled={accepting}
          >
            Decline
          </button>
          <button
            className="btn btn-primary"
            onClick={handleAccept}
            disabled={accepting}
          >
            {accepting ? "Accepting..." : "Accept"}
          </button>
        </div>
      </div>
    </div>
  );
}
