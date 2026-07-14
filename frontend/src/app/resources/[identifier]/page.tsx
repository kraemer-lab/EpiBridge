"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { Markdown } from "@/components/Markdown";
import { PublicationTabs, PublicationTab } from "@/components/PublicationTabs";
import {
  DataResource,
  ExampleAnalysis,
  getDataResource,
  getResourceArtefacts,
  getResourceArtefactUrl,
  getResourceArtefactContent,
  getTermsStatus,
  acceptResourceTerms,
  getExampleAnalyses,
} from "@/lib/api";
import { TermsDialog } from "@/components/TermsDialog";

const PROVIDER_LABELS: Record<string, string> = {
  csv: "CSV Dataset",
  duckdb: "DuckDB Database",
  postgres: "PostgreSQL Database",
  excel: "Excel Spreadsheet",
  parquet: "Parquet Dataset",
};

const MARKDOWN_FILES = new Set(["SCHEMA.md", "DOCUMENTATION.md"]);

function stripFirstHeading(md: string): string {
  return md.replace(/^#{1,3}\s+.*\n?/, "").trim();
}

function isRepresentativeFile(name: string): boolean {
  return name.startsWith("representative/")
    || name.startsWith("sample/");
}

export default function ResourceDetailPage() {
  const params = useParams();
  const identifier = params.identifier as string;

  const [resource, setResource] = useState<DataResource | null>(null);
  const [artefacts, setArtefacts] = useState<string[] | null>(null);
  const [schemaMd, setSchemaMd] = useState<string | null>(null);
  const [docMd, setDocMd] = useState<string | null>(null);
  const [relatedExamples, setRelatedExamples] = useState<ExampleAnalysis[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [termsStatus, setTermsStatus] = useState<{ resource_id: string; version: string; title: string; accepted: boolean } | null>(null);
  const [showTerms, setShowTerms] = useState(false);

  const load = useCallback(async () => {
    try {
      const [resData, artefactData] = await Promise.all([
        getDataResource(identifier),
        getResourceArtefacts(identifier),
      ]);
      setResource(resData);
      setArtefacts(artefactData.artefacts);

      const files = artefactData.artefacts;
      const pending: Promise<void>[] = [];

      if (files.includes("SCHEMA.md")) {
        pending.push(
          getResourceArtefactContent(identifier, "SCHEMA.md").then(setSchemaMd),
        );
      }
      if (files.includes("DOCUMENTATION.md")) {
        pending.push(
          getResourceArtefactContent(identifier, "DOCUMENTATION.md").then(setDocMd),
        );
      }

      await Promise.all(pending);

      try {
        const examples = await getExampleAnalyses({ resource: identifier });
        setRelatedExamples(examples);
      } catch {
        setRelatedExamples([]);
      }

      try {
        const status = await getTermsStatus();
        const match = status.dataset_terms.find(
          (t: { resource_id: string }) => t.resource_id === resData.id,
        );
        if (match) {
          setTermsStatus(match);
        }
      } catch {
        // Terms status not available
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load resource");
    }
  }, [identifier]);

  useEffect(() => {
    load();
  }, [load]);

  const dataFiles = useMemo(
    () => (artefacts ?? []).filter((f) => f.startsWith("data/")),
    [artefacts],
  );

  const representativeFiles = useMemo(
    () => (artefacts ?? []).filter(isRepresentativeFile),
    [artefacts],
  );

  const remainingArtefacts = useMemo(
    () =>
      artefacts
        ? Array.from(new Set(artefacts)).sort().filter(
            (f) => f !== "manifest.yaml"
              && !MARKDOWN_FILES.has(f)
              && !f.startsWith("data/")
              && !isRepresentativeFile(f),
          )
        : [],
    [artefacts],
  );

  const handleAcceptTerms = async () => {
    if (!resource) return;
    try {
      await acceptResourceTerms(resource.id);
      setTermsStatus((prev) => prev ? { ...prev, accepted: true } : null);
      setShowTerms(false);
    } catch {
      // Acceptance failed
    }
  };

  const tabs = useMemo<PublicationTab[]>(() => {
    if (!resource) return [];
    const result: PublicationTab[] = [];

    result.push({
      id: "overview",
      label: "Overview",
      content: (
        <div>
          <p className="overview-description">{resource.description || "No description provided."}</p>

          {dataFiles.length > 0 && (
            <div
              className="card"
              style={{
                marginTop: "var(--spacing-md)",
                padding: "var(--spacing-sm) var(--spacing-md)",
              }}
            >
              <h4
                style={{
                  fontSize: "0.85rem",
                  fontWeight: 600,
                  textTransform: "uppercase",
                  letterSpacing: "0.05em",
                  marginBottom: "var(--spacing-xs)",
                }}
              >
                Runtime Access
              </h4>
              <p
                style={{
                  fontSize: "0.85rem",
                  color: "var(--color-text-secondary)",
                  lineHeight: 1.5,
                }}
              >
                Data is mounted at <code>/data/{resource.alias}/</code> inside
                execution containers. See the Documentation tab and
                the resource description for details on available files.
              </p>
            </div>
          )}

          {termsStatus && (
            <div
              className="card"
              style={{
                marginTop: "var(--spacing-md)",
                padding: "var(--spacing-sm) var(--spacing-md)",
                fontSize: "0.9rem",
              }}
            >
              {termsStatus.accepted ? (
                <span>
                  <strong>Dataset Terms:</strong> You have accepted{" "}
                  {termsStatus.title || `version ${termsStatus.version}`}.
                </span>
              ) : (
                <span>
                  <strong>Dataset Terms:</strong>{" "}
                  {termsStatus.title || `Version ${termsStatus.version}`} —{" "}
                  <button
                    className="btn"
                    style={{ fontSize: "0.85rem", padding: "2px 10px" }}
                    onClick={() => setShowTerms(true)}
                  >
                    Accept
                  </button>
                </span>
              )}
            </div>
          )}
        </div>
      ),
    });

    if (schemaMd) {
      result.push({
        id: "schema",
        label: "Schema",
        content: <Markdown content={stripFirstHeading(schemaMd)} />,
      });
    }

    if (docMd) {
      result.push({
        id: "documentation",
        label: "Documentation",
        content: <Markdown content={stripFirstHeading(docMd)} />,
      });
    }

    if (representativeFiles.length > 0) {
      result.push({
        id: "representative",
        label: "Representative Dataset",
        content: (
          <div>
            <p style={{ marginBottom: "var(--spacing-md)", color: "var(--color-text-secondary)", lineHeight: 1.6 }}>
              A sample dataset for local development and bundle testing.
              Download to use in your analysis workspace.
            </p>
            <ul style={{ margin: 0, paddingLeft: "0", listStyle: "none" }}>
              {representativeFiles.map((file) => (
                <li key={file} style={{ marginBottom: "var(--spacing-xs)" }}>
                  <a
                    href={getResourceArtefactUrl(identifier, file)}
                    className="btn btn-primary"
                    download
                  >
                    Download {file.replace("representative/", "").replace("sample/", "")}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        ),
      });
    }

    if (remainingArtefacts.length > 0) {
      result.push({
        id: "technical-reference",
        label: "Technical Reference",
        content: (
          <div>
            <h3 style={{ fontSize: "0.85rem", fontWeight: 600, color: "var(--color-text-secondary)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "var(--spacing-sm)" }}>
              Published Artefacts
            </h3>
            <ul style={{ margin: 0, paddingLeft: "var(--spacing-lg)" }}>
              {remainingArtefacts.map((file) => (
                <li key={file} style={{ marginBottom: "var(--spacing-xs)" }}>
                  <a
                    href={getResourceArtefactUrl(identifier, file)}
                    style={{ color: "var(--color-primary)", textDecoration: "none" }}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    {file}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        ),
      });
    }

    if (relatedExamples.length > 0) {
      result.push({
        id: "example-analyses",
        label: "Example Analyses",
        content: (
          <div>
            <p style={{ marginBottom: "var(--spacing-md)", color: "var(--color-text-secondary)", lineHeight: 1.6 }}>
              Example analyses using this data resource.
            </p>
            <ul style={{ margin: 0, paddingLeft: "var(--spacing-lg)" }}>
              {relatedExamples.map((ex) => (
                <li key={ex.identifier} style={{ marginBottom: "var(--spacing-sm)" }}>
                  <Link
                    href={`/examples/${ex.identifier}`}
                    style={{ color: "var(--color-primary)", textDecoration: "none", fontWeight: 500 }}
                  >
                    {ex.name}
                  </Link>
                  <span style={{ color: "var(--color-text-secondary)", fontSize: "0.85rem", marginLeft: "var(--spacing-sm)" }}>
                    {ex.description}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        ),
      });
    }

    return result;
  }, [resource, schemaMd, docMd, dataFiles, representativeFiles, remainingArtefacts, identifier, termsStatus, relatedExamples]);

  if (error) {
    return (
      <>
        <Link href="/resources" style={{ color: "var(--color-primary)", textDecoration: "none", fontSize: "0.9rem" }}>
          ← Resources
        </Link>
        <div className="card empty-state" style={{ marginTop: "var(--spacing-lg)" }}>
          {error}
        </div>
      </>
    );
  }

  if (!resource) {
    return <div className="card empty-state">Loading…</div>;
  }

  return (
    <>
      <Link href="/resources" style={{ color: "var(--color-primary)", textDecoration: "none", fontSize: "0.9rem" }}>
        ← Resources
      </Link>

      <div className="publication-header">
        <h2>{resource.name}</h2>
        <dl className="publication-meta">
          <div>
            <dt>Identifier</dt>
            <dd>{resource.identifier}</dd>
          </div>
          <div>
            <dt>Mount Path</dt>
            <dd>
              <code>/data/{resource.alias}/</code>
            </dd>
          </div>
          <div>
            <dt>Type</dt>
            <dd>{PROVIDER_LABELS[resource.provider_type] || resource.provider_type}</dd>
          </div>
          <div>
            <dt>Version</dt>
            <dd>{resource.version}</dd>
          </div>
        </dl>
      </div>

      <PublicationTabs tabs={tabs} defaultTab="overview" />

      {showTerms && resource && termsStatus && (
        <TermsDialog
          resourceId={resource.id}
          resourceName={resource.name}
          onAccept={handleAcceptTerms}
          onCancel={() => setShowTerms(false)}
          requireAcceptance={false}
        />
      )}
    </>
  );
}
