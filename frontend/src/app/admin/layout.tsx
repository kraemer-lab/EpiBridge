"use client";

import Link from "next/link";
import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/AuthContext";

interface AdminTab {
  href: string;
  label: string;
  requiredCapability: string;
}

const adminTabs: AdminTab[] = [
  { href: "/admin", label: "Data Resources", requiredCapability: "data.manage" },
  { href: "/admin/environments", label: "Environments", requiredCapability: "environment.manage" },
  { href: "/admin/bundles", label: "Submissions", requiredCapability: "bundle.review" },
  { href: "/admin/executions", label: "Executions", requiredCapability: "bundle.review" },
  { href: "/admin/outputs", label: "Outputs", requiredCapability: "output.review" },
  { href: "/admin/terms", label: "Terms", requiredCapability: "terms.manage" },
  { href: "/admin/audit", label: "Audit Log", requiredCapability: "bundle.review" },
  { href: "/admin/users", label: "Users", requiredCapability: "user.manage" },
  { href: "/admin/settings", label: "Settings", requiredCapability: "settings.manage" },
];

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user } = useAuth();

  const visibleTabs = user !== null
    ? adminTabs.filter((tab) => user.capabilities.includes(tab.requiredCapability))
    : [];

  useEffect(() => {
    if (pathname === "/admin" && visibleTabs.length > 0) {
      router.replace(visibleTabs[0].href);
    }
  }, [pathname, visibleTabs, router]);

  const baseStyle: React.CSSProperties = {
    display: "flex",
    gap: "var(--spacing-md)",
    marginBottom: "var(--spacing-lg)",
    borderBottom: "1px solid var(--color-border)",
    paddingBottom: "var(--spacing-sm)",
  };

  return (
    <div>
      <h1 className="page-title">Admin</h1>

      {visibleTabs.length > 0 && (
        <nav style={baseStyle} aria-label="Admin tabs">
          {visibleTabs.map((tab) => {
            const isActive = pathname === tab.href;
            return (
              <Link
                key={tab.href}
                href={tab.href}
                style={{
                  color: isActive ? "var(--color-primary)" : "var(--color-text-secondary)",
                  fontWeight: isActive ? 600 : 500,
                  fontSize: "0.9rem",
                  textDecoration: "none",
                  paddingBottom: "var(--spacing-sm)",
                  borderBottom: isActive ? "2px solid var(--color-primary)" : "2px solid transparent",
                }}
              >
                {tab.label}
              </Link>
            );
          })}
        </nav>
      )}

      {children}
    </div>
  );
}
