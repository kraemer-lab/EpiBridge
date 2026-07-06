"use client";

import { useEffect, useState } from "react";
import { User, getCurrentUser } from "@/lib/api";
import styles from "./Header.module.css";

export default function Header() {
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    getCurrentUser()
      .then(setUser)
      .catch(() => setUser(null));
  }, []);

  return (
    <header className={styles.header}>
      <span className={styles.brand}>EpiBridge</span>
      <div className={styles.user}>
        {user ? (
          <>
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
