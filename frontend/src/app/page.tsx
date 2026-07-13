"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/AuthContext";
import {
  AnalysisBundle,
  getProjects,
  getProjectBundles,
  getAdminBundles,
  getAdminOutputSets,
  getAdminExecutionRequests,
  getAdminTermsStatus,
  getUsers,
} from "@/lib/api";

// ─── Role detection ──────────────────────────────────────────────────────
// Roles are assigned explicitly — they are not derived from capabilities.
// Each role maps to a homepage section.
// Users may hold multiple roles (additive).

// ─── Section model ───────────────────────────────────────────────────────

interface SectionItem {
  label: string;
  href: string;
  value: string | number;
}

interface SectionData {
  title: string;
  empty: boolean;
  emptyMessage: string;
  items: SectionItem[];
}

// ─── Data loading ────────────────────────────────────────────────────────

async function loadResearcher(): Promise<SectionData> {
  try {
    const projects = await getProjects();
    const bundleLists = await Promise.all(
      projects.map((p) =>
        getProjectBundles(p.id).catch(() => [] as AnalysisBundle[]),
      ),
    );
    const allBundles = bundleLists.flat();

    const draftCount = allBundles.filter(
      (b) => b.status === "draft",
    ).length;
    const submittedCount = allBundles.filter(
      (b) => b.status === "submitted",
    ).length;

    const items: SectionItem[] = [];
    if (draftCount > 0) {
      items.push({
        label: "Draft Bundles",
        href: "/projects",
        value: draftCount,
      });
    }
    if (submittedCount > 0) {
      items.push({
        label: "Awaiting Review",
        href: "/projects",
        value: submittedCount,
      });
    }
    items.push({
      label: "Projects",
      href: "/projects",
      value: projects.length,
    });

    return {
      title: "Research",
      empty: draftCount === 0 && submittedCount === 0,
      emptyMessage: "Nothing currently requires your attention.",
      items,
    };
  } catch {
    return {
      title: "Research",
      empty: true,
      emptyMessage: "Nothing currently requires your attention.",
      items: [],
    };
  }
}

async function loadModerator(): Promise<SectionData> {
  try {
    const bundles = await getAdminBundles();
    const submittedCount = bundles.filter(
      (b) => b.status === "submitted",
    ).length;

    const outputSets = await getAdminOutputSets();
    const pendingReviewCount = outputSets.filter(
      (o) => o.status === "pending_review",
    ).length;

    const items: SectionItem[] = [];
    if (submittedCount > 0) {
      items.push({
        label: "Submissions Awaiting Review",
        href: "/admin/bundles",
        value: submittedCount,
      });
    }
    if (pendingReviewCount > 0) {
      items.push({
        label: "Outputs Awaiting Review",
        href: "/admin/outputs",
        value: pendingReviewCount,
      });
    }

    return {
      title: "Moderation",
      empty: submittedCount === 0 && pendingReviewCount === 0,
      emptyMessage: "No items pending review.",
      items,
    };
  } catch {
    return {
      title: "Moderation",
      empty: true,
      emptyMessage: "No items pending review.",
      items: [],
    };
  }
}

async function loadMaintainer(): Promise<SectionData> {
  try {
    const bundles = await getAdminBundles();
    const buildFailures = bundles.filter(
      (b) => b.build_status === "environment_build_failed",
    ).length;

    const outputSets = await getAdminOutputSets();
    const pendingReleaseCount = outputSets.filter(
      (o) => o.status === "approved",
    ).length;

    const executions = await getAdminExecutionRequests();
    const runningCount = executions.filter(
      (e) => e.status === "pending" || e.status === "running",
    ).length;

    const items: SectionItem[] = [];
    if (buildFailures > 0) {
      items.push({
        label: "Build Failures",
        href: "/admin/bundles",
        value: buildFailures,
      });
    }
    if (pendingReleaseCount > 0) {
      items.push({
        label: "Pending Releases",
        href: "/admin/outputs",
        value: pendingReleaseCount,
      });
    }
    if (runningCount > 0) {
      items.push({
        label: "Running Executions",
        href: "/admin/executions",
        value: runningCount,
      });
    }

    return {
      title: "Operations",
      empty:
        buildFailures === 0 &&
        pendingReleaseCount === 0 &&
        runningCount === 0,
      emptyMessage: "All systems operational.",
      items,
    };
  } catch {
    return {
      title: "Operations",
      empty: true,
      emptyMessage: "All systems operational.",
      items: [],
    };
  }
}

async function loadAdministrator(): Promise<SectionData> {
  try {
    const termsStatus = await getAdminTermsStatus();
    const hasPlatformTerms = termsStatus.platform.current !== null;
    const resourcesWithoutTerms = termsStatus.resource_terms.filter(
      (r) => r.current === null,
    ).length;

    const users = await getUsers();

    const items: SectionItem[] = [];
    if (!hasPlatformTerms) {
      items.push({
        label: "Platform Terms",
        href: "/admin/terms",
        value: "Unpublished",
      });
    }
    if (resourcesWithoutTerms > 0) {
      items.push({
        label: "Resources Without Terms",
        href: "/admin/terms",
        value: resourcesWithoutTerms,
      });
    }
    if (hasPlatformTerms) {
      items.push({
        label: "Platform Terms",
        href: "/admin/terms",
        value: "Published",
      });
    }
    items.push({
      label: "Users",
      href: "/admin/users",
      value: users.length,
    });

    return {
      title: "Administration",
      empty: hasPlatformTerms && resourcesWithoutTerms === 0,
      emptyMessage: "Platform administration is up to date.",
      items,
    };
  } catch {
    return {
      title: "Administration",
      empty: true,
      emptyMessage: "Platform administration is up to date.",
      items: [],
    };
  }
}

// ─── Page component ──────────────────────────────────────────────────────

export default function HomePage() {
  const { user, loading: authLoading } = useAuth();
  const [sections, setSections] = useState<SectionData[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (authLoading || !user) return;

    const roles = user.roles || [user.role];
    const loaders: Promise<SectionData>[] = [];

    if (roles.includes("researcher")) loaders.push(loadResearcher());
    if (roles.includes("moderator")) loaders.push(loadModerator());
    if (roles.includes("maintainer")) loaders.push(loadMaintainer());
    if (roles.includes("admin")) loaders.push(loadAdministrator());

    if (loaders.length === 0) {
      setSections([]);
      setLoading(false);
      return;
    }

    Promise.all(loaders)
      .then(setSections)
      .catch(() => setSections([]))
      .finally(() => setLoading(false));
  }, [user, authLoading]);

  if (authLoading || loading) {
    return (
      <div className="card empty-state" style={{ marginTop: 0 }}>
        Loading...
      </div>
    );
  }

  return (
    <>
      <h1 className="page-title">Home</h1>
      <ArrivalSummary sections={sections} />
    </>
  );
}

// ─── Rendering ───────────────────────────────────────────────────────────

function ArrivalSummary({ sections }: { sections: SectionData[] }) {
  if (sections.length === 0) {
    return (
      <div className="card empty-state">Nothing currently requires your attention.</div>
    );
  }

  const allEmpty = sections.every((s) => s.empty);

  if (allEmpty) {
    return (
      <div className="card empty-state">Nothing currently requires your attention.</div>
    );
  }

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "var(--spacing-lg)",
      }}
    >
      {sections.map((s) => (
        <SectionCard key={s.title} section={s} />
      ))}
    </div>
  );
}

function SectionCard({ section }: { section: SectionData }) {
  if (section.empty) {
    return (
      <div className="card">
        <div
          style={{
            fontSize: "0.75rem",
            fontWeight: 600,
            textTransform: "uppercase",
            letterSpacing: "0.05em",
            color: "var(--color-text-secondary)",
            marginBottom: "var(--spacing-xs)",
          }}
        >
          {section.title}
        </div>
        <div
          style={{
            color: "var(--color-text-secondary)",
            fontSize: "0.9rem",
          }}
        >
          {section.emptyMessage}
        </div>
      </div>
    );
  }

  return (
    <div className="card" style={{ padding: 0, overflow: "hidden" }}>
      <div
        style={{
          padding: "var(--spacing-sm) var(--spacing-lg)",
          borderBottom: "1px solid var(--color-border)",
        }}
      >
        <div
          style={{
            fontSize: "0.75rem",
            fontWeight: 600,
            textTransform: "uppercase",
            letterSpacing: "0.05em",
            color: "var(--color-text-secondary)",
          }}
        >
          {section.title}
        </div>
      </div>
      {section.items.map((item, i) => (
        <Link
          key={item.label}
          href={item.href}
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            padding: "var(--spacing-sm) var(--spacing-lg)",
            borderBottom:
              i < section.items.length - 1
                ? "1px solid var(--color-border)"
                : "none",
            color: "var(--color-text)",
            textDecoration: "none",
            fontSize: "0.9rem",
            transition: "background 0.1s",
          }}
          onMouseEnter={(e) => {
            (e.currentTarget as HTMLElement).style.background =
              "var(--color-surface)";
          }}
          onMouseLeave={(e) => {
            (e.currentTarget as HTMLElement).style.background = "";
          }}
        >
          <span>{item.label}</span>
          <span
            style={{
              fontWeight: 600,
              color: "var(--color-primary)",
            }}
          >
            {item.value}
          </span>
        </Link>
      ))}
    </div>
  );
}
