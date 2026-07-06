"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Project, getProject } from "@/lib/api";

export default function ProjectSettingsPage() {
  const params = useParams();
  const projectId = params.id as string;

  const [project, setProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getProject(projectId)
      .then(setProject)
      .catch(() => setProject(null))
      .finally(() => setLoading(false));
  }, [projectId]);

  return (
    <div>
      <h2 style={{ fontSize: "1.1rem", fontWeight: 600, marginBottom: "var(--spacing-md)" }}>
        Settings
      </h2>

      {loading ? (
        <div className="card empty-state">Loading...</div>
      ) : !project ? (
        <div className="card empty-state">Failed to load project.</div>
      ) : (
        <div className="card" style={{ maxWidth: "600px" }}>
          <div style={{ marginBottom: "var(--spacing-md)" }}>
            <div style={{ fontSize: "0.8rem", color: "var(--color-text-secondary)", marginBottom: "var(--spacing-xs)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>
              Name
            </div>
            <div>{project.name}</div>
          </div>
          <div style={{ marginBottom: "var(--spacing-md)" }}>
            <div style={{ fontSize: "0.8rem", color: "var(--color-text-secondary)", marginBottom: "var(--spacing-xs)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>
              Description
            </div>
            <div>{project.description || "—"}</div>
          </div>
          <div style={{ marginBottom: "var(--spacing-md)" }}>
            <div style={{ fontSize: "0.8rem", color: "var(--color-text-secondary)", marginBottom: "var(--spacing-xs)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>
              Created
            </div>
            <div>{new Date(project.created_at).toLocaleDateString()}</div>
          </div>
          <div>
            <div style={{ fontSize: "0.8rem", color: "var(--color-text-secondary)", marginBottom: "var(--spacing-xs)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>
              Updated
            </div>
            <div>{new Date(project.updated_at).toLocaleDateString()}</div>
          </div>
        </div>
      )}
    </div>
  );
}
