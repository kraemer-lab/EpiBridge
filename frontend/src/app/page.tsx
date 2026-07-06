"use client";

import { useEffect, useState } from "react";
import { DashboardStats, getDashboardStats } from "@/lib/api";

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);

  useEffect(() => {
    getDashboardStats()
      .then(setStats)
      .catch(() => setStats(null));
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
      <div className="card empty-state">
        No recent activity.
      </div>
    </>
  );
}
