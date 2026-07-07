"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import Header from "@/components/Header";
import Sidebar from "@/components/Sidebar";
import { getCurrentUser } from "@/lib/api";
import "./globals.css";

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    if (pathname === "/login") {
      setChecking(false);
      return;
    }
    getCurrentUser()
      .then(() => setChecking(false))
      .catch(() => {
        router.push("/login");
      });
  }, [pathname, router]);

  if (checking) {
    return (
      <html lang="en">
        <body>
          <div className="app-layout">
            <main className="app-main" style={{ marginLeft: 0 }}>
              <div className="app-content" />
            </main>
          </div>
        </body>
      </html>
    );
  }

  if (pathname === "/login") {
    return (
      <html lang="en">
        <body>{children}</body>
      </html>
    );
  }

  return (
    <html lang="en">
      <body>
        <div className="app-layout">
          <Header />
          <Sidebar />
          <main className="app-main">
            <div className="app-content">{children}</div>
          </main>
        </div>
      </body>
    </html>
  );
}
