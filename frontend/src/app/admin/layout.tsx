"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const adminTabs = [
  { href: "/admin", label: "Data Resources" },
  { href: "/admin/bundles", label: "Analysis Bundles" },
  { href: "/admin/outputs", label: "Outputs" },
  { href: "/admin/audit", label: "Audit Log" },
  { href: "/admin/users", label: "Users" },
];

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div>
      <h1 className="page-title">Admin</h1>

      <nav style={{ display: "flex", gap: "var(--spacing-md)", marginBottom: "var(--spacing-lg)", borderBottom: "1px solid var(--color-border)", paddingBottom: "var(--spacing-sm)" }}>
        {adminTabs.map((tab) => {
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

      {children}
    </div>
  );
}
