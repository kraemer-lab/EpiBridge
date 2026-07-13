"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, usePathname } from "next/navigation";
import { Project, getProject } from "@/lib/api";

const tabs = [
  { href: "", label: "Overview" },
  { href: "/resources", label: "Resources" },
  { href: "/analysis", label: "Analysis" },
  { href: "/jobs", label: "Jobs" },
  { href: "/outputs", label: "Outputs" },
  { href: "/members", label: "Members" },
];

export default function ProjectLayout({ children }: { children: React.ReactNode }) {
  const params = useParams();
  const pathname = usePathname();
  const projectId = params.id as string;

  const [project, setProject] = useState<Project | null>(null);

  useEffect(() => {
    getProject(projectId).then(setProject).catch(() => setProject(null));
  }, [projectId]);

  const basePath = `/projects/${projectId}`;

  return (
    <div>
      <div style={{ marginBottom: "var(--spacing-lg)" }}>
        <Link
          href="/projects"
          style={{ color: "var(--color-text-secondary)", fontSize: "0.85rem", textDecoration: "none" }}
        >
          &larr; Projects
        </Link>
        <h1 className="page-title" style={{ marginTop: "var(--spacing-xs)", marginBottom: 0 }}>
          {project?.name ?? "Loading..."}
        </h1>
      </div>

      <nav
        style={{
          display: "flex",
          gap: 0,
          borderBottom: "1px solid var(--color-border)",
          marginBottom: "var(--spacing-lg)",
        }}
      >
        {tabs.map((tab) => {
          const tabHref = tab.href === "" ? basePath : `${basePath}${tab.href}`;
          const isActive = pathname === tabHref || (tab.href !== "" && pathname.startsWith(tabHref));
          return (
            <Link
              key={tab.href}
              href={tabHref}
              style={{
                padding: "var(--spacing-sm) var(--spacing-md)",
                fontSize: "0.9rem",
                fontWeight: isActive ? 600 : 500,
                color: isActive ? "var(--color-primary)" : "var(--color-text-secondary)",
                textDecoration: "none",
                borderBottom: isActive ? "2px solid var(--color-primary)" : "2px solid transparent",
                marginBottom: "-1px",
                transition: "color 0.15s, border-color 0.15s",
              }}
            >
              {tab.label}
            </Link>
          );
        })}
      </nav>

      {children}
    </div>
  );
}
