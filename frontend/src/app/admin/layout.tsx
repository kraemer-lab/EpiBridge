"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { getCurrentUser } from "@/lib/api";
import type { User } from "@/lib/api";

interface AdminTab {
  href: string;
  label: string;
  requiredCapability: string;
}

const adminTabs: AdminTab[] = [
  { href: "/admin", label: "Data Resources", requiredCapability: "data.manage" },
  { href: "/admin/bundles", label: "Analysis Bundles", requiredCapability: "bundle.review" },
  { href: "/admin/outputs", label: "Outputs", requiredCapability: "output.review" },
  { href: "/admin/audit", label: "Audit Log", requiredCapability: "bundle.review" },
  { href: "/admin/users", label: "Users", requiredCapability: "user.manage" },
];

function hasCapability(user: User, capability: string): boolean {
  return user.capabilities.includes(capability);
}

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    getCurrentUser().then(setUser).catch(() => setUser(null));
  }, []);

  const visibleTabs = user !== null
    ? adminTabs.filter((tab) => hasCapability(user, tab.requiredCapability))
    : [];

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
        <nav style={baseStyle}>
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
