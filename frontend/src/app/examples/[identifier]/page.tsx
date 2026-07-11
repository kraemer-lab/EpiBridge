"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { CodeBlock } from "@/components/CodeBlock";
import { Markdown } from "@/components/Markdown";
import { PublicationTabs, PublicationTab } from "@/components/PublicationTabs";
import {
  ExampleAnalysis,
  getExampleAnalysis,
  getExampleAnalysisArtefacts,
  getExampleAnalysisArtefactUrl,
  getExampleAnalysisArtefactContent,
} from "@/lib/api";

const CODE_EXTENSIONS = new Set([".py", ".r", ".sh", ".js", ".ipynb"]);
const MARKDOWN_FILES = new Set(["README.md"]);

function isCodeFile(name: string): boolean {
  const ext = name.includes(".") ? "." + name.split(".").pop()?.toLowerCase() : "";
  return CODE_EXTENSIONS.has(ext);
}

function stripFirstHeading(md: string): string {
  return md.replace(/^#{1,3}\s+.*\n?/, "").trim();
}

export default function ExampleDetailPage() {
  const params = useParams();
  const identifier = params.identifier as string;

  const [example, setExample] = useState<ExampleAnalysis | null>(null);
  const [artefacts, setArtefacts] = useState<string[] | null>(null);
  const [readmeMd, setReadmeMd] = useState<string | null>(null);
  const [codeFiles, setCodeFiles] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [exData, artefactData] = await Promise.all([
        getExampleAnalysis(identifier),
        getExampleAnalysisArtefacts(identifier),
      ]);
      setExample(exData);
      setArtefacts(artefactData.artefacts);

      const files = artefactData.artefacts;
      const pending: Promise<void>[] = [];

      if (files.includes("README.md")) {
        pending.push(
          getExampleAnalysisArtefactContent(identifier, "README.md").then(setReadmeMd),
        );
      }

      for (const file of files) {
        if (isCodeFile(file)) {
          pending.push(
            getExampleAnalysisArtefactContent(identifier, file).then(
              (content) => setCodeFiles((prev) => ({ ...prev, [file]: content })),
            ),
          );
        }
      }

      await Promise.all(pending);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load example analysis");
    }
  }, [identifier]);

  useEffect(() => {
    load();
  }, [load]);

  const remainingArtefacts = useMemo(
    () =>
      artefacts
        ? Array.from(new Set(artefacts)).sort().filter(
            (f) => f !== "manifest.yaml" && !MARKDOWN_FILES.has(f) && !isCodeFile(f),
          )
        : [],
    [artefacts],
  );

  const tabs = useMemo<PublicationTab[]>(() => {
    if (!example) return [];
    const result: PublicationTab[] = [];

    result.push({
      id: "overview",
      label: "Overview",
      content: (
        <div>
          <p className="overview-description" style={{ lineHeight: 1.6, marginBottom: "var(--spacing-md)" }}>
            {example.description || "No description provided."}
          </p>

          <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-sm)" }}>
            {example.execution_environment_identifier && (
              <div>
                <strong>Execution Environment: </strong>
                <Link
                  href={`/environments/${example.execution_environment_identifier}`}
                  style={{ color: "var(--color-primary)", textDecoration: "none" }}
                >
                  {example.execution_environment_identifier}
                </Link>
              </div>
            )}

            {example.data_resource_identifiers.length > 0 && (
              <div>
                <strong>Data Resources: </strong>
                {example.data_resource_identifiers.map((rid) => (
                  <Link
                    key={rid}
                    href={`/resources/${rid}`}
                    style={{ color: "var(--color-primary)", textDecoration: "none", marginRight: "var(--spacing-sm)" }}
                  >
                    {rid}
                  </Link>
                ))}
              </div>
            )}

            {example.entrypoint && (
              <div>
                <strong>Entrypoint: </strong>
                <code>{example.entrypoint}</code>
              </div>
            )}

            {example.expected_outputs.length > 0 && (
              <div>
                <strong>Expected Outputs: </strong>
                {example.expected_outputs.join(", ")}
              </div>
            )}
          </div>
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

    const codeEntries = Object.entries(codeFiles);
    if (codeEntries.length > 0) {
      result.push({
        id: "source-code",
        label: "Source Code",
        content: (
          <div>
            {codeEntries.map(([filename, content]) => (
              <div key={filename} style={{ marginBottom: "var(--spacing-lg)" }}>
                <h3 style={{ fontSize: "0.85rem", fontWeight: 600, color: "var(--color-text-secondary)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "var(--spacing-sm)" }}>
                  {filename}
                </h3>
                <CodeBlock code={content} language={filename.split(".").pop() || "python"} />
              </div>
            ))}
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
                    href={getExampleAnalysisArtefactUrl(identifier, file)}
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
  }, [example, readmeMd, codeFiles, remainingArtefacts, identifier]);

  if (error) {
    return (
      <>
        <Link href="/examples" style={{ color: "var(--color-primary)", textDecoration: "none", fontSize: "0.9rem" }}>
          ← Examples
        </Link>
        <div className="card empty-state" style={{ marginTop: "var(--spacing-lg)" }}>
          {error}
        </div>
      </>
    );
  }

  if (!example) {
    return <div className="card empty-state">Loading…</div>;
  }

  return (
    <>
      <Link href="/examples" style={{ color: "var(--color-primary)", textDecoration: "none", fontSize: "0.9rem" }}>
        ← Examples
      </Link>

      <div className="publication-header">
        <h2>{example.name}</h2>
        <dl className="publication-meta">
          <div>
            <dt>Identifier</dt>
            <dd>{example.identifier}</dd>
          </div>
          {example.execution_environment_identifier && (
            <div>
              <dt>Environment</dt>
              <dd>
                <Link
                  href={`/environments/${example.execution_environment_identifier}`}
                  style={{ color: "var(--color-primary)", textDecoration: "none" }}
                >
                  {example.execution_environment_identifier}
                </Link>
              </dd>
            </div>
          )}
          {example.entrypoint && (
            <div>
              <dt>Entrypoint</dt>
              <dd><code>{example.entrypoint}</code></dd>
            </div>
          )}
        </dl>
      </div>

      <PublicationTabs tabs={tabs} defaultTab="overview" />
    </>
  );
}
