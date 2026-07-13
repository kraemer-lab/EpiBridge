"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/AuthContext";
import styles from "./Sidebar.module.css";

const adminCapabilities = [
  "bundle.review",
  "output.review",
  "output.release",
  "user.manage",
  "data.manage",
  "environment.manage",
];

function hasAdminAccess(capabilities: string[]): boolean {
  return capabilities.some((c) => adminCapabilities.includes(c));
}

const links = [
  { href: "/", label: "Home" },
  { href: "/projects", label: "Projects" },
  { href: "/resources", label: "Resources" },
  { href: "/environments", label: "Environments" },
  { href: "/examples", label: "Examples" },
  { href: "/templates", label: "Templates" },
  { href: "/docs", label: "Documentation" },
];

export default function Sidebar() {
  const pathname = usePathname();
  const { user } = useAuth();

  const showAdmin =
    user !== null && hasAdminAccess(user.capabilities);

  return (
    <aside className={styles.sidebar}>
      <nav className={styles.nav}>
        {links.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            aria-label={link.href === "/resources" ? "Browse Data Resources" : undefined}
            className={`${styles.link} ${pathname === link.href ? styles.active : ""}`}
          >
            {link.label}
          </Link>
        ))}
        {showAdmin && (
          <Link
            href="/admin"
            className={`${styles.link} ${pathname.startsWith("/admin") ? styles.active : ""}`}
          >
            Admin
          </Link>
        )}
      </nav>
    </aside>
  );
}
