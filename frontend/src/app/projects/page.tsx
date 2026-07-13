"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import {
  AnalysisBundle,
  ExecutionRequest,
  OutputSetListItem,
  Project,
  getProjects,
  getProjectBundles,
  getProjectExecutionRequests,
  getProjectOutputSets,
} from "@/lib/api";
import { useAuth } from "@/lib/AuthContext";
import ProjectDialog from "@/components/ProjectDialog";

interface ProjectCounts {
  draft: number;
  awaitingApproval: number;
  ready: number;
  running: number;
  awaitingRelease: number;
  released: number;
}

const STATES: {
  key: keyof ProjectCounts;
  label: string;
  section: string;
}[] = [
  { key: "draft", label: "Draft", section: "analysis" },
  { key: "awaitingApproval", label: "Awaiting Approval", section: "analysis" },
  { key: "ready", label: "Ready", section: "analysis" },
  { key: "running", label: "Running", section: "jobs" },
  { key: "awaitingRelease", label: "Awaiting Release", section: "outputs" },
  { key: "released", label: "Released", section: "outputs" },
];

function StateLink({
  count,
  label,
  href,
}: {
  count: number;
  label: string;
  href: string;
}) {
  return (
    <Link
      href={href}
      style={{
        color: count > 0 ? "var(--color-text)" : "var(--color-text-secondary)",
        textDecoration: "none",
        fontWeight: count > 0 ? 500 : 400,
      }}
      onMouseEnter={(e) => {
        (e.currentTarget as HTMLElement).style.textDecoration = "underline";
      }}
      onMouseLeave={(e) => {
        (e.currentTarget as HTMLElement).style.textDecoration = "none";
      }}
    >
      {count} {label}
    </Link>
  );
}

export default function ProjectsPage() {
  const { user } = useAuth();
  const [projects, setProjects] = useState<Project[]>([]);
  const [counts, setCounts] = useState<Record<string, ProjectCounts>>({});
  const [loading, setLoading] = useState(true);
  const [showDialog, setShowDialog] = useState(false);
  const canCreate = user?.capabilities.includes("project.manage");

  const loadProjects = useCallback(async () => {
    setLoading(true);
    try {
      const projectList = await getProjects();
      setProjects(projectList);

      const results = await Promise.allSettled(
        projectList.map(async (project) => {
          const [bundles, executions, outputSets] = await Promise.all([
            getProjectBundles(project.id).catch(() => [] as AnalysisBundle[]),
            getProjectExecutionRequests(project.id).catch(
              () => [] as ExecutionRequest[],
            ),
            getProjectOutputSets(project.id).catch(
              () => [] as OutputSetListItem[],
            ),
          ]);

          return {
            id: project.id,
            draft: bundles.filter((b) => b.status === "draft").length,
            awaitingApproval: bundles.filter((b) => b.status === "submitted")
              .length,
            ready: bundles.filter(
              (b) => b.status === "approved_for_execution",
            ).length,
            running: executions.filter(
              (e) => e.status === "pending" || e.status === "running",
            ).length,
            awaitingRelease: outputSets.filter(
              (o) => o.status === "pending_review" || o.status === "approved",
            ).length,
            released: outputSets.filter((o) => o.status === "released").length,
          };
        }),
      );

      const countMap: Record<string, ProjectCounts> = {};
      for (const result of results) {
        if (result.status === "fulfilled") {
          countMap[result.value.id] = result.value;
        }
      }
      setCounts(countMap);
    } catch {
      setProjects([]);
      setCounts({});
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadProjects();
  }, [loadProjects]);

  return (
    <>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "var(--spacing-lg)",
        }}
      >
        <h1 className="page-title" style={{ marginBottom: 0 }}>
          Projects
        </h1>
        {canCreate && (
          <button
            className="btn btn-primary"
            onClick={() => setShowDialog(true)}
          >
            Create Project
          </button>
        )}
      </div>

      {projects.length === 0 ? (
        <div className="card empty-state">
          {loading
            ? "Loading..."
            : "No projects yet. Click \u201CCreate Project\u201D to get started."}
        </div>
      ) : (
        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          <table className="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Activity</th>
              </tr>
            </thead>
            <tbody>
              {projects.map((project) => {
                const c = counts[project.id];
                return (
                  <tr key={project.id}>
                    <td style={{ fontWeight: 500, whiteSpace: "nowrap" }}>
                      <Link
                        href={`/projects/${project.id}`}
                        style={{
                          color: "var(--color-primary)",
                          textDecoration: "none",
                        }}
                      >
                        {project.name}
                      </Link>
                    </td>
                    <td
                      style={{
                        fontSize: "0.85rem",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {c ? (
                        <span
                          style={{
                            display: "inline-flex",
                            gap: "0.5rem",
                            alignItems: "center",
                          }}
                        >
                          {STATES.map((state, i) => (
                            <span key={state.key}>
                              {i > 0 && (
                                <span
                                  style={{
                                    color: "var(--color-text-secondary)",
                                    marginRight: "0.5rem",
                                  }}
                                >
                                  ·
                                </span>
                              )}
                              <StateLink
                                count={c[state.key]}
                                label={state.label}
                                href={`/projects/${project.id}/${state.section}`}
                              />
                            </span>
                          ))}
                        </span>
                      ) : (
                        <span style={{ color: "var(--color-text-secondary)" }}>
                          Loading...
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
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
