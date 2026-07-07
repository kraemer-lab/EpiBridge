"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { User, getCurrentUser, logout } from "@/lib/api";
import styles from "./Header.module.css";

export default function Header() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    getCurrentUser()
      .then(setUser)
      .catch(() => setUser(null));
  }, []);

  async function handleLogout() {
    await logout();
    setUser(null);
    router.push("/login");
  }

  return (
    <header className={styles.header}>
      <span className={styles.brand}>EpiBridge</span>
      <div className={styles.user}>
        {user ? (
          <>
            <button
              onClick={handleLogout}
              style={{
                background: "none",
                border: "none",
                color: "var(--color-text-secondary)",
                cursor: "pointer",
                fontSize: "0.85rem",
                marginRight: "var(--spacing-sm)",
              }}
            >
              Sign out
            </button>
            <span>{user.display_name}</span>
            <div className={styles.avatar}>
              {user.display_name.charAt(0).toUpperCase()}
            </div>
          </>
        ) : (
          <span>Loading…</span>
        )}
      </div>
    </header>
  );
}
