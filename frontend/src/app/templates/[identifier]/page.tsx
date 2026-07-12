"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { Markdown } from "@/components/Markdown";
import { PublicationTabs, PublicationTab } from "@/components/PublicationTabs";
import {
  Template,
  getTemplate,
  getTemplateArtefacts,
  getTemplateArtefactUrl,
  getTemplateArtefactContent,
} from "@/lib/api";

const MARKDOWN_FILES = new Set(["README.md"]);
const TEMPLATE_ZIP = "template.zip";

function stripFirstHeading(md: string): string {
  return md.replace(/^#{1,3}\s+.*\n?/, "").trim();
}

export default function TemplateDetailPage() {
  const params = useParams();
  const identifier = params.identifier as string;

  const [tpl, setTpl] = useState<Template | null>(null);
  const [artefacts, setArtefacts] = useState<string[] | null>(null);
  const [readmeMd, setReadmeMd] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [tplData, artefactData] = await Promise.all([
        getTemplate(identifier),
        getTemplateArtefacts(identifier),
      ]);
      setTpl(tplData);
      setArtefacts(artefactData.artefacts);

      const files = artefactData.artefacts;
      const pending: Promise<void>[] = [];

      if (files.includes("README.md")) {
        pending.push(
          getTemplateArtefactContent(identifier, "README.md").then(setReadmeMd),
        );
      }

      await Promise.all(pending);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load template");
    }
  }, [identifier]);

  useEffect(() => {
    load();
  }, [load]);

  const remainingArtefacts = useMemo(
    () =>
      artefacts
        ? Array.from(new Set(artefacts)).sort().filter(
            (f) => f !== "manifest.yaml" && !MARKDOWN_FILES.has(f) && f !== TEMPLATE_ZIP,
          )
        : [],
    [artefacts],
  );

  const hasTemplateZip = artefacts?.includes(TEMPLATE_ZIP) ?? false;

  const tabs = useMemo<PublicationTab[]>(() => {
    if (!tpl) return [];
    const result: PublicationTab[] = [];

    result.push({
      id: "overview",
      label: "Overview",
      content: (
        <div>
          <p className="overview-description" style={{ lineHeight: 1.6, marginBottom: "var(--spacing-lg)" }}>
            {tpl.description || "No description provided."}
          </p>

          {tpl.execution_environment_identifier && (
            <div style={{ marginBottom: "var(--spacing-md)" }}>
              <strong>Execution Environment: </strong>
              <Link
                href={`/environments/${tpl.execution_environment_identifier}`}
                style={{ color: "var(--color-primary)", textDecoration: "none" }}
              >
                {tpl.execution_environment_identifier}
              </Link>
            </div>
          )}

          {hasTemplateZip && (
            <div style={{ marginTop: "var(--spacing-lg)" }}>
              <a
                href={getTemplateArtefactUrl(identifier, TEMPLATE_ZIP)}
                className="btn btn-primary"
                download
              >
                Download template.zip
              </a>
              <p style={{ color: "var(--color-text-secondary)", fontSize: "0.85rem", marginTop: "var(--spacing-sm)" }}>
                Extract, customise with your analysis code, zip, and upload as a new Analysis Bundle.
              </p>
            </div>
          )}
        </div>
      ),
    });

    if (readmeMd) {
      result.push({
        id: "documentation",
        label: "Documentation",
        content: <Markdown content={stripFirstHeading(readmeMd)} />,
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
                    href={getTemplateArtefactUrl(identifier, file)}
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

    return result;
  }, [tpl, readmeMd, remainingArtefacts, identifier, hasTemplateZip]);

  if (error) {
    return (
      <>
        <Link href="/templates" style={{ color: "var(--color-primary)", textDecoration: "none", fontSize: "0.9rem" }}>
          ← Templates
        </Link>
        <div className="card empty-state" style={{ marginTop: "var(--spacing-lg)" }}>
          {error}
        </div>
      </>
    );
  }

  if (!tpl) {
    return <div className="card empty-state">Loading…</div>;
  }

  return (
    <>
      <Link href="/templates" style={{ color: "var(--color-primary)", textDecoration: "none", fontSize: "0.9rem" }}>
        ← Templates
      </Link>

      <div className="publication-header">
        <h2>{tpl.name}</h2>
        <dl className="publication-meta">
          <div>
            <dt>Identifier</dt>
            <dd>{tpl.identifier}</dd>
          </div>
          {tpl.execution_environment_identifier && (
            <div>
              <dt>Environment</dt>
              <dd>
                <Link
                  href={`/environments/${tpl.execution_environment_identifier}`}
                  style={{ color: "var(--color-primary)", textDecoration: "none" }}
                >
                  {tpl.execution_environment_identifier}
                </Link>
              </dd>
            </div>
          )}
          <div>
            <dt>Download</dt>
            <dd>
              {hasTemplateZip ? (
                <a
                  href={getTemplateArtefactUrl(identifier, TEMPLATE_ZIP)}
                  style={{ color: "var(--color-primary)", textDecoration: "none" }}
                  download
                >
                  template.zip
                </a>
              ) : "—"}
            </dd>
          </div>
        </dl>
      </div>

      <PublicationTabs tabs={tabs} defaultTab="overview" />
    </>
  );
}
