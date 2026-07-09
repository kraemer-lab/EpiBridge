"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { getCurrentUser } from "@/lib/api";
import type { User } from "@/lib/api";
import styles from "./Sidebar.module.css";

const adminCapabilities = [
  "bundle.review",
  "output.review",
  "output.release",
  "user.manage",
  "data.manage",
  "environment.manage",
];

function hasAdminAccess(user: User): boolean {
  return user.capabilities.some((c) => adminCapabilities.includes(c));
}

const links = [
  { href: "/", label: "Dashboard" },
  { href: "/projects", label: "Projects" },
];

export default function Sidebar() {
  const pathname = usePathname();
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    getCurrentUser().then(setUser).catch(() => setUser(null));
  }, []);

  const showAdmin = user !== null && hasAdminAccess(user);

  return (
    <aside className={styles.sidebar}>
      <nav className={styles.nav}>
        {links.map((link) => (
          <Link
            key={link.href}
            href={link.href}
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
