"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { AuditEvent, Project, getAuditEvents, getProject, getProjectResources, getProjectBundles } from "@/lib/api";

function eventLabel(eventType: string): string {
  const labels: Record<string, string> = {
    "project.created": "Project created",
    "project.member.added": "Member added",
    "project.member.removed": "Member removed",
    "project.resource.allocated": "Resource allocated",
    "project.resource.deallocated": "Resource deallocated",
    "bundle.created": "Analysis created",
    "bundle.submitted": "Analysis submitted",
    "bundle.approved": "Analysis approved",
    "bundle.rejected": "Analysis rejected",
    "bundle.superseded": "Analysis superseded",
    "execution.requested": "Execution requested",
    "execution.started": "Execution started",
    "execution.completed": "Execution completed",
    "execution.failed": "Execution failed",
    "output_set.created": "Output set created",
    "output_set.approved": "Output approved",
    "output_set.rejected": "Output rejected",
    "output_set.released": "Output released",
    "user.created": "User created",
  };
  return labels[eventType] || eventType;
}

function formatTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString();
}

export default function ProjectOverviewPage() {
  const params = useParams();
  const projectId = params.id as string;

  const [project, setProject] = useState<Project | null>(null);
  const [resourceCount, setResourceCount] = useState<number | null>(null);
  const [bundleCount, setBundleCount] = useState<number | null>(null);
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);
  const [auditLoading, setAuditLoading] = useState(true);

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

  useEffect(() => {
    setAuditLoading(true);
    getAuditEvents({ project_id: projectId, limit: 20 })
      .then((res) => setAuditEvents(res.items))
      .catch(() => setAuditEvents([]))
      .finally(() => setAuditLoading(false));
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

      {auditLoading ? (
        <div className="card empty-state">Loading...</div>
      ) : auditEvents.length === 0 ? (
        <div className="card empty-state">No recent activity.</div>
      ) : (
        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          <table className="table">
            <thead>
              <tr>
                <th>Event</th>
                <th>Actor</th>
                <th>Resource</th>
                <th>When</th>
              </tr>
            </thead>
            <tbody>
              {auditEvents.map((e) => (
                <tr key={e.id}>
                  <td style={{ fontWeight: 500 }}>{eventLabel(e.event_type)}</td>
                  <td style={{ color: "var(--color-text-secondary)", fontSize: "0.85rem" }}>
                    {e.actor_display_name}
                  </td>
                  <td style={{ color: "var(--color-text-secondary)", fontSize: "0.85rem" }}>
                    {e.resource_type}
                  </td>
                  <td style={{ color: "var(--color-text-secondary)", fontSize: "0.85rem" }}>
                    {formatTime(e.occurred_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
