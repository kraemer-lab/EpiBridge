"use client";

import { useEffect, useState, useCallback } from "react";
import { Project, getProjects } from "@/lib/api";
import ProjectDialog from "@/components/ProjectDialog";

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [showDialog, setShowDialog] = useState(false);

  const loadProjects = useCallback(async () => {
    try {
      const data = await getProjects();
      setProjects(data);
    } catch {
      setProjects([]);
    }
  }, []);

  useEffect(() => {
    loadProjects();
  }, [loadProjects]);

  return (
    <>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "var(--spacing-lg)" }}>
        <h1 className="page-title" style={{ marginBottom: 0 }}>Projects</h1>
        <button className="btn btn-primary" onClick={() => setShowDialog(true)}>
          Create Project
        </button>
      </div>

      {projects.length === 0 ? (
        <div className="card empty-state">
          No projects yet. Click &ldquo;Create Project&rdquo; to get started.
        </div>
      ) : (
        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          <table className="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Description</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {projects.map((project) => (
                <tr key={project.id}>
                  <td style={{ fontWeight: 500 }}>{project.name}</td>
                  <td style={{ color: "var(--color-text-secondary)" }}>
                    {project.description || "—"}
                  </td>
                  <td style={{ color: "var(--color-text-secondary)" }}>
                    {new Date(project.created_at).toLocaleDateString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showDialog && (
        <ProjectDialog
          onClose={() => setShowDialog(false)}
          onCreated={loadProjects}
        />
      )}
    </>
  );
}
