"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { Markdown } from "@/components/Markdown";
import { CodeBlock } from "@/components/CodeBlock";
import { PublicationTabs, PublicationTab } from "@/components/PublicationTabs";
import {
  ExecutionEnvironment,
  ExampleAnalysis,
  getExecutionEnvironment,
  getEnvironmentArtefacts,
  getEnvironmentArtefactUrl,
  getEnvironmentArtefactContent,
  getExampleAnalyses,
} from "@/lib/api";

const MARKDOWN_FILES = new Set(["PACKAGES.md", "LOCAL_DEV.md", "EXECUTION_CONTRACT.md"]);
const CODE_FILES = new Set(["Dockerfile", "requirements.txt"]);

const CODE_META: Record<string, { label: string; lang: string }> = {
  Dockerfile: { label: "Dockerfile", lang: "Dockerfile" },
  "requirements.txt": { label: "requirements.txt", lang: "txt" },
};

function stripFirstHeading(md: string): string {
  return md.replace(/^#{1,3}\s+.*\n?/, "").trim();
}

function purposeStatement(env: ExecutionEnvironment): string {
  if (env.identifier === "conda") {
    return `The ${env.name} provides flexible package management for analyses that require specialised dependencies. Researchers define their own environment using conda's environment.yml format.`;
  }
  return `The ${env.name} is the institution's standard environment for computational epidemiology analyses. Develop and test against this environment to maximise reproducibility between local development and institutional execution.`;
}

export default function EnvironmentDetailPage() {
  const params = useParams();
  const identifier = params.identifier as string;

  const [env, setEnv] = useState<ExecutionEnvironment | null>(null);
  const [artefacts, setArtefacts] = useState<string[] | null>(null);
  const [localDevMd, setLocalDevMd] = useState<string | null>(null);
  const [contractMd, setContractMd] = useState<string | null>(null);
  const [packagesMd, setPackagesMd] = useState<string | null>(null);
  const [dockerfile, setDockerfile] = useState<string | null>(null);
  const [requirementsTxt, setRequirementsTxt] = useState<string | null>(null);
  const [relatedExamples, setRelatedExamples] = useState<ExampleAnalysis[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [envData, artefactData] = await Promise.all([
        getExecutionEnvironment(identifier),
        getEnvironmentArtefacts(identifier),
      ]);
      setEnv(envData);
      setArtefacts(artefactData.artefacts);

      const files = artefactData.artefacts;
      const pending: Promise<void>[] = [];

      if (files.includes("LOCAL_DEV.md")) {
        pending.push(
          getEnvironmentArtefactContent(identifier, "LOCAL_DEV.md").then(setLocalDevMd),
        );
      }
      if (files.includes("EXECUTION_CONTRACT.md")) {
        pending.push(
          getEnvironmentArtefactContent(identifier, "EXECUTION_CONTRACT.md").then(setContractMd),
        );
      }
      if (files.includes("PACKAGES.md")) {
        pending.push(
          getEnvironmentArtefactContent(identifier, "PACKAGES.md").then(setPackagesMd),
        );
      }
      if (files.includes("Dockerfile")) {
        pending.push(
          getEnvironmentArtefactContent(identifier, "Dockerfile").then(setDockerfile),
        );
      }
      if (files.includes("requirements.txt")) {
        pending.push(
          getEnvironmentArtefactContent(identifier, "requirements.txt").then(setRequirementsTxt),
        );
      }

      await Promise.all(pending);

      try {
        const examples = await getExampleAnalyses({ environment: identifier });
        setRelatedExamples(examples);
      } catch {
        setRelatedExamples([]);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load environment");
    }
  }, [identifier]);

  useEffect(() => {
    load();
  }, [load]);

  const remainingArtefacts = useMemo(
    () =>
      artefacts
        ? Array.from(new Set(artefacts)).sort().filter(
            (f) => f !== "manifest.yaml" && !MARKDOWN_FILES.has(f) && !CODE_FILES.has(f),
          )
        : [],
    [artefacts],
  );

  const tabs = useMemo<PublicationTab[]>(() => {
    if (!env) return [];
    const result: PublicationTab[] = [];

    result.push({
      id: "overview",
      label: "Overview",
      content: (
        <div>
          <p className="overview-purpose">{purposeStatement(env)}</p>
          <p className="overview-description">{env.description || "No description provided."}</p>
        </div>
      ),
    });

    if (localDevMd) {
      result.push({
        id: "local-development",
        label: "Local Development",
        content: <Markdown content={stripFirstHeading(localDevMd)} />,
      });
    }

    if (contractMd) {
      result.push({
        id: "execution-contract",
        label: "Execution Contract",
        content: <Markdown content={stripFirstHeading(contractMd)} />,
      });
    }

    if (packagesMd) {
      result.push({
        id: "software",
        label: "Software",
        content: <Markdown content={stripFirstHeading(packagesMd)} />,
      });
    }

    if (dockerfile || requirementsTxt || remainingArtefacts.length > 0) {
      result.push({
        id: "technical-reference",
        label: "Technical Reference",
        content: (
          <div>
            {dockerfile && (
              <div style={{ marginBottom: requirementsTxt || remainingArtefacts.length > 0 ? "var(--spacing-lg)" : 0 }}>
                <h3 style={{ fontSize: "0.85rem", fontWeight: 600, color: "var(--color-text-secondary)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "var(--spacing-sm)" }}>
                  {CODE_META.Dockerfile?.label || "Dockerfile"}
                </h3>
                <CodeBlock code={dockerfile} language={CODE_META.Dockerfile?.lang} />
              </div>
            )}
            {requirementsTxt && (
              <div style={{ marginBottom: remainingArtefacts.length > 0 ? "var(--spacing-lg)" : 0 }}>
                <h3 style={{ fontSize: "0.85rem", fontWeight: 600, color: "var(--color-text-secondary)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "var(--spacing-sm)" }}>
                  {CODE_META["requirements.txt"]?.label || "requirements.txt"}
                </h3>
                <CodeBlock code={requirementsTxt} language={CODE_META["requirements.txt"]?.lang} />
              </div>
            )}
            {remainingArtefacts.length > 0 && (
              <div>
                <h3 style={{ fontSize: "0.85rem", fontWeight: 600, color: "var(--color-text-secondary)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "var(--spacing-sm)" }}>
                  Published Artefacts
                </h3>
                <ul style={{ margin: 0, paddingLeft: "var(--spacing-lg)" }}>
                  {remainingArtefacts.map((file) => (
                    <li key={file} style={{ marginBottom: "var(--spacing-xs)" }}>
                      <a
                        href={getEnvironmentArtefactUrl(identifier, file)}
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
            )}
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
              Example analyses compatible with this execution environment.
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
  }, [env, localDevMd, contractMd, packagesMd, dockerfile, requirementsTxt, remainingArtefacts, identifier, relatedExamples]);

  if (error) {
    return (
      <>
        <Link href="/environments" style={{ color: "var(--color-primary)", textDecoration: "none", fontSize: "0.9rem" }}>
          ← Environments
        </Link>
        <div className="card empty-state" style={{ marginTop: "var(--spacing-lg)" }}>
          {error}
        </div>
      </>
    );
  }

  if (!env) {
    return <div className="card empty-state">Loading…</div>;
  }

  return (
    <>
      <Link href="/environments" style={{ color: "var(--color-primary)", textDecoration: "none", fontSize: "0.9rem" }}>
        ← Environments
      </Link>

      <div className="publication-header">
        <h2>{env.display_name}</h2>
        <dl className="publication-meta">
          <div>
            <dt>Identifier</dt>
            <dd>{env.identifier}</dd>
          </div>
          <div>
            <dt>Runtime</dt>
            <dd>{env.runtime}</dd>
          </div>
          <div>
            <dt>Image</dt>
            <dd>{env.image_reference}</dd>
          </div>
        </dl>
      </div>

      <PublicationTabs tabs={tabs} defaultTab="overview" />
    </>
  );
}
