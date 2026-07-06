"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Project, getProject, getProjectResources, getProjectBundles } from "@/lib/api";

export default function ProjectOverviewPage() {
  const params = useParams();
  const projectId = params.id as string;

  const [project, setProject] = useState<Project | null>(null);
  const [resourceCount, setResourceCount] = useState<number | null>(null);
  const [bundleCount, setBundleCount] = useState<number | null>(null);

  useEffect(() => {
    getProject(projectId)
      .then(setProject)
      .catch(() => setProject(null));
  }, [projectId]);

  useEffect(() => {
    getProjectResources(projectId)
      .then((res) => setResourceCount(res.length))
      .catch(() => setResourceCount(null));
  }, [projectId]);

  useEffect(() => {
    getProjectBundles(projectId)
      .then((res) => setBundleCount(res.length))
      .catch(() => setBundleCount(null));
  }, [projectId]);

  return (
    <div>
      <div className="card" style={{ marginBottom: "var(--spacing-lg)" }}>
        <h2 style={{ fontSize: "1.1rem", fontWeight: 600, marginBottom: "var(--spacing-sm)" }}>
          Description
        </h2>
        <p style={{ color: "var(--color-text-secondary)", lineHeight: 1.6 }}>
          {project?.description || "No description provided."}
        </p>
      </div>

      <div style={{ display: "flex", gap: "var(--spacing-md)", marginBottom: "var(--spacing-xl)" }}>
        <div className="card" style={{ flex: 1 }}>
          <div style={{ fontSize: "0.8rem", color: "var(--color-text-secondary)", marginBottom: "var(--spacing-xs)" }}>
            Data Resources
          </div>
          <div style={{ fontSize: "2rem", fontWeight: 700 }}>
            {resourceCount !== null ? resourceCount : "—"}
          </div>
        </div>
        <div className="card" style={{ flex: 1 }}>
          <div style={{ fontSize: "0.8rem", color: "var(--color-text-secondary)", marginBottom: "var(--spacing-xs)" }}>
            Analysis Bundles
          </div>
          <div style={{ fontSize: "2rem", fontWeight: 700 }}>
            {bundleCount !== null ? bundleCount : "—"}
          </div>
        </div>
        <div className="card" style={{ flex: 1 }}>
          <div style={{ fontSize: "0.8rem", color: "var(--color-text-secondary)", marginBottom: "var(--spacing-xs)" }}>
            Jobs
          </div>
          <div style={{ fontSize: "2rem", fontWeight: 700 }}>0</div>
        </div>
      </div>

      <h2 style={{ fontSize: "1.1rem", fontWeight: 600, marginBottom: "var(--spacing-md)" }}>
        Recent Activity
      </h2>
      <div className="card empty-state">
        No recent activity.
      </div>
    </div>
  );
}
