"use client";

import { useEffect, useState } from "react";
import { AuditEvent, DashboardStats, getAuditEvents, getDashboardStats } from "@/lib/api";

function formatTime(iso: string): string {
  return new Date(iso).toLocaleString();
}

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [recentEvents, setRecentEvents] = useState<AuditEvent[]>([]);
  const [eventsLoading, setEventsLoading] = useState(true);

  useEffect(() => {
    getDashboardStats()
      .then(setStats)
      .catch(() => setStats(null));
  }, []);

  useEffect(() => {
    setEventsLoading(true);
    getAuditEvents({ limit: 10 })
      .then((res) => setRecentEvents(res.items))
      .catch(() => setRecentEvents([]))
      .finally(() => setEventsLoading(false));
  }, []);

  return (
    <>
      <h1 className="page-title">Dashboard</h1>

      <div style={{ display: "flex", gap: "var(--spacing-md)", marginBottom: "var(--spacing-xl)" }}>
        <div className="card" style={{ flex: 1 }}>
          <div style={{ fontSize: "0.8rem", color: "var(--color-text-secondary)", marginBottom: "var(--spacing-xs)" }}>
            Projects
          </div>
          <div style={{ fontSize: "2rem", fontWeight: 700 }}>
            {stats ? stats.projects : "—"}
          </div>
        </div>
        <div className="card" style={{ flex: 1 }}>
          <div style={{ fontSize: "0.8rem", color: "var(--color-text-secondary)", marginBottom: "var(--spacing-xs)" }}>
            Jobs
          </div>
          <div style={{ fontSize: "2rem", fontWeight: 700 }}>
            {stats ? stats.jobs : "—"}
          </div>
        </div>
        <div className="card" style={{ flex: 1 }}>
          <div style={{ fontSize: "0.8rem", color: "var(--color-text-secondary)", marginBottom: "var(--spacing-xs)" }}>
            Outputs
          </div>
          <div style={{ fontSize: "2rem", fontWeight: 700 }}>
            {stats ? stats.outputs : "—"}
          </div>
        </div>
      </div>

      <h2 style={{ fontSize: "1.1rem", fontWeight: 600, marginBottom: "var(--spacing-md)" }}>
        Recent Activity
      </h2>
      {eventsLoading ? (
        <div className="card empty-state">Loading...</div>
      ) : recentEvents.length === 0 ? (
        <div className="card empty-state">No recent activity.</div>
      ) : (
        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          <table className="table">
            <thead>
              <tr>
                <th>Event</th>
                <th>Actor</th>
                <th>When</th>
              </tr>
            </thead>
            <tbody>
              {recentEvents.map((e) => (
                <tr key={e.id}>
                  <td style={{ fontWeight: 500, fontSize: "0.9rem" }}>
                    <span
                      style={{
                        display: "inline-block",
                        padding: "2px 8px",
                        borderRadius: "4px",
                        fontSize: "0.8rem",
                        fontWeight: 600,
                        background: "#f0f4ff",
                        color: "#1565c0",
                      }}
                    >
                      {e.event_type}
                    </span>
                  </td>
                  <td style={{ color: "var(--color-text-secondary)", fontSize: "0.85rem" }}>
                    {e.actor_display_name}
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
    </>
  );
}
