"use client";

import { useEffect, useState } from "react";
import { User, UserCreate, createUser, getUsers } from "@/lib/api";

export default function AdminUsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [showForm, setShowForm] = useState(false);
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("researcher");
  const [creating, setCreating] = useState(false);

  const load = () => {
    setLoading(true);
    getUsers()
      .then(setUsers)
      .catch(() => setError("Failed to load users"))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const handleCreate = async () => {
    if (!email.trim() || !displayName.trim() || !password.trim()) return;
    setCreating(true);
    setError(null);
    try {
      const data: UserCreate = { email: email.trim(), display_name: displayName.trim(), password, role };
      await createUser(data);
      setEmail("");
      setDisplayName("");
      setPassword("");
      setRole("researcher");
      setShowForm(false);
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to create user");
    } finally {
      setCreating(false);
    }
  };

  return (
    <>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "var(--spacing-md)" }}>
        <h2 style={{ fontSize: "1.1rem", fontWeight: 600, margin: 0 }}>
          Users
        </h2>
        <button onClick={() => setShowForm(!showForm)}>
          {showForm ? "Cancel" : "Create User"}
        </button>
      </div>

      {error && (
        <div className="card" style={{ background: "var(--color-error-bg, #fdecea)", color: "var(--color-error, #d32f2f)", marginBottom: "var(--spacing-md)", padding: "var(--spacing-sm)" }}>
          {error}
        </div>
      )}

      {showForm && (
        <div className="card" style={{ marginBottom: "var(--spacing-lg)" }}>
          <div style={{ display: "grid", gap: "var(--spacing-sm)", gridTemplateColumns: "1fr 1fr" }}>
            <div>
              <label style={{ display: "block", fontSize: "0.85rem", fontWeight: 500, marginBottom: "4px" }}>Email</label>
              <input type="email" placeholder="user@institution.org" value={email} onChange={(e) => setEmail(e.target.value)} style={{ width: "100%" }} />
            </div>
            <div>
              <label style={{ display: "block", fontSize: "0.85rem", fontWeight: 500, marginBottom: "4px" }}>Display Name</label>
              <input type="text" placeholder="Jane Researcher" value={displayName} onChange={(e) => setDisplayName(e.target.value)} style={{ width: "100%" }} />
            </div>
            <div>
              <label style={{ display: "block", fontSize: "0.85rem", fontWeight: 500, marginBottom: "4px" }}>Password</label>
              <input type="password" placeholder="Initial password" value={password} onChange={(e) => setPassword(e.target.value)} style={{ width: "100%" }} />
            </div>
            <div>
              <label style={{ display: "block", fontSize: "0.85rem", fontWeight: 500, marginBottom: "4px" }}>Role</label>
              <select value={role} onChange={(e) => setRole(e.target.value)} style={{ width: "100%" }}>
                <option value="researcher">Researcher</option>
                <option value="moderator">Moderator</option>
                <option value="maintainer">Maintainer</option>
                <option value="admin">Administrator</option>
              </select>
            </div>
          </div>
          <div style={{ marginTop: "var(--spacing-md)" }}>
            <button onClick={handleCreate} disabled={creating || !email.trim() || !displayName.trim() || !password.trim()}>
              {creating ? "Creating..." : "Create User"}
            </button>
          </div>
        </div>
      )}

      {loading ? (
        <div className="card empty-state">Loading...</div>
      ) : users.length === 0 ? (
        <div className="card empty-state">No users found.</div>
      ) : (
        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          <table className="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Role</th>
                <th>Capabilities</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id}>
                  <td style={{ fontWeight: 500 }}>{u.display_name}</td>
                  <td style={{ color: "var(--color-text-secondary)" }}>{u.email}</td>
                  <td>
                    <span style={{
                      display: "inline-block",
                      padding: "2px 8px",
                      borderRadius: "4px",
                      fontSize: "0.8rem",
                      fontWeight: 600,
                      background: u.role === "admin" ? "var(--color-primary-bg, #e3f2fd)" : "var(--color-bg-secondary, #f5f5f5)",
                      color: u.role === "admin" ? "var(--color-primary, #1976d2)" : "var(--color-text-secondary)",
                    }}>
                      {u.role}
                    </span>
                  </td>
                  <td style={{ fontSize: "0.8rem", color: "var(--color-text-secondary)", maxWidth: "300px", overflow: "hidden", textOverflow: "ellipsis" }}>
                    {(u.capabilities || []).join(", ")}
                  </td>
                  <td style={{ color: "var(--color-text-secondary)", fontSize: "0.85rem" }}>
                    {new Date(u.created_at).toLocaleDateString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
