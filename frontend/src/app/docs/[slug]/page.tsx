"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { Markdown } from "@/components/Markdown";

const docTitles: Record<string, string> = {
  "getting-started": "Getting Started",
  "bundle-structure": "Bundle Structure",
  "local-development": "Local Development",
  "submission-workflow": "Submission Workflow",
  "governance-overview": "Governance Overview",
};

export default function DocPage() {
  const params = useParams();
  const slug = params.slug as string;

  const [content, setContent] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`/docs/${slug}.md`)
      .then((res) => {
        if (!res.ok) throw new Error("Document not found");
        return res.text();
      })
      .then(setContent)
      .catch(() => setError("Document not found"));
  }, [slug]);

  const title = docTitles[slug] || slug.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

  if (error) {
    return (
      <>
        <Link href="/docs" style={{ color: "var(--color-primary)", textDecoration: "none", fontSize: "0.9rem" }}>
          ← Documentation
        </Link>
        <div className="card empty-state" style={{ marginTop: "var(--spacing-lg)" }}>
          {error}
        </div>
      </>
    );
  }

  if (!content) {
    return (
      <>
        <Link href="/docs" style={{ color: "var(--color-primary)", textDecoration: "none", fontSize: "0.9rem" }}>
          ← Documentation
        </Link>
        <div className="card empty-state" style={{ marginTop: "var(--spacing-lg)" }}>
          Loading…
        </div>
      </>
    );
  }

  return (
    <>
      <Link href="/docs" style={{ color: "var(--color-primary)", textDecoration: "none", fontSize: "0.9rem" }}>
        ← Documentation
      </Link>

      <div className="publication-header">
        <h2>{title}</h2>
      </div>

      <div className="card">
        <Markdown content={content} />
      </div>
    </>
  );
}
