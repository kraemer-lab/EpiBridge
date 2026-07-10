"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import Header from "@/components/Header";
import Sidebar from "@/components/Sidebar";
import { AuthProvider, useAuth } from "@/lib/AuthContext";
import "./globals.css";

function AuthGate({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, loading } = useAuth();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (pathname === "/login" || pathname === "/terms") {
      if (!loading && user && pathname !== "/terms") {
        router.push("/");
      }
      if (!loading) {
        setReady(true);
      }
      return;
    }
    if (!loading) {
      if (!user) {
        router.push("/login");
      } else if (user.needs_platform_terms_acceptance && pathname !== "/terms") {
        router.push("/terms");
      } else {
        setReady(true);
      }
    }
  }, [pathname, router, user, loading]);

  if (pathname === "/login" || pathname === "/terms") {
    return ready ? <>{children}</> : null;
  }

  if (!ready) {
    return (
      <div className="app-layout">
        <main className="app-main" style={{ marginLeft: 0 }}>
          <div className="app-content" />
        </main>
      </div>
    );
  }

  return (
    <div className="app-layout">
      <Header />
      <Sidebar />
      <main className="app-main">
        <div className="app-content">{children}</div>
      </main>
    </div>
  );
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>
          <AuthGate>{children}</AuthGate>
        </AuthProvider>
      </body>
    </html>
  );
}
