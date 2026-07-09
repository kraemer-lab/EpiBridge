"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/AuthContext";
import {
  DataResource,
  ExecutionEnvironment,
  getProjectResources,
  uploadProjectBundle,
  getExecutionEnvironments,
} from "@/lib/api";

export default function CreateAnalysisPage() {
  const params = useParams();
  const router = useRouter();
  const { user } = useAuth();
  const projectId = params.id as string;

  const [resources, setResources] = useState<DataResource[]>([]);
  const [environments, setEnvironments] = useState<ExecutionEnvironment[]>([]);
  const [name, setName] = useState("");
  const [selectedEnvId, setSelectedEnvId] = useState("");
  const [version, setVersion] = useState("");
  const [description, setDescription] = useState("");
  const [entrypoint, setEntrypoint] = useState("");
  const [interpreter, setInterpreter] = useState("python");
  const [argumentsStr, setArgumentsStr] = useState("");
  const [selectedResources, setSelectedResources] = useState<string[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [buildStrategy, setBuildStrategy] = useState("institutional");
  const [saving, setSaving] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    getProjectResources(projectId)
      .then(setResources)
      .catch(() => setResources([]));
    getExecutionEnvironments()
      .then((envs) => {
        setEnvironments(envs);
        if (envs.length > 0) setSelectedEnvId(envs[0].id);
      })
      .catch(() => {});
  }, [projectId]);

  const toggleResource = (id: string) => {
    setSelectedResources((prev) =>
      prev.includes(id) ? prev.filter((r) => r !== id) : [...prev, id],
    );
  };

  const validate = (): boolean => {
    const errors: Record<string, string> = {};
    if (!name.trim()) errors.name = "Name is required";
    if (!version.trim()) errors.version = "Version is required";
    if (!entrypoint.trim()) errors.entrypoint = "Entrypoint is required";
    if (!selectedEnvId) errors.environment = "Execution environment is required";
    if (!file) errors.file = "Analysis bundle file is required";
    else if (!file.name.endsWith(".zip")) errors.file = "File must be a ZIP archive";
    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async () => {
    if (!validate()) return;

    const formData = new FormData();
    formData.append("file", file!);
    formData.append("name", name.trim());
    formData.append("execution_environment_id", selectedEnvId);
    formData.append("version", version.trim());
    formData.append("entrypoint", entrypoint.trim());
    formData.append("interpreter", interpreter);
    formData.append("arguments", argumentsStr.trim());
    formData.append("description", description.trim());
    formData.append("resource_identifiers", JSON.stringify(selectedResources));
    formData.append("build_strategy", buildStrategy);

    setSaving(true);
    try {
      await uploadProjectBundle(projectId, formData);
      router.push(`/projects/${projectId}/analysis`);
    } catch {
      setFieldErrors({ form: "Failed to upload analysis bundle." });
      setSaving(false);
    }
  };

  return (
    <div>
      <Link
        href={`/projects/${projectId}/analysis`}
        style={{ color: "var(--color-text-secondary)", fontSize: "0.85rem", textDecoration: "none" }}
      >
        &larr; Back to Analysis
      </Link>
      <h2 style={{ fontSize: "1.1rem", fontWeight: 600, marginTop: "var(--spacing-md)", marginBottom: "var(--spacing-lg)" }}>
        Create Analysis
      </h2>

      <div className="card" style={{ maxWidth: "640px" }}>
        {fieldErrors.form && (
          <div style={{ color: "#e65100", marginBottom: "var(--spacing-md)", fontSize: "0.9rem" }}>
            {fieldErrors.form}
          </div>
        )}

        <div style={{ marginBottom: "var(--spacing-md)" }}>
          <label htmlFor="analysis-name" style={{ display: "block", fontWeight: 600, marginBottom: "var(--spacing-xs)", fontSize: "0.9rem" }}>
            Name <span style={{ color: "#e65100" }}>*</span>
          </label>
          <input
            id="analysis-name"
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Analysis name"
            style={{
              width: "100%",
              padding: "var(--spacing-sm) var(--spacing-md)",
              border: `1px solid ${fieldErrors.name ? "#e65100" : "var(--color-border)"}`,
              borderRadius: "var(--radius-md)",
              fontSize: "0.9rem",
            }}
          />
          {fieldErrors.name && (
            <div style={{ color: "#e65100", fontSize: "0.8rem", marginTop: "var(--spacing-xs)" }}>
              {fieldErrors.name}
            </div>
          )}
        </div>

        <div style={{ marginBottom: "var(--spacing-md)" }}>
          <label htmlFor="analysis-env" style={{ display: "block", fontWeight: 600, marginBottom: "var(--spacing-xs)", fontSize: "0.9rem" }}>
            Execution Environment <span style={{ color: "#e65100" }}>*</span>
          </label>
          <select
            id="analysis-env"
            value={selectedEnvId}
            onChange={(e) => setSelectedEnvId(e.target.value)}
            style={{
              width: "100%",
              padding: "var(--spacing-sm) var(--spacing-md)",
              border: `1px solid ${fieldErrors.environment ? "#e65100" : "var(--color-border)"}`,
              borderRadius: "var(--radius-md)",
              fontSize: "0.9rem",
              background: "var(--color-bg)",
            }}
          >
            <option value="">Select environment...</option>
            {environments.map((env) => (
              <option key={env.id} value={env.id}>
                {env.display_name}
              </option>
            ))}
          </select>
          {selectedEnvId && (
            <Link
              href={`/environments/${environments.find((e) => e.id === selectedEnvId)?.identifier ?? ""}`}
              style={{ fontSize: "0.85rem", color: "var(--color-primary)", textDecoration: "none", marginTop: "var(--spacing-xs)", display: "inline-block" }}
              target="_blank"
              rel="noopener noreferrer"
            >
              View environment details →
            </Link>
          )}
          {fieldErrors.environment && (
            <div style={{ color: "#e65100", fontSize: "0.8rem", marginTop: "var(--spacing-xs)" }}>
              {fieldErrors.environment}
            </div>
          )}
        </div>

        <div style={{ marginBottom: "var(--spacing-md)" }}>
          <label htmlFor="analysis-version" style={{ display: "block", fontWeight: 600, marginBottom: "var(--spacing-xs)", fontSize: "0.9rem" }}>
            Version <span style={{ color: "#e65100" }}>*</span>
          </label>
          <input
            id="analysis-version"
            type="text"
            value={version}
            onChange={(e) => setVersion(e.target.value)}
            placeholder="1.0.0"
            style={{
              width: "100%",
              padding: "var(--spacing-sm) var(--spacing-md)",
              border: `1px solid ${fieldErrors.version ? "#e65100" : "var(--color-border)"}`,
              borderRadius: "var(--radius-md)",
              fontSize: "0.9rem",
            }}
          />
          {fieldErrors.version && (
            <div style={{ color: "#e65100", fontSize: "0.8rem", marginTop: "var(--spacing-xs)" }}>
              {fieldErrors.version}
            </div>
          )}
        </div>

        <div style={{ marginBottom: "var(--spacing-md)" }}>
          <label style={{ display: "block", fontWeight: 600, marginBottom: "var(--spacing-xs)", fontSize: "0.9rem" }}>
            Description
          </label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
            style={{
              width: "100%",
              padding: "var(--spacing-sm) var(--spacing-md)",
              border: "1px solid var(--color-border)",
              borderRadius: "var(--radius-md)",
              fontSize: "0.9rem",
              resize: "vertical",
            }}
          />
        </div>

        <div style={{ marginBottom: "var(--spacing-md)" }}>
          <label htmlFor="analysis-entrypoint" style={{ display: "block", fontWeight: 600, marginBottom: "var(--spacing-xs)", fontSize: "0.9rem" }}>
            Entrypoint <span style={{ color: "#e65100" }}>*</span>
          </label>
          <input
            id="analysis-entrypoint"
            type="text"
            value={entrypoint}
            onChange={(e) => setEntrypoint(e.target.value)}
            placeholder="run.py"
            style={{
              width: "100%",
              padding: "var(--spacing-sm) var(--spacing-md)",
              border: `1px solid ${fieldErrors.entrypoint ? "#e65100" : "var(--color-border)"}`,
              borderRadius: "var(--radius-md)",
              fontSize: "0.9rem",
            }}
          />
          {fieldErrors.entrypoint && (
            <div style={{ color: "#e65100", fontSize: "0.8rem", marginTop: "var(--spacing-xs)" }}>
              {fieldErrors.entrypoint}
            </div>
          )}
        </div>

        <div style={{ marginBottom: "var(--spacing-md)" }}>
          <label htmlFor="analysis-interpreter" style={{ display: "block", fontWeight: 600, marginBottom: "var(--spacing-xs)", fontSize: "0.9rem" }}>
            Interpreter
          </label>
          <select
            id="analysis-interpreter"
            value={interpreter}
            onChange={(e) => setInterpreter(e.target.value)}
            style={{
              width: "100%",
              padding: "var(--spacing-sm) var(--spacing-md)",
              border: "1px solid var(--color-border)",
              borderRadius: "var(--radius-md)",
              fontSize: "0.9rem",
              background: "var(--color-bg)",
            }}
          >
            <option value="python">Python</option>
            <option value="shell">Shell</option>
            <option value="r">R</option>
          </select>
        </div>

        <div style={{ marginBottom: "var(--spacing-md)" }}>
          <label htmlFor="analysis-arguments" style={{ display: "block", fontWeight: 600, marginBottom: "var(--spacing-xs)", fontSize: "0.9rem" }}>
            Arguments
          </label>
          <input
            id="analysis-arguments"
            type="text"
            value={argumentsStr}
            onChange={(e) => setArgumentsStr(e.target.value)}
            placeholder="--verbose --output /output/results.csv"
            style={{
              width: "100%",
              padding: "var(--spacing-sm) var(--spacing-md)",
              border: "1px solid var(--color-border)",
              borderRadius: "var(--radius-md)",
              fontSize: "0.9rem",
            }}
          />
          <div style={{ color: "var(--color-text-secondary)", fontSize: "0.8rem", marginTop: "var(--spacing-xs)" }}>
            Optional CLI arguments passed to the entrypoint script.
          </div>
        </div>

        <div style={{ marginBottom: "var(--spacing-md)" }}>
          <label style={{ display: "block", fontWeight: 600, marginBottom: "var(--spacing-xs)", fontSize: "0.9rem" }}>
            Referenced Data Resources
          </label>
          {resources.length === 0 ? (
            <div style={{ color: "var(--color-text-secondary)", fontSize: "0.85rem" }}>
              No resources available for this project.
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-xs)" }}>
              {resources.map((r) => (
                <label
                  key={r.id}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "var(--spacing-sm)",
                    fontSize: "0.9rem",
                    cursor: "pointer",
                  }}
                >
                  <input
                    type="checkbox"
                    checked={selectedResources.includes(r.identifier)}
                    onChange={() => toggleResource(r.identifier)}
                  />
                  {r.name}
                  <span style={{ color: "var(--color-text-secondary)", fontSize: "0.8rem" }}>
                    ({r.identifier})
                  </span>
                </label>
              ))}
            </div>
          )}
        </div>

        <div style={{ marginBottom: "var(--spacing-md)" }}>
          <label htmlFor="analysis-build-strategy" style={{ display: "block", fontWeight: 600, marginBottom: "var(--spacing-xs)", fontSize: "0.9rem" }}>
            Build Strategy
          </label>
          <select
            id="analysis-build-strategy"
            value={buildStrategy}
            onChange={(e) => setBuildStrategy(e.target.value)}
            style={{
              width: "100%",
              padding: "var(--spacing-sm) var(--spacing-md)",
              border: "1px solid var(--color-border)",
              borderRadius: "var(--radius-md)",
              fontSize: "0.9rem",
              background: "var(--color-bg)",
            }}
          >
            <option value="institutional">Institutional Build</option>
            {user?.capabilities.includes("build.customize") && (
              <option value="custom">Custom Build</option>
            )}
          </select>
          {buildStrategy === "custom" && (
            <div style={{ color: "var(--color-text-secondary)", fontSize: "0.85rem", marginTop: "var(--spacing-sm)", lineHeight: 1.5, padding: "var(--spacing-sm)", border: "1px solid #e3f2fd", borderRadius: "var(--radius-md)", background: "#f5f9ff" }}>
              Include a <code>build/Dockerfile</code> in your Analysis Bundle ZIP to
              customise how the execution environment is built.
              The institutional base image is available as the <code>BASE_IMAGE</code> build argument.
            </div>
          )}
        </div>

        <div style={{ marginBottom: "var(--spacing-lg)" }}>
          <label htmlFor="analysis-bundle" style={{ display: "block", fontWeight: 600, marginBottom: "var(--spacing-xs)", fontSize: "0.9rem" }}>
            Analysis Bundle <span style={{ color: "#e65100" }}>*</span>
          </label>
          <input
            id="analysis-bundle"
            type="file"
            accept=".zip"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            style={{
              width: "100%",
              padding: "var(--spacing-sm) var(--spacing-md)",
              border: `1px solid ${fieldErrors.file ? "#e65100" : "var(--color-border)"}`,
              borderRadius: "var(--radius-md)",
              fontSize: "0.9rem",
            }}
          />
          {fieldErrors.file && (
            <div style={{ color: "#e65100", fontSize: "0.8rem", marginTop: "var(--spacing-xs)" }}>
              {fieldErrors.file}
            </div>
          )}
          <div style={{ color: "var(--color-text-secondary)", fontSize: "0.8rem", marginTop: "var(--spacing-xs)" }}>
            Upload a ZIP archive containing your analysis code (run.py etc.).
          </div>
        </div>

        <div style={{ display: "flex", gap: "var(--spacing-md)" }}>
          <button className="btn btn-primary" onClick={handleSubmit} disabled={saving}>
            {saving ? "Saving..." : "Save"}
          </button>
          <Link
            href={`/projects/${projectId}/analysis`}
            className="btn"
            style={{ textDecoration: "none" }}
          >
            Cancel
          </Link>
        </div>
      </div>
    </div>
  );
}
