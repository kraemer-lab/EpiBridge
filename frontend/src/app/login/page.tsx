"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getCurrentUser, login } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getCurrentUser()
      .then(() => router.push("/"))
      .catch(() => setLoading(false));
  }, [router]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    try {
      await login(email, password);
      router.push("/");
    } catch {
      setError("Invalid email or password");
    }
  }

  if (loading) {
    return null;
  }

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        minHeight: "100vh",
      }}
    >
      <div className="card" style={{ width: 360 }}>
        <h1 style={{ fontSize: "1.5rem", fontWeight: 600, marginBottom: "var(--spacing-lg)" }}>
          EpiBridge
        </h1>
        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: "var(--spacing-md)" }}>
            <label
              htmlFor="email"
              style={{ display: "block", marginBottom: "var(--spacing-xs)", fontWeight: 500 }}
            >
              Email
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoFocus
              style={{
                width: "100%",
                padding: "var(--spacing-sm) var(--spacing-md)",
                border: "1px solid var(--color-border)",
                borderRadius: "var(--radius-md)",
              }}
            />
          </div>
          <div style={{ marginBottom: "var(--spacing-md)" }}>
            <label
              htmlFor="password"
              style={{ display: "block", marginBottom: "var(--spacing-xs)", fontWeight: 500 }}
            >
              Password
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              style={{
                width: "100%",
                padding: "var(--spacing-sm) var(--spacing-md)",
                border: "1px solid var(--color-border)",
                borderRadius: "var(--radius-md)",
              }}
            />
          </div>
          {error && (
            <div
              style={{
                color: "#dc3545",
                marginBottom: "var(--spacing-md)",
                fontSize: "0.9rem",
              }}
            >
              {error}
            </div>
          )}
          <button
            type="submit"
            className="btn btn-primary"
            style={{ width: "100%", justifyContent: "center" }}
          >
            Sign in
          </button>
        </form>
      </div>
    </div>
  );
}
