"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  DataResource,
  ExecutionEnvironment,
  AnalysisBundle,
  getProjectBundle,
  getProjectResources,
  updateProjectBundle,
  getExecutionEnvironments,
} from "@/lib/api";

export default function EditAnalysisPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.id as string;
  const bundleId = params.bundle_id as string;

  const [resources, setResources] = useState<DataResource[]>([]);
  const [environments, setEnvironments] = useState<ExecutionEnvironment[]>([]);
  const [bundle, setBundle] = useState<AnalysisBundle | null>(null);
  const [loading, setLoading] = useState(true);
  const [name, setName] = useState("");
  const [selectedEnvId, setSelectedEnvId] = useState("");
  const [version, setVersion] = useState("");
  const [description, setDescription] = useState("");
  const [entrypoint, setEntrypoint] = useState("");
  const [interpreter, setInterpreter] = useState("python");
  const [argumentsStr, setArgumentsStr] = useState("");
  const [selectedResources, setSelectedResources] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    Promise.all([
      getProjectBundle(projectId, bundleId),
      getProjectResources(projectId),
      getExecutionEnvironments(),
    ])
      .then(([b, res, envs]) => {
        setBundle(b);
        setName(b.name);
        setVersion(b.version);
        setDescription(b.description);
        setEntrypoint(b.entrypoint);
        setInterpreter(b.interpreter || "python");
        setArgumentsStr(b.arguments || "");
        setSelectedResources(b.resource_identifiers);
        setResources(res);
        setEnvironments(envs);
        if (b.execution_environment_id) {
          setSelectedEnvId(b.execution_environment_id);
        } else if (envs.length > 0) {
          setSelectedEnvId(envs[0].id);
        }
      })
      .catch(() => setFieldErrors({ form: "Failed to load analysis bundle." }))
      .finally(() => setLoading(false));
  }, [projectId, bundleId]);

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
    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async () => {
    if (!validate()) return;

    setSaving(true);
    try {
      await updateProjectBundle(projectId, bundleId, {
        name: name.trim(),
        execution_environment_id: selectedEnvId || undefined,
        version: version.trim(),
        entrypoint: entrypoint.trim(),
        interpreter,
        arguments: argumentsStr.trim(),
        description: description.trim(),
        resource_identifiers: selectedResources,
      });
      router.push(`/projects/${projectId}/analysis/${bundleId}`);
    } catch {
      setFieldErrors({ form: "Failed to update analysis bundle." });
      setSaving(false);
    }
  };

  if (loading) return <div className="card empty-state">Loading...</div>;

  return (
    <div>
      <Link
        href={`/projects/${projectId}/analysis/${bundleId}`}
        style={{ color: "var(--color-text-secondary)", fontSize: "0.85rem", textDecoration: "none" }}
      >
        &larr; Back to Analysis
      </Link>
      <h2 style={{ fontSize: "1.1rem", fontWeight: 600, marginTop: "var(--spacing-md)", marginBottom: "var(--spacing-lg)" }}>
        Continue Editing
      </h2>

      <div className="card" style={{ maxWidth: "640px" }}>
        {fieldErrors.form && (
          <div style={{ color: "#e65100", marginBottom: "var(--spacing-md)", fontSize: "0.9rem" }}>
            {fieldErrors.form}
          </div>
        )}

        <div style={{ marginBottom: "var(--spacing-md)" }}>
          <label style={{ display: "block", fontWeight: 600, marginBottom: "var(--spacing-xs)", fontSize: "0.9rem" }}>
            Name <span style={{ color: "#e65100" }}>*</span>
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
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
          <label style={{ display: "block", fontWeight: 600, marginBottom: "var(--spacing-xs)", fontSize: "0.9rem" }}>
            Execution Environment
          </label>
          <select
            value={selectedEnvId}
            onChange={(e) => setSelectedEnvId(e.target.value)}
            style={{
              width: "100%",
              padding: "var(--spacing-sm) var(--spacing-md)",
              border: "1px solid var(--color-border)",
              borderRadius: "var(--radius-md)",
              fontSize: "0.9rem",
              background: "var(--color-bg)",
            }}
          >
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
        </div>

        <div style={{ marginBottom: "var(--spacing-md)" }}>
          <label style={{ display: "block", fontWeight: 600, marginBottom: "var(--spacing-xs)", fontSize: "0.9rem" }}>
            Version <span style={{ color: "#e65100" }}>*</span>
          </label>
          <input
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
          <label style={{ display: "block", fontWeight: 600, marginBottom: "var(--spacing-xs)", fontSize: "0.9rem" }}>
            Entrypoint <span style={{ color: "#e65100" }}>*</span>
          </label>
          <input
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
          <label htmlFor="edit-interpreter" style={{ display: "block", fontWeight: 600, marginBottom: "var(--spacing-xs)", fontSize: "0.9rem" }}>
            Interpreter
          </label>
          <select
            id="edit-interpreter"
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
          <label htmlFor="edit-arguments" style={{ display: "block", fontWeight: 600, marginBottom: "var(--spacing-xs)", fontSize: "0.9rem" }}>
            Arguments
          </label>
          <input
            id="edit-arguments"
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

        <div style={{ display: "flex", gap: "var(--spacing-md)" }}>
          <button className="btn btn-primary" onClick={handleSubmit} disabled={saving}>
            {saving ? "Saving..." : "Save"}
          </button>
          <Link
            href={`/projects/${projectId}/analysis/${bundleId}`}
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
